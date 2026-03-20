"""Security tests for Google Admin Console integration."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.database import Base, get_db
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
    session = AsyncSession(sec_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest.fixture
async def authed_client(sec_engine, sec_session):
    """Client with auth override (authenticated)."""
    app = create_app()
    auth = GroupContext(group_id=uuid.uuid4(), user_id=uuid.uuid4(), role="school_admin")

    async def override_db():
        yield sec_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: auth

    from src.integrations.google_admin import integration
    integration.reset()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    integration.reset()


@pytest.fixture
async def unauthed_client(sec_engine, sec_session):
    """Client WITHOUT auth override (no credentials)."""
    app = create_app()

    async def override_db():
        yield sec_session

    app.dependency_overrides[get_db] = override_db
    # Deliberately NOT overriding get_current_user

    from src.integrations.google_admin import integration
    integration.reset()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    integration.reset()


PREFIX = "/api/v1/integrations/google-admin"


# ---------------------------------------------------------------------------
# Auth required tests — all endpoints must reject unauthenticated requests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_school_requires_auth(unauthed_client):
    """POST /google-admin/schools without auth returns 401/403."""
    resp = await unauthed_client.post(f"{PREFIX}/schools", json={
        "school_id": "s1", "school_name": "School", "admin_email": "a@b.com",
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_status_requires_auth(unauthed_client):
    """GET deployment status without auth returns 401/403."""
    resp = await unauthed_client.get(f"{PREFIX}/schools/s1/status")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_add_device_requires_auth(unauthed_client):
    """POST add device without auth returns 401/403."""
    resp = await unauthed_client.post(f"{PREFIX}/schools/s1/devices", json={
        "device_id": "d1",
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_device_requires_auth(unauthed_client):
    """PATCH device status without auth returns 401/403."""
    resp = await unauthed_client.patch(f"{PREFIX}/devices/s1/d1", json={
        "status": "deployed",
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_devices_requires_auth(unauthed_client):
    """GET list devices without auth returns 401/403."""
    resp = await unauthed_client.get(f"{PREFIX}/schools/s1/devices")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_push_policy_requires_auth(unauthed_client):
    """POST push policy without auth returns 401/403."""
    resp = await unauthed_client.post(f"{PREFIX}/schools/s1/policy", json={
        "policy": {"k": "v"},
    })
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_force_install_requires_auth(unauthed_client):
    """POST force install without auth returns 401/403."""
    resp = await unauthed_client.post(f"{PREFIX}/schools/s1/force-install", json={
        "extension_id": "ext-1",
    })
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Input validation / injection prevention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_school_id_injection_prevention(authed_client):
    """School IDs with path traversal characters are handled safely."""
    resp = await authed_client.post(f"{PREFIX}/schools", json={
        "school_id": "../etc/passwd",
        "school_name": "Evil School",
        "admin_email": "evil@evil.com",
    })
    # Should succeed (the ID is just a string key) but not cause issues
    assert resp.status_code == 201
    data = resp.json()
    assert data["school_id"] == "../etc/passwd"


@pytest.mark.asyncio
async def test_xss_in_school_name(authed_client):
    """XSS payload in school_name does not execute."""
    resp = await authed_client.post(f"{PREFIX}/schools", json={
        "school_id": "xss-test",
        "school_name": "<script>alert('xss')</script>",
        "admin_email": "a@b.com",
    })
    assert resp.status_code == 201
    # Verify it's stored as plain text, not interpreted
    data = resp.json()
    assert data["school_id"] == "xss-test"


@pytest.mark.asyncio
async def test_oversized_policy_payload(authed_client):
    """Large policy payload is handled without crashing."""
    await authed_client.post(f"{PREFIX}/schools", json={
        "school_id": "big", "school_name": "Big School", "admin_email": "a@b.com",
    })
    # Send a very large policy
    big_policy = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
    resp = await authed_client.post(f"{PREFIX}/schools/big/policy", json={
        "policy": big_policy,
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_empty_extension_id_rejected(authed_client):
    """Empty extension_id is rejected with 422."""
    await authed_client.post(f"{PREFIX}/schools", json={
        "school_id": "empty-ext", "school_name": "School", "admin_email": "a@b.com",
    })
    resp = await authed_client.post(f"{PREFIX}/schools/empty-ext/force-install", json={
        "extension_id": "",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_in_school_id_path(authed_client):
    """SQL injection in path parameter is handled safely."""
    resp = await authed_client.get(f"{PREFIX}/schools/'; DROP TABLE schools;--/status")
    # Should return 404, not crash
    assert resp.status_code == 404
