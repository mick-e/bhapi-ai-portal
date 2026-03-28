"""Unit tests for middleware modules: auth, rate_limit, security_headers, timing, locale."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app
from src.middleware.auth import PUBLIC_PATHS, PUBLIC_PREFIXES, AuthMiddleware
from src.middleware.locale import DEFAULT_LOCALE, SUPPORTED_LOCALES, LocaleMiddleware
from src.middleware.rate_limit import _InMemoryRateLimiter, _in_memory_limiter
from src.middleware.timing import TimingMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def app_client():
    """Create a test HTTP client with in-memory SQLite so downstream
    auth/dependency resolution doesn't crash on missing tables."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()

    async def override_get_db():
        async_session_maker = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ===========================================================================
# Auth Middleware
# ===========================================================================

class TestAuthMiddlewarePublicPaths:
    """Public paths should bypass authentication."""

    @pytest.mark.asyncio
    async def test_health_endpoint_no_auth(self, app_client):
        """GET /health does not require auth."""
        resp = await app_client.get("/health")
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_docs_endpoint_no_auth(self, app_client):
        """GET /docs does not require auth."""
        resp = await app_client.get("/docs")
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_openapi_json_no_auth(self, app_client):
        """GET /openapi.json does not require auth."""
        resp = await app_client.get("/openapi.json")
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_all_public_paths_defined(self):
        """Ensure core public paths are in the set."""
        for path in ("/health", "/health/live", "/health/ready", "/", "/docs", "/favicon.ico"):
            assert path in PUBLIC_PATHS

    @pytest.mark.asyncio
    async def test_public_prefix_register(self, app_client):
        """POST /api/v1/auth/register is public."""
        resp = await app_client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "TestPass123!"},
        )
        # Should NOT be 401 (may be 422 due to missing fields — that's fine)
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_public_prefix_login(self, app_client):
        """POST /api/v1/auth/login is public (not blocked by auth middleware).

        The middleware returns {"error": "Authentication required"}.
        The login handler returns {"error": "Invalid email or password"}.
        We verify middleware did not block (i.e. the request reached the handler).
        """
        resp = await app_client.post(
            "/api/v1/auth/login",
            json={"email": "x@example.com", "password": "x"},
        )
        # If 401, it should be from the handler, not middleware
        if resp.status_code == 401:
            body = resp.json()
            # Middleware would say "Authentication required"; handler says something else
            assert body.get("error") != "Authentication required"

    @pytest.mark.asyncio
    async def test_billing_plans_public(self, app_client):
        """GET /api/v1/billing/plans is public."""
        resp = await app_client.get("/api/v1/billing/plans")
        assert resp.status_code != 401


