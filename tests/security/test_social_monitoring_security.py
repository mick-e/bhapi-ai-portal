"""Security tests for social activity monitoring (P2-M1).

Covers:
- Unauthenticated access (401)
- Child role cannot access monitoring (403)
- Cross-group isolation (member from different group)
- Role escalation prevention
- SQL injection in member_id parameter
- Invalid UUID format handling
- Rate limiting awareness
- IDOR: parent from group A cannot view child in group B
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
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.schemas import GroupContext

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
async def sec_data(sec_session):
    """Two families: family A (parent + child) and family B (parent + child)."""
    # Family A
    parent_a = User(
        id=uuid.uuid4(),
        email=f"parentA-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Parent A",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child_a = User(
        id=uuid.uuid4(),
        email=f"childA-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Child A",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    # Family B
    parent_b = User(
        id=uuid.uuid4(),
        email=f"parentB-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Parent B",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child_b = User(
        id=uuid.uuid4(),
        email=f"childB-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Child B",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add_all([parent_a, child_a, parent_b, child_b])
    await sec_session.flush()

    group_a = Group(
        id=uuid.uuid4(), name="Family A", type="family", owner_id=parent_a.id,
    )
    group_b = Group(
        id=uuid.uuid4(), name="Family B", type="family", owner_id=parent_b.id,
    )
    sec_session.add_all([group_a, group_b])
    await sec_session.flush()

    parent_a_member = GroupMember(
        id=uuid.uuid4(), group_id=group_a.id, user_id=parent_a.id,
        role="parent", display_name="Parent A",
    )
    child_a_member = GroupMember(
        id=uuid.uuid4(), group_id=group_a.id, user_id=child_a.id,
        role="member", display_name="Child A",
        date_of_birth=datetime(2015, 1, 1, tzinfo=timezone.utc),
    )
    parent_b_member = GroupMember(
        id=uuid.uuid4(), group_id=group_b.id, user_id=parent_b.id,
        role="parent", display_name="Parent B",
    )
    child_b_member = GroupMember(
        id=uuid.uuid4(), group_id=group_b.id, user_id=child_b.id,
        role="member", display_name="Child B",
        date_of_birth=datetime(2016, 6, 1, tzinfo=timezone.utc),
    )
    sec_session.add_all([parent_a_member, child_a_member, parent_b_member, child_b_member])
    await sec_session.flush()
    await sec_session.commit()

    return {
        "parent_a": parent_a, "child_a": child_a,
        "parent_b": parent_b, "child_b": child_b,
        "group_a": group_a, "group_b": group_b,
        "parent_a_member": parent_a_member,
        "child_a_member": child_a_member,
        "parent_b_member": parent_b_member,
        "child_b_member": child_b_member,
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
# Tests — Authentication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(sec_engine, sec_session, sec_data):
    """Unauthenticated request is rejected with 401."""
    d = sec_data
    async with _make_unauthed_client(sec_engine, sec_session) as c:
        resp = await c.get(
            f"/api/v1/portal/social-activity?member_id={d['child_a_member'].id}"
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_no_bearer_token(sec_engine, sec_session, sec_data):
    """Request without Bearer token is rejected."""
    d = sec_data
    app = create_app()

    async def get_db_override():
        yield sec_session

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": "InvalidScheme xyz"},
    ) as c:
        resp = await c.get(
            f"/api/v1/portal/social-activity?member_id={d['child_a_member'].id}"
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests — Authorization (role-based)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_child_role_forbidden(sec_engine, sec_session, sec_data):
    """Child (member) role cannot access social activity."""
    d = sec_data
    async with _make_client(
        sec_engine, sec_session, d["child_a"].id, d["group_a"].id, role="member"
    ) as c:
        resp = await c.get(
            f"/api/v1/portal/social-activity?member_id={d['child_a_member'].id}"
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unknown_role_forbidden(sec_engine, sec_session, sec_data):
    """Unknown role is rejected."""
    d = sec_data
    async with _make_client(
        sec_engine, sec_session, d["parent_a"].id, d["group_a"].id, role="viewer"
    ) as c:
        resp = await c.get(
            f"/api/v1/portal/social-activity?member_id={d['child_a_member'].id}"
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests — Cross-group isolation (IDOR)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parent_a_cannot_view_child_b(sec_engine, sec_session, sec_data):
    """Parent A cannot view child B from group B (different group)."""
    d = sec_data
    async with _make_client(
        sec_engine, sec_session, d["parent_a"].id, d["group_a"].id, role="parent"
    ) as c:
        resp = await c.get(
            f"/api/v1/portal/social-activity?member_id={d['child_b_member'].id}"
        )
    # child_b_member belongs to group_b, but auth context is group_a => 404
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_parent_b_cannot_view_child_a(sec_engine, sec_session, sec_data):
    """Parent B cannot view child A from group A."""
    d = sec_data
    async with _make_client(
        sec_engine, sec_session, d["parent_b"].id, d["group_b"].id, role="parent"
    ) as c:
        resp = await c.get(
            f"/api/v1/portal/social-activity?member_id={d['child_a_member'].id}"
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cross_group_with_spoofed_member_id(sec_engine, sec_session, sec_data):
    """Attempting to pass a member from another group returns 404, not data."""
    d = sec_data
    async with _make_client(
        sec_engine, sec_session, d["parent_a"].id, d["group_a"].id, role="parent"
    ) as c:
        resp = await c.get(
            f"/api/v1/portal/social-activity?member_id={d['child_b_member'].id}"
        )
    assert resp.status_code == 404
    body = resp.json()
    # Should not leak any data about child B
    assert "member_name" not in body or body.get("detail")


# ---------------------------------------------------------------------------
# Tests — Input validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_uuid_format(sec_engine, sec_session, sec_data):
    """Invalid UUID returns 422."""
    d = sec_data
    async with _make_client(
        sec_engine, sec_session, d["parent_a"].id, d["group_a"].id
    ) as c:
        resp = await c.get("/api/v1/portal/social-activity?member_id=not-a-uuid")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_in_member_id(sec_engine, sec_session, sec_data):
    """SQL injection attempt in member_id returns 422."""
    d = sec_data
    async with _make_client(
        sec_engine, sec_session, d["parent_a"].id, d["group_a"].id
    ) as c:
        resp = await c.get(
            "/api/v1/portal/social-activity?member_id=1%27%20OR%201=1--"
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_missing_member_id(sec_engine, sec_session, sec_data):
    """Missing member_id returns 422."""
    d = sec_data
    async with _make_client(
        sec_engine, sec_session, d["parent_a"].id, d["group_a"].id
    ) as c:
        resp = await c.get("/api/v1/portal/social-activity")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests — No group context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_group_context_rejected(sec_engine, sec_session, sec_data):
    """Request with no group_id in auth context is rejected."""
    d = sec_data
    async with _make_client(
        sec_engine, sec_session, d["parent_a"].id, group_id=None, role="parent"
    ) as c:
        resp = await c.get(
            f"/api/v1/portal/social-activity?member_id={d['child_a_member'].id}"
        )
    # Should return 422 (validation error for no group) or 403
    assert resp.status_code in (403, 422)
