"""End-to-end tests for the contacts module — HTTP endpoint tests."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.contacts.models import Contact
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.schemas import GroupContext
from src.social.models import Profile

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def e2e_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def e2e_session(e2e_engine):
    async_session_maker = sessionmaker(
        e2e_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def e2e_users(e2e_session):
    """Create test users: parent, child (young), teen, and a target."""
    parent = User(
        id=uuid.uuid4(),
        email=f"parent-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child = User(
        id=uuid.uuid4(),
        email=f"child-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    teen = User(
        id=uuid.uuid4(),
        email=f"teen-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Teen",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    target = User(
        id=uuid.uuid4(),
        email=f"target-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Target",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add_all([parent, child, teen, target])
    await e2e_session.flush()

    # Create profiles
    today = datetime.now(timezone.utc).date()
    child_profile = Profile(
        id=uuid.uuid4(), user_id=child.id, display_name="Child",
        date_of_birth=today.replace(year=today.year - 7), age_tier="young",
        visibility="friends_only",
    )
    teen_profile = Profile(
        id=uuid.uuid4(), user_id=teen.id, display_name="Teen",
        date_of_birth=today.replace(year=today.year - 14), age_tier="teen",
        visibility="friends_only",
    )
    e2e_session.add_all([child_profile, teen_profile])
    await e2e_session.flush()

    # Create family group with parent and child
    group = Group(
        id=uuid.uuid4(), name="Test Family", type="family", owner_id=parent.id,
    )
    e2e_session.add(group)
    await e2e_session.flush()

    parent_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=parent.id,
        role="parent", display_name="Parent",
    )
    child_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=child.id,
        role="member", display_name="Child",
    )
    e2e_session.add_all([parent_member, child_member])
    await e2e_session.flush()

    return {
        "parent": parent, "child": child, "teen": teen,
        "target": target, "group": group,
    }


def _make_client(e2e_engine, e2e_session, user_id, group_id=None, role="parent"):
    """Create an authenticated test client for a specific user."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(user_id=user_id, group_id=group_id, role=role)

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest_asyncio.fixture
async def parent_client(e2e_engine, e2e_session, e2e_users):
    async with _make_client(
        e2e_engine, e2e_session, e2e_users["parent"].id,
        e2e_users["group"].id, "parent",
    ) as c:
        yield c


@pytest_asyncio.fixture
async def child_client(e2e_engine, e2e_session, e2e_users):
    async with _make_client(
        e2e_engine, e2e_session, e2e_users["child"].id,
        e2e_users["group"].id, "member",
    ) as c:
        yield c


@pytest_asyncio.fixture
async def teen_client(e2e_engine, e2e_session, e2e_users):
    async with _make_client(
        e2e_engine, e2e_session, e2e_users["teen"].id,
    ) as c:
        yield c


