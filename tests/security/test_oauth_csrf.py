"""Security tests for OAuth CSRF state parameter validation.

Covers:
- OAuth callback rejects invalid state tokens (CSRF protection)
- OAuth callback rejects missing state tokens
- OAuth callback rejects reused state tokens (one-time use)
- OAuth authorize endpoint generates and stores state tokens
- Expired state tokens are rejected
"""

import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.auth.router import (
    _generate_oauth_state,
    _oauth_states,
    _validate_oauth_state,
)
from src.exceptions import ForbiddenError
from src.main import create_app


# ---------------------------------------------------------------------------
# Unit tests for state helpers
# ---------------------------------------------------------------------------


class TestValidateOAuthState:
    """Unit tests for _validate_oauth_state."""

    def setup_method(self):
        _oauth_states.clear()

    def teardown_method(self):
        _oauth_states.clear()

    def test_valid_state_is_consumed(self):
        """A valid, unexpired state is accepted and removed (one-time use)."""
        state = _generate_oauth_state()
        assert state in _oauth_states
        _validate_oauth_state(state)
        assert state not in _oauth_states

    def test_missing_state_raises_forbidden(self):
        """Empty string state raises ForbiddenError."""
        with pytest.raises(ForbiddenError, match="missing"):
            _validate_oauth_state("")

    def test_invalid_state_raises_forbidden(self):
        """An unknown state value raises ForbiddenError."""
        with pytest.raises(ForbiddenError, match="Invalid or already-used"):
            _validate_oauth_state("not-a-real-state-token")

    def test_reused_state_raises_forbidden(self):
        """Using the same state twice raises ForbiddenError on second use."""
        state = _generate_oauth_state()
        _validate_oauth_state(state)  # first use — OK
        with pytest.raises(ForbiddenError, match="Invalid or already-used"):
            _validate_oauth_state(state)  # second use — rejected

    def test_expired_state_raises_forbidden(self):
        """A state whose TTL has passed raises ForbiddenError."""
        state = _generate_oauth_state()
        # Manually backdate the expiry
        _oauth_states[state] = time.time() - 1
        with pytest.raises(ForbiddenError, match="expired"):
            _validate_oauth_state(state)


class TestGenerateOAuthState:
    """Unit tests for _generate_oauth_state."""

    def setup_method(self):
        _oauth_states.clear()

    def teardown_method(self):
        _oauth_states.clear()

    def test_generates_unique_states(self):
        """Each call produces a distinct state token."""
        states = {_generate_oauth_state() for _ in range(50)}
        assert len(states) == 50

    def test_state_stored_with_future_expiry(self):
        """Generated state is stored with an expiry in the future."""
        state = _generate_oauth_state()
        assert state in _oauth_states
        assert _oauth_states[state] > time.time()

    def test_evicts_expired_entries_on_generate(self):
        """Expired entries are cleaned up when generating a new state."""
        # Insert some expired entries
        for i in range(5):
            _oauth_states[f"expired-{i}"] = time.time() - 100
        assert len(_oauth_states) == 5
        _generate_oauth_state()
        # Expired entries should be gone, only the new one remains
        assert len(_oauth_states) == 1


# ---------------------------------------------------------------------------
# Integration tests against the app
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_oauth_authorize_generates_state(client):
    """GET /oauth/{provider}/authorize returns a state that is stored server-side."""
    _oauth_states.clear()

    with patch("src.auth.router.get_authorization_url") as mock_get_url:
        mock_get_url.return_value = (
            "https://accounts.google.com/o/oauth2/v2/auth?state=provider-state&client_id=x",
            "provider-state",
        )
        resp = await client.get("/api/v1/auth/oauth/google/authorize")

    assert resp.status_code == 200
    data = resp.json()
    returned_state = data["state"]
    # The state returned to the client should exist in our server-side store
    assert returned_state in _oauth_states
    # The authorization URL should contain our server-side state, not the provider one
    assert returned_state in data["authorization_url"]
    _oauth_states.clear()


@pytest.mark.asyncio
async def test_oauth_callback_rejects_invalid_state(client):
    """OAuth callback with a fabricated state returns 403."""
    _oauth_states.clear()
    resp = await client.get(
        "/api/v1/auth/oauth/google/callback",
        params={"code": "fake-code", "state": "attacker-forged-state"},
    )
    assert resp.status_code == 403
    assert "Invalid or already-used" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_oauth_callback_rejects_missing_state(client):
    """OAuth callback with empty state returns 403."""
    _oauth_states.clear()
    resp = await client.get(
        "/api/v1/auth/oauth/google/callback",
        params={"code": "fake-code", "state": ""},
    )
    assert resp.status_code == 403
    assert "missing" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_oauth_callback_rejects_reused_state(client):
    """OAuth callback rejects a state token that was already consumed."""
    _oauth_states.clear()

    # Generate a valid state
    state = _generate_oauth_state()

    # Mock the OAuth flow so the first call succeeds
    with (
        patch("src.auth.router.exchange_code_for_tokens", new_callable=AsyncMock) as mock_exchange,
        patch("src.auth.router.get_oauth_user_info", new_callable=AsyncMock) as mock_info,
        patch("src.auth.router.find_or_create_oauth_user", new_callable=AsyncMock) as mock_find,
        patch("src.auth.router.create_session", new_callable=AsyncMock) as mock_session,
    ):
        mock_exchange.return_value = {"access_token": "tok", "id_token": None}
        mock_info.return_value = AsyncMock(refresh_token=None)
        mock_find.return_value = AsyncMock(id="user-123")
        mock_session.return_value = "session-token"

        # First call consumes the state
        resp1 = await client.get(
            "/api/v1/auth/oauth/google/callback",
            params={"code": "auth-code", "state": state},
            follow_redirects=False,
        )
        assert resp1.status_code == 302

    # Second call with same state should be rejected (no mocks needed — fails before exchange)
    resp2 = await client.get(
        "/api/v1/auth/oauth/google/callback",
        params={"code": "auth-code", "state": state},
    )
    assert resp2.status_code == 403
    assert "Invalid or already-used" in resp2.json()["detail"]
    _oauth_states.clear()