class TestAuthMiddlewareProtectedPaths:
    """Protected API paths should require authentication."""

    @pytest.mark.asyncio
    async def test_groups_requires_auth(self, app_client):
        """GET /api/v1/groups without auth returns 401."""
        resp = await app_client.get("/api/v1/groups")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_capture_requires_auth(self, app_client):
        """GET /api/v1/capture/events without auth returns 401."""
        resp = await app_client.get("/api/v1/capture/events")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_reports_requires_auth(self, app_client):
        """GET /api/v1/reports without auth returns 401."""
        resp = await app_client.get("/api/v1/reports")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_401_response_format(self, app_client):
        """401 response has structured error body."""
        resp = await app_client.get("/api/v1/groups")
        body = resp.json()
        assert body["error"] == "Authentication required"
        assert body["code"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_invalid_bearer_token_rejected(self, app_client):
        """Invalid Bearer token is rejected by auth middleware."""
        resp = await app_client.get(
            "/api/v1/groups",
            headers={"Authorization": "Bearer some-token"},
        )
        # Middleware validates the token — invalid tokens get 401
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, app_client):
        """Invalid API key is rejected by auth middleware."""
        resp = await app_client.get(
            "/api/v1/groups",
            headers={"Authorization": "Bearer bhapi_sk_test123"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_static_paths_bypass_auth(self, app_client):
        """Requests to /static/* bypass auth."""
        resp = await app_client.get("/static/nonexistent.js")
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_non_api_paths_bypass_auth(self, app_client):
        """Non-API paths (e.g. /some-page) bypass auth middleware."""
        resp = await app_client.get("/random-page")
        assert resp.status_code != 401


# ===========================================================================
# Rate Limiter — In-Memory
# ===========================================================================

class TestInMemoryRateLimiter:
    """Test the in-memory sliding window rate limiter."""

    def test_allows_under_limit(self):
        limiter = _InMemoryRateLimiter()
        allowed, remaining, _ = limiter.check("test-key", 10, 60)
        assert allowed is True
        assert remaining == 9

    def test_blocks_at_limit(self):
        limiter = _InMemoryRateLimiter()
        for _ in range(10):
            limiter.check("block-key", 10, 60)
        allowed, remaining, _ = limiter.check("block-key", 10, 60)
        assert allowed is False
        assert remaining == 0

    def test_separate_keys_independent(self):
        limiter = _InMemoryRateLimiter()
        for _ in range(10):
            limiter.check("key-a", 10, 60)
        # key-b should still be allowed
        allowed, _, _ = limiter.check("key-b", 10, 60)
        assert allowed is True

    def test_window_expiry(self):
        """Entries older than the window should be evicted."""
        limiter = _InMemoryRateLimiter()
        # Manually inject old timestamps
        old_time = time.time() - 120  # 2 minutes ago
        limiter._buckets["expire-key"] = [old_time] * 10
        # With a 60s window, all old entries should be evicted
        allowed, remaining, _ = limiter.check("expire-key", 10, 60)
        assert allowed is True
        assert remaining == 9

    def test_remaining_count_decrements(self):
        limiter = _InMemoryRateLimiter()
        _, r1, _ = limiter.check("dec-key", 5, 60)
        _, r2, _ = limiter.check("dec-key", 5, 60)
        _, r3, _ = limiter.check("dec-key", 5, 60)
        assert r1 == 4
        assert r2 == 3
        assert r3 == 2


class TestRateLimitMiddleware:
    """Test rate limit middleware integration."""

    @pytest.mark.asyncio
    async def test_health_exempt_from_rate_limit(self, app_client):
        """Health endpoints are exempt from rate limiting."""
        resp = await app_client.get("/health")
        # Should not have rate limit headers (exempt paths skip middleware)
        assert resp.status_code != 429

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, app_client):
        """Non-exempt requests should have rate limit headers."""
        resp = await app_client.get(
            "/api/v1/groups",
            headers={"Authorization": "Bearer test-token"},
        )
        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers
        assert "X-RateLimit-Reset" in resp.headers


# ===========================================================================
# Security Headers
# ===========================================================================

class TestSecurityHeaders:
    """Test that security headers are present on responses."""

    @pytest.mark.asyncio
    async def test_csp_header(self, app_client):
        resp = await app_client.get("/health")
        assert "Content-Security-Policy" in resp.headers
        csp = resp.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp

    @pytest.mark.asyncio
    async def test_hsts_header(self, app_client):
        resp = await app_client.get("/health")
        assert "Strict-Transport-Security" in resp.headers
        assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_x_frame_options(self, app_client):
        resp = await app_client.get("/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    @pytest.mark.asyncio
    async def test_x_content_type_options(self, app_client):
        resp = await app_client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    @pytest.mark.asyncio
    async def test_permissions_policy(self, app_client):
        resp = await app_client.get("/health")
        pp = resp.headers.get("Permissions-Policy", "")
        assert "camera=()" in pp
        assert "microphone=()" in pp

    @pytest.mark.asyncio
    async def test_referrer_policy(self, app_client):
        resp = await app_client.get("/health")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_cross_origin_opener_policy(self, app_client):
        resp = await app_client.get("/health")
        assert resp.headers.get("Cross-Origin-Opener-Policy") == "same-origin"

    @pytest.mark.asyncio
    async def test_cross_origin_embedder_policy_on_api(self, app_client):
        """API paths should get Cross-Origin-Embedder-Policy."""
        resp = await app_client.get(
            "/api/v1/groups",
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.headers.get("Cross-Origin-Embedder-Policy") == "require-corp"


# ===========================================================================
# Timing Middleware
# ===========================================================================

class TestTimingMiddleware:
    """Test request timing and correlation IDs."""

    @pytest.mark.asyncio
    async def test_request_id_generated(self, app_client):
        """X-Request-ID is generated when not provided."""
        resp = await app_client.get("/health")
        assert "X-Request-ID" in resp.headers
        # Should be UUID-like
        rid = resp.headers["X-Request-ID"]
        assert len(rid) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_request_id_honoured(self, app_client):
        """X-Request-ID from the request is echoed back."""
        custom_id = "my-custom-correlation-id"
        resp = await app_client.get(
            "/health",
            headers={"X-Request-ID": custom_id},
        )
        assert resp.headers["X-Request-ID"] == custom_id

    @pytest.mark.asyncio
    async def test_process_time_header(self, app_client):
        """X-Process-Time-Ms is present and numeric."""
        resp = await app_client.get("/health")
        pt = resp.headers.get("X-Process-Time-Ms")
        assert pt is not None
        assert float(pt) >= 0


# ===========================================================================
# Locale Middleware
# ===========================================================================

class TestLocaleMiddleware:
    """Test locale detection from Accept-Language and query params."""

    @pytest.mark.asyncio
    async def test_default_locale(self, app_client):
        """No language info defaults to English."""
        resp = await app_client.get("/health")
        assert resp.headers.get("Content-Language") == "en"

    @pytest.mark.asyncio
    async def test_accept_language_french(self, app_client):
        """Accept-Language: fr sets French locale."""
        resp = await app_client.get(
            "/health",
            headers={"Accept-Language": "fr"},
        )
        assert resp.headers.get("Content-Language") == "fr"

    @pytest.mark.asyncio
    async def test_accept_language_with_region(self, app_client):
        """Accept-Language: pt-BR is parsed to pt."""
        resp = await app_client.get(
            "/health",
            headers={"Accept-Language": "pt-BR"},
        )
        assert resp.headers.get("Content-Language") == "pt"

    @pytest.mark.asyncio
    async def test_accept_language_with_quality(self, app_client):
        """Accept-Language with quality values picks first supported."""
        resp = await app_client.get(
            "/health",
            headers={"Accept-Language": "ja;q=0.9, de;q=0.8"},
        )
        # ja is not supported, de is
        assert resp.headers.get("Content-Language") == "de"

    @pytest.mark.asyncio
    async def test_query_param_overrides_header(self, app_client):
        """?locale=es overrides Accept-Language header."""
        resp = await app_client.get(
            "/health?locale=es",
            headers={"Accept-Language": "fr"},
        )
        assert resp.headers.get("Content-Language") == "es"

    @pytest.mark.asyncio
    async def test_unsupported_locale_fallback(self, app_client):
        """Unsupported locale in query param falls back to header or default."""
        resp = await app_client.get(
            "/health?locale=zh",
            headers={"Accept-Language": "it"},
        )
        assert resp.headers.get("Content-Language") == "it"

    @pytest.mark.asyncio
    async def test_supported_locales_complete(self):
        """All 6 supported locales are defined."""
        expected = {"en", "fr", "de", "it", "pt", "es"}
        assert SUPPORTED_LOCALES == expected

    @pytest.mark.asyncio
    async def test_default_locale_is_english(self):
        assert DEFAULT_LOCALE == "en"
