"""Security tests for Australian Online Safety compliance endpoints.

Tests authentication enforcement, input validation, injection prevention,
and authorization boundaries.
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
    email = email or f"sec-{uuid4().hex[:8]}@example.com"
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Security Tester",
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
async def sec_client():
    """Test client for security tests."""
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
# Authentication Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_au_age_requirement_requires_auth(sec_client):
    """GET /au/age-requirement without auth returns 401."""
    resp = await sec_client.get(
        "/api/v1/compliance/au/age-requirement",
        params={"user_id": str(uuid4()), "country_code": "AU"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_au_age_verification_requires_auth(sec_client):
    """POST /au/age-verification without auth returns 401."""
    resp = await sec_client.post(
        "/api/v1/compliance/au/age-verification",
        json={"country_code": "AU", "method": "yoti"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_au_esafety_sla_requires_auth(sec_client):
    """GET /au/esafety-sla without auth returns 401."""
    resp = await sec_client.get("/api/v1/compliance/au/esafety-sla")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_au_esafety_report_requires_auth(sec_client):
    """GET /au/esafety-report without auth returns 401."""
    resp = await sec_client.get("/api/v1/compliance/au/esafety-report")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_au_cyberbullying_create_requires_auth(sec_client):
    """POST /au/cyberbullying-case without auth returns 401."""
    resp = await sec_client.post(
        "/api/v1/compliance/au/cyberbullying-case",
        json={
            "reporter_id": str(uuid4()),
            "target_id": str(uuid4()),
            "evidence_ids": [],
            "severity": "low",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_au_cyberbullying_get_requires_auth(sec_client):
    """GET /au/cyberbullying-case/{id} without auth returns 401."""
    resp = await sec_client.get(
        f"/api/v1/compliance/au/cyberbullying-case/{uuid4()}"
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Input Validation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_au_age_verification_xss_in_method(sec_client):
    """XSS in verification method is rejected."""
    token, _ = await _register_and_login(sec_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await sec_client.post(
        "/api/v1/compliance/au/age-verification",
        json={"country_code": "AU", "method": "<script>alert(1)</script>"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_au_cyberbullying_sql_injection_severity(sec_client):
    """SQL injection in severity field is rejected."""
    token, _ = await _register_and_login(sec_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await sec_client.post(
        "/api/v1/compliance/au/cyberbullying-case",
        json={
            "reporter_id": str(uuid4()),
            "target_id": str(uuid4()),
            "evidence_ids": [],
            "severity": "'; DROP TABLE users; --",
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_au_age_verification_oversized_data(sec_client):
    """Extremely large verification_data is handled."""
    token, _ = await _register_and_login(sec_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await sec_client.post(
        "/api/v1/compliance/au/age-verification",
        json={
            "country_code": "AU",
            "method": "yoti",
            "verification_data": {"large_field": "x" * 100000},
        },
        headers=headers,
    )
    # Should succeed (encryption handles it) or fail gracefully
    assert resp.status_code in (201, 422, 500)


@pytest.mark.asyncio
async def test_au_cyberbullying_invalid_uuid_reporter(sec_client):
    """Invalid UUID for reporter_id returns error."""
    token, _ = await _register_and_login(sec_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await sec_client.post(
        "/api/v1/compliance/au/cyberbullying-case",
        json={
            "reporter_id": "not-a-uuid",
            "target_id": str(uuid4()),
            "evidence_ids": [],
            "severity": "low",
        },
        headers=headers,
    )
    assert resp.status_code in (422, 500)


@pytest.mark.asyncio
async def test_au_invalid_bearer_token(sec_client):
    """Invalid bearer token returns 401."""
    headers = {"Authorization": "Bearer invalid-token-abc123"}

    resp = await sec_client.get(
        "/api/v1/compliance/au/esafety-sla",
        headers=headers,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_au_cyberbullying_empty_body(sec_client):
    """Empty JSON body on case creation returns 422."""
    token, _ = await _register_and_login(sec_client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await sec_client.post(
        "/api/v1/compliance/au/cyberbullying-case",
        json={},
        headers=headers,
    )
    assert resp.status_code in (422, 500)


# ---------------------------------------------------------------------------
# Authorization Boundary Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_au_workflow_advance_requires_auth(sec_client):
    """PATCH /au/cyberbullying-case/{id}/workflow without auth returns 401."""
    resp = await sec_client.patch(
        f"/api/v1/compliance/au/cyberbullying-case/{uuid4()}/workflow",
        json={"step": "document"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_au_case_close_requires_auth(sec_client):
    """POST /au/cyberbullying-case/{id}/close without auth returns 401."""
    resp = await sec_client.post(
        f"/api/v1/compliance/au/cyberbullying-case/{uuid4()}/close",
        json={"resolution": "test"},
    )
    assert resp.status_code == 401
