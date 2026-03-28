"""End-to-end tests for the integrations module.

Tests all integrations API endpoints through HTTP using an isolated in-memory
SQLite database and mocked auth/billing dependencies:
- SIS: connect, list, sync, disconnect
- SSO: create, list, update, delete, sync
- Yoti: age-verify start, callback, webhook
- Cross-product: register, list alerts
- Developer portal: create app, list apps
- Error cases: invalid provider, duplicate SSO config, missing connection
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.dependencies import require_active_trial_or_subscription
from src.groups.models import Group, GroupMember
from src.integrations.cross_product import CrossProductAlert, ProductRegistration  # noqa: F401
from src.integrations.developer_portal import DeveloperApp, WebhookDelivery, WebhookEndpoint  # noqa: F401
from src.main import create_app
from src.schemas import GroupContext

PREFIX = "/api/v1/integrations"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def e2e_engine():
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
    async_session_maker = sessionmaker(
        e2e_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def e2e_data(e2e_session):
    """Create a school group with owner/member for integration tests."""
    owner = User(
        id=uuid.uuid4(),
        email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
        display_name="School Admin",
        account_type="school",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(owner)
    await e2e_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="E2E School",
        type="school",
        owner_id=owner.id,
    )
    e2e_session.add(group)
    await e2e_session.flush()

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=owner.id,
        role="admin",
        display_name="School Admin",
    )
    e2e_session.add(member)
    await e2e_session.flush()
    await e2e_session.commit()

    return {"owner": owner, "group": group, "member": member}


@pytest.fixture
async def e2e_client(e2e_engine, e2e_session, e2e_data):
    """HTTP client with auth and billing overrides."""
    app = create_app()

    async def override_get_db():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=e2e_data["owner"].id,
            group_id=e2e_data["group"].id,
            role="admin",
        )

    async def fake_billing(auth=None, db=None):
        return GroupContext(
            user_id=e2e_data["owner"].id,
            group_id=e2e_data["group"].id,
            role="admin",
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = fake_auth
    app.dependency_overrides[require_active_trial_or_subscription] = fake_billing

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# SIS Endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sis_connect_clever(e2e_client, e2e_data):
    """POST /connect creates a Clever SIS connection."""
    resp = await e2e_client.post(f"{PREFIX}/connect", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "clever",
        "access_token": "clever-token-abc",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["provider"] == "clever"
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_sis_connect_classlink(e2e_client, e2e_data):
    """POST /connect creates a ClassLink SIS connection."""
    resp = await e2e_client.post(f"{PREFIX}/connect", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "classlink",
        "access_token": "classlink-tok-xyz",
    })
    assert resp.status_code == 201
    assert resp.json()["provider"] == "classlink"


@pytest.mark.asyncio
async def test_sis_connect_invalid_provider(e2e_client, e2e_data):
    """POST /connect rejects invalid provider."""
    resp = await e2e_client.post(f"{PREFIX}/connect", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "invalid_sis",
        "access_token": "token",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sis_connect_empty_token(e2e_client, e2e_data):
    """POST /connect rejects empty access_token."""
    resp = await e2e_client.post(f"{PREFIX}/connect", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "clever",
        "access_token": "",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sis_list_connections(e2e_client, e2e_data):
    """GET /status lists SIS connections for a group."""
    # Create a connection first
    await e2e_client.post(f"{PREFIX}/connect", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "clever",
        "access_token": "tok-list",
    })
    resp = await e2e_client.get(f"{PREFIX}/status", params={
        "group_id": str(e2e_data["group"].id),
    })
    assert resp.status_code == 200
    connections = resp.json()
    assert isinstance(connections, list)
    assert len(connections) >= 1
    assert connections[0]["provider"] == "clever"


@pytest.mark.asyncio
async def test_sis_sync_clever(e2e_client, e2e_data):
    """POST /sync/{id} triggers a Clever roster sync."""
    # Create connection
    create_resp = await e2e_client.post(f"{PREFIX}/connect", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "clever",
        "access_token": "sync-tok",
    })
    conn_id = create_resp.json()["id"]

    # Mock the Clever fetch to return test roster
    mock_roster = [
        {"first_name": "Alice", "last_name": "Smith", "sis_id": "1", "email": "", "role": "member"},
    ]
    with patch("src.integrations.clever.fetch_clever_roster", new_callable=AsyncMock, return_value=mock_roster):
        resp = await e2e_client.post(f"{PREFIX}/sync/{conn_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["members_created"] == 1
    assert body["connection_id"] == conn_id


@pytest.mark.asyncio
async def test_sis_sync_not_found(e2e_client):
    """POST /sync/{id} returns 404 for nonexistent connection."""
    fake_id = uuid.uuid4()
    resp = await e2e_client.post(f"{PREFIX}/sync/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sis_disconnect(e2e_client, e2e_data):
    """DELETE /disconnect/{id} deactivates a connection."""
    create_resp = await e2e_client.post(f"{PREFIX}/connect", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "clever",
        "access_token": "disconnect-tok",
    })
    conn_id = create_resp.json()["id"]

    resp = await e2e_client.delete(f"{PREFIX}/disconnect/{conn_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "disconnected"

    # Verify it's inactive in listing
    list_resp = await e2e_client.get(f"{PREFIX}/status", params={
        "group_id": str(e2e_data["group"].id),
    })
    for conn in list_resp.json():
        if conn["id"] == conn_id:
            assert conn["status"] == "inactive"


@pytest.mark.asyncio
async def test_sis_disconnect_not_found(e2e_client):
    """DELETE /disconnect/{id} returns 404 for nonexistent connection."""
    resp = await e2e_client.delete(f"{PREFIX}/disconnect/{uuid.uuid4()}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# SSO Endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sso_create_google_workspace(e2e_client, e2e_data):
    """POST /sso creates a Google Workspace SSO config."""
    resp = await e2e_client.post(f"{PREFIX}/sso", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "google_workspace",
        "tenant_id": "school.edu",
        "auto_provision_members": True,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["provider"] == "google_workspace"
    assert body["tenant_id"] == "school.edu"
    assert body["auto_provision_members"] is True


@pytest.mark.asyncio
async def test_sso_create_microsoft_entra(e2e_client, e2e_data):
    """POST /sso creates a Microsoft Entra SSO config."""
    resp = await e2e_client.post(f"{PREFIX}/sso", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "microsoft_entra",
        "tenant_id": "tenant-abc-123",
    })
    assert resp.status_code == 201
    assert resp.json()["provider"] == "microsoft_entra"


@pytest.mark.asyncio
async def test_sso_create_invalid_provider(e2e_client, e2e_data):
    """POST /sso rejects invalid provider."""
    resp = await e2e_client.post(f"{PREFIX}/sso", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "okta",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sso_create_duplicate_conflict(e2e_client, e2e_data):
    """POST /sso returns 409 for duplicate provider on same group."""
    payload = {
        "group_id": str(e2e_data["group"].id),
        "provider": "google_workspace",
        "tenant_id": "school.edu",
    }
    resp1 = await e2e_client.post(f"{PREFIX}/sso", json=payload)
    assert resp1.status_code == 201

    resp2 = await e2e_client.post(f"{PREFIX}/sso", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_sso_list_configs(e2e_client, e2e_data):
    """GET /sso lists SSO configs for a group."""
    await e2e_client.post(f"{PREFIX}/sso", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "google_workspace",
        "tenant_id": "list-school.edu",
    })
    resp = await e2e_client.get(f"{PREFIX}/sso", params={
        "group_id": str(e2e_data["group"].id),
    })
    assert resp.status_code == 200
    configs = resp.json()
    assert isinstance(configs, list)
    assert len(configs) >= 1


@pytest.mark.asyncio
async def test_sso_update_config(e2e_client, e2e_data):
    """PATCH /sso/{id} updates an SSO config."""
    create_resp = await e2e_client.post(f"{PREFIX}/sso", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "google_workspace",
        "tenant_id": "old-domain.edu",
    })
    config_id = create_resp.json()["id"]

    resp = await e2e_client.patch(f"{PREFIX}/sso/{config_id}", json={
        "tenant_id": "new-domain.edu",
        "auto_provision_members": True,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == "new-domain.edu"
    assert body["auto_provision_members"] is True


@pytest.mark.asyncio
async def test_sso_update_not_found(e2e_client):
    """PATCH /sso/{id} returns 404 for nonexistent config."""
    resp = await e2e_client.patch(f"{PREFIX}/sso/{uuid.uuid4()}", json={
        "tenant_id": "x",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sso_delete_config(e2e_client, e2e_data):
    """DELETE /sso/{id} removes an SSO config."""
    create_resp = await e2e_client.post(f"{PREFIX}/sso", json={
        "group_id": str(e2e_data["group"].id),
        "provider": "microsoft_entra",
        "tenant_id": "delete-tenant",
    })
    config_id = create_resp.json()["id"]

    resp = await e2e_client.delete(f"{PREFIX}/sso/{config_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_sso_delete_not_found(e2e_client):
    """DELETE /sso/{id} returns 404 for nonexistent config."""
    resp = await e2e_client.delete(f"{PREFIX}/sso/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sso_directory_sync_not_found(e2e_client):
    """POST /sso/{id}/sync returns 404 for nonexistent config."""
    resp = await e2e_client.post(f"{PREFIX}/sso/{uuid.uuid4()}/sync")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Yoti Age Verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_age_verify_start(e2e_client, e2e_data):
    """POST /age-verify/start initiates Yoti flow for a member."""
    resp = await e2e_client.post(f"{PREFIX}/age-verify/start", params={
        "group_id": str(e2e_data["group"].id),
        "member_id": str(e2e_data["member"].id),
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "session_id" in body
    assert "url" in body


@pytest.mark.asyncio
async def test_age_verify_start_invalid_member(e2e_client, e2e_data):
    """POST /age-verify/start returns 404 for unknown member."""
    resp = await e2e_client.post(f"{PREFIX}/age-verify/start", params={
        "group_id": str(e2e_data["group"].id),
        "member_id": str(uuid.uuid4()),
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_age_verify_callback_success(e2e_client, e2e_data):
    """POST /age-verify/callback processes verification result."""
    # Start a verification first
    start_resp = await e2e_client.post(f"{PREFIX}/age-verify/start", params={
        "group_id": str(e2e_data["group"].id),
        "member_id": str(e2e_data["member"].id),
    })
    session_id = start_resp.json()["session_id"]

    resp = await e2e_client.post(f"{PREFIX}/age-verify/callback", params={
        "group_id": str(e2e_data["group"].id),
        "member_id": str(e2e_data["member"].id),
        "session_id": session_id,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True


# ---------------------------------------------------------------------------
# Yoti Webhook (public)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_yoti_webhook_invalid_status(e2e_client):
    """POST /yoti/callback rejects invalid status values."""
    resp = await e2e_client.post(f"{PREFIX}/yoti/callback", json={
        "session_id": "sess-123",
        "status": "INVALID",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_yoti_webhook_missing_session(e2e_client):
    """POST /yoti/callback rejects missing session_id."""
    resp = await e2e_client.post(f"{PREFIX}/yoti/callback", json={
        "status": "DONE",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Cross-product & Developer Portal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_product_register(e2e_client):
    """POST /cross-product/register creates a product registration."""
    resp = await e2e_client.post(f"{PREFIX}/cross-product/register", json={
        "product_name": "Test App",
        "product_type": "app",
        "api_key": "test-api-key-12345",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["product_name"] == "Test App"
    assert body["active"] is True


@pytest.mark.asyncio
async def test_cross_product_list_alerts(e2e_client):
    """GET /cross-product/alerts returns alerts list (empty initially)."""
    resp = await e2e_client.get(f"{PREFIX}/cross-product/alerts")
    assert resp.status_code == 200
    assert resp.json()["alerts"] == []


@pytest.mark.asyncio
async def test_developer_create_app(e2e_client):
    """POST /developer/apps creates a developer application."""
    resp = await e2e_client.post(f"{PREFIX}/developer/apps", json={
        "name": "My Test App",
        "description": "A test developer app",
        "redirect_uris": ["https://example.com/callback"],
        "scopes": ["read:alerts"],
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "My Test App"
    assert "client_id" in body
    assert "client_secret" in body


@pytest.mark.asyncio
async def test_developer_list_apps(e2e_client):
    """GET /developer/apps lists apps for the authenticated user."""
    # Create one first
    await e2e_client.post(f"{PREFIX}/developer/apps", json={
        "name": "List Test App",
    })
    resp = await e2e_client.get(f"{PREFIX}/developer/apps")
    assert resp.status_code == 200
    assert len(resp.json()["apps"]) >= 1
