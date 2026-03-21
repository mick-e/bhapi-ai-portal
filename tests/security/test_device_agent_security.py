"""Security tests for the device agent module."""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
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
    """Create test data for security tests — two separate families."""
    user1 = User(
        id=uuid.uuid4(),
        email=f"sec1-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Parent 1",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user2 = User(
        id=uuid.uuid4(),
        email=f"sec2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Parent 2",
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

    return {
        "user1": user1, "user2": user2,
        "group1": group1, "group2": group2,
        "member1": member1, "member2": member2,
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
# 401 — Auth enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sessions_requires_auth(unauthed_client):
    """POST /device/sessions without auth returns 401."""
    resp = await unauthed_client.post("/api/v1/device/sessions", json={
        "member_id": str(uuid.uuid4()),
        "device_id": "test-device",
        "device_type": "ios",
        "started_at": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_usage_post_requires_auth(unauthed_client):
    """POST /device/usage without auth returns 401."""
    resp = await unauthed_client.post("/api/v1/device/usage", json={
        "member_id": str(uuid.uuid4()),
        "app_name": "App",
        "bundle_id": "com.test.app",
        "started_at": "2026-03-21T10:00:00Z",
        "foreground_minutes": 10.0,
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_usage_get_requires_auth(unauthed_client):
    """GET /device/usage without auth returns 401."""
    resp = await unauthed_client.get(
        f"/api/v1/device/usage?member_id={uuid.uuid4()}"
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_screen_time_requires_auth(unauthed_client):
    """GET /device/screen-time without auth returns 401."""
    resp = await unauthed_client.get(
        f"/api/v1/device/screen-time?member_id={uuid.uuid4()}"
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sync_requires_auth(unauthed_client):
    """POST /device/sync without auth returns 401."""
    resp = await unauthed_client.post("/api/v1/device/sync", json={
        "member_id": str(uuid.uuid4()),
        "device_id": "test",
        "device_type": "ios",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_screen_time_range_requires_auth(unauthed_client):
    """GET /device/screen-time/range without auth returns 401."""
    resp = await unauthed_client.get(
        f"/api/v1/device/screen-time/range?member_id={uuid.uuid4()}"
        "&start_date=2026-03-01&end_date=2026-03-07"
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 422 — Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sessions_invalid_device_type(authed_client_user1, sec_data):
    """POST /device/sessions with invalid device type returns 422."""
    resp = await authed_client_user1.post("/api/v1/device/sessions", json={
        "member_id": str(sec_data["member1"].id),
        "device_id": "dev",
        "device_type": "smartfridge",
        "started_at": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_usage_negative_minutes(authed_client_user1, sec_data):
    """POST /device/usage with negative foreground_minutes returns 422."""
    resp = await authed_client_user1.post("/api/v1/device/usage", json={
        "member_id": str(sec_data["member1"].id),
        "app_name": "App",
        "bundle_id": "com.test.app",
        "started_at": "2026-03-21T10:00:00Z",
        "foreground_minutes": -5.0,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_usage_missing_app_name(authed_client_user1, sec_data):
    """POST /device/usage without app_name returns 422."""
    resp = await authed_client_user1.post("/api/v1/device/usage", json={
        "member_id": str(sec_data["member1"].id),
        "bundle_id": "com.test.app",
        "started_at": "2026-03-21T10:00:00Z",
        "foreground_minutes": 5.0,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sync_missing_device_id(authed_client_user1, sec_data):
    """POST /device/sync without device_id returns 422."""
    resp = await authed_client_user1.post("/api/v1/device/sync", json={
        "member_id": str(sec_data["member1"].id),
        "device_type": "ios",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_battery_level_out_of_range(authed_client_user1, sec_data):
    """POST /device/sessions with battery_level > 100 returns 422."""
    resp = await authed_client_user1.post("/api/v1/device/sessions", json={
        "member_id": str(sec_data["member1"].id),
        "device_id": "dev",
        "device_type": "ios",
        "started_at": "2026-03-21T10:00:00Z",
        "battery_level": 150.0,
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Authenticated — valid operations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authed_can_create_session(authed_client_user1, sec_data):
    """Authenticated user can create a device session for their group member."""
    resp = await authed_client_user1.post("/api/v1/device/sessions", json={
        "member_id": str(sec_data["member1"].id),
        "device_id": "auth-dev",
        "device_type": "ios",
        "started_at": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_authed_can_record_usage(authed_client_user1, sec_data):
    """Authenticated user can record app usage."""
    resp = await authed_client_user1.post("/api/v1/device/usage", json={
        "member_id": str(sec_data["member1"].id),
        "app_name": "Safari",
        "bundle_id": "com.apple.safari",
        "started_at": "2026-03-21T10:00:00Z",
        "foreground_minutes": 15.0,
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_authed_can_get_usage(authed_client_user1, sec_data):
    """Authenticated user can get usage history."""
    resp = await authed_client_user1.get(
        f"/api/v1/device/usage?member_id={sec_data['member1'].id}"
    )
    assert resp.status_code == 200
