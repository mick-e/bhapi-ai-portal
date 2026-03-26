"""End-to-end tests for the contact approval flow (P2-M5).

Covers:
- Child sends request -> parent gets notified -> parent views pending -> approves -> status updated
- Child sends request -> parent denies -> status rejected
- Batch approval (parent approves multiple requests at once)
- Pending approvals with requester profiles
- Parent notification triggered on child request
- Batch deny
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
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
    """Create test users: parent, child (young), second child, teen, and targets."""
    today = datetime.now(timezone.utc).date()

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
        display_name="Child One",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child2 = User(
        id=uuid.uuid4(),
        email=f"child2-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Child Two",
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
    e2e_session.add_all([parent, child, child2, teen])
    await e2e_session.flush()

    # Create targets (friends the children want to add)
    targets = []
    for i in range(4):
        t = User(
            id=uuid.uuid4(),
            email=f"target{i}-{uuid.uuid4().hex[:8]}@example.com",
            display_name=f"Target Friend {i}",
            account_type="family",
            email_verified=False,
            mfa_enabled=False,
        )
        e2e_session.add(t)
        targets.append(t)
    await e2e_session.flush()

    # Create profiles — preteen tier (10-12) can add contacts but needs parent approval
    child_profile = Profile(
        id=uuid.uuid4(), user_id=child.id, display_name="Child One",
        date_of_birth=today.replace(year=today.year - 11), age_tier="preteen",
        visibility="friends_only",
    )
    child2_profile = Profile(
        id=uuid.uuid4(), user_id=child2.id, display_name="Child Two",
        date_of_birth=today.replace(year=today.year - 10), age_tier="preteen",
        visibility="friends_only",
    )
    teen_profile = Profile(
        id=uuid.uuid4(), user_id=teen.id, display_name="Teen",
        date_of_birth=today.replace(year=today.year - 14), age_tier="teen",
        visibility="friends_only",
    )
    e2e_session.add_all([child_profile, child2_profile, teen_profile])

    for i, t in enumerate(targets):
        tp = Profile(
            id=uuid.uuid4(), user_id=t.id, display_name=f"Target Friend {i}",
            date_of_birth=today.replace(year=today.year - 10), age_tier="preteen",
            visibility="friends_only",
        )
        e2e_session.add(tp)
    await e2e_session.flush()

    # Create family group with parent and both children
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
        role="member", display_name="Child One",
    )
    child2_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=child2.id,
        role="member", display_name="Child Two",
    )
    e2e_session.add_all([parent_member, child_member, child2_member])
    await e2e_session.flush()

    return {
        "parent": parent, "child": child, "child2": child2,
        "teen": teen, "targets": targets, "group": group,
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
async def child2_client(e2e_engine, e2e_session, e2e_users):
    async with _make_client(
        e2e_engine, e2e_session, e2e_users["child2"].id,
        e2e_users["group"].id, "member",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests — Full Approval Flow: Child -> Parent Notified -> Approve -> Status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_child_request_triggers_parent_notification(
    child_client, parent_client, e2e_users, e2e_session,
):
    """Child sends contact request -> parent receives push notification."""
    target = e2e_users["targets"][0]

    with patch(
        "src.contacts.service.expo_push_service.send_notification",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_push:
        resp = await child_client.post(f"/api/v1/contacts/request/{target.id}")
        assert resp.status_code == 201
        data = resp.json()
        assert data["parent_approval_status"] == "pending"

        # Verify push notification was called for parent
        mock_push.assert_called_once()
        call_args = mock_push.call_args
        assert call_args[1]["user_id"] == e2e_users["parent"].id
        assert "contact" in call_args[1]["title"].lower() or "approval" in call_args[1]["title"].lower()


@pytest.mark.asyncio
async def test_full_approval_flow_approve(
    child_client, parent_client, e2e_users,
):
    """Full flow: child sends request -> parent views pending -> approves -> status updated."""
    target = e2e_users["targets"][0]

    # 1. Child sends request
    resp = await child_client.post(f"/api/v1/contacts/request/{target.id}")
    assert resp.status_code == 201
    contact_id = resp.json()["id"]

    # 2. Parent views pending approvals
    resp2 = await parent_client.get("/api/v1/contacts/pending")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["total"] >= 1
    pending_ids = [item["id"] for item in data["items"]]
    assert contact_id in pending_ids

    # 3. Parent approves
    resp3 = await parent_client.patch(
        f"/api/v1/contacts/{contact_id}/parent-approve",
        json={"decision": "approve"},
    )
    assert resp3.status_code == 200
    assert resp3.json()["decision"] == "approve"

    # 4. Verify pending list no longer contains this contact
    resp4 = await parent_client.get("/api/v1/contacts/pending")
    assert resp4.status_code == 200
    remaining_ids = [item["id"] for item in resp4.json()["items"]]
    assert contact_id not in remaining_ids


@pytest.mark.asyncio
async def test_full_approval_flow_deny(
    child_client, parent_client, e2e_users,
):
    """Full flow: child sends request -> parent denies -> contact rejected."""
    target = e2e_users["targets"][0]

    # Child sends request
    resp = await child_client.post(f"/api/v1/contacts/request/{target.id}")
    assert resp.status_code == 201
    contact_id = resp.json()["id"]

    # Parent denies
    resp2 = await parent_client.patch(
        f"/api/v1/contacts/{contact_id}/parent-approve",
        json={"decision": "deny"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["decision"] == "deny"


@pytest.mark.asyncio
async def test_pending_with_profiles_returns_requester_info(
    child_client, parent_client, e2e_users,
):
    """Pending approvals endpoint returns profile info for the requester."""
    target = e2e_users["targets"][0]

    resp = await child_client.post(f"/api/v1/contacts/request/{target.id}")
    assert resp.status_code == 201

    resp2 = await parent_client.get("/api/v1/contacts/pending-with-profiles")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["total"] >= 1

    # Each item should have profile info
    item = data["items"][0]
    assert "requester_display_name" in item
    assert "requester_age_tier" in item
    assert "target_display_name" in item


@pytest.mark.asyncio
async def test_teen_request_no_parent_notification(e2e_engine, e2e_session, e2e_users):
    """Teen contact requests do NOT trigger parent notification (no approval needed)."""
    teen = e2e_users["teen"]
    target = e2e_users["targets"][0]

    with patch(
        "src.contacts.service.expo_push_service.send_notification",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_push:
        async with _make_client(
            e2e_engine, e2e_session, teen.id, e2e_users["group"].id, "member",
        ) as client:
            resp = await client.post(f"/api/v1/contacts/request/{target.id}")
            assert resp.status_code == 201
            assert resp.json()["parent_approval_status"] == "not_required"

        # Push should NOT have been called
        mock_push.assert_not_called()


# ---------------------------------------------------------------------------
# Tests — Batch Approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_approve(
    child_client, child2_client, parent_client, e2e_users, e2e_session,
):
    """Parent can batch-approve multiple contact requests at once."""
    targets = e2e_users["targets"]

    # Child 1 sends 2 requests
    resp1 = await child_client.post(f"/api/v1/contacts/request/{targets[0].id}")
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    resp2 = await child_client.post(f"/api/v1/contacts/request/{targets[1].id}")
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    # Batch approve
    resp3 = await parent_client.post(
        "/api/v1/contacts/batch-approve",
        json={"contact_ids": [id1, id2], "decision": "approve"},
    )
    assert resp3.status_code == 200
    data = resp3.json()
    assert data["processed"] == 2
    assert data["failed"] == 0

    # Verify both are approved (no longer pending)
    resp4 = await parent_client.get("/api/v1/contacts/pending")
    assert resp4.status_code == 200
    pending_ids = [item["id"] for item in resp4.json()["items"]]
    assert id1 not in pending_ids
    assert id2 not in pending_ids


@pytest.mark.asyncio
async def test_batch_deny(
    child_client, parent_client, e2e_users,
):
    """Parent can batch-deny multiple contact requests."""
    targets = e2e_users["targets"]

    resp1 = await child_client.post(f"/api/v1/contacts/request/{targets[0].id}")
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    resp2 = await child_client.post(f"/api/v1/contacts/request/{targets[1].id}")
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    resp3 = await parent_client.post(
        "/api/v1/contacts/batch-approve",
        json={"contact_ids": [id1, id2], "decision": "deny"},
    )
    assert resp3.status_code == 200
    data = resp3.json()
    assert data["processed"] == 2
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_batch_approve_partial_invalid(
    child_client, parent_client, e2e_users,
):
    """Batch approve with some invalid IDs still processes valid ones."""
    targets = e2e_users["targets"]

    resp1 = await child_client.post(f"/api/v1/contacts/request/{targets[0].id}")
    assert resp1.status_code == 201
    valid_id = resp1.json()["id"]

    fake_id = str(uuid.uuid4())

    resp3 = await parent_client.post(
        "/api/v1/contacts/batch-approve",
        json={"contact_ids": [valid_id, fake_id], "decision": "approve"},
    )
    assert resp3.status_code == 200
    data = resp3.json()
    assert data["processed"] == 1
    assert data["failed"] == 1


@pytest.mark.asyncio
async def test_batch_approve_empty_list(parent_client):
    """Batch approve with empty list returns 422."""
    resp = await parent_client.post(
        "/api/v1/contacts/batch-approve",
        json={"contact_ids": [], "decision": "approve"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests — Multiple Children
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_children_pending(
    child_client, child2_client, parent_client, e2e_users,
):
    """Parent sees pending requests from both children."""
    targets = e2e_users["targets"]

    resp1 = await child_client.post(f"/api/v1/contacts/request/{targets[0].id}")
    assert resp1.status_code == 201

    resp2 = await child2_client.post(f"/api/v1/contacts/request/{targets[1].id}")
    assert resp2.status_code == 201

    resp3 = await parent_client.get("/api/v1/contacts/pending")
    assert resp3.status_code == 200
    assert resp3.json()["total"] >= 2


@pytest.mark.asyncio
async def test_notification_not_sent_when_no_parent(e2e_engine, e2e_session, e2e_users):
    """If child has no parent in group, no push notification is sent (graceful)."""
    # Create an orphan child not in any group
    orphan = User(
        id=uuid.uuid4(),
        email=f"orphan-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Orphan Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(orphan)
    await e2e_session.flush()

    today = datetime.now(timezone.utc).date()
    orphan_profile = Profile(
        id=uuid.uuid4(), user_id=orphan.id, display_name="Orphan",
        date_of_birth=today.replace(year=today.year - 11), age_tier="preteen",
        visibility="friends_only",
    )
    e2e_session.add(orphan_profile)
    await e2e_session.flush()

    target = e2e_users["targets"][0]

    with patch(
        "src.contacts.service.expo_push_service.send_notification",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_push:
        async with _make_client(
            e2e_engine, e2e_session, orphan.id, None, "member",
        ) as client:
            resp = await client.post(f"/api/v1/contacts/request/{target.id}")
            assert resp.status_code == 201
            assert resp.json()["parent_approval_status"] == "pending"

        # No parent found, so no push sent
        mock_push.assert_not_called()
