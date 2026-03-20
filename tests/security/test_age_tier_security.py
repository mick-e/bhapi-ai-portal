"""Security tests for the age tier module."""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.age_tier.models import AgeTierConfig
from src.age_tier.rules import AgeTier
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.schemas import GroupContext
from src.auth.middleware import get_current_user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sec_engine():
    """Create a security test engine."""
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
    """Create a security test session."""
    session = AsyncSession(sec_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest.fixture
async def sec_data(sec_session):
    """Create test data for security tests."""
    # User 1 (owner of group 1)
    user1 = User(
        id=uuid.uuid4(),
        email=f"user1-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="User 1",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    # User 2 (owner of group 2)
    user2 = User(
        id=uuid.uuid4(),
        email=f"user2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="User 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add_all([user1, user2])
    await sec_session.flush()

    group1 = Group(id=uuid.uuid4(), name="Family 1", type="family", owner_id=user1.id)
    group2 = Group(id=uuid.uuid4(), name="Family 2", type="family", owner_id=user2.id)
    sec_session.add_all([group1, group2])
    await sec_session.flush()

    member1 = GroupMember(
        id=uuid.uuid4(),
        group_id=group1.id,
        user_id=None,
        role="member",
        display_name="Child 1",
        date_of_birth=datetime(2016, 5, 15, tzinfo=timezone.utc),
    )
    member2 = GroupMember(
        id=uuid.uuid4(),
        group_id=group2.id,
        user_id=None,
        role="member",
        display_name="Child 2",
        date_of_birth=datetime(2014, 8, 20, tzinfo=timezone.utc),
    )
    sec_session.add_all([member1, member2])
    await sec_session.flush()

    # Assign tier to member1
    config1 = AgeTierConfig(
        member_id=member1.id,
        tier="young",
        date_of_birth=member1.date_of_birth,
        jurisdiction="US",
        feature_overrides={},
        locked_features=[],
    )
    sec_session.add(config1)
    await sec_session.flush()

    return {
        "user1": user1,
        "user2": user2,
        "group1": group1,
        "group2": group2,
        "member1": member1,
        "member2": member2,
        "config1": config1,
    }


@pytest.fixture
async def unauthed_client(sec_engine, sec_session):
    """HTTP client WITHOUT auth — should get 401."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def authed_client_user1(sec_engine, sec_session, sec_data):
    """HTTP client authenticated as user1."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=sec_data["user1"].id,
            group_id=sec_data["group1"].id,
            role="parent",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Auth enforcement tests (401)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_requires_auth(unauthed_client):
    """POST /assign without auth returns 401."""
    resp = await unauthed_client.post("/api/v1/age-tier/assign", json={
        "member_id": str(uuid.uuid4()),
        "date_of_birth": "2016-05-15T00:00:00Z",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_member_requires_auth(unauthed_client):
    """GET /member/{id} without auth returns 401."""
    resp = await unauthed_client.get(f"/api/v1/age-tier/member/{uuid.uuid4()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_permissions_requires_auth(unauthed_client):
    """GET /member/{id}/permissions without auth returns 401."""
    resp = await unauthed_client.get(f"/api/v1/age-tier/member/{uuid.uuid4()}/permissions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_check_permission_requires_auth(unauthed_client):
    """GET /member/{id}/check/{perm} without auth returns 401."""
    resp = await unauthed_client.get(
        f"/api/v1/age-tier/member/{uuid.uuid4()}/check/can_post"
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authenticated endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_member_tier_authed(authed_client_user1, sec_data):
    """Authenticated user can fetch their group member's tier."""
    resp = await authed_client_user1.get(
        f"/api/v1/age-tier/member/{sec_data['member1'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "young"
    assert "permissions" in body


@pytest.mark.asyncio
async def test_get_permissions_authed(authed_client_user1, sec_data):
    """Authenticated user can fetch permissions."""
    resp = await authed_client_user1.get(
        f"/api/v1/age-tier/member/{sec_data['member1'].id}/permissions"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["permissions"]["can_post"] is True
    assert body["permissions"]["can_message"] is False


@pytest.mark.asyncio
async def test_check_permission_authed(authed_client_user1, sec_data):
    """Authenticated user can check a permission."""
    resp = await authed_client_user1.get(
        f"/api/v1/age-tier/member/{sec_data['member1'].id}/check/can_post"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["allowed"] is True
    assert body["tier"] == "young"


@pytest.mark.asyncio
async def test_assign_tier_authed(authed_client_user1, sec_data):
    """Authenticated user can assign tier to their member."""
    resp = await authed_client_user1.post("/api/v1/age-tier/assign", json={
        "member_id": str(sec_data["member1"].id),
        "date_of_birth": "2016-05-15T00:00:00Z",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "young"


@pytest.mark.asyncio
async def test_get_nonexistent_member_404(authed_client_user1):
    """Fetching tier for nonexistent member returns 404."""
    resp = await authed_client_user1.get(
        f"/api/v1/age-tier/member/{uuid.uuid4()}"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_assign_invalid_age_422(authed_client_user1, sec_data):
    """Assigning tier for age outside range returns 422."""
    resp = await authed_client_user1.post("/api/v1/age-tier/assign", json={
        "member_id": str(sec_data["member1"].id),
        "date_of_birth": "2025-01-01T00:00:00Z",  # Age ~1, outside range
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_missing_member_id(authed_client_user1):
    """Missing member_id returns 422."""
    resp = await authed_client_user1.post("/api/v1/age-tier/assign", json={
        "date_of_birth": "2016-05-15T00:00:00Z",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_assign_invalid_jurisdiction(authed_client_user1, sec_data):
    """Jurisdiction > 2 chars returns 422."""
    resp = await authed_client_user1.post("/api/v1/age-tier/assign", json={
        "member_id": str(sec_data["member1"].id),
        "date_of_birth": "2016-05-15T00:00:00Z",
        "jurisdiction": "USA",  # Too long
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Cross-group authorization tests (403)
# ---------------------------------------------------------------------------


@pytest.fixture
async def authed_client_user2(sec_engine, sec_session, sec_data):
    """HTTP client authenticated as user2 (owns group2)."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=sec_data["user2"].id,
            group_id=sec_data["group2"].id,
            role="parent",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_cross_group_get_member_tier_forbidden(authed_client_user2, sec_data):
    """User2 cannot GET tier for member1 (belongs to group1) — returns 403."""
    resp = await authed_client_user2.get(
        f"/api/v1/age-tier/member/{sec_data['member1'].id}"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cross_group_assign_tier_forbidden(authed_client_user2, sec_data):
    """User2 cannot POST /assign for member1 (belongs to group1) — returns 403."""
    resp = await authed_client_user2.post("/api/v1/age-tier/assign", json={
        "member_id": str(sec_data["member1"].id),
        "date_of_birth": "2016-05-15T00:00:00Z",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cross_group_get_permissions_forbidden(authed_client_user2, sec_data):
    """User2 cannot GET permissions for member1 (belongs to group1) — returns 403."""
    resp = await authed_client_user2.get(
        f"/api/v1/age-tier/member/{sec_data['member1'].id}/permissions"
    )
    assert resp.status_code == 403
