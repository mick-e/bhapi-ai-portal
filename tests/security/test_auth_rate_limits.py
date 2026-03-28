"""Security tests for per-endpoint auth rate limiting.

Covers:
- POST /register is limited to 5 requests per hour per IP
- POST /login is limited to 10 requests per hour per IP
- POST /password/reset is limited to 5 requests per hour per IP
- Rate limit window resets after expiry (mocked time)
"""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app
from src.middleware.rate_limit import _endpoint_limiter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_endpoint_limiter():
    """Reset the endpoint rate limiter buckets between tests."""
    _endpoint_limiter._buckets.clear()
    yield
    _endpoint_limiter._buckets.clear()


@pytest.fixture
async def rl_client():
    """Lightweight client — we only need to hit the rate limiter, not succeed."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()

    async def override_get_db():
        async_session_maker = sessionmaker(
            engine,
            class_=__import__("sqlalchemy.ext.asyncio", fromlist=["AsyncSession"]).AsyncSession,
            expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
RESET_URL = "/api/v1/auth/password/reset"

REGISTER_PAYLOAD = {
    "email": "rl-test@example.com",
    "password": "StrongPass123!",
    "display_name": "RL Test",
    "account_type": "family",
    "privacy_notice_accepted": True,
}

LOGIN_PAYLOAD = {
    "email": "rl-test@example.com",
    "password": "StrongPass123!",
}

RESET_PAYLOAD = {
    "email": "rl-test@example.com",
}


async def _fire_requests(client, url, payload, count):
    """Send *count* POST requests and return the list of status codes."""
    codes = []
    for _ in range(count):
        resp = await client.post(url, json=payload)
        codes.append(resp.status_code)
    return codes


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_rate_limited_after_5_attempts(rl_client):
    """POST /register must return 429 after 5 requests within the window."""
    codes = await _fire_requests(rl_client, REGISTER_URL, REGISTER_PAYLOAD, 7)

    # First 5 should be allowed (may be 201 or 409/422 — we only care they aren't 429)
    for code in codes[:5]:
        assert code != 429, f"Request within limit got 429"

    # Requests 6 and 7 must be rate-limited
    for code in codes[5:]:
        assert code == 429, f"Expected 429 after limit, got {code}"


@pytest.mark.asyncio
async def test_login_rate_limited_after_10_attempts(rl_client):
    """POST /login must return 429 after 10 requests within the window."""
    codes = await _fire_requests(rl_client, LOGIN_URL, LOGIN_PAYLOAD, 12)

    for code in codes[:10]:
        assert code != 429, f"Request within limit got 429"

    for code in codes[10:]:
        assert code == 429, f"Expected 429 after limit, got {code}"


@pytest.mark.asyncio
async def test_password_reset_rate_limited_after_5_attempts(rl_client):
    """POST /password/reset must return 429 after 5 requests within the window."""
    codes = await _fire_requests(rl_client, RESET_URL, RESET_PAYLOAD, 7)

    for code in codes[:5]:
        assert code != 429, f"Request within limit got 429"

    for code in codes[5:]:
        assert code == 429, f"Expected 429 after limit, got {code}"


@pytest.mark.asyncio
async def test_rate_limit_resets_after_window(rl_client):
    """After the window expires, requests should be allowed again."""
    # Exhaust the register limit
    codes = await _fire_requests(rl_client, REGISTER_URL, REGISTER_PAYLOAD, 6)
    assert codes[-1] == 429

    # Advance time past the 1-hour window by patching time.time in the limiter
    import src.middleware.rate_limit as rl_mod

    original_time = rl_mod.time.time

    with patch.object(rl_mod.time, "time", return_value=original_time() + 3601):
        resp = await rl_client.post(REGISTER_URL, json=REGISTER_PAYLOAD)
        # Should no longer be rate-limited
        assert resp.status_code != 429, (
            f"Expected request to succeed after window reset, got {resp.status_code}"
        )


@pytest.mark.asyncio
async def test_rate_limit_response_body(rl_client):
    """429 response should include an informative error message."""
    # Exhaust register limit
    await _fire_requests(rl_client, REGISTER_URL, REGISTER_PAYLOAD, 5)
    resp = await rl_client.post(REGISTER_URL, json=REGISTER_PAYLOAD)

    assert resp.status_code == 429
    body = resp.json()
    assert "RATE_LIMITED" in body.get("code", "")
    assert "Too many requests" in body.get("detail", "") or "Too many requests" in body.get("error", "")


@pytest.mark.asyncio
async def test_different_endpoints_have_separate_limits(rl_client):
    """Exhausting the register limit should not affect login."""
    # Exhaust register (5 requests)
    codes = await _fire_requests(rl_client, REGISTER_URL, REGISTER_PAYLOAD, 6)
    assert codes[-1] == 429

    # Login should still work (separate bucket)
    resp = await rl_client.post(LOGIN_URL, json=LOGIN_PAYLOAD)
    assert resp.status_code != 429
