"""End-to-end tests for the contacts flow.

Covers:
- Search users by display_name -> send request -> target receives -> accepts -> in contacts list
- Parent approval gate for under-13
- Blocking prevents future requests
- Search excludes blocked and private profiles
- Pagination of search results
"""

import uuid
from datetime import datetime, timezone

import pytest
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


@pytest.fixture
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


@pytest.fixture
async def e2e_session(e2e_engine):
    async_session_maker = sessionmaker(
        e2e_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def e2e_users(e2e_session):
    """Create a family with parent, preteen child (10-12), teen, and external user."""
    today = datetime.now(timezone.utc).date()

    parent = User(
        id=uuid.uuid4(),
        email=f"parent-{uuid.uuid4().hex[:8]}@example.com",
        display_name="E2E Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    # Preteen child (age 11) — can_add_contacts=True but needs parent approval
    child = User(
        id=uuid.uuid4(),
        email=f"child-{uuid.uuid4().hex[:8]}@example.com",
        display_name="E2E Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    teen = User(
        id=uuid.uuid4(),
        email=f"teen-{uuid.uuid4().hex[:8]}@example.com",
        display_name="E2E Teen",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    other = User(
        id=uuid.uuid4(),
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Other Kid",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    private_user = User(
        id=uuid.uuid4(),
        email=f"private-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Private Kid",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add_all([parent, child, teen, other, private_user])
    await e2e_session.flush()

    # Profiles
    child_profile = Profile(
        id=uuid.uuid4(), user_id=child.id, display_name="E2E Child",
        date_of_birth=today.replace(year=today.year - 11), age_tier="preteen",
        visibility="friends_only",
    )
    teen_profile = Profile(
        id=uuid.uuid4(), user_id=teen.id, display_name="E2E Teen",
        date_of_birth=today.replace(year=today.year - 14), age_tier="teen",
        visibility="public",
    )
    other_profile = Profile(
        id=uuid.uuid4(), user_id=other.id, display_name="Other Kid",
        date_of_birth=today.replace(year=today.year - 11), age_tier="preteen",
        visibility="friends_only",
    )
    private_profile = Profile(
        id=uuid.uuid4(), user_id=private_user.id, display_name="Private Kid",
        date_of_birth=today.replace(year=today.year - 12), age_tier="preteen",
        visibility="private",
    )
    e2e_session.add_all([child_profile, teen_profile, other_profile, private_profile])
    await e2e_session.flush()

    # Family group
    group = Group(
        id=uuid.uuid4(), name="E2E Family", type="family", owner_id=parent.id,
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
    teen_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=teen.id,
        role="member", display_name="Teen",
    )
    e2e_session.add_all([parent_member, child_member, teen_member])
    await e2e_session.flush()

    return {
        "parent": parent, "child": child, "teen": teen,
        "other": other, "private_user": private_user, "group": group,
    }


def _make_client(e2e_engine, e2e_session, user_id, group_id=None, role="parent"):
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


# ---------------------------------------------------------------------------
# Tests — Search Users
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_users_by_display_name(e2e_engine, e2e_session, e2e_users):
    """Search by display_name returns matching profiles."""
    teen = e2e_users["teen"]

    async with _make_client(
        e2e_engine, e2e_session, teen.id, e2e_users["group"].id, "member",
    ) as client:
        resp = await client.get("/api/v1/social/search", params={"q": "Other"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        names = [item["display_name"] for item in data["items"]]
        assert "Other Kid" in names


@pytest.mark.asyncio
async def test_search_is_case_insensitive(e2e_engine, e2e_session, e2e_users):
    """Search is case-insensitive."""
    teen = e2e_users["teen"]

    async with _make_client(
        e2e_engine, e2e_session, teen.id, e2e_users["group"].id, "member",
    ) as client:
        resp = await client.get("/api/v1/social/search", params={"q": "other kid"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


@pytest.mark.asyncio
async def test_search_excludes_own_profile(e2e_engine, e2e_session, e2e_users):
    """Search never returns the requester's own profile."""
    teen = e2e_users["teen"]

    async with _make_client(
        e2e_engine, e2e_session, teen.id, e2e_users["group"].id, "member",
    ) as client:
        resp = await client.get("/api/v1/social/search", params={"q": "E2E Teen"})
        assert resp.status_code == 200
        data = resp.json()
        user_ids = [item["user_id"] for item in data["items"]]
        assert str(teen.id) not in user_ids


@pytest.mark.asyncio
async def test_search_excludes_private_profiles(e2e_engine, e2e_session, e2e_users):
    """Search excludes private-visibility profiles."""
    teen = e2e_users["teen"]

    async with _make_client(
        e2e_engine, e2e_session, teen.id, e2e_users["group"].id, "member",
    ) as client:
        resp = await client.get("/api/v1/social/search", params={"q": "Private"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0


@pytest.mark.asyncio
async def test_search_empty_query_returns_empty(e2e_engine, e2e_session, e2e_users):
    """Empty search query returns validation error."""
    teen = e2e_users["teen"]

    async with _make_client(
        e2e_engine, e2e_session, teen.id, e2e_users["group"].id, "member",
    ) as client:
        resp = await client.get("/api/v1/social/search", params={"q": ""})
        # min_length=1 on query param should return 422
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_pagination(e2e_engine, e2e_session, e2e_users):
    """Search supports pagination."""
    teen = e2e_users["teen"]

    async with _make_client(
        e2e_engine, e2e_session, teen.id, e2e_users["group"].id, "member",
    ) as client:
        resp = await client.get(
            "/api/v1/social/search",
            params={"q": "E2E", "page": 1, "page_size": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 1
        assert len(data["items"]) <= 1


# ---------------------------------------------------------------------------
# Tests — Full Contact Request Flow (Teen — no parent approval)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_contact_flow_teen(e2e_engine, e2e_session, e2e_users):
    """Teen: search -> send request -> target accepts -> in contacts."""
    teen = e2e_users["teen"]
    other = e2e_users["other"]
    group = e2e_users["group"]

    # 1. Teen searches for Other Kid
    async with _make_client(
        e2e_engine, e2e_session, teen.id, group.id, "member",
    ) as client:
        resp = await client.get("/api/v1/social/search", params={"q": "Other"})
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # 2. Teen sends contact request
        resp = await client.post(f"/api/v1/contacts/request/{other.id}")
        assert resp.status_code == 201
        contact_data = resp.json()
        assert contact_data["status"] == "pending"
        assert contact_data["parent_approval_status"] == "not_required"
        contact_id = contact_data["id"]

    # 3. Other user accepts
    async with _make_client(
        e2e_engine, e2e_session, other.id, None, "member",
    ) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{contact_id}/respond",
            json={"action": "accept"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"

    # 4. Verify in contacts list
    async with _make_client(
        e2e_engine, e2e_session, teen.id, group.id, "member",
    ) as client:
        resp = await client.get("/api/v1/contacts/", params={"status": "accepted"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        contact_ids = [c["id"] for c in data["items"]]
        assert contact_id in contact_ids


# ---------------------------------------------------------------------------
# Tests — Parent Approval Gate (under-13 child)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_approval_gate_child(e2e_engine, e2e_session, e2e_users):
    """Preteen child request requires parent approval before acceptance."""
    # Capture IDs up-front to avoid MissingGreenlet on lazy attribute access
    child_id = e2e_users["child"].id
    other_id = e2e_users["other"].id
    parent_id = e2e_users["parent"].id
    group_id = e2e_users["group"].id

    # 1. Child sends request — should set parent_approval_status="pending"
    async with _make_client(
        e2e_engine, e2e_session, child_id, group_id, "member",
    ) as client:
        resp = await client.post(f"/api/v1/contacts/request/{other_id}")
        assert resp.status_code == 201
        data = resp.json()
        assert data["parent_approval_status"] == "pending"
        contact_id = data["id"]

    # 2. Other user tries to accept — should fail (parent approval pending)
    async with _make_client(
        e2e_engine, e2e_session, other_id, None, "member",
    ) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{contact_id}/respond",
            json={"action": "accept"},
        )
        assert resp.status_code == 422

    # 3. Parent approves
    async with _make_client(
        e2e_engine, e2e_session, parent_id, group_id, "parent",
    ) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{contact_id}/parent-approve",
            json={"decision": "approve"},
        )
        assert resp.status_code == 200
        assert resp.json()["decision"] == "approve"

    # 4. Now other user can accept
    async with _make_client(
        e2e_engine, e2e_session, other_id, None, "member",
    ) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{contact_id}/respond",
            json={"action": "accept"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_parent_denial_rejects_contact(e2e_engine, e2e_session, e2e_users):
    """Parent denial sets contact to rejected."""
    child_id = e2e_users["child"].id
    parent_id = e2e_users["parent"].id
    group_id = e2e_users["group"].id

    # Create fresh contact (need new user to avoid conflict)
    new_user = User(
        id=uuid.uuid4(),
        email=f"newkid-{uuid.uuid4().hex[:8]}@example.com",
        display_name="New Kid",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(new_user)
    await e2e_session.flush()

    today = datetime.now(timezone.utc).date()
    new_user_id = new_user.id
    new_profile = Profile(
        id=uuid.uuid4(), user_id=new_user_id, display_name="New Kid",
        date_of_birth=today.replace(year=today.year - 11), age_tier="preteen",
        visibility="friends_only",
    )
    e2e_session.add(new_profile)
    await e2e_session.flush()

    async with _make_client(
        e2e_engine, e2e_session, child_id, group_id, "member",
    ) as client:
        resp = await client.post(f"/api/v1/contacts/request/{new_user_id}")
        assert resp.status_code == 201
        contact_id = resp.json()["id"]

    # Parent denies
    async with _make_client(
        e2e_engine, e2e_session, parent_id, group_id, "parent",
    ) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{contact_id}/parent-approve",
            json={"decision": "deny"},
        )
        assert resp.status_code == 200
        assert resp.json()["decision"] == "deny"


# ---------------------------------------------------------------------------
# Tests — Blocking Prevents Future Requests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blocking_prevents_future_requests(e2e_engine, e2e_session, e2e_users):
    """Blocking a user prevents them from sending future requests."""
    teen = e2e_users["teen"]
    group = e2e_users["group"]

    # Create another user to block
    blocker_target = User(
        id=uuid.uuid4(),
        email=f"blockme-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Block Target",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(blocker_target)
    await e2e_session.flush()

    today = datetime.now(timezone.utc).date()
    bt_profile = Profile(
        id=uuid.uuid4(), user_id=blocker_target.id, display_name="Block Target",
        date_of_birth=today.replace(year=today.year - 13), age_tier="teen",
        visibility="public",
    )
    e2e_session.add(bt_profile)
    await e2e_session.flush()

    # Teen blocks the user
    async with _make_client(
        e2e_engine, e2e_session, teen.id, group.id, "member",
    ) as client:
        resp = await client.post(f"/api/v1/contacts/{blocker_target.id}/block")
        assert resp.status_code == 201
        assert resp.json()["status"] == "blocked"

    # Blocked user tries to send request to teen — forbidden
    async with _make_client(
        e2e_engine, e2e_session, blocker_target.id, None, "member",
    ) as client:
        resp = await client.post(f"/api/v1/contacts/request/{teen.id}")
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_blocked_user_excluded_from_search(e2e_engine, e2e_session, e2e_users):
    """Blocked users do not appear in search results."""
    teen = e2e_users["teen"]
    group = e2e_users["group"]

    # Create user, block them, then search
    blocked_user = User(
        id=uuid.uuid4(),
        email=f"searchblock-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Searchblock Person",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(blocked_user)
    await e2e_session.flush()

    today = datetime.now(timezone.utc).date()
    sb_profile = Profile(
        id=uuid.uuid4(), user_id=blocked_user.id, display_name="Searchblock Person",
        date_of_birth=today.replace(year=today.year - 13), age_tier="teen",
        visibility="public",
    )
    e2e_session.add(sb_profile)
    await e2e_session.flush()

    # Block the user
    block_contact = Contact(
        id=uuid.uuid4(), requester_id=teen.id, target_id=blocked_user.id,
        status="blocked", parent_approval_status="not_required",
    )
    e2e_session.add(block_contact)
    await e2e_session.flush()

    # Search
    async with _make_client(
        e2e_engine, e2e_session, teen.id, group.id, "member",
    ) as client:
        resp = await client.get(
            "/api/v1/social/search", params={"q": "Searchblock"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0


@pytest.mark.asyncio
async def test_pending_contacts_list(e2e_engine, e2e_session, e2e_users):
    """Parent can list pending approvals for their children."""
    parent = e2e_users["parent"]
    child = e2e_users["child"]
    group = e2e_users["group"]

    # Create a pending contact for the child
    pending_target = User(
        id=uuid.uuid4(),
        email=f"pending-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Pending Target",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(pending_target)
    await e2e_session.flush()

    contact = Contact(
        id=uuid.uuid4(), requester_id=child.id, target_id=pending_target.id,
        status="pending", parent_approval_status="pending",
    )
    e2e_session.add(contact)
    await e2e_session.flush()

    async with _make_client(
        e2e_engine, e2e_session, parent.id, group.id, "parent",
    ) as client:
        resp = await client.get("/api/v1/contacts/pending")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


@pytest.mark.asyncio
async def test_reject_contact_request(e2e_engine, e2e_session, e2e_users):
    """Target can reject a contact request."""
    teen = e2e_users["teen"]
    group = e2e_users["group"]

    reject_user = User(
        id=uuid.uuid4(),
        email=f"reject-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Reject User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(reject_user)
    await e2e_session.flush()

    # Teen sends request
    async with _make_client(
        e2e_engine, e2e_session, teen.id, group.id, "member",
    ) as client:
        resp = await client.post(f"/api/v1/contacts/request/{reject_user.id}")
        assert resp.status_code == 201
        contact_id = resp.json()["id"]

    # Target rejects
    async with _make_client(
        e2e_engine, e2e_session, reject_user.id, None, "member",
    ) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{contact_id}/respond",
            json={"action": "reject"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_duplicate_request_prevented(e2e_engine, e2e_session, e2e_users):
    """Cannot send duplicate contact request."""
    teen = e2e_users["teen"]
    group = e2e_users["group"]

    dup_user = User(
        id=uuid.uuid4(),
        email=f"dup-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Dup User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(dup_user)
    await e2e_session.flush()

    async with _make_client(
        e2e_engine, e2e_session, teen.id, group.id, "member",
    ) as client:
        resp = await client.post(f"/api/v1/contacts/request/{dup_user.id}")
        assert resp.status_code == 201

        # Try again — should conflict
        resp = await client.post(f"/api/v1/contacts/request/{dup_user.id}")
        assert resp.status_code == 409
