"""E2E tests for OAuth SSO endpoints.

Tests OAuth authorize URL generation, callback handling with mocked provider
responses, user creation/linking, and token encryption.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client, email="oauth@test.com"):
    """Register, return (token, user_id as str)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "OAuth Tester",
        "account_type": "family",
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


def _mock_google_token_response():
    """Mock Google token exchange response."""
    return {
        "access_token": "ya29.mock-google-access-token",
        "refresh_token": "1//mock-google-refresh-token",
        "id_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.stub",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


def _mock_google_userinfo_response():
    """Mock Google userinfo response."""
    return {
        "sub": "google-user-12345",
        "email": "testuser@gmail.com",
        "name": "Test Google User",
        "picture": "https://example.com/photo.jpg",
    }


def _mock_microsoft_token_response():
    """Mock Microsoft token exchange response."""
    return {
        "access_token": "EwB-mock-microsoft-access-token",
        "refresh_token": "M.mock-microsoft-refresh-token",
        "id_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.stub",
        "token_type": "Bearer",
        "expires_in": 3600,
    }


def _mock_microsoft_userinfo_response():
    """Mock Microsoft Graph /me response."""
    return {
        "id": "ms-user-67890",
        "displayName": "Test Microsoft User",
        "mail": "testuser@outlook.com",
        "userPrincipalName": "testuser@outlook.com",
    }


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def oauth_client():
    """Test client for OAuth tests with committing session."""
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
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
    ) as client:
        yield client, session

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Authorization URL tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("src.auth.oauth.settings")
async def test_google_authorize_url(mock_settings, oauth_client):
    """GET /auth/oauth/google/authorize returns authorization URL."""
    client, _ = oauth_client
    mock_settings.oauth_google_client_id = "test-google-client-id"
    mock_settings.oauth_google_client_secret = "test-google-secret"
    mock_settings.oauth_redirect_base_url = "http://test"

    resp = await client.get("/api/v1/auth/oauth/google/authorize")
    assert resp.status_code == 200
    data = resp.json()
    assert "authorization_url" in data
    assert "state" in data
    assert "accounts.google.com" in data["authorization_url"]
    assert "test-google-client-id" in data["authorization_url"]


@pytest.mark.asyncio
@patch("src.auth.oauth.settings")
async def test_microsoft_authorize_url(mock_settings, oauth_client):
    """GET /auth/oauth/microsoft/authorize returns authorization URL."""
    client, _ = oauth_client
    mock_settings.oauth_microsoft_client_id = "test-ms-client-id"
    mock_settings.oauth_microsoft_client_secret = "test-ms-secret"
    mock_settings.oauth_redirect_base_url = "http://test"

    resp = await client.get("/api/v1/auth/oauth/microsoft/authorize")
    assert resp.status_code == 200
    data = resp.json()
    assert "login.microsoftonline.com" in data["authorization_url"]


@pytest.mark.asyncio
@patch("src.auth.oauth.settings")
async def test_apple_authorize_url(mock_settings, oauth_client):
    """GET /auth/oauth/apple/authorize returns authorization URL."""
    client, _ = oauth_client
    mock_settings.oauth_apple_client_id = "test-apple-client-id"
    mock_settings.oauth_apple_client_secret = "test-apple-secret"
    mock_settings.oauth_redirect_base_url = "http://test"

    resp = await client.get("/api/v1/auth/oauth/apple/authorize")
    assert resp.status_code == 200
    data = resp.json()
    assert "appleid.apple.com" in data["authorization_url"]
    assert "response_mode=form_post" in data["authorization_url"]


@pytest.mark.asyncio
async def test_unsupported_provider_returns_422(oauth_client):
    """GET /auth/oauth/invalid/authorize returns 422."""
    client, _ = oauth_client
    resp = await client.get("/api/v1/auth/oauth/invalid/authorize")
    assert resp.status_code == 422


@pytest.mark.asyncio
@patch("src.auth.oauth.settings")
async def test_unconfigured_provider_returns_422(mock_settings, oauth_client):
    """Provider without credentials returns 422."""
    client, _ = oauth_client
    mock_settings.oauth_google_client_id = None
    mock_settings.oauth_google_client_secret = None

    resp = await client.get("/api/v1/auth/oauth/google/authorize")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Callback tests (mocked provider responses)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("src.auth.oauth.settings")
