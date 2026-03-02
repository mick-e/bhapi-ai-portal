"""Auth flow E2E tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


@pytest.fixture
async def auth_client():
    """Auth test client with committing DB session."""
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


# --- Registration Tests ---

@pytest.mark.asyncio
async def test_register_family_account(auth_client):
    """Register a family account returns token and session cookie."""
    response = await auth_client.post("/api/v1/auth/register", json={
        "email": "parent@example.com",
        "password": "SecurePass1",
        "display_name": "Test Parent",
        "account_type": "family",
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "parent@example.com"
    assert data["user"]["display_name"] == "Test Parent"
    assert data["user"]["account_type"] == "family"
    assert data["user"]["group_id"] is not None
    assert "bhapi_session" in response.cookies


@pytest.mark.asyncio
async def test_register_school_account(auth_client):
    """Register a school account returns token."""
    response = await auth_client.post("/api/v1/auth/register", json={
        "email": "admin@school.edu",
        "password": "SecurePass1",
        "display_name": "School Admin",
        "account_type": "school",
    })
    assert response.status_code == 201
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_register_club_account(auth_client):
    """Register a club account returns token."""
    response = await auth_client.post("/api/v1/auth/register", json={
        "email": "manager@club.org",
        "password": "SecurePass1",
        "display_name": "Club Manager",
        "account_type": "club",
    })
    assert response.status_code == 201
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_register_duplicate_email(auth_client):
    """Duplicate email returns 409."""
    user_data = {
        "email": "dup@example.com",
        "password": "SecurePass1",
        "display_name": "First User",
        "account_type": "family",
    }
    await auth_client.post("/api/v1/auth/register", json=user_data)
    response = await auth_client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(auth_client):
    """Weak password is rejected."""
    response = await auth_client.post("/api/v1/auth/register", json={
        "email": "user@example.com",
        "password": "weak",
        "display_name": "User",
        "account_type": "family",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_account_type(auth_client):
    """Invalid account type is rejected."""
    response = await auth_client.post("/api/v1/auth/register", json={
        "email": "user@example.com",
        "password": "SecurePass1",
        "display_name": "User",
        "account_type": "invalid",
    })
    assert response.status_code == 422


# --- Login Tests ---

@pytest.mark.asyncio
async def test_login_success(auth_client):
    """Login with valid credentials returns token."""
    # Register first
    await auth_client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "SecurePass1",
        "display_name": "Login User",
        "account_type": "family",
    })

    # Login
    response = await auth_client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "SecurePass1",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "login@example.com"

    # Check session cookie
    assert "bhapi_session" in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_password(auth_client):
    """Login with wrong password returns 401."""
    await auth_client.post("/api/v1/auth/register", json={
        "email": "user2@example.com",
        "password": "SecurePass1",
        "display_name": "User",
        "account_type": "family",
    })

    response = await auth_client.post("/api/v1/auth/login", json={
        "email": "user2@example.com",
        "password": "WrongPassword1",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(auth_client):
    """Login with non-existent email returns 401."""
    response = await auth_client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "SecurePass1",
    })
    assert response.status_code == 401


# --- Auth-Protected Endpoints ---

@pytest.mark.asyncio
async def test_api_requires_auth_header(auth_client):
    """API endpoints require auth."""
    response = await auth_client.get("/api/v1/groups")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_with_bearer_token(auth_client):
    """API works with valid bearer token."""
    # Register and login
    await auth_client.post("/api/v1/auth/register", json={
        "email": "bearer@example.com",
        "password": "SecurePass1",
        "display_name": "Bearer User",
        "account_type": "family",
    })
    login_response = await auth_client.post("/api/v1/auth/login", json={
        "email": "bearer@example.com",
        "password": "SecurePass1",
    })
    token = login_response.json()["access_token"]

    # Use token to access protected endpoint
    response = await auth_client.get(
        "/api/v1/groups",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


# --- Logout ---

@pytest.mark.asyncio
async def test_logout(auth_client):
    """Logout clears session cookie."""
    response = await auth_client.post("/api/v1/auth/logout")
    assert response.status_code == 204


# --- Password Reset ---

@pytest.mark.asyncio
async def test_password_reset_request(auth_client):
    """Password reset always returns 202 (prevents email enumeration)."""
    response = await auth_client.post("/api/v1/auth/password/reset", json={
        "email": "nonexistent@example.com",
    })
    assert response.status_code == 202
