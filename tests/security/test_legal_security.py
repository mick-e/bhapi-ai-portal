"""Legal module security tests — public access, injection, read-only enforcement."""

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


# --- Public Access (no auth required) ---


@pytest.mark.asyncio
async def test_privacy_policy_accessible_without_auth(sec_client):
    """Privacy policy is publicly accessible without authentication."""
    resp = await sec_client.get("/legal/privacy")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_terms_accessible_without_auth(sec_client):
    """Terms of service is publicly accessible without authentication."""
    resp = await sec_client.get("/legal/terms")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_children_privacy_accessible_without_auth(sec_client):
    """Children's privacy notice is publicly accessible without authentication."""
    resp = await sec_client.get("/legal/privacy-for-children")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_security_program_accessible_without_auth(sec_client):
    """Security program page is publicly accessible (returns 200 or 404 if doc missing)."""
    resp = await sec_client.get("/legal/security-program")
    assert resp.status_code in (200, 404)


# --- Content-Type Headers ---


@pytest.mark.asyncio
async def test_privacy_policy_html_content_type(sec_client):
    """Privacy policy returns HTML content-type."""
    resp = await sec_client.get("/legal/privacy")
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_terms_html_content_type(sec_client):
    """Terms of service returns HTML content-type."""
    resp = await sec_client.get("/legal/terms")
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_children_privacy_html_content_type(sec_client):
    """Children's privacy notice returns HTML content-type."""
    resp = await sec_client.get("/legal/privacy-for-children")
    assert "text/html" in resp.headers.get("content-type", "")


# --- Read-Only Enforcement ---


@pytest.mark.asyncio
async def test_post_to_privacy_rejected(sec_client):
    """POST to legal endpoints is not allowed (405 Method Not Allowed)."""
    resp = await sec_client.post("/legal/privacy", content="modified content")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_put_to_terms_rejected(sec_client):
    """PUT to legal endpoints is not allowed (405 Method Not Allowed)."""
    resp = await sec_client.put("/legal/terms", content="modified content")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_delete_to_privacy_rejected(sec_client):
    """DELETE to legal endpoints is not allowed (405 Method Not Allowed)."""
    resp = await sec_client.delete("/legal/privacy")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_patch_to_children_privacy_rejected(sec_client):
    """PATCH to legal endpoints is not allowed (405 Method Not Allowed)."""
    resp = await sec_client.patch("/legal/privacy-for-children", content="modified")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_post_to_terms_rejected(sec_client):
    """POST to terms endpoint is not allowed."""
    resp = await sec_client.post("/legal/terms", json={"content": "new terms"})
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_put_to_security_program_rejected(sec_client):
    """PUT to security program endpoint is not allowed."""
    resp = await sec_client.put("/legal/security-program", content="modified")
    assert resp.status_code == 405


# --- Injection Attempts ---


@pytest.mark.asyncio
async def test_path_traversal_in_legal_routes(sec_client):
    """Path traversal attempts on legal routes do not serve arbitrary files."""
    resp = await sec_client.get("/legal/../../etc/passwd")
    # SPA catch-all may return 200 with HTML — the key check is no file content leaked
    assert resp.status_code != 500
    assert "root:" not in resp.text  # /etc/passwd content not served
    assert "/etc/passwd" not in resp.text


@pytest.mark.asyncio
async def test_xss_in_query_params_not_reflected(sec_client):
    """XSS payloads in query params are not reflected in legal page responses."""
    xss = "<script>alert('xss')</script>"
    resp = await sec_client.get("/legal/privacy", params={"q": xss})
    assert resp.status_code == 200
    assert "<script>alert('xss')</script>" not in resp.text


@pytest.mark.asyncio
async def test_sql_injection_in_legal_path(sec_client):
    """SQL injection in legal paths does not cause server errors."""
    resp = await sec_client.get("/legal/'; DROP TABLE users; --")
    # SPA catch-all may return 200 with HTML — key check is no 500 or SQL error
    assert resp.status_code != 500
    assert "syntax error" not in resp.text.lower()
    assert "DROP TABLE" not in resp.text


# --- No Internal Data Exposure ---


@pytest.mark.asyncio
async def test_privacy_policy_no_internal_paths(sec_client):
    """Privacy policy does not expose internal file paths or secrets."""
    resp = await sec_client.get("/legal/privacy")
    body = resp.text.lower()
    assert "traceback" not in body
    assert "secret_key" not in body
    assert "password_hash" not in body
    assert "database_url" not in body


@pytest.mark.asyncio
async def test_terms_no_internal_paths(sec_client):
    """Terms of service does not expose internal file paths or secrets."""
    resp = await sec_client.get("/legal/terms")
    body = resp.text.lower()
    assert "traceback" not in body
    assert "secret_key" not in body
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_children_privacy_no_internal_data(sec_client):
    """Children's privacy notice does not expose internal data."""
    resp = await sec_client.get("/legal/privacy-for-children")
    body = resp.text.lower()
    assert "traceback" not in body
    assert "secret_key" not in body
    assert "database_url" not in body


# --- Security Headers on Legal Pages ---


@pytest.mark.asyncio
async def test_legal_pages_have_security_headers(sec_client):
    """Legal pages include standard security headers."""
    resp = await sec_client.get("/legal/privacy")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"


@pytest.mark.asyncio
async def test_legal_pages_have_csp(sec_client):
    """Legal pages include Content-Security-Policy header."""
    resp = await sec_client.get("/legal/terms")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "default-src" in csp


# --- Content Integrity ---


@pytest.mark.asyncio
async def test_privacy_policy_contains_expected_content(sec_client):
    """Privacy policy contains expected sections (not empty or error)."""
    resp = await sec_client.get("/legal/privacy")
    body = resp.text
    assert "Privacy Policy" in body
    assert len(body) > 500  # Not a stub


@pytest.mark.asyncio
async def test_terms_contains_expected_content(sec_client):
    """Terms of service contains expected sections."""
    resp = await sec_client.get("/legal/terms")
    body = resp.text
    assert "Terms" in body
    assert len(body) > 500


@pytest.mark.asyncio
async def test_children_privacy_contains_expected_content(sec_client):
    """Children's privacy notice contains expected child-friendly content."""
    resp = await sec_client.get("/legal/privacy-for-children")
    body = resp.text
    assert len(body) > 200
