"""E2E tests for Google Admin Console integration endpoints."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client, email=None):
    """Register a user and return the access token."""
    if email is None:
        email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "School Admin",
        "account_type": "school",
        "privacy_notice_accepted": True,
    })
    return reg.json()["access_token"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """AsyncClient wired to the test app with committing DB session."""
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

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    # Reset integration state
    from src.integrations.google_admin import integration
    integration.reset()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    integration.reset()
    await session.close()
    await engine.dispose()


@pytest.fixture
async def auth_headers(client):
    """Get auth headers by registering and logging in."""
    token = await _register_and_login(client)
    return {"Authorization": f"Bearer {token}"}


PREFIX = "/api/v1/integrations/google-admin"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_school(client, auth_headers):
    """POST /google-admin/schools registers a school."""
    resp = await client.post(f"{PREFIX}/schools", json={
        "school_id": "sch-1",
        "school_name": "Lincoln High",
        "admin_email": "admin@lincoln.com",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["school_id"] == "sch-1"
    assert data["status"] == "registered"


@pytest.mark.asyncio
async def test_register_school_duplicate(client, auth_headers):
    """Registering the same school twice returns 422."""
    payload = {"school_id": "sch-dup", "school_name": "Dup School", "admin_email": "a@b.com"}
    await client.post(f"{PREFIX}/schools", json=payload, headers=auth_headers)
    resp = await client.post(f"{PREFIX}/schools", json=payload, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_school_invalid_email(client, auth_headers):
    """Invalid email returns 422."""
    resp = await client.post(f"{PREFIX}/schools", json={
        "school_id": "sch-bad", "school_name": "Bad", "admin_email": "not-email",
    }, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_deployment_status(client, auth_headers):
    """GET deployment status after registering a school."""
    await client.post(f"{PREFIX}/schools", json={
        "school_id": "sch-2", "school_name": "School 2", "admin_email": "a@b.com",
    }, headers=auth_headers)
    resp = await client.get(f"{PREFIX}/schools/sch-2/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_devices"] == 0
    assert data["deployment_percentage"] == 0.0


@pytest.mark.asyncio
async def test_get_deployment_status_not_found(client, auth_headers):
    """Deployment status for missing school returns 404."""
    resp = await client.get(f"{PREFIX}/schools/missing/status", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_device(client, auth_headers):
    """POST adds a device to a school."""
    await client.post(f"{PREFIX}/schools", json={
        "school_id": "sch-3", "school_name": "School 3", "admin_email": "a@b.com",
    }, headers=auth_headers)
    resp = await client.post(f"{PREFIX}/schools/sch-3/devices", json={
        "device_id": "dev-1", "serial_number": "SN001",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["device_id"] == "dev-1"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_add_device_school_not_found(client, auth_headers):
    """Adding device to missing school returns 404."""
    resp = await client.post(f"{PREFIX}/schools/missing/devices", json={
        "device_id": "dev-x",
    }, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_device_status(client, auth_headers):
    """PATCH updates a device status."""
    await client.post(f"{PREFIX}/schools", json={
        "school_id": "sch-4", "school_name": "School 4", "admin_email": "a@b.com",
    }, headers=auth_headers)
    await client.post(f"{PREFIX}/schools/sch-4/devices", json={"device_id": "dev-1"}, headers=auth_headers)
    resp = await client.patch(f"{PREFIX}/devices/sch-4/dev-1", json={"status": "deployed"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deployed"
    assert data["last_sync"] is not None


@pytest.mark.asyncio
async def test_update_device_status_invalid(client, auth_headers):
    """Invalid status returns 422."""
    await client.post(f"{PREFIX}/schools", json={
        "school_id": "sch-5", "school_name": "School 5", "admin_email": "a@b.com",
    }, headers=auth_headers)
    await client.post(f"{PREFIX}/schools/sch-5/devices", json={"device_id": "dev-1"}, headers=auth_headers)
    resp = await client.patch(f"{PREFIX}/devices/sch-5/dev-1", json={"status": "bogus"}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_device_not_found(client, auth_headers):
    """Updating missing device returns 404."""
    await client.post(f"{PREFIX}/schools", json={
        "school_id": "sch-6", "school_name": "School 6", "admin_email": "a@b.com",
    }, headers=auth_headers)
    resp = await client.patch(f"{PREFIX}/devices/sch-6/no-device", json={"status": "deployed"}, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_devices(client, auth_headers):
    """GET lists all devices for a school."""
    await client.post(f"{PREFIX}/schools", json={
        "school_id": "sch-7", "school_name": "School 7", "admin_email": "a@b.com",
    }, headers=auth_headers)
    await client.post(f"{PREFIX}/schools/sch-7/devices", json={"device_id": "d1"}, headers=auth_headers)
    await client.post(f"{PREFIX}/schools/sch-7/devices", json={"device_id": "d2"}, headers=auth_headers)
    resp = await client.get(f"{PREFIX}/schools/sch-7/devices", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["devices"]) == 2


@pytest.mark.asyncio
async def test_list_devices_filtered(client, auth_headers):
    """GET with status filter returns matching devices only."""
    await client.post(f"{PREFIX}/schools", json={
        "school_id": "sch-8", "school_name": "School 8", "admin_email": "a@b.com",
    }, headers=auth_headers)
    await client.post(f"{PREFIX}/schools/sch-8/devices", json={"device_id": "d1"}, headers=auth_headers)
    await client.post(f"{PREFIX}/schools/sch-8/devices", json={"device_id": "d2"}, headers=auth_headers)
    await client.patch(f"{PREFIX}/devices/sch-8/d1", json={"status": "deployed"}, headers=auth_headers)
    resp = await client.get(f"{PREFIX}/schools/sch-8/devices", params={"status": "deployed"}, headers=auth_headers)
    assert resp.status_code == 200
    devices = resp.json()["devices"]
    assert len(devices) == 1
    assert devices[0]["device_id"] == "d1"


@pytest.mark.asyncio
async def test_list_devices_school_not_found(client, auth_headers):
    """List devices for missing school returns 404."""
    resp = await client.get(f"{PREFIX}/schools/missing/devices", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_push_policy(client, auth_headers):
    """POST pushes a policy to a school."""
    await client.post(f"{PREFIX}/schools", json={
        "school_id": "sch-9", "school_name": "School 9", "admin_email": "a@b.com",
    }, headers=auth_headers)
    resp = await client.post(f"{PREFIX}/schools/sch-9/policy", json={
        "policy": {"content_filtering": True, "safe_search": True},
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "policy_pushed"


@pytest.mark.asyncio
async def test_push_policy_school_not_found(client, auth_headers):
    """Push policy to missing school returns 404."""
    resp = await client.post(f"{PREFIX}/schools/missing/policy", json={
        "policy": {"k": "v"},
    }, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_force_install(client, auth_headers):
    """POST configures force-install."""
    await client.post(f"{PREFIX}/schools", json={
        "school_id": "sch-10", "school_name": "School 10", "admin_email": "a@b.com",
    }, headers=auth_headers)
    resp = await client.post(f"{PREFIX}/schools/sch-10/force-install", json={
        "extension_id": "ext-abc123",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "force_install_configured"
    assert data["extension_id"] == "ext-abc123"


@pytest.mark.asyncio
async def test_force_install_school_not_found(client, auth_headers):
    """Force install for missing school returns 404."""
    resp = await client.post(f"{PREFIX}/schools/missing/force-install", json={
        "extension_id": "ext-1",
    }, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_full_deployment_flow(client, auth_headers):
    """Full flow: register -> add devices -> deploy -> check status."""
    # Register
    resp = await client.post(f"{PREFIX}/schools", json={
        "school_id": "full", "school_name": "Full Flow", "admin_email": "admin@full.com",
    }, headers=auth_headers)
    assert resp.status_code == 201

    # Add devices
    for i in range(3):
        resp = await client.post(f"{PREFIX}/schools/full/devices", json={
            "device_id": f"dev-{i}",
        }, headers=auth_headers)
        assert resp.status_code == 201

    # Deploy two
    await client.patch(f"{PREFIX}/devices/full/dev-0", json={"status": "deployed"}, headers=auth_headers)
    await client.patch(f"{PREFIX}/devices/full/dev-1", json={"status": "deployed"}, headers=auth_headers)

    # Check status
    resp = await client.get(f"{PREFIX}/schools/full/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_devices"] == 3
    assert data["deployed"] == 2
    assert data["pending"] == 1
    assert abs(data["deployment_percentage"] - 66.67) < 1.0

    # Push policy
    resp = await client.post(f"{PREFIX}/schools/full/policy", json={
        "policy": {"monitoring_level": "strict"},
    }, headers=auth_headers)
    assert resp.status_code == 200

    # Force install
    resp = await client.post(f"{PREFIX}/schools/full/force-install", json={
        "extension_id": "bhapi-ext-v2",
    }, headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_deployment_status_after_error(client, auth_headers):
    """Error devices are correctly tracked."""
    await client.post(f"{PREFIX}/schools", json={
        "school_id": "err", "school_name": "Error School", "admin_email": "a@b.com",
    }, headers=auth_headers)
    await client.post(f"{PREFIX}/schools/err/devices", json={"device_id": "d1"}, headers=auth_headers)
    await client.patch(f"{PREFIX}/devices/err/d1", json={"status": "error"}, headers=auth_headers)

    resp = await client.get(f"{PREFIX}/schools/err/status", headers=auth_headers)
    data = resp.json()
    assert data["errors"] == 1
    assert data["deployment_percentage"] == 0.0
