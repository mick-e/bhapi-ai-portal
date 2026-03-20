"""Security tests for Google Admin Console integration."""

import uuid

import pytest
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
        email = f"sec-{uuid.uuid4().hex[:8]}@example.com"
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
async def sec_client():
    """Test client with committing DB session."""
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


PREFIX = "/api/v1/integrations/google-admin"


# ---------------------------------------------------------------------------
# Auth required tests — all endpoints must reject unauthenticated requests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_school_requires_auth(sec_client):
    """POST /google-admin/schools without auth returns 401/403."""
    resp = await sec_client.post(f"{PREFIX}/schools", json={
        "school_id": "s1", "school_name": "School", "admin_email": "a@b.com",
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_status_requires_auth(sec_client):
    """GET deployment status without auth returns 401/403."""
    resp = await sec_client.get(f"{PREFIX}/schools/s1/status")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_add_device_requires_auth(sec_client):
    """POST add device without auth returns 401/403."""
    resp = await sec_client.post(f"{PREFIX}/schools/s1/devices", json={
        "device_id": "d1",
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_device_requires_auth(sec_client):
    """PATCH device status without auth returns 401/403."""
    resp = await sec_client.patch(f"{PREFIX}/devices/s1/d1", json={
        "status": "deployed",
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_devices_requires_auth(sec_client):
    """GET list devices without auth returns 401/403."""
    resp = await sec_client.get(f"{PREFIX}/schools/s1/devices")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_push_policy_requires_auth(sec_client):
    """POST push policy without auth returns 401/403."""
    resp = await sec_client.post(f"{PREFIX}/schools/s1/policy", json={
        "policy": {"k": "v"},
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_force_install_requires_auth(sec_client):
    """POST force install without auth returns 401/403."""
    resp = await sec_client.post(f"{PREFIX}/schools/s1/force-install", json={
        "extension_id": "ext-1",
    })
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Input validation / injection prevention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_school_id_injection_prevention(sec_client):
    """School IDs with path traversal characters are handled safely."""
    token = await _register_and_login(sec_client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await sec_client.post(f"{PREFIX}/schools", json={
        "school_id": "../etc/passwd",
        "school_name": "Evil School",
        "admin_email": "evil@evil.com",
    }, headers=headers)
    # Should succeed (the ID is just a string key) but not cause issues
    assert resp.status_code == 201
    data = resp.json()
    assert data["school_id"] == "../etc/passwd"


@pytest.mark.asyncio
async def test_xss_in_school_name(sec_client):
    """XSS payload in school_name does not execute."""
    token = await _register_and_login(sec_client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await sec_client.post(f"{PREFIX}/schools", json={
        "school_id": "xss-test",
        "school_name": "<script>alert('xss')</script>",
        "admin_email": "a@b.com",
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["school_id"] == "xss-test"


@pytest.mark.asyncio
async def test_oversized_policy_payload(sec_client):
    """Large policy payload is handled without crashing."""
    token = await _register_and_login(sec_client)
    headers = {"Authorization": f"Bearer {token}"}
    await sec_client.post(f"{PREFIX}/schools", json={
        "school_id": "big", "school_name": "Big School", "admin_email": "a@b.com",
    }, headers=headers)
    big_policy = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
    resp = await sec_client.post(f"{PREFIX}/schools/big/policy", json={
        "policy": big_policy,
    }, headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_empty_extension_id_rejected(sec_client):
    """Empty extension_id is rejected with 422."""
    token = await _register_and_login(sec_client)
    headers = {"Authorization": f"Bearer {token}"}
    await sec_client.post(f"{PREFIX}/schools", json={
        "school_id": "empty-ext", "school_name": "School", "admin_email": "a@b.com",
    }, headers=headers)
    resp = await sec_client.post(f"{PREFIX}/schools/empty-ext/force-install", json={
        "extension_id": "",
    }, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_in_school_id_path(sec_client):
    """SQL injection in path parameter is handled safely."""
    token = await _register_and_login(sec_client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await sec_client.get(
        f"{PREFIX}/schools/'; DROP TABLE schools;--/status",
        headers=headers,
    )
    # Should return 404, not crash
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_bearer_token(sec_client):
    """Invalid bearer token returns 401."""
    headers = {"Authorization": "Bearer invalid-token-abc123"}
    resp = await sec_client.post(f"{PREFIX}/schools", json={
        "school_id": "s1", "school_name": "School", "admin_email": "a@b.com",
    }, headers=headers)
    assert resp.status_code in (401, 403)