async def test_google_callback_creates_new_user(mock_settings, oauth_client):
    """Google OAuth callback creates a new user and redirects."""
    client, session = oauth_client
    mock_settings.oauth_google_client_id = "test-client-id"
    mock_settings.oauth_google_client_secret = "test-secret"
    mock_settings.oauth_redirect_base_url = "http://test"
    mock_settings.is_production = False
    mock_settings.session_timeout_hours = 24
    mock_settings.cookie_domain = None

    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = _mock_google_token_response()

    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.status_code = 200
    mock_userinfo_resp.json.return_value = _mock_google_userinfo_response()

    with patch("src.auth.oauth.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_token_resp
        mock_instance.get.return_value = mock_userinfo_resp
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_instance

        resp = await client.get(
            "/api/v1/auth/oauth/google/callback?code=test-auth-code&state=test-state",
            follow_redirects=False,
        )

    # Should redirect with token
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "token=" in location
    assert "bhapi_session" in resp.headers.get("set-cookie", "")

    # Verify user was created
    from src.auth.models import User
    result = await session.execute(select(User).where(User.email == "testuser@gmail.com"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.display_name == "Test Google User"
    assert user.email_verified is True
    assert user.password_hash is None  # OAuth user, no password


@pytest.mark.asyncio
@patch("src.auth.oauth.settings")
async def test_callback_links_to_existing_user(mock_settings, oauth_client):
    """OAuth callback links to existing user with same email."""
    client, session = oauth_client
    mock_settings.oauth_google_client_id = "test-client-id"
    mock_settings.oauth_google_client_secret = "test-secret"
    mock_settings.oauth_redirect_base_url = "http://test"
    mock_settings.is_production = False
    mock_settings.session_timeout_hours = 24
    mock_settings.cookie_domain = None

    # Register user first
    await client.post("/api/v1/auth/register", json={
        "email": "testuser@gmail.com",
        "password": "SecurePass1",
        "display_name": "Existing User",
        "account_type": "family",
    })

    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = _mock_google_token_response()

    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.status_code = 200
    mock_userinfo_resp.json.return_value = _mock_google_userinfo_response()

    with patch("src.auth.oauth.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_token_resp
        mock_instance.get.return_value = mock_userinfo_resp
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_instance

        resp = await client.get(
            "/api/v1/auth/oauth/google/callback?code=test-auth-code&state=test-state",
            follow_redirects=False,
        )

    assert resp.status_code == 302

    # Verify only one user exists (linked, not duplicated)
    from src.auth.models import User
    result = await session.execute(select(User).where(User.email == "testuser@gmail.com"))
    users = list(result.scalars().all())
    assert len(users) == 1
    assert users[0].display_name == "Existing User"  # Original name preserved


@pytest.mark.asyncio
@patch("src.auth.oauth.settings")
async def test_callback_token_encryption(mock_settings, oauth_client):
    """OAuth tokens are encrypted before storage."""
    client, session = oauth_client
    mock_settings.oauth_google_client_id = "test-client-id"
    mock_settings.oauth_google_client_secret = "test-secret"
    mock_settings.oauth_redirect_base_url = "http://test"
    mock_settings.is_production = False
    mock_settings.session_timeout_hours = 24
    mock_settings.cookie_domain = None

    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = _mock_google_token_response()

    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.status_code = 200
    mock_userinfo_resp.json.return_value = _mock_google_userinfo_response()

    with patch("src.auth.oauth.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_token_resp
        mock_instance.get.return_value = mock_userinfo_resp
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_instance

        await client.get(
            "/api/v1/auth/oauth/google/callback?code=test-code&state=test-state",
            follow_redirects=False,
        )

    # Verify tokens are encrypted (not stored in plaintext)
    from src.auth.models import OAuthConnection
    result = await session.execute(select(OAuthConnection))
    conn = result.scalar_one()
    assert conn.access_token_encrypted.startswith("fernet:")
    assert conn.refresh_token_encrypted.startswith("fernet:")
    assert "ya29" not in conn.access_token_encrypted  # Raw token not visible


@pytest.mark.asyncio
async def test_oauth_authorize_no_auth_required(oauth_client):
    """OAuth endpoints don't require authentication (public prefix)."""
    client, _ = oauth_client
    # The middleware allows /api/v1/auth/oauth prefix without auth
    # Even if provider is not configured, we should get 422 (not 401)
    resp = await client.get("/api/v1/auth/oauth/google/authorize")
    # Should be 422 (not configured) rather than 401 (unauthorized)
    assert resp.status_code != 401
