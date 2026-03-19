"""Auth security tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def sec_client():
    """Security test client."""
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


# --- Password Security ---

@pytest.mark.asyncio
async def test_password_too_short(sec_client):
    """Password under 8 chars rejected."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "a@b.com", "password": "Short1", "display_name": "X", "account_type": "family",
        "privacy_notice_accepted": True,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_password_no_uppercase(sec_client):
    """Password without uppercase rejected."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "a@b.com", "password": "nouppercase1", "display_name": "X", "account_type": "family",
        "privacy_notice_accepted": True,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_password_no_lowercase(sec_client):
    """Password without lowercase rejected."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "a@b.com", "password": "NOLOWERCASE1", "display_name": "X", "account_type": "family",
        "privacy_notice_accepted": True,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_password_no_digit(sec_client):
    """Password without digit rejected."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "a@b.com", "password": "NoDigitHere", "display_name": "X", "account_type": "family",
        "privacy_notice_accepted": True,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_password_not_returned_in_response(sec_client):
    """Password hash never exposed in API response."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "safe@test.com", "password": "SecurePass1", "display_name": "Safe", "account_type": "family",
        "privacy_notice_accepted": True,
    })
    data = resp.json()
    assert "password" not in data
    assert "password_hash" not in data


# --- Token Security ---

@pytest.mark.asyncio
async def test_invalid_bearer_token(sec_client):
    """Invalid bearer token returns 401."""
    resp = await sec_client.get(
        "/api/v1/groups",
        headers={"Authorization": "Bearer invalid-token-here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_token(sec_client):
    """Expired token returns 401."""
    from datetime import datetime, timedelta, timezone

    from jose import jwt
    token = jwt.encode(
        {"sub": "fake-user-id", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        "test-secret-key-for-testing-only-min32chars",
        algorithm="HS256",
    )
    resp = await sec_client.get(
        "/api/v1/groups",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_malformed_auth_header(sec_client):
    """Malformed auth header returns 401."""
    resp = await sec_client.get(
        "/api/v1/groups",
        headers={"Authorization": "NotBearer something"},
    )
    assert resp.status_code == 401


# --- Email Enumeration ---

@pytest.mark.asyncio
async def test_password_reset_no_email_enumeration(sec_client):
    """Password reset returns 202 regardless of email existence."""
    resp1 = await sec_client.post("/api/v1/auth/password/reset", json={
        "email": "exists@test.com",
    })
    resp2 = await sec_client.post("/api/v1/auth/password/reset", json={
        "email": "doesnotexist@test.com",
    })
    assert resp1.status_code == resp2.status_code == 202


@pytest.mark.asyncio
async def test_login_generic_error_message(sec_client):
    """Login with wrong password doesn't reveal if email exists."""
    # Register a user
    await sec_client.post("/api/v1/auth/register", json={
        "email": "victim@test.com", "password": "SecurePass1",
        "display_name": "Victim", "account_type": "family",
        "privacy_notice_accepted": True,
    })

    # Wrong password
    resp1 = await sec_client.post("/api/v1/auth/login", json={
        "email": "victim@test.com", "password": "WrongPassword1",
    })
    # Non-existent email
    resp2 = await sec_client.post("/api/v1/auth/login", json={
        "email": "nobody@test.com", "password": "WrongPassword1",
    })

    assert resp1.status_code == resp2.status_code == 401
    # Both should have same error message
    assert resp1.json()["error"] == resp2.json()["error"]


# --- Security Headers ---

@pytest.mark.asyncio
async def test_security_headers_present(sec_client):
    """All required security headers are present."""
    resp = await sec_client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "max-age=" in resp.headers.get("Strict-Transport-Security", "")
    assert "Permissions-Policy" in resp.headers
    assert "Referrer-Policy" in resp.headers


@pytest.mark.asyncio
async def test_csp_header(sec_client):
    """Content Security Policy header is present and restrictive."""
    resp = await sec_client.get("/health")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


@pytest.mark.asyncio
async def test_cors_rejects_unknown_origin(sec_client):
    """CORS rejects requests from unknown origins."""
    resp = await sec_client.options("/api/v1/auth/login", headers={
        "Origin": "https://evil.com",
        "Access-Control-Request-Method": "POST",
    })
    # Should not have Access-Control-Allow-Origin for evil.com
    allow_origin = resp.headers.get("Access-Control-Allow-Origin", "")
    assert "evil.com" not in allow_origin


# --- Input Validation ---

@pytest.mark.asyncio
async def test_sql_injection_in_email(sec_client):
    """SQL injection in email field is rejected."""
    resp = await sec_client.post("/api/v1/auth/login", json={
        "email": "'; DROP TABLE users; --",
        "password": "SecurePass1",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_xss_in_display_name(sec_client):
    """XSS in display name is stored safely (not executed)."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "xss@test.com",
        "password": "SecurePass1",
        "display_name": "<script>alert('xss')</script>",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    assert resp.status_code == 201
    # Register returns TokenResponse; verify via /me that name is stored as-is
    token = resp.json()["access_token"]
    me = await sec_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["display_name"] == "<script>alert('xss')</script>"


@pytest.mark.asyncio
async def test_oversized_payload(sec_client):
    """Very large payloads are handled."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "big@test.com",
        "password": "SecurePass1",
        "display_name": "A" * 300,  # Over max_length
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    assert resp.status_code == 422


# --- Data Isolation ---

@pytest.mark.asyncio
async def test_user_cannot_see_other_users_groups(sec_client):
    """Users can only see their own groups."""
    # User 1
    await sec_client.post("/api/v1/auth/register", json={
        "email": "u1@test.com", "password": "SecurePass1",
        "display_name": "U1", "account_type": "family",
        "privacy_notice_accepted": True,
    })
    login1 = await sec_client.post("/api/v1/auth/login", json={
        "email": "u1@test.com", "password": "SecurePass1",
    })
    token1 = login1.json()["access_token"]
    h1 = {"Authorization": f"Bearer {token1}"}

    await sec_client.post("/api/v1/groups", json={"name": "U1 Family", "type": "family"}, headers=h1)

    # User 2
    await sec_client.post("/api/v1/auth/register", json={
        "email": "u2@test.com", "password": "SecurePass1",
        "display_name": "U2", "account_type": "family",
        "privacy_notice_accepted": True,
    })
    login2 = await sec_client.post("/api/v1/auth/login", json={
        "email": "u2@test.com", "password": "SecurePass1",
    })
    token2 = login2.json()["access_token"]
    h2 = {"Authorization": f"Bearer {token2}"}

    # User 2 should only see their own auto-created group (not user 1's group)
    resp = await sec_client.get("/api/v1/groups", headers=h2)
    assert resp.status_code == 200
    groups = resp.json()
    assert all("U1 Family" != g["name"] for g in groups)
