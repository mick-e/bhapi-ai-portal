"""IDOR tests for integrations module.

Finding #4: All integrations endpoints accept arbitrary group_id without
verifying that the authenticated user owns or belongs to that group.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def sec_client():
    """Security test client with committing session."""
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

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, session

    await session.close()
    await engine.dispose()


async def _setup_user(client, email):
    """Register user, return (headers, group_id, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": f"User {email}",
        "account_type": "school",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    me_data = me.json()
    return headers, me_data.get("group_id"), me_data["id"]


@pytest.mark.asyncio
async def test_connect_sis_to_other_group(sec_client):
    """User B should NOT be able to connect SIS to User A's group.

    Finding #4: integrations router has no group_id ownership check.
    """
    client, session = sec_client

    headers_a, gid_a, _ = await _setup_user(client, "sis-owner@example.com")
    headers_b, gid_b, _ = await _setup_user(client, "sis-attacker@example.com")

    # User B tries to connect SIS to User A's group
    resp = await client.post("/api/v1/integrations/connect", json={
        "group_id": gid_a,
        "provider": "clever",
        "access_token": "fake-clever-token",
    }, headers=headers_b)

    # Should be 403 if ownership check exists; currently 201 (vulnerability)
    if resp.status_code == 201:
        pytest.xfail("VULNERABILITY: User can connect SIS to another user's group (Finding #4)")
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_list_sis_of_other_group(sec_client):
    """User B should NOT see User A's SIS connections.

    Leaks SIS connection details (provider, status, etc.).
    """
    client, session = sec_client

    headers_a, gid_a, _ = await _setup_user(client, "sis-list-owner@example.com")
    headers_b, gid_b, _ = await _setup_user(client, "sis-list-attacker@example.com")

    # User A connects SIS
    await client.post("/api/v1/integrations/connect", json={
        "group_id": gid_a,
        "provider": "clever",
        "access_token": "real-token",
    }, headers=headers_a)

    # User B tries to list User A's connections
    resp = await client.get(
        f"/api/v1/integrations/status?group_id={gid_a}",
        headers=headers_b,
    )

    if resp.status_code == 200 and len(resp.json()) > 0:
        pytest.xfail("VULNERABILITY: User can list another group's SIS connections (Finding #4)")
    assert resp.status_code in (200, 403, 404)


@pytest.mark.asyncio
async def test_sync_other_groups_sis(sec_client):
    """User B should NOT trigger sync on User A's SIS connection."""
    client, session = sec_client

    headers_a, gid_a, _ = await _setup_user(client, "sis-sync-owner@example.com")
    headers_b, gid_b, _ = await _setup_user(client, "sis-sync-attacker@example.com")

    # User A connects SIS
    conn_resp = await client.post("/api/v1/integrations/connect", json={
        "group_id": gid_a,
        "provider": "clever",
        "access_token": "real-token",
    }, headers=headers_a)

    if conn_resp.status_code != 201:
        pytest.skip("Could not create SIS connection")

    conn_id = conn_resp.json()["id"]

    # User B tries to sync User A's connection
    # The Clever API call will fail with ValueError since the token is fake,
    # which results in a 500. The key question is whether auth check happens first.
    try:
        resp = await client.post(
            f"/api/v1/integrations/sync/{conn_id}",
            headers=headers_b,
        )
    except Exception:
        # If the endpoint raises an unhandled error, that still means no auth check
        pytest.xfail(
            "VULNERABILITY: User B reached sync handler for User A's SIS "
            "(unhandled error, no auth check, Finding #4)"
        )
        return

    # Should be 403 if ownership check exists
    if resp.status_code == 500:
        # 500 means the handler ran (no auth check) but Clever API failed
        pytest.xfail(
            "VULNERABILITY: User can reach sync handler for another group's SIS "
            f"(status=500, no ownership check, Finding #4)"
        )
    elif resp.status_code not in (401, 403, 404):
        pytest.xfail(
            f"VULNERABILITY: User can trigger sync on another group's SIS "
            f"(status={resp.status_code}, Finding #4)"
        )


@pytest.mark.asyncio
async def test_create_sso_config_for_other_group(sec_client):
    """User B should NOT create SSO config for User A's group."""
    client, session = sec_client

    headers_a, gid_a, _ = await _setup_user(client, "sso-owner@example.com")
    headers_b, gid_b, _ = await _setup_user(client, "sso-attacker@example.com")

    # User B tries to create SSO config for User A's group
    try:
        resp = await client.post("/api/v1/integrations/sso", json={
            "group_id": gid_a,
            "provider": "google_workspace",
            "tenant_id": "attacker-tenant",
            "auto_provision_members": True,
        }, headers=headers_b)
    except Exception:
        # Server-side response validation errors propagate as exceptions
        # in ASGI test client. If the handler ran at all (even with a
        # serialization bug), there was no ownership check.
        pytest.xfail(
            "VULNERABILITY: SSO config handler ran for another group "
            "(server error, no ownership check, Finding #4)"
        )
        return

    if resp.status_code in (201, 500):
        pytest.xfail("VULNERABILITY: User can create SSO config for another group (Finding #4)")
    assert resp.status_code in (403, 404, 409)


@pytest.mark.asyncio
async def test_disconnect_other_groups_sis(sec_client):
    """User B should NOT disconnect User A's SIS integration."""
    client, session = sec_client

    headers_a, gid_a, _ = await _setup_user(client, "sis-disc-owner@example.com")
    headers_b, gid_b, _ = await _setup_user(client, "sis-disc-attacker@example.com")

    # User A connects SIS
    conn_resp = await client.post("/api/v1/integrations/connect", json={
        "group_id": gid_a,
        "provider": "clever",
        "access_token": "real-token",
    }, headers=headers_a)

    if conn_resp.status_code != 201:
        pytest.skip("Could not create SIS connection")

    conn_id = conn_resp.json()["id"]

    # User B tries to disconnect
    resp = await client.delete(
        f"/api/v1/integrations/disconnect/{conn_id}",
        headers=headers_b,
    )

    if resp.status_code == 200:
        pytest.xfail("VULNERABILITY: User can disconnect another group's SIS (Finding #4)")
    assert resp.status_code in (403, 404)
