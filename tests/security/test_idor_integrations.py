"""IDOR tests for integrations module.

Finding #4: Verify that all integrations endpoints enforce group_id ownership
so that users cannot access or modify other groups' SIS/SSO integrations.
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
    """User B should NOT be able to connect SIS to User A's group."""
    client, session = sec_client

    headers_a, gid_a, _ = await _setup_user(client, "sis-owner@example.com")
    headers_b, gid_b, _ = await _setup_user(client, "sis-attacker@example.com")

    # User B tries to connect SIS to User A's group
    resp = await client.post("/api/v1/integrations/connect", json={
        "group_id": gid_a,
        "provider": "clever",
        "access_token": "fake-clever-token",
    }, headers=headers_b)

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_sis_of_other_group(sec_client):
    """User B should NOT see User A's SIS connections."""
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

    assert resp.status_code == 403


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

    assert conn_resp.status_code == 201, "Could not create SIS connection"
    conn_id = conn_resp.json()["id"]

    # User B tries to sync User A's connection
    resp = await client.post(
        f"/api/v1/integrations/sync/{conn_id}",
        headers=headers_b,
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_sso_config_for_other_group(sec_client):
    """User B should NOT create SSO config for User A's group."""
    client, session = sec_client

    headers_a, gid_a, _ = await _setup_user(client, "sso-owner@example.com")
    headers_b, gid_b, _ = await _setup_user(client, "sso-attacker@example.com")

    # User B tries to create SSO config for User A's group
    resp = await client.post("/api/v1/integrations/sso", json={
        "group_id": gid_a,
        "provider": "google_workspace",
        "tenant_id": "attacker-tenant",
        "auto_provision_members": True,
    }, headers=headers_b)

    assert resp.status_code == 403


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

    assert conn_resp.status_code == 201, "Could not create SIS connection"
    conn_id = conn_resp.json()["id"]

    # User B tries to disconnect
    resp = await client.delete(
        f"/api/v1/integrations/disconnect/{conn_id}",
        headers=headers_b,
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_sso_configs_of_other_group(sec_client):
    """User B should NOT list User A's SSO configurations."""
    client, session = sec_client

    headers_a, gid_a, _ = await _setup_user(client, "sso-list-owner@example.com")
    headers_b, gid_b, _ = await _setup_user(client, "sso-list-attacker@example.com")

    # User A creates SSO config
    await client.post("/api/v1/integrations/sso", json={
        "group_id": gid_a,
        "provider": "google_workspace",
        "tenant_id": "owner-tenant",
        "auto_provision_members": False,
    }, headers=headers_a)

    # User B tries to list User A's SSO configs
    resp = await client.get(
        f"/api/v1/integrations/sso?group_id={gid_a}",
        headers=headers_b,
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_sso_config_of_other_group(sec_client):
    """User B should NOT update User A's SSO configuration."""
    client, session = sec_client

    headers_a, gid_a, _ = await _setup_user(client, "sso-upd-owner@example.com")
    headers_b, gid_b, _ = await _setup_user(client, "sso-upd-attacker@example.com")

    # User A creates SSO config
    create_resp = await client.post("/api/v1/integrations/sso", json={
        "group_id": gid_a,
        "provider": "google_workspace",
        "tenant_id": "owner-tenant",
        "auto_provision_members": False,
    }, headers=headers_a)

    assert create_resp.status_code == 201, "Could not create SSO config"
    config_id = create_resp.json()["id"]

    # User B tries to update User A's SSO config
    resp = await client.patch(
        f"/api/v1/integrations/sso/{config_id}",
        json={"tenant_id": "attacker-tenant"},
        headers=headers_b,
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_sso_config_of_other_group(sec_client):
    """User B should NOT delete User A's SSO configuration."""
    client, session = sec_client

    headers_a, gid_a, _ = await _setup_user(client, "sso-del-owner@example.com")
    headers_b, gid_b, _ = await _setup_user(client, "sso-del-attacker@example.com")

    # User A creates SSO config
    create_resp = await client.post("/api/v1/integrations/sso", json={
        "group_id": gid_a,
        "provider": "google_workspace",
        "tenant_id": "owner-tenant",
        "auto_provision_members": False,
    }, headers=headers_a)

    assert create_resp.status_code == 201, "Could not create SSO config"
    config_id = create_resp.json()["id"]

    # User B tries to delete User A's SSO config
    resp = await client.delete(
        f"/api/v1/integrations/sso/{config_id}",
        headers=headers_b,
    )

    assert resp.status_code == 403
