"""Injection attack security tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy import event

from httpx import ASGITransport, AsyncClient
from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def sec_client():
    """Security test client with committing sessions."""
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


# --- SQL Injection ---

@pytest.mark.asyncio
async def test_sql_injection_in_login_email(sec_client):
    """SQL injection in login email field is rejected."""
    resp = await sec_client.post("/api/v1/auth/login", json={
        "email": "' OR 1=1 --",
        "password": "SecurePass1",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_union_select(sec_client):
    """UNION SELECT injection in email is rejected."""
    resp = await sec_client.post("/api/v1/auth/login", json={
        "email": "admin@test.com' UNION SELECT * FROM users --",
        "password": "SecurePass1",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_in_display_name(sec_client):
    """SQL injection in display_name doesn't cause errors."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "sqli@test.com",
        "password": "SecurePass1",
        "display_name": "'; DROP TABLE users; --",
        "account_type": "family",
    })
    # Should succeed (display_name allows freeform text) or 422 if too long
    assert resp.status_code in (201, 422)


@pytest.mark.asyncio
async def test_sql_injection_boolean_blind(sec_client):
    """Boolean-based blind SQL injection in email rejected."""
    resp = await sec_client.post("/api/v1/auth/login", json={
        "email": "admin@test.com' AND 1=1 --",
        "password": "SecurePass1",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_stacked_queries(sec_client):
    """Stacked queries injection in email rejected."""
    resp = await sec_client.post("/api/v1/auth/login", json={
        "email": "admin@test.com'; INSERT INTO users VALUES('hacked');--",
        "password": "SecurePass1",
    })
    assert resp.status_code == 422


# --- NoSQL/JSON Injection ---

@pytest.mark.asyncio
async def test_json_injection_in_password(sec_client):
    """JSON injection in password field doesn't bypass validation."""
    resp = await sec_client.post("/api/v1/auth/login", json={
        "email": "test@test.com",
        "password": {"$gt": ""},
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_json_injection_nested_object(sec_client):
    """Nested objects in fields are rejected by Pydantic."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": {"$ne": ""},
        "password": "SecurePass1",
        "display_name": "Test",
        "account_type": "family",
    })
    assert resp.status_code == 422


# --- XSS / HTML Injection ---

@pytest.mark.asyncio
async def test_xss_script_tag_in_email(sec_client):
    """Script tag in email rejected by validation."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "<script>alert('xss')</script>@test.com",
        "password": "SecurePass1",
        "display_name": "Test",
        "account_type": "family",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_xss_img_onerror(sec_client):
    """Image tag with onerror in display name is safely stored."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "xss2@test.com",
        "password": "SecurePass1",
        "display_name": '<img src=x onerror="alert(1)">',
        "account_type": "family",
    })
    assert resp.status_code == 201
    # JSON response is inherently safe — frontend must escape
    data = resp.json()
    assert data["display_name"] == '<img src=x onerror="alert(1)">'


@pytest.mark.asyncio
async def test_xss_event_handler(sec_client):
    """Event handler XSS in display name stored safely."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "xss3@test.com",
        "password": "SecurePass1",
        "display_name": '" onmouseover="alert(document.cookie)"',
        "account_type": "family",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_xss_svg_injection(sec_client):
    """SVG injection in display name stored safely."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "xss4@test.com",
        "password": "SecurePass1",
        "display_name": '<svg onload="alert(1)">',
        "account_type": "family",
    })
    assert resp.status_code == 201


# --- Path Traversal ---

@pytest.mark.asyncio
async def test_path_traversal_in_url(sec_client):
    """Path traversal in URL doesn't leak files."""
    resp = await sec_client.get("/api/v1/../../../etc/passwd")
    assert resp.status_code in (404, 400, 307)


@pytest.mark.asyncio
async def test_null_byte_injection(sec_client):
    """Null byte in email field is rejected."""
    resp = await sec_client.post("/api/v1/auth/register", json={
        "email": "test\x00admin@test.com",
        "password": "SecurePass1",
        "display_name": "Test",
        "account_type": "family",
    })
    assert resp.status_code == 422


# --- Header Injection ---

@pytest.mark.asyncio
async def test_host_header_injection(sec_client):
    """Host header injection doesn't affect responses."""
    resp = await sec_client.get(
        "/health",
        headers={"Host": "evil.com"},
    )
    # App should still respond normally
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_crlf_injection(sec_client):
    """CRLF injection in header values."""
    resp = await sec_client.get(
        "/health",
        headers={"X-Custom": "value\r\nInjected-Header: evil"},
    )
    assert resp.status_code == 200
    assert "Injected-Header" not in resp.headers
