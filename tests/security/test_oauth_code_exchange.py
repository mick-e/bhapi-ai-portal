"""Security tests for OAuth auth-code exchange (R-16).

Covers:
- OAuth callback redirects with auth code, NOT session token in URL
- POST /oauth/exchange swaps a one-time code for a session
- Used codes cannot be replayed (one-time use)
- Invalid/expired codes return 401
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.auth.router import (
    _generate_oauth_state,
    _oauth_code_store,
    _oauth_states,
)
from src.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _mock_oauth_flow():
    """Return context managers that mock the full OAuth provider exchange."""
    return (
        patch("src.auth.router.exchange_code_for_tokens", new_callable=AsyncMock,
              return_value={"access_token": "tok", "id_token": None}),
        patch("src.auth.router.get_oauth_user_info", new_callable=AsyncMock,
              return_value=AsyncMock(refresh_token=None)),
        patch("src.auth.router.find_or_create_oauth_user", new_callable=AsyncMock,
              return_value=AsyncMock(id="user-123")),
        patch("src.auth.router.create_session", new_callable=AsyncMock,
              return_value="real-session-token-xyz"),
    )


@pytest.fixture(autouse=True)
def _clean_stores():
    """Clear OAuth state and code stores before/after each test."""
    _oauth_states.clear()
    _oauth_code_store.clear()
    yield
    _oauth_states.clear()
    _oauth_code_store.clear()


# ---------------------------------------------------------------------------
# Callback redirect must contain auth code, NOT session token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_oauth_callback_redirects_with_code_not_token(client):
    """OAuth callback redirect URL must contain code=, not token= or session=."""
    state = _generate_oauth_state()

    mock_exchange, mock_info, mock_find, mock_session = _mock_oauth_flow()
    with mock_exchange, mock_info, mock_find, mock_session:
        resp = await client.get(
            "/api/v1/auth/oauth/google/callback",
            params={"code": "provider-auth-code", "state": state},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "code=" in location, f"Redirect missing auth code: {location}"
    assert "token=" not in location, f"Session token leaked in URL: {location}"
    assert "session=" not in location, f"Session leaked in URL: {location}"
    assert "Bearer" not in location, f"Bearer token leaked in URL: {location}"


@pytest.mark.asyncio
async def test_oauth_callback_does_not_set_cookie(client):
    """OAuth callback should NOT set session cookie — that happens on exchange."""
    state = _generate_oauth_state()

    mock_exchange, mock_info, mock_find, mock_session = _mock_oauth_flow()
    with mock_exchange, mock_info, mock_find, mock_session:
        resp = await client.get(
            "/api/v1/auth/oauth/google/callback",
            params={"code": "provider-auth-code", "state": state},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    # No session cookie on the redirect response
    assert "bhapi_session" not in resp.cookies


# ---------------------------------------------------------------------------
# Code exchange endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_oauth_code_exchange_returns_session(client):
    """POST /oauth/exchange swaps a valid auth code for a session token."""
    state = _generate_oauth_state()

    mock_exchange, mock_info, mock_find, mock_session = _mock_oauth_flow()
    with mock_exchange, mock_info, mock_find, mock_session:
        callback = await client.get(
            "/api/v1/auth/oauth/google/callback",
            params={"code": "provider-code", "state": state},
            follow_redirects=False,
        )

    # Extract auth code from redirect URL
    location = callback.headers["location"]
    auth_code = location.split("code=")[1].split("&")[0]

    # Exchange for session
    resp = await client.post(
        "/api/v1/auth/oauth/exchange",
        json={"code": auth_code},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["token"] == "real-session-token-xyz"


@pytest.mark.asyncio
async def test_oauth_code_is_one_time_use(client):
    """The same auth code cannot be exchanged twice."""
    state = _generate_oauth_state()

    mock_exchange, mock_info, mock_find, mock_session = _mock_oauth_flow()
    with mock_exchange, mock_info, mock_find, mock_session:
        callback = await client.get(
            "/api/v1/auth/oauth/google/callback",
            params={"code": "provider-code", "state": state},
            follow_redirects=False,
        )

    auth_code = callback.headers["location"].split("code=")[1].split("&")[0]

    # First exchange succeeds
    resp1 = await client.post("/api/v1/auth/oauth/exchange", json={"code": auth_code})
    assert resp1.status_code == 200

    # Second exchange with same code fails
    resp2 = await client.post("/api/v1/auth/oauth/exchange", json={"code": auth_code})
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_oauth_exchange_rejects_invalid_code(client):
    """Exchange with a fabricated code returns 401."""
    resp = await client.post(
        "/api/v1/auth/oauth/exchange",
        json={"code": "totally-fake-code"},
    )
    assert resp.status_code == 401
    assert "Invalid or expired" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_oauth_exchange_rejects_empty_code(client):
    """Exchange with empty code returns 422 (validation error)."""
    resp = await client.post(
        "/api/v1/auth/oauth/exchange",
        json={},
    )
    assert resp.status_code == 422
