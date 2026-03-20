"""Security tests for the contacts module.

Covers:
- Unauthenticated access (401)
- Only target can respond to requests
- Only parent can approve
- Cross-user isolation
- Blocked user restrictions
"""

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
    parent = User(
        id=uuid.uuid4(),
        email=f"secparent-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Sec Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child = User(
        id=uuid.uuid4(),
        email=f"secchild-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Sec Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    attacker = User(
        id=uuid.uuid4(),
        email=f"attacker-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Attacker",
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
    sec_session.add_all([parent, child, attacker, target])
    await sec_session.flush()

    # Profiles
    today = datetime.now(timezone.utc).date()
    child_profile = Profile(
        id=uuid.uuid4(), user_id=child.id, display_name="Child",
        date_of_birth=today.replace(year=today.year - 8), age_tier="young",
        visibility="friends_only",
    )
    sec_session.add(child_profile)
    await sec_session.flush()

    # Family group
    group = Group(
        id=uuid.uuid4(), name="Sec Family", type="family", owner_id=parent.id,
    )
    sec_session.add(group)
    await sec_session.flush()

    parent_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=parent.id,
        role="parent", display_name="Parent",
    )
    child_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=child.id,
        role="member", display_name="Child",
    )
    sec_session.add_all([parent_member, child_member])
    await sec_session.flush()

    return {
        "parent": parent, "child": child,
        "attacker": attacker, "target": target, "group": group,
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
    """Client without auth override — relies on real auth middleware."""
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
# Tests — Unauthenticated Access (401)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthed_list_contacts(sec_engine, sec_session):
    """Unauthenticated request to list contacts returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get("/api/v1/contacts/")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_send_request(sec_engine, sec_session):
    """Unauthenticated request to send contact request returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.post(f"/api/v1/contacts/request/{uuid.uuid4()}")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_respond(sec_engine, sec_session):
    """Unauthenticated request to respond returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{uuid.uuid4()}/respond",
            json={"action": "accept"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_pending(sec_engine, sec_session):
    """Unauthenticated request to pending approvals returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get("/api/v1/contacts/pending")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests — Authorization Boundaries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_only_target_can_respond(sec_engine, sec_session, sec_users):
    """Requester cannot respond to their own request."""
    child = sec_users["child"]
    target = sec_users["target"]

    # Create contact request directly
    contact = Contact(
        id=uuid.uuid4(), requester_id=child.id, target_id=target.id,
        status="pending", parent_approval_status="not_required",
    )
    sec_session.add(contact)
    await sec_session.flush()

    # Requester (child) tries to accept — should fail
    async with _make_client(
        sec_engine, sec_session, child.id, sec_users["group"].id, "member",
    ) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{contact.id}/respond",
            json={"action": "accept"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_only_parent_can_approve(sec_engine, sec_session, sec_users):
    """Non-parent (attacker) cannot approve a child's contact request."""
    child = sec_users["child"]
    target = sec_users["target"]
    attacker = sec_users["attacker"]

    contact = Contact(
        id=uuid.uuid4(), requester_id=child.id, target_id=target.id,
        status="pending", parent_approval_status="pending",
    )
    sec_session.add(contact)
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, attacker.id) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{contact.id}/parent-approve",
            json={"decision": "approve"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_attacker_cannot_respond_for_target(sec_engine, sec_session, sec_users):
    """Attacker cannot respond to a request meant for another user."""
    child = sec_users["child"]
    target = sec_users["target"]
    attacker = sec_users["attacker"]

    contact = Contact(
        id=uuid.uuid4(), requester_id=child.id, target_id=target.id,
        status="pending", parent_approval_status="not_required",
    )
    sec_session.add(contact)
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, attacker.id) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{contact.id}/respond",
            json={"action": "accept"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_blocked_user_cannot_request(sec_engine, sec_session, sec_users):
    """A blocked user cannot send a contact request to the blocker."""
    target = sec_users["target"]
    attacker = sec_users["attacker"]

    # Target blocks attacker
    blocked = Contact(
        id=uuid.uuid4(), requester_id=target.id, target_id=attacker.id,
        status="blocked", parent_approval_status="not_required",
    )
    sec_session.add(blocked)
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, attacker.id) as client:
        resp = await client.post(f"/api/v1/contacts/request/{target.id}")
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cannot_send_request_to_self(sec_engine, sec_session, sec_users):
    """Cannot send a contact request to yourself."""
    target = sec_users["target"]

    async with _make_client(sec_engine, sec_session, target.id) as client:
        resp = await client.post(f"/api/v1/contacts/request/{target.id}")
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cross_group_parent_cannot_approve(sec_engine, sec_session, sec_users):
    """A parent from a different group cannot approve a child's request."""
    child = sec_users["child"]
    target = sec_users["target"]

    # Create a different parent in a different group
    other_parent = User(
        id=uuid.uuid4(),
        email=f"other-parent-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Other Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add(other_parent)
    await sec_session.flush()

    other_group = Group(
        id=uuid.uuid4(), name="Other Family", type="family", owner_id=other_parent.id,
    )
    sec_session.add(other_group)
    await sec_session.flush()

    other_parent_member = GroupMember(
        id=uuid.uuid4(), group_id=other_group.id, user_id=other_parent.id,
        role="parent", display_name="Other Parent",
    )
    sec_session.add(other_parent_member)
    await sec_session.flush()

    contact = Contact(
        id=uuid.uuid4(), requester_id=child.id, target_id=target.id,
        status="pending", parent_approval_status="pending",
    )
    sec_session.add(contact)
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, other_parent.id) as client:
        resp = await client.patch(
            f"/api/v1/contacts/{contact.id}/parent-approve",
            json={"decision": "approve"},
        )
        assert resp.status_code == 403
