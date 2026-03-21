"""End-to-end tests for the device agent module."""

import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.device_agent.models import ScreenTimeRecord
from src.device_agent.service import record_app_usage, update_screen_time
from src.device_agent.schemas import AppUsageCreate
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def e2e_engine():
    """Create an E2E test engine."""
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
    """Create an E2E test session."""
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def e2e_data(e2e_session):
    """Create test data for E2E tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"e2e-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="E2E Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()

    group = Group(
        id=uuid.uuid4(), name="E2E Family", type="family", owner_id=user.id,
    )
    e2e_session.add(group)
    await e2e_session.flush()

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="E2E Child",
        date_of_birth=datetime(2016, 5, 15, tzinfo=timezone.utc),
    )
    e2e_session.add(member)
    await e2e_session.flush()

    return {"user": user, "group": group, "member": member}


@pytest.fixture
async def e2e_client(e2e_engine, e2e_session, e2e_data):
    """HTTP client authenticated as the E2E user."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=e2e_data["user"].id,
            group_id=e2e_data["group"].id,
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
# POST /api/v1/device/sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_device_session(e2e_client, e2e_data):
    """POST /device/sessions creates a session."""
    resp = await e2e_client.post("/api/v1/device/sessions", json={
        "member_id": str(e2e_data["member"].id),
        "device_id": "iphone-14",
        "device_type": "ios",
        "os_version": "18.3",
        "app_version": "1.0.0",
        "started_at": "2026-03-21T10:00:00Z",
        "battery_level": 90.0,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["device_id"] == "iphone-14"
    assert body["device_type"] == "ios"
    assert body["battery_level"] == 90.0


@pytest.mark.asyncio
async def test_create_device_session_minimal(e2e_client, e2e_data):
    """POST /device/sessions with minimal fields."""
    resp = await e2e_client.post("/api/v1/device/sessions", json={
        "member_id": str(e2e_data["member"].id),
        "device_id": "android-basic",
        "device_type": "android",
        "started_at": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_device_session_invalid_type(e2e_client, e2e_data):
    """POST /device/sessions with invalid device_type returns 422."""
    resp = await e2e_client.post("/api/v1/device/sessions", json={
        "member_id": str(e2e_data["member"].id),
        "device_id": "unknown",
        "device_type": "smartwatch",
        "started_at": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/device/usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_usage(e2e_client, e2e_data):
    """POST /device/usage records app usage."""
    resp = await e2e_client.post("/api/v1/device/usage", json={
        "member_id": str(e2e_data["member"].id),
        "app_name": "Instagram",
        "bundle_id": "com.instagram.android",
        "category": "social",
        "started_at": "2026-03-21T10:00:00Z",
        "foreground_minutes": 25.0,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["app_name"] == "Instagram"
    assert body["foreground_minutes"] == 25.0


@pytest.mark.asyncio
async def test_record_usage_missing_bundle_id(e2e_client, e2e_data):
    """POST /device/usage without bundle_id returns 422."""
    resp = await e2e_client.post("/api/v1/device/usage", json={
        "member_id": str(e2e_data["member"].id),
        "app_name": "SomeApp",
        "started_at": "2026-03-21T10:00:00Z",
        "foreground_minutes": 5.0,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_record_usage_invalid_category(e2e_client, e2e_data):
    """POST /device/usage with invalid category returns 422."""
    resp = await e2e_client.post("/api/v1/device/usage", json={
        "member_id": str(e2e_data["member"].id),
        "app_name": "App",
        "bundle_id": "com.test.app",
        "category": "invalid_category",
        "started_at": "2026-03-21T10:00:00Z",
        "foreground_minutes": 5.0,
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/device/usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_usage_empty(e2e_client, e2e_data):
    """GET /device/usage returns empty list when no records."""
    resp = await e2e_client.get(
        f"/api/v1/device/usage?member_id={e2e_data['member'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_get_usage_after_recording(e2e_client, e2e_data):
    """GET /device/usage returns records after POST."""
    # Record usage first
    await e2e_client.post("/api/v1/device/usage", json={
        "member_id": str(e2e_data["member"].id),
        "app_name": "YouTube",
        "bundle_id": "com.google.android.youtube",
        "category": "entertainment",
        "started_at": "2026-03-21T14:00:00Z",
        "foreground_minutes": 40.0,
    })

    resp = await e2e_client.get(
        f"/api/v1/device/usage?member_id={e2e_data['member'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(item["app_name"] == "YouTube" for item in body["items"])


@pytest.mark.asyncio
async def test_get_usage_with_category_filter(e2e_client, e2e_data):
    """GET /device/usage with category filter."""
    await e2e_client.post("/api/v1/device/usage", json={
        "member_id": str(e2e_data["member"].id),
        "app_name": "Roblox",
        "bundle_id": "com.roblox.client",
        "category": "games",
        "started_at": "2026-03-21T15:00:00Z",
        "foreground_minutes": 30.0,
    })

    resp = await e2e_client.get(
        f"/api/v1/device/usage?member_id={e2e_data['member'].id}&category=games"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["category"] == "games" for item in body["items"])


@pytest.mark.asyncio
async def test_get_usage_pagination(e2e_client, e2e_data):
    """GET /device/usage supports offset/limit."""
    for i in range(3):
        await e2e_client.post("/api/v1/device/usage", json={
            "member_id": str(e2e_data["member"].id),
            "app_name": f"PaginApp{i}",
            "bundle_id": f"com.test.pagin{i}",
            "started_at": f"2026-03-21T1{i}:00:00Z",
            "foreground_minutes": 5.0,
        })

    resp = await e2e_client.get(
        f"/api/v1/device/usage?member_id={e2e_data['member'].id}&limit=2&offset=0"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) <= 2


# ---------------------------------------------------------------------------
# GET /api/v1/device/screen-time
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_screen_time_not_found(e2e_client, e2e_data):
    """GET /device/screen-time returns 404 when no summary exists."""
    resp = await e2e_client.get(
        f"/api/v1/device/screen-time?member_id={e2e_data['member'].id}&target_date=2026-01-01"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_screen_time_after_sync(e2e_client, e2e_data):
    """Screen time is correct after batch sync."""
    resp = await e2e_client.post("/api/v1/device/sync", json={
        "member_id": str(e2e_data["member"].id),
        "device_id": "sync-device",
        "device_type": "ios",
        "usage_records": [
            {
                "member_id": str(e2e_data["member"].id),
                "app_name": "TikTok",
                "bundle_id": "com.tiktok.app",
                "category": "social",
                "started_at": "2026-03-21T10:00:00Z",
                "foreground_minutes": 30.0,
            },
            {
                "member_id": str(e2e_data["member"].id),
                "app_name": "Chrome",
                "bundle_id": "com.android.chrome",
                "category": "productivity",
                "started_at": "2026-03-21T11:00:00Z",
                "foreground_minutes": 20.0,
            },
        ],
    })
    assert resp.status_code == 201

    resp2 = await e2e_client.get(
        f"/api/v1/device/screen-time?member_id={e2e_data['member'].id}&target_date=2026-03-21"
    )
    assert resp2.status_code == 200
    body = resp2.json()
    assert body["total_minutes"] == 50.0


# ---------------------------------------------------------------------------
# POST /api/v1/device/sync
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_creates_records(e2e_client, e2e_data):
    """POST /device/sync creates sessions and usage records."""
    resp = await e2e_client.post("/api/v1/device/sync", json={
        "member_id": str(e2e_data["member"].id),
        "device_id": "sync-dev",
        "device_type": "android",
        "sessions": [
            {
                "member_id": str(e2e_data["member"].id),
                "device_id": "sync-dev",
                "device_type": "android",
                "started_at": "2026-03-21T08:00:00Z",
            },
        ],
        "usage_records": [
            {
                "member_id": str(e2e_data["member"].id),
                "app_name": "WhatsApp",
                "bundle_id": "com.whatsapp",
                "category": "social",
                "started_at": "2026-03-21T08:05:00Z",
                "foreground_minutes": 10.0,
            },
        ],
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["sessions_created"] == 1
    assert body["usage_records_created"] == 1
    assert body["screen_time_updated"] is True


@pytest.mark.asyncio
async def test_sync_empty(e2e_client, e2e_data):
    """POST /device/sync with empty data returns zeros."""
    resp = await e2e_client.post("/api/v1/device/sync", json={
        "member_id": str(e2e_data["member"].id),
        "device_id": "sync-empty",
        "device_type": "ios",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["sessions_created"] == 0
    assert body["usage_records_created"] == 0


@pytest.mark.asyncio
async def test_sync_missing_device_id(e2e_client, e2e_data):
    """POST /device/sync without device_id returns 422."""
    resp = await e2e_client.post("/api/v1/device/sync", json={
        "member_id": str(e2e_data["member"].id),
        "device_type": "ios",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/device/screen-time/range
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_screen_time_range_empty(e2e_client, e2e_data):
    """GET /device/screen-time/range returns empty list when no data."""
    resp = await e2e_client.get(
        f"/api/v1/device/screen-time/range?member_id={e2e_data['member'].id}"
        "&start_date=2026-03-01&end_date=2026-03-07"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_screen_time_range_after_sync(e2e_client, e2e_data):
    """GET /device/screen-time/range returns data after sync."""
    # Sync data for two different dates
    for day in [20, 21]:
        await e2e_client.post("/api/v1/device/sync", json={
            "member_id": str(e2e_data["member"].id),
            "device_id": "range-dev",
            "device_type": "ios",
            "usage_records": [
                {
                    "member_id": str(e2e_data["member"].id),
                    "app_name": f"App-{day}",
                    "bundle_id": f"com.test.app{day}",
                    "started_at": f"2026-03-{day}T10:00:00Z",
                    "foreground_minutes": 30.0,
                },
            ],
        })

    resp = await e2e_client.get(
        f"/api/v1/device/screen-time/range?member_id={e2e_data['member'].id}"
        "&start_date=2026-03-19&end_date=2026-03-22"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2


# ---------------------------------------------------------------------------
# Additional E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_response_has_required_fields(e2e_client, e2e_data):
    """Session response contains all expected fields."""
    resp = await e2e_client.post("/api/v1/device/sessions", json={
        "member_id": str(e2e_data["member"].id),
        "device_id": "field-check",
        "device_type": "ios",
        "started_at": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert "member_id" in body
    assert "group_id" in body
    assert "device_id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_usage_response_has_required_fields(e2e_client, e2e_data):
    """Usage response contains all expected fields."""
    resp = await e2e_client.post("/api/v1/device/usage", json={
        "member_id": str(e2e_data["member"].id),
        "app_name": "Fields App",
        "bundle_id": "com.test.fields",
        "started_at": "2026-03-21T10:00:00Z",
        "foreground_minutes": 5.0,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert "app_name" in body
    assert "bundle_id" in body
    assert "foreground_minutes" in body
    assert "category" in body


@pytest.mark.asyncio
async def test_sync_multiple_sessions(e2e_client, e2e_data):
    """Sync can create multiple sessions."""
    resp = await e2e_client.post("/api/v1/device/sync", json={
        "member_id": str(e2e_data["member"].id),
        "device_id": "multi-sess",
        "device_type": "android",
        "sessions": [
            {
                "member_id": str(e2e_data["member"].id),
                "device_id": "multi-sess",
                "device_type": "android",
                "started_at": "2026-03-21T{:02d}:00:00Z".format(8 + i),
            }
            for i in range(3)
        ],
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["sessions_created"] == 3


@pytest.mark.asyncio
async def test_usage_with_end_time(e2e_client, e2e_data):
    """Usage record can include ended_at."""
    resp = await e2e_client.post("/api/v1/device/usage", json={
        "member_id": str(e2e_data["member"].id),
        "app_name": "TimedApp",
        "bundle_id": "com.test.timed",
        "started_at": "2026-03-21T10:00:00Z",
        "ended_at": "2026-03-21T10:30:00Z",
        "foreground_minutes": 30.0,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["ended_at"] is not None


@pytest.mark.asyncio
async def test_screen_time_breakdown_structure(e2e_client, e2e_data):
    """Screen time response has correct breakdown structure."""
    # Create usage and sync
    await e2e_client.post("/api/v1/device/sync", json={
        "member_id": str(e2e_data["member"].id),
        "device_id": "breakdown-dev",
        "device_type": "ios",
        "usage_records": [
            {
                "member_id": str(e2e_data["member"].id),
                "app_name": "Discord",
                "bundle_id": "com.discord",
                "category": "social",
                "started_at": "2026-03-21T12:00:00Z",
                "foreground_minutes": 20.0,
            },
        ],
    })

    resp = await e2e_client.get(
        f"/api/v1/device/screen-time?member_id={e2e_data['member'].id}&target_date=2026-03-21"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "total_minutes" in body
    assert "app_breakdown" in body
    assert "category_breakdown" in body
    assert "pickups" in body


@pytest.mark.asyncio
async def test_usage_list_has_more_field(e2e_client, e2e_data):
    """Usage list response includes has_more pagination field."""
    resp = await e2e_client.get(
        f"/api/v1/device/usage?member_id={e2e_data['member'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "has_more" in body
    assert body["has_more"] is False
