"""End-to-end tests for the location module — API endpoints."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
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
async def e2e_engine():
    """In-memory SQLite engine for E2E location tests."""
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
    """Session for E2E tests."""
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def e2e_data(e2e_session):
    """Seed user, group, and child member."""
    user = User(
        id=uuid.uuid4(),
        email=f"loc-e2e-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="E2E Location Parent",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="E2E Location Family",
        type="family",
        owner_id=user.id,
    )
    e2e_session.add(group)
    await e2e_session.flush()

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="child",
        display_name="E2E Child",
    )
    e2e_session.add(member)
    await e2e_session.flush()

    return {"user": user, "group": group, "member": member}


@pytest.fixture
async def e2e_client(e2e_engine, e2e_session, e2e_data):
    """HTTP client with auth and DB overrides."""
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
            role="owner",
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
# Test 1: Report location — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_location_happy_path(e2e_client, e2e_data):
    """POST /report creates a location record."""
    resp = await e2e_client.post("/api/v1/location/report", json={
        "member_id": str(e2e_data["member"].id),
        "latitude": 51.5074,
        "longitude": -0.1278,
        "accuracy": 10.0,
        "source": "gps",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })

    assert resp.status_code == 201
    body = resp.json()
    assert body is not None
    assert body["member_id"] == str(e2e_data["member"].id)


# ---------------------------------------------------------------------------
# Test 2: Report location — validation error on bad source
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_location_invalid_source(e2e_client, e2e_data):
    """POST /report returns 422 for an invalid source value."""
    resp = await e2e_client.post("/api/v1/location/report", json={
        "member_id": str(e2e_data["member"].id),
        "latitude": 51.5,
        "longitude": -0.1,
        "accuracy": 5.0,
        "source": "bluetooth",  # invalid
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test 3: Get current location — no data returns null
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_location_no_data(e2e_client, e2e_data):
    """GET /{child_id}/current returns null when no location recorded."""
    resp = await e2e_client.get(f"/api/v1/location/{e2e_data['member'].id}/current")

    assert resp.status_code == 200
    assert resp.json() is None


# ---------------------------------------------------------------------------
# Test 4: Full flow — report then get current
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_then_get_current(e2e_client, e2e_data):
    """Report location then immediately retrieve it."""
    lat, lng = 40.7128, -74.0060

    await e2e_client.post("/api/v1/location/report", json={
        "member_id": str(e2e_data["member"].id),
        "latitude": lat,
        "longitude": lng,
        "accuracy": 5.0,
        "source": "gps",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })

    resp = await e2e_client.get(f"/api/v1/location/{e2e_data['member'].id}/current")

    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert abs(body["latitude"] - lat) < 0.0001
    assert abs(body["longitude"] - lng) < 0.0001


# ---------------------------------------------------------------------------
# Test 5: Get location history — paginated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_location_history_paginated(e2e_client, e2e_data):
    """GET /{child_id}/history returns paginated results."""
    for i in range(5):
        await e2e_client.post("/api/v1/location/report", json={
            "member_id": str(e2e_data["member"].id),
            "latitude": 51.5 + i * 0.001,
            "longitude": -0.1,
            "accuracy": 5.0,
            "source": "gps",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })

    resp = await e2e_client.get(
        f"/api/v1/location/{e2e_data['member'].id}/history",
        params={"offset": 0, "limit": 3},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 3
    assert body["has_more"] is True


# ---------------------------------------------------------------------------
# Test 6: Create geofence — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_geofence_happy_path(e2e_client, e2e_data):
    """POST /geofences creates a geofence."""
    resp = await e2e_client.post("/api/v1/location/geofences", json={
        "member_id": str(e2e_data["member"].id),
        "name": "School",
        "latitude": 51.5,
        "longitude": -0.1,
        "radius_meters": 200.0,
        "notify_on_enter": True,
        "notify_on_exit": True,
    })

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "School"
    assert body["radius_meters"] == 200.0


# ---------------------------------------------------------------------------
# Test 7: List geofences
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_geofences(e2e_client, e2e_data):
    """GET /geofences returns all geofences for a member."""
    for i in range(2):
        await e2e_client.post("/api/v1/location/geofences", json={
            "member_id": str(e2e_data["member"].id),
            "name": f"Fence {i}",
            "latitude": 51.5 + i * 0.01,
            "longitude": -0.1,
            "radius_meters": 100.0,
        })

    resp = await e2e_client.get(
        "/api/v1/location/geofences",
        params={"member_id": str(e2e_data["member"].id)},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


# ---------------------------------------------------------------------------
# Test 8: Delete geofence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_geofence(e2e_client, e2e_data):
    """DELETE /geofences/{id} removes the geofence."""
    create_resp = await e2e_client.post("/api/v1/location/geofences", json={
        "member_id": str(e2e_data["member"].id),
        "name": "Temp",
        "latitude": 51.5,
        "longitude": -0.1,
        "radius_meters": 100.0,
    })
    assert create_resp.status_code == 201
    fence_id = create_resp.json()["id"]

    delete_resp = await e2e_client.delete(f"/api/v1/location/geofences/{fence_id}")
    assert delete_resp.status_code == 204

    list_resp = await e2e_client.get(
        "/api/v1/location/geofences",
        params={"member_id": str(e2e_data["member"].id)},
    )
    assert list_resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Test 9: Kill switch activate → report fails → deactivate → report succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_switch_blocks_then_allows(e2e_client, e2e_data):
    """Full kill switch lifecycle: activate blocks, deactivate allows reporting."""
    # Activate
    ks_resp = await e2e_client.post(f"/api/v1/location/{e2e_data['member'].id}/kill-switch")
    assert ks_resp.status_code == 201

    # Report should return null (kill switch active)
    report_resp = await e2e_client.post("/api/v1/location/report", json={
        "member_id": str(e2e_data["member"].id),
        "latitude": 51.5,
        "longitude": -0.1,
        "accuracy": 5.0,
        "source": "gps",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    assert report_resp.status_code == 201
    assert report_resp.json() is None  # blocked

    # Deactivate
    deact_resp = await e2e_client.delete(f"/api/v1/location/{e2e_data['member'].id}/kill-switch")
    assert deact_resp.status_code == 204

    # Report should succeed now
    report_resp2 = await e2e_client.post("/api/v1/location/report", json={
        "member_id": str(e2e_data["member"].id),
        "latitude": 51.5,
        "longitude": -0.1,
        "accuracy": 5.0,
        "source": "gps",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    assert report_resp2.status_code == 201
    assert report_resp2.json() is not None


# ---------------------------------------------------------------------------
# Test 10: Get kill switch status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_kill_switch_status(e2e_client, e2e_data):
    """GET /{child_id}/kill-switch returns current kill switch state."""
    # Before activation: None
    resp = await e2e_client.get(f"/api/v1/location/{e2e_data['member'].id}/kill-switch")
    assert resp.status_code == 200
    assert resp.json() is None

    # After activation: active record
    await e2e_client.post(f"/api/v1/location/{e2e_data['member'].id}/kill-switch")
    resp = await e2e_client.get(f"/api/v1/location/{e2e_data['member'].id}/kill-switch")
    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert body["deactivated_at"] is None


# ---------------------------------------------------------------------------
# Test 11: GDPR delete — removes all location data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gdpr_delete_history(e2e_client, e2e_data):
    """DELETE /{child_id}/history removes all location data (GDPR)."""
    for _ in range(3):
        await e2e_client.post("/api/v1/location/report", json={
            "member_id": str(e2e_data["member"].id),
            "latitude": 51.5,
            "longitude": -0.1,
            "accuracy": 5.0,
            "source": "gps",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })

    resp = await e2e_client.delete(f"/api/v1/location/{e2e_data['member'].id}/history")

    assert resp.status_code == 200
    body = resp.json()
    assert body["records_deleted"] == 3
    assert body["status"] == "erased"


# ---------------------------------------------------------------------------
# Test 12: Audit log — accessible after location reads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_log_accessible(e2e_client, e2e_data):
    """GET /{child_id}/audit-log returns entries after location access."""
    await e2e_client.post("/api/v1/location/report", json={
        "member_id": str(e2e_data["member"].id),
        "latitude": 51.5,
        "longitude": -0.1,
        "accuracy": 5.0,
        "source": "gps",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    await e2e_client.get(f"/api/v1/location/{e2e_data['member'].id}/current")

    resp = await e2e_client.get(f"/api/v1/location/{e2e_data['member'].id}/audit-log")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


# ---------------------------------------------------------------------------
# Test 13: Geofence full CRUD flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geofence_full_crud(e2e_client, e2e_data):
    """Full geofence CRUD: create, list, delete, verify removal."""
    create_resp = await e2e_client.post("/api/v1/location/geofences", json={
        "member_id": str(e2e_data["member"].id),
        "name": "CRUD Test",
        "latitude": 51.5,
        "longitude": -0.1,
        "radius_meters": 150.0,
    })
    assert create_resp.status_code == 201
    fence_id = create_resp.json()["id"]

    list_resp = await e2e_client.get(
        "/api/v1/location/geofences",
        params={"member_id": str(e2e_data["member"].id)},
    )
    assert list_resp.json()["total"] == 1

    del_resp = await e2e_client.delete(f"/api/v1/location/geofences/{fence_id}")
    assert del_resp.status_code == 204

    list_resp2 = await e2e_client.get(
        "/api/v1/location/geofences",
        params={"member_id": str(e2e_data["member"].id)},
    )
    assert list_resp2.json()["total"] == 0


# ---------------------------------------------------------------------------
# Test 14: Report location — validation error on out-of-range lat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_location_out_of_range_lat(e2e_client, e2e_data):
    """POST /report returns 422 when latitude is out of range."""
    resp = await e2e_client.post("/api/v1/location/report", json={
        "member_id": str(e2e_data["member"].id),
        "latitude": 95.0,  # invalid
        "longitude": -0.1,
        "accuracy": 5.0,
        "source": "gps",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test 15: History pagination — has_more correctness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_history_has_more_false_when_exhausted(e2e_client, e2e_data):
    """GET /{child_id}/history sets has_more=False on last page."""
    for i in range(2):
        await e2e_client.post("/api/v1/location/report", json={
            "member_id": str(e2e_data["member"].id),
            "latitude": 51.5 + i * 0.001,
            "longitude": -0.1,
            "accuracy": 5.0,
            "source": "gps",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })

    resp = await e2e_client.get(
        f"/api/v1/location/{e2e_data['member'].id}/history",
        params={"offset": 0, "limit": 10},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["has_more"] is False
    assert body["total"] == 2


# ---------------------------------------------------------------------------
# Test 16: Geofence max limit enforced via API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geofence_limit_enforced_via_api(e2e_client, e2e_data):
    """POST /geofences returns 422 after 10 geofences."""
    for i in range(10):
        await e2e_client.post("/api/v1/location/geofences", json={
            "member_id": str(e2e_data["member"].id),
            "name": f"Zone {i}",
            "latitude": 51.5 + i * 0.01,
            "longitude": -0.1,
            "radius_meters": 100.0,
        })

    resp = await e2e_client.post("/api/v1/location/geofences", json={
        "member_id": str(e2e_data["member"].id),
        "name": "Overflow",
        "latitude": 52.0,
        "longitude": -0.1,
        "radius_meters": 100.0,
    })

    assert resp.status_code == 422