@pytest_asyncio.fixture
async def target_client(e2e_engine, e2e_session, e2e_users):
    async with _make_client(
        e2e_engine, e2e_session, e2e_users["target"].id,
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests — Send + Accept Flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_and_accept_flow(teen_client, target_client, e2e_users):
    """Full flow: teen sends request, target accepts."""
    target_id = str(e2e_users["target"].id)

    resp = await teen_client.post(f"/api/v1/contacts/request/{target_id}")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["parent_approval_status"] == "not_required"
    contact_id = data["id"]

    resp2 = await target_client.patch(
        f"/api/v1/contacts/{contact_id}/respond",
        json={"action": "accept"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_send_and_reject_flow(teen_client, target_client, e2e_users):
    """Full flow: teen sends request, target rejects."""
    target_id = str(e2e_users["target"].id)

    resp = await teen_client.post(f"/api/v1/contacts/request/{target_id}")
    assert resp.status_code == 201
    contact_id = resp.json()["id"]

    resp2 = await target_client.patch(
        f"/api/v1/contacts/{contact_id}/respond",
        json={"action": "reject"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "rejected"


# ---------------------------------------------------------------------------
# Tests — Parent Approval Flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_child_request_parent_approve_flow(
    child_client, target_client, parent_client, e2e_users,
):
    """Full flow: child sends request, parent approves, target accepts."""
    target_id = str(e2e_users["target"].id)

    # Child sends request
    resp = await child_client.post(f"/api/v1/contacts/request/{target_id}")
    assert resp.status_code == 201
    data = resp.json()
    assert data["parent_approval_status"] == "pending"
    contact_id = data["id"]

    # Target cannot accept yet (parent approval pending)
    resp2 = await target_client.patch(
        f"/api/v1/contacts/{contact_id}/respond",
        json={"action": "accept"},
    )
    assert resp2.status_code == 422

    # Parent approves
    resp3 = await parent_client.patch(
        f"/api/v1/contacts/{contact_id}/parent-approve",
        json={"decision": "approve"},
    )
    assert resp3.status_code == 200
    assert resp3.json()["decision"] == "approve"

    # Now target can accept
    resp4 = await target_client.patch(
        f"/api/v1/contacts/{contact_id}/respond",
        json={"action": "accept"},
    )
    assert resp4.status_code == 200
    assert resp4.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_child_request_parent_deny_flow(
    child_client, parent_client, e2e_users,
):
    """Full flow: child sends request, parent denies."""
    target_id = str(e2e_users["target"].id)

    resp = await child_client.post(f"/api/v1/contacts/request/{target_id}")
    assert resp.status_code == 201
    contact_id = resp.json()["id"]

    resp2 = await parent_client.patch(
        f"/api/v1/contacts/{contact_id}/parent-approve",
        json={"decision": "deny"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["decision"] == "deny"


# ---------------------------------------------------------------------------
# Tests — Block Flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_block_user_flow(teen_client, e2e_users):
    """Block a user via API."""
    target_id = str(e2e_users["target"].id)

    resp = await teen_client.post(f"/api/v1/contacts/{target_id}/block")
    assert resp.status_code == 201
    assert resp.json()["status"] == "blocked"


@pytest.mark.asyncio
async def test_block_then_cannot_request(teen_client, target_client, e2e_users):
    """After blocking, cannot send contact request."""
    target_id = str(e2e_users["target"].id)
    teen_id = str(e2e_users["teen"].id)

    await teen_client.post(f"/api/v1/contacts/{target_id}/block")

    # Target cannot request blocked teen
    resp = await target_client.post(f"/api/v1/contacts/request/{teen_id}")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests — List Contacts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_contacts_empty(teen_client):
    """List contacts when none exist."""
    resp = await teen_client.get("/api/v1/contacts/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_contacts_filtered(teen_client, target_client, e2e_users):
    """List contacts with status filter."""
    target_id = str(e2e_users["target"].id)

    resp = await teen_client.post(f"/api/v1/contacts/request/{target_id}")
    assert resp.status_code == 201

    # Pending
    resp2 = await teen_client.get("/api/v1/contacts/?status=pending")
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 1

    # Accepted (none yet)
    resp3 = await teen_client.get("/api/v1/contacts/?status=accepted")
    assert resp3.status_code == 200
    assert resp3.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_contacts_pagination(teen_client, e2e_session, e2e_users):
    """List contacts with pagination."""
    teen_id = e2e_users["teen"].id

    # Create 5 contacts directly
    for i in range(5):
        target = User(
            id=uuid.uuid4(),
            email=f"page-{uuid.uuid4().hex[:8]}@example.com",
            display_name=f"Page User {i}",
            account_type="family",
            email_verified=False,
            mfa_enabled=False,
        )
        e2e_session.add(target)
        await e2e_session.flush()

        contact = Contact(
            id=uuid.uuid4(),
            requester_id=teen_id,
            target_id=target.id,
            status="accepted",
            parent_approval_status="not_required",
        )
        e2e_session.add(contact)
    await e2e_session.flush()

    resp = await teen_client.get("/api/v1/contacts/?page=1&page_size=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 5

    resp2 = await teen_client.get("/api/v1/contacts/?page=2&page_size=3")
    assert resp2.status_code == 200
    assert len(resp2.json()["items"]) == 2


# ---------------------------------------------------------------------------
# Tests — Pending Approvals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_approvals_endpoint(
    child_client, parent_client, e2e_users,
):
    """Parent sees pending approvals for their children."""
    target_id = str(e2e_users["target"].id)

    await child_client.post(f"/api/v1/contacts/request/{target_id}")

    resp = await parent_client.get("/api/v1/contacts/pending")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_pending_approvals_empty_for_non_parent(teen_client):
    """Non-parent user sees no pending approvals."""
    resp = await teen_client.get("/api/v1/contacts/pending")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Tests — Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_respond_invalid_action(teen_client, target_client, e2e_users):
    """Invalid action in respond body returns 422."""
    target_id = str(e2e_users["target"].id)

    resp = await teen_client.post(f"/api/v1/contacts/request/{target_id}")
    contact_id = resp.json()["id"]

    resp2 = await target_client.patch(
        f"/api/v1/contacts/{contact_id}/respond",
        json={"action": "invalid"},
    )
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_parent_approve_invalid_decision(parent_client):
    """Invalid decision in parent-approve body returns 422."""
    resp = await parent_client.patch(
        f"/api/v1/contacts/{uuid.uuid4()}/parent-approve",
        json={"decision": "maybe"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_request_returns_409(teen_client, e2e_users):
    """Sending a duplicate contact request returns 409."""
    target_id = str(e2e_users["target"].id)

    resp1 = await teen_client.post(f"/api/v1/contacts/request/{target_id}")
    assert resp1.status_code == 201

    resp2 = await teen_client.post(f"/api/v1/contacts/request/{target_id}")
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_self_request_returns_422(teen_client, e2e_users):
    """Sending a contact request to yourself returns 422."""
    teen_id = str(e2e_users["teen"].id)

    resp = await teen_client.post(f"/api/v1/contacts/request/{teen_id}")
    assert resp.status_code == 422
