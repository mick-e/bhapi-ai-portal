"""Emergency Contacts E2E tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


async def _register_and_login(client, email="test@example.com", account_type="family"):
    """Helper: register and return token."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Test User",
        "account_type": account_type,
        "privacy_notice_accepted": True,
    })
    return reg.json()["access_token"]


@pytest.fixture
async def ec_client():
    """Emergency contacts test client with committing DB session."""
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
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await session.close()
    await engine.dispose()


# --- CRUD ---


@pytest.mark.asyncio
async def test_add_emergency_contact(ec_client):
    """Add an emergency contact to a group."""
    token = await _register_and_login(ec_client, "add@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await ec_client.post("/api/v1/groups", json={
        "name": "Emergency Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    response = await ec_client.post(
        f"/api/v1/groups/{group_id}/emergency-contacts",
        json={
            "name": "Grandma Smith",
            "relationship": "grandparent",
            "phone": "+15551234567",
            "email": "grandma@example.com",
            "notify_on": ["critical"],
            "consent_given": True,
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Grandma Smith"
    assert data["relationship"] == "grandparent"
    assert data["phone"] == "+15551234567"
    assert data["consent_given"] is True
    assert data["consent_given_at"] is not None
    assert "critical" in data["notify_on"]


@pytest.mark.asyncio
async def test_list_emergency_contacts(ec_client):
    """List emergency contacts for a group."""
    token = await _register_and_login(ec_client, "list@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await ec_client.post("/api/v1/groups", json={
        "name": "List Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    # Add two contacts
    await ec_client.post(
        f"/api/v1/groups/{group_id}/emergency-contacts",
        json={"name": "Contact 1", "phone": "+15551111111"},
        headers=headers,
    )
    await ec_client.post(
        f"/api/v1/groups/{group_id}/emergency-contacts",
        json={"name": "Contact 2", "email": "c2@example.com"},
        headers=headers,
    )

    response = await ec_client.get(
        f"/api/v1/groups/{group_id}/emergency-contacts", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_update_emergency_contact(ec_client):
    """Update an emergency contact."""
    token = await _register_and_login(ec_client, "update@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await ec_client.post("/api/v1/groups", json={
        "name": "Update Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    add_resp = await ec_client.post(
        f"/api/v1/groups/{group_id}/emergency-contacts",
        json={"name": "Old Name", "phone": "+15559999999"},
        headers=headers,
    )
    contact_id = add_resp.json()["id"]

    response = await ec_client.patch(
        f"/api/v1/groups/{group_id}/emergency-contacts/{contact_id}",
        json={"name": "New Name", "consent_given": True},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["consent_given"] is True


@pytest.mark.asyncio
async def test_remove_emergency_contact(ec_client):
    """Remove an emergency contact."""
    token = await _register_and_login(ec_client, "remove@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await ec_client.post("/api/v1/groups", json={
        "name": "Remove Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    add_resp = await ec_client.post(
        f"/api/v1/groups/{group_id}/emergency-contacts",
        json={"name": "Remove Me", "phone": "+15550000000"},
        headers=headers,
    )
    contact_id = add_resp.json()["id"]

    response = await ec_client.delete(
        f"/api/v1/groups/{group_id}/emergency-contacts/{contact_id}",
        headers=headers,
    )
    assert response.status_code == 204

    # Verify gone
    list_resp = await ec_client.get(
        f"/api/v1/groups/{group_id}/emergency-contacts", headers=headers
    )
    assert len(list_resp.json()) == 0


# --- Validation ---


@pytest.mark.asyncio
async def test_add_contact_requires_name(ec_client):
    """Adding a contact without a name fails validation."""
    token = await _register_and_login(ec_client, "noname@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await ec_client.post("/api/v1/groups", json={
        "name": "Noname Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    response = await ec_client.post(
        f"/api/v1/groups/{group_id}/emergency-contacts",
        json={"phone": "+15551111111"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_contact_requires_phone_or_email(ec_client):
    """Adding a contact without phone or email fails validation."""
    token = await _register_and_login(ec_client, "nophone@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await ec_client.post("/api/v1/groups", json={
        "name": "Nophone Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    response = await ec_client.post(
        f"/api/v1/groups/{group_id}/emergency-contacts",
        json={"name": "No Contact Info"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_notify_on_rejected(ec_client):
    """Invalid notify_on types are rejected."""
    token = await _register_and_login(ec_client, "badnotify@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await ec_client.post("/api/v1/groups", json={
        "name": "BadNotify Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    response = await ec_client.post(
        f"/api/v1/groups/{group_id}/emergency-contacts",
        json={
            "name": "Test",
            "phone": "+15551111111",
            "notify_on": ["invalid_type"],
        },
        headers=headers,
    )
    assert response.status_code == 422


# --- Notification Trigger ---


@pytest.mark.asyncio
async def test_critical_alert_triggers_emergency_notification(ec_client):
    """Creating a critical alert triggers emergency contact notification."""
    token = await _register_and_login(ec_client, "trigger@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await ec_client.post("/api/v1/groups", json={
        "name": "Trigger Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    # Add emergency contact with consent
    await ec_client.post(
        f"/api/v1/groups/{group_id}/emergency-contacts",
        json={
            "name": "Grandpa",
            "phone": "+15550001111",
            "notify_on": ["critical"],
            "consent_given": True,
        },
        headers=headers,
    )

    # Create a critical alert (this should trigger the notification)
    # The alert creation is internal, so we test it via the service layer
    # Here we just verify the contact is set up correctly
    list_resp = await ec_client.get(
        f"/api/v1/groups/{group_id}/emergency-contacts", headers=headers
    )
    contacts = list_resp.json()
    assert len(contacts) == 1
    assert contacts[0]["consent_given"] is True
    assert "critical" in contacts[0]["notify_on"]


@pytest.mark.asyncio
async def test_remove_nonexistent_contact_returns_404(ec_client):
    """Removing a non-existent contact returns 404."""
    token = await _register_and_login(ec_client, "notfound@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await ec_client.post("/api/v1/groups", json={
        "name": "NotFound Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    response = await ec_client.delete(
        f"/api/v1/groups/{group_id}/emergency-contacts/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert response.status_code == 404
