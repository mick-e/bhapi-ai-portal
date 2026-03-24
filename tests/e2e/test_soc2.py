"""E2E tests for SOC 2 audit initiation endpoints (P3-B4).

Covers:
- GET /soc2/policies
- POST /soc2/policies
- GET /soc2/readiness
- POST /soc2/evidence/collect
- PUT /soc2/controls/{control_id}
"""

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


async def _register_and_login(client: AsyncClient, email: str = "soc2user@example.com") -> str:
    """Register a user and return the JWT access token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass1!",
            "display_name": "SOC2 Tester",
            "account_type": "family",
            "privacy_notice_accepted": True,
        },
    )
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def soc2_client():
    """Async test client with committing SQLite session for SOC 2 E2E tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_soc2_policies_returns_200(soc2_client):
    """GET /soc2/policies returns 200 with authenticated user."""
    token = await _register_and_login(soc2_client, "policies_list@example.com")
    resp = await soc2_client.get(
        "/api/v1/compliance/soc2/policies",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_post_soc2_policies_creates_policy(soc2_client):
    """POST /soc2/policies creates a new audit policy and returns 201."""
    token = await _register_and_login(soc2_client, "create_policy@example.com")
    resp = await soc2_client.post(
        "/api/v1/compliance/soc2/policies",
        json={
            "name": "Access Control Policy",
            "category": "security",
            "description": "RBAC, API key management, session controls",
            "version": "1.0",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Access Control Policy"
    assert data["category"] == "security"
    assert "id" in data


@pytest.mark.asyncio
async def test_post_soc2_policies_missing_name_returns_422(soc2_client):
    """POST /soc2/policies without name returns 422."""
    token = await _register_and_login(soc2_client, "bad_policy@example.com")
    resp = await soc2_client.post(
        "/api/v1/compliance/soc2/policies",
        json={"category": "security"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (422, 400)


@pytest.mark.asyncio
async def test_get_soc2_readiness_returns_report(soc2_client):
    """GET /soc2/readiness returns a structured readiness report."""
    token = await _register_and_login(soc2_client, "readiness@example.com")
    resp = await soc2_client.get(
        "/api/v1/compliance/soc2/readiness",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_readiness_pct" in data
    assert "categories" in data
    assert "total_controls" in data


@pytest.mark.asyncio
async def test_get_soc2_readiness_categories_present(soc2_client):
    """Readiness report includes all four TSC categories."""
    token = await _register_and_login(soc2_client, "readiness_cats@example.com")
    resp = await soc2_client.get(
        "/api/v1/compliance/soc2/readiness",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    cats = resp.json()["categories"]
    assert "security" in cats
    assert "availability" in cats
    assert "privacy" in cats
    assert "confidentiality" in cats


@pytest.mark.asyncio
async def test_post_soc2_evidence_collect_creates_evidence(soc2_client):
    """POST /soc2/evidence/collect creates evidence and returns 201."""
    token = await _register_and_login(soc2_client, "evidence@example.com")
    resp = await soc2_client.post(
        "/api/v1/compliance/soc2/evidence/collect",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["collected"] == 3
    assert len(data["evidence"]) == 3


@pytest.mark.asyncio
async def test_post_soc2_evidence_returns_expected_types(soc2_client):
    """Collected evidence includes deployment_log, access_control, encryption types."""
    token = await _register_and_login(soc2_client, "evidence_types@example.com")
    resp = await soc2_client.post(
        "/api/v1/compliance/soc2/evidence/collect",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    types = {e["evidence_type"] for e in resp.json()["evidence"]}
    assert "deployment_log" in types
    assert "access_control" in types
    assert "encryption" in types


@pytest.mark.asyncio
async def test_put_soc2_controls_creates_control(soc2_client):
    """PUT /soc2/controls/{control_id} creates a control and returns it."""
    token = await _register_and_login(soc2_client, "controls@example.com")
    resp = await soc2_client.put(
        "/api/v1/compliance/soc2/controls/CC6.1",
        json={"status": "implemented", "description": "JWT + RBAC in place"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["control_id"] == "CC6.1"
    assert data["status"] == "implemented"


@pytest.mark.asyncio
async def test_put_soc2_controls_updates_existing(soc2_client):
    """PUT /soc2/controls/{control_id} can update an existing control."""
    token = await _register_and_login(soc2_client, "update_ctrl@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    await soc2_client.put(
        "/api/v1/compliance/soc2/controls/CC7.1",
        json={"status": "planned"},
        headers=headers,
    )
    # Update
    resp = await soc2_client.put(
        "/api/v1/compliance/soc2/controls/CC7.1",
        json={"status": "implemented", "description": "Monitoring active"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "implemented"


@pytest.mark.asyncio
async def test_soc2_endpoints_require_auth(soc2_client):
    """SOC 2 endpoints return 401 without an Authorization header."""
    resp = await soc2_client.get("/api/v1/compliance/soc2/policies")
    assert resp.status_code == 401

    resp = await soc2_client.get("/api/v1/compliance/soc2/readiness")
    assert resp.status_code == 401

    resp = await soc2_client.post("/api/v1/compliance/soc2/evidence/collect")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_soc2_policies_filter_by_category(soc2_client):
    """GET /soc2/policies?category=privacy filters correctly."""
    token = await _register_and_login(soc2_client, "filter_cat@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create two policies in different categories
    await soc2_client.post(
        "/api/v1/compliance/soc2/policies",
        json={"name": "Privacy Notice", "category": "privacy", "description": None},
        headers=headers,
    )
    await soc2_client.post(
        "/api/v1/compliance/soc2/policies",
        json={"name": "Access Controls", "category": "security", "description": None},
        headers=headers,
    )

    resp = await soc2_client.get(
        "/api/v1/compliance/soc2/policies?category=privacy",
        headers=headers,
    )
    assert resp.status_code == 200
    policies = resp.json()
    assert len(policies) == 1
    assert policies[0]["category"] == "privacy"


@pytest.mark.asyncio
async def test_readiness_reflects_seeded_controls(soc2_client):
    """Readiness report reflects controls created via the controls endpoint."""
    token = await _register_and_login(soc2_client, "readiness_ctls@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create controls
    await soc2_client.put(
        "/api/v1/compliance/soc2/controls/CC6.3",
        json={"status": "implemented"},
        headers=headers,
    )
    await soc2_client.put(
        "/api/v1/compliance/soc2/controls/A1.1",
        json={"status": "partial"},
        headers=headers,
    )

    resp = await soc2_client.get(
        "/api/v1/compliance/soc2/readiness",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_controls"] == 2
    assert data["implemented"] == 1
