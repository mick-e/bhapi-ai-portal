"""Family AI Agreement E2E tests."""

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
async def agreement_client():
    """Agreement test client with committing DB session."""
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


# --- Templates ---


@pytest.mark.asyncio
async def test_list_agreement_templates(agreement_client):
    """List available agreement templates."""
    token = await _register_and_login(agreement_client, "templates@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await agreement_client.get(
        "/api/v1/groups/agreement-templates", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "ages_7_10" in data
    assert "ages_11_13" in data
    assert "ages_14_16" in data
    assert "ages_17_plus" in data
    assert data["ages_7_10"]["title"] == "Family AI Rules (Ages 7-10)"


# --- CRUD ---


@pytest.mark.asyncio
async def test_create_agreement_from_template(agreement_client):
    """Create an agreement from a template."""
    token = await _register_and_login(agreement_client, "create@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create group first
    group_resp = await agreement_client.post("/api/v1/groups", json={
        "name": "Smith Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    # Create agreement
    response = await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement",
        json={"template_id": "ages_11_13"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Family AI Rules (Ages 11-13)"
    assert data["template_id"] == "ages_11_13"
    assert data["active"] is True
    assert len(data["rules"]) == 6
    assert data["signed_by_parent"] is not None
    assert data["review_due"] is not None


@pytest.mark.asyncio
async def test_get_active_agreement(agreement_client):
    """Get active agreement for a group."""
    token = await _register_and_login(agreement_client, "active@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await agreement_client.post("/api/v1/groups", json={
        "name": "Test Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    # No agreement yet
    response = await agreement_client.get(
        f"/api/v1/groups/{group_id}/agreement", headers=headers
    )
    assert response.status_code == 200

    # Create one
    await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement",
        json={"template_id": "ages_7_10"},
        headers=headers,
    )

    # Now there is one
    response = await agreement_client.get(
        f"/api/v1/groups/{group_id}/agreement", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is True
    assert data["template_id"] == "ages_7_10"


@pytest.mark.asyncio
async def test_update_agreement_rules(agreement_client):
    """Update the rules of an agreement."""
    token = await _register_and_login(agreement_client, "update@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await agreement_client.post("/api/v1/groups", json={
        "name": "Update Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement",
        json={"template_id": "ages_14_16"},
        headers=headers,
    )

    # Update rules
    new_rules = [
        {"category": "custom", "rule_text": "Custom rule", "enabled": True},
        {"category": "safety", "rule_text": "Stay safe", "enabled": False},
    ]
    response = await agreement_client.patch(
        f"/api/v1/groups/{group_id}/agreement",
        json={"rules": new_rules},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["rules"]) == 2
    assert data["rules"][0]["rule_text"] == "Custom rule"


@pytest.mark.asyncio
async def test_create_agreement_invalid_template(agreement_client):
    """Create agreement with invalid template returns 422."""
    token = await _register_and_login(agreement_client, "invalid@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await agreement_client.post("/api/v1/groups", json={
        "name": "Invalid Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    response = await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement",
        json={"template_id": "nonexistent"},
        headers=headers,
    )
    assert response.status_code == 422


# --- Signing ---


@pytest.mark.asyncio
async def test_sign_agreement(agreement_client):
    """A member signs the agreement."""
    token = await _register_and_login(agreement_client, "sign@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await agreement_client.post("/api/v1/groups", json={
        "name": "Sign Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    # Add a member
    member_resp = await agreement_client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"display_name": "Child", "role": "member"},
        headers=headers,
    )
    member_id = member_resp.json()["id"]

    # Create agreement
    await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement",
        json={"template_id": "ages_11_13"},
        headers=headers,
    )

    # Sign it
    response = await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement/sign",
        json={"member_id": member_id, "name": "Child"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["signed_by_members"]) == 1
    assert data["signed_by_members"][0]["name"] == "Child"


@pytest.mark.asyncio
async def test_duplicate_signature_rejected(agreement_client):
    """A member cannot sign the same agreement twice."""
    token = await _register_and_login(agreement_client, "dupsign@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await agreement_client.post("/api/v1/groups", json={
        "name": "Dup Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    member_resp = await agreement_client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"display_name": "Kid", "role": "member"},
        headers=headers,
    )
    member_id = member_resp.json()["id"]

    await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement",
        json={"template_id": "ages_7_10"},
        headers=headers,
    )

    await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement/sign",
        json={"member_id": member_id, "name": "Kid"},
        headers=headers,
    )

    # Second sign should fail
    response = await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement/sign",
        json={"member_id": member_id, "name": "Kid"},
        headers=headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_mark_agreement_reviewed(agreement_client):
    """Mark agreement as reviewed."""
    token = await _register_and_login(agreement_client, "review@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await agreement_client.post("/api/v1/groups", json={
        "name": "Review Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement",
        json={"template_id": "ages_17_plus"},
        headers=headers,
    )

    response = await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement/review",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["last_reviewed"] is not None


@pytest.mark.asyncio
async def test_creating_new_agreement_deactivates_old(agreement_client):
    """Creating a new agreement deactivates the old one."""
    token = await _register_and_login(agreement_client, "replace@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    group_resp = await agreement_client.post("/api/v1/groups", json={
        "name": "Replace Family",
        "type": "family",
    }, headers=headers)
    group_id = group_resp.json()["id"]

    # Create first
    resp1 = await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement",
        json={"template_id": "ages_7_10"},
        headers=headers,
    )
    assert resp1.status_code == 201

    # Create second (replaces first)
    resp2 = await agreement_client.post(
        f"/api/v1/groups/{group_id}/agreement",
        json={"template_id": "ages_14_16"},
        headers=headers,
    )
    assert resp2.status_code == 201
    data = resp2.json()
    assert data["template_id"] == "ages_14_16"
    assert data["active"] is True

    # Active should be the new one
    get_resp = await agreement_client.get(
        f"/api/v1/groups/{group_id}/agreement", headers=headers
    )
    assert get_resp.json()["template_id"] == "ages_14_16"
