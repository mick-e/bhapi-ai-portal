"""E2E tests for Australian Online Safety compliance endpoints.

Tests the full HTTP request/response cycle for AU age verification,
eSafety SLA monitoring, and cyberbullying case management.
"""

from uuid import uuid4

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
    """Register a user, return (token, user_id)."""
    email = email or f"au-{uuid4().hex[:8]}@example.com"
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "AU Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def au_client():
    """Test client with committing DB session for AU compliance tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def get_db_override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Age Verification Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_au_age_requirement_check(au_client):
    """GET /au/age-requirement returns verification status for AU user."""
    token, user_id = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await au_client.get(
        "/api/v1/compliance/au/age-requirement",
        params={"user_id": user_id, "country_code": "AU"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["required"] is True
    assert data["verified"] is False


@pytest.mark.asyncio
async def test_e2e_au_age_requirement_non_au(au_client):
    """Non-AU user gets verified=True, required=False."""
    token, user_id = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await au_client.get(
        "/api/v1/compliance/au/age-requirement",
        params={"user_id": user_id, "country_code": "US"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["required"] is False
    assert data["verified"] is True


@pytest.mark.asyncio
async def test_e2e_au_age_verification_create(au_client):
    """POST /au/age-verification creates a verification record."""
    token, user_id = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await au_client.post(
        "/api/v1/compliance/au/age-verification",
        json={"country_code": "AU", "method": "yoti"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["verified"] is True
    assert data["method"] == "yoti"


@pytest.mark.asyncio
async def test_e2e_au_age_verification_then_check(au_client):
    """After verification, age requirement check shows verified."""
    token, user_id = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create verification
    await au_client.post(
        "/api/v1/compliance/au/age-verification",
        json={"country_code": "AU", "method": "document"},
        headers=headers,
    )

    # Check requirement
    resp = await au_client.get(
        "/api/v1/compliance/au/age-requirement",
        params={"user_id": user_id, "country_code": "AU"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["verified"] is True


@pytest.mark.asyncio
async def test_e2e_au_age_verification_invalid_method(au_client):
    """Invalid verification method returns 422."""
    token, user_id = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await au_client.post(
        "/api/v1/compliance/au/age-verification",
        json={"country_code": "AU", "method": "invalid_method"},
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# eSafety SLA Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_esafety_sla_empty(au_client):
    """GET /au/esafety-sla returns 100% compliant when no reports."""
    token, _ = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await au_client.get(
        "/api/v1/compliance/au/esafety-sla",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["compliant"] is True
    assert data["sla_hours"] == 24


@pytest.mark.asyncio
async def test_e2e_esafety_report_generation(au_client):
    """GET /au/esafety-report returns commissioner report data."""
    token, _ = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await au_client.get(
        "/api/v1/compliance/au/esafety-report",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "esafety_commissioner"
    assert "sla_compliance" in data


# ---------------------------------------------------------------------------
# Cyberbullying Case Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_cyberbullying_case_create(au_client):
    """POST /au/cyberbullying-case creates a case with workflow."""
    token, _ = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    reporter_id = str(uuid4())
    target_id = str(uuid4())

    resp = await au_client.post(
        "/api/v1/compliance/au/cyberbullying-case",
        json={
            "reporter_id": reporter_id,
            "target_id": target_id,
            "evidence_ids": ["ev1", "ev2"],
            "severity": "high",
            "description": "Repeated harassment",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["severity"] == "high"
    assert data["status"] == "open"
    assert len(data["workflow_steps"]) == 7


@pytest.mark.asyncio
async def test_e2e_cyberbullying_case_get(au_client):
    """GET /au/cyberbullying-case/{id} returns case details."""
    token, _ = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create case
    create_resp = await au_client.post(
        "/api/v1/compliance/au/cyberbullying-case",
        json={
            "reporter_id": str(uuid4()),
            "target_id": str(uuid4()),
            "evidence_ids": [],
            "severity": "low",
        },
        headers=headers,
    )
    case_id = create_resp.json()["id"]

    # Retrieve
    resp = await au_client.get(
        f"/api/v1/compliance/au/cyberbullying-case/{case_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == case_id
    assert data["severity"] == "low"


@pytest.mark.asyncio
async def test_e2e_cyberbullying_workflow_advance(au_client):
    """PATCH /au/cyberbullying-case/{id}/workflow advances a step."""
    token, _ = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await au_client.post(
        "/api/v1/compliance/au/cyberbullying-case",
        json={
            "reporter_id": str(uuid4()),
            "target_id": str(uuid4()),
            "evidence_ids": [],
            "severity": "medium",
        },
        headers=headers,
    )
    case_id = create_resp.json()["id"]

    resp = await au_client.patch(
        f"/api/v1/compliance/au/cyberbullying-case/{case_id}/workflow",
        json={"step": "document", "notes": "Evidence collected"},
        headers=headers,
    )
    assert resp.status_code == 200
    steps = resp.json()["workflow_steps"]
    doc_step = [s for s in steps if s["step"] == "document"][0]
    assert doc_step["completed"] is True


@pytest.mark.asyncio
async def test_e2e_cyberbullying_case_close(au_client):
    """POST /au/cyberbullying-case/{id}/close closes with resolution."""
    token, _ = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await au_client.post(
        "/api/v1/compliance/au/cyberbullying-case",
        json={
            "reporter_id": str(uuid4()),
            "target_id": str(uuid4()),
            "evidence_ids": [],
            "severity": "high",
        },
        headers=headers,
    )
    case_id = create_resp.json()["id"]

    resp = await au_client.post(
        f"/api/v1/compliance/au/cyberbullying-case/{case_id}/close",
        json={"resolution": "Warning issued"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "closed"
    assert data["resolution"] == "Warning issued"
    assert data["resolved_at"] is not None


@pytest.mark.asyncio
async def test_e2e_cyberbullying_case_not_found(au_client):
    """GET non-existent cyberbullying case returns 404."""
    token, _ = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await au_client.get(
        f"/api/v1/compliance/au/cyberbullying-case/{uuid4()}",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_e2e_cyberbullying_invalid_severity(au_client):
    """Creating case with invalid severity returns 422."""
    token, _ = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await au_client.post(
        "/api/v1/compliance/au/cyberbullying-case",
        json={
            "reporter_id": str(uuid4()),
            "target_id": str(uuid4()),
            "evidence_ids": [],
            "severity": "extreme",
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_e2e_full_cyberbullying_workflow(au_client):
    """Full cyberbullying lifecycle: create -> advance -> close."""
    token, _ = await _register_and_login(au_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    create_resp = await au_client.post(
        "/api/v1/compliance/au/cyberbullying-case",
        json={
            "reporter_id": str(uuid4()),
            "target_id": str(uuid4()),
            "evidence_ids": ["screenshot1"],
            "severity": "critical",
            "description": "Ongoing bullying campaign",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    case_id = create_resp.json()["id"]

    # Advance through workflow
    for step in ["document", "notify_parent", "review", "action"]:
        resp = await au_client.patch(
            f"/api/v1/compliance/au/cyberbullying-case/{case_id}/workflow",
            json={"step": step},
            headers=headers,
        )
        assert resp.status_code == 200

    # Close
    close_resp = await au_client.post(
        f"/api/v1/compliance/au/cyberbullying-case/{case_id}/close",
        json={"resolution": "Account suspended, parents notified"},
        headers=headers,
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"
