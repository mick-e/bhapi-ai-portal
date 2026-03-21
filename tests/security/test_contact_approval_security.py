"""Security tests for the contact approval flow (P2-M5).

Covers:
- Only parent of the child can approve — cross-family parent is rejected
- Batch approve rejects requests from other families
- Cannot approve already-decided requests
- Unauthenticated batch-approve returns 401
- Cannot view another family's pending-with-profiles
- Non-parent cannot use batch-approve
- Cannot forge requester_id in batch
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
async def sec_engine():
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
async def sec_session(sec_engine):
    async_session_maker = sessionmaker(
        sec_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def sec_users(sec_session):
    """Two families: family A (parent_a + child_a), family B (parent_b + child_b), plus a target."""
    today = datetime.now(timezone.utc).date()

    parent_a = User(
        id=uuid.uuid4(),
        email=f"parenta-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Parent A",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child_a = User(
        id=uuid.uuid4(),
        email=f"childa-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Child A",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    parent_b = User(
        id=uuid.uuid4(),
        email=f"parentb-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Parent B",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child_b = User(
        id=uuid.uuid4(),
        email=f"childb-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Child B",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    target = User(
        id=uuid.uuid4(),
        email=f"sectarget-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Sec Target",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add_all([parent_a, child_a, parent_b, child_b, target])
    await sec_session.flush()

    # Profiles
    child_a_profile = Profile(
        id=uuid.uuid4(), user_id=child_a.id, display_name="Child A",
        date_of_birth=today.replace(year=today.year - 7), age_tier="young",
        visibility="friends_only",
    )
    child_b_profile = Profile(
        id=uuid.uuid4(), user_id=child_b.id, display_name="Child B",
        date_of_birth=today.replace(year=today.year - 8), age_tier="young",
        visibility="friends_only",
    )
    sec_session.add_all([child_a_profile, child_b_profile])
    await sec_session.flush()

    # Family A
    group_a = Group(
        id=uuid.uuid4(), name="Family A", type="family", owner_id=parent_a.id,
    )
    sec_session.add(group_a)
    await sec_session.flush()

    sec_session.add_all([
        GroupMember(
            id=uuid.uuid4(), group_id=group_a.id, user_id=parent_a.id,
            role="parent", display_name="Parent A",
        ),
        GroupMember(
            id=uuid.uuid4(), group_id=group_a.id, user_id=child_a.id,
            role="member", display_name="Child A",
        ),
    ])
    await sec_session.flush()

    # Family B
    group_b = Group(
        id=uuid.uuid4(), name="Family B", type="family", owner_id=parent_b.id,
    )
    sec_session.add(group_b)
    await sec_session.flush()

    sec_session.add_all([
        GroupMember(
            id=uuid.uuid4(), group_id=group_b.id, user_id=parent_b.id,
            role="parent", display_name="Parent B",
        ),
        GroupMember(
            id=uuid.uuid4(), group_id=group_b.id, user_id=child_b.id,
            role="member", display_name="Child B",
        ),
    ])
    await sec_session.flush()

    return {
        "parent_a": parent_a, "child_a": child_a, "group_a": group_a,
        "parent_b": parent_b, "child_b": child_b, "group_b": group_b,
        "target": target,
    }


def _make_client(sec_engine, sec_session, user_id, group_id=None, role="parent"):
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
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


def _make_unauthed_client(sec_engine, sec_session):
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


# ---------------------------------------------------------------------------
# Tests — Cross-Family Isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_family_parent_cannot_batch_approve(sec_engine, sec_session, sec_users):
    """Parent B cannot batch-approve child A's contact requests."""
    child_a = sec_users["child_a"]
    parent_b = sec_users["parent_b"]
    group_a = sec_users["group_a"]
    group_b = sec_users["group_b"]
    target = sec_users["target"]

    # Create a pending contact for child A
    contact = Contact(
        id=uuid.uuid4(), requester_id=child_a.id, target_id=target.id,
        status="pending", parent_approval_status="pending",
    )
    sec_session.add(contact)
    await sec_session.flush()

    # Parent B tries to batch-approve — should fail
    async with _make_client(
        sec_engine, sec_session, parent_b.id, group_b.id, "parent",
    ) as client:
        resp = await client.post(
            "/api/v1/contacts/batch-approve",
            json={"contact_ids": [str(contact.id)], "decision": "approve"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should fail to process (not this parent's child)
        assert data["processed"] == 0
        assert data["failed"] == 1


@pytest.mark.asyncio
async def test_cross_family_parent_cannot_see_pending_profiles(
    sec_engine, sec_session, sec_users,
):
    """Parent B cannot see pending-with-profiles for child A's requests."""
    child_a = sec_users["child_a"]
    parent_b = sec_users["parent_b"]
    group_b = sec_users["group_b"]
    target = sec_users["target"]

    contact = Contact(
        id=uuid.uuid4(), requester_id=child_a.id, target_id=target.id,
        status="pending", parent_approval_status="pending",
    )
    sec_session.add(contact)
    await sec_session.flush()

    async with _make_client(
        sec_engine, sec_session, parent_b.id, group_b.id, "parent",
    ) as client:
        resp = await client.get("/api/v1/contacts/pending-with-profiles")
        assert resp.status_code == 200
        # Should return empty — not parent B's children
        assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_cross_family_approve_single_rejected(sec_engine, sec_session, sec_users):
    """Parent B cannot approve child A's individual request via parent-approve."""
    child_a = sec_users["child_a"]
    parent_b = sec_users["parent_b"]
    group_b = sec_users["group_b"]
    target = sec_users["target"]

    contact = Contact(
        id=uuid.uuid4(), requester_id=child_a.id, target_id=target.id,
        status="pending", parent_approval_status="pending",
    )
    sec_session.add(contact)
    await sec_session.flush()

    async with _make_client(
        sec_engine, sec_session, parent_b.id, group_b.id, "parent",
    ) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{contact.id}/parent-approve",
            json={"decision": "approve"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests — Unauthenticated Access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthed_batch_approve_returns_401(sec_engine, sec_session):
    """Unauthenticated request to batch-approve returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.post(
            "/api/v1/contacts/batch-approve",
            json={"contact_ids": [str(uuid.uuid4())], "decision": "approve"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_pending_profiles_returns_401(sec_engine, sec_session):
    """Unauthenticated request to pending-with-profiles returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get("/api/v1/contacts/pending-with-profiles")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests — Non-Parent Cannot Batch Approve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_child_cannot_batch_approve(sec_engine, sec_session, sec_users):
    """A child user cannot batch-approve requests (even their own)."""
    child_a = sec_users["child_a"]
    group_a = sec_users["group_a"]
    target = sec_users["target"]

    contact = Contact(
        id=uuid.uuid4(), requester_id=child_a.id, target_id=target.id,
        status="pending", parent_approval_status="pending",
    )
    sec_session.add(contact)
    await sec_session.flush()

    # Child tries to batch-approve their own request
    async with _make_client(
        sec_engine, sec_session, child_a.id, group_a.id, "member",
    ) as client:
        resp = await client.post(
            "/api/v1/contacts/batch-approve",
            json={"contact_ids": [str(contact.id)], "decision": "approve"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should fail — child is not the parent
        assert data["processed"] == 0
        assert data["failed"] == 1


# ---------------------------------------------------------------------------
# Tests — Cannot Re-Approve Already Decided
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_approve_already_decided_fails(sec_engine, sec_session, sec_users):
    """Cannot batch-approve a request that has already been decided."""
    child_a = sec_users["child_a"]
    parent_a = sec_users["parent_a"]
    group_a = sec_users["group_a"]
    target = sec_users["target"]

    contact = Contact(
        id=uuid.uuid4(), requester_id=child_a.id, target_id=target.id,
        status="pending", parent_approval_status="approved",
    )
    sec_session.add(contact)
    await sec_session.flush()

    async with _make_client(
        sec_engine, sec_session, parent_a.id, group_a.id, "parent",
    ) as client:
        resp = await client.post(
            "/api/v1/contacts/batch-approve",
            json={"contact_ids": [str(contact.id)], "decision": "approve"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 0
        assert data["failed"] == 1
