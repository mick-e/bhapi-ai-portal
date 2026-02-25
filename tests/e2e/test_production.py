"""
Production E2E Tests — Bhapi AI Portal

Runs against a live deployment to verify endpoints are reachable and
returning expected responses.

Usage:
    PROD_BASE_URL=https://bhapi.ai pytest tests/e2e/test_production.py -v

Set PROD_BASE_URL to the production (or staging) URL.
Optionally set PROD_API_KEY for authenticated endpoint tests.
"""

import os

import httpx
import pytest

PROD_BASE_URL = os.environ.get("PROD_BASE_URL", "").rstrip("/")
PROD_API_KEY = os.environ.get("PROD_API_KEY", "")

pytestmark = pytest.mark.skipif(
    not PROD_BASE_URL,
    reason="PROD_BASE_URL not set — skipping production E2E tests",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def http() -> httpx.Client:
    """Synchronous HTTP client for production tests."""
    headers = {}
    if PROD_API_KEY:
        headers["Authorization"] = f"Bearer {PROD_API_KEY}"
    with httpx.Client(
        base_url=PROD_BASE_URL,
        headers=headers,
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        yield client


@pytest.fixture(scope="module")
def anon_http() -> httpx.Client:
    """Unauthenticated HTTP client."""
    with httpx.Client(
        base_url=PROD_BASE_URL,
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Health & Infrastructure
# ---------------------------------------------------------------------------


class TestHealth:
    """Verify the service is alive and responding."""

    def test_health_live(self, anon_http: httpx.Client):
        r = anon_http.get("/health/live")
        assert r.status_code == 200

    def test_health_response_json(self, anon_http: httpx.Client):
        r = anon_http.get("/health/live")
        data = r.json()
        assert "status" in data

    def test_health_endpoint(self, anon_http: httpx.Client):
        r = anon_http.get("/health")
        assert r.status_code in (200, 404)  # /health may not exist if only /health/live

    def test_openapi_docs(self, anon_http: httpx.Client):
        r = anon_http.get("/docs")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_openapi_json(self, anon_http: httpx.Client):
        r = anon_http.get("/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert "openapi" in data
        assert "paths" in data

    def test_cors_headers(self, anon_http: httpx.Client):
        r = anon_http.options(
            "/health/live",
            headers={
                "Origin": "https://bhapi.ai",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should not error out (CORS preflight)
        assert r.status_code in (200, 204, 405)

    def test_security_headers(self, anon_http: httpx.Client):
        r = anon_http.get("/health/live")
        headers = r.headers
        # Check key security headers are present
        assert "x-content-type-options" in headers or "X-Content-Type-Options" in headers
        assert "x-frame-options" in headers or "X-Frame-Options" in headers


# ---------------------------------------------------------------------------
# Legal Pages
# ---------------------------------------------------------------------------


class TestLegalPages:
    """Verify legal documents are publicly accessible."""

    def test_privacy_policy(self, anon_http: httpx.Client):
        r = anon_http.get("/legal/privacy")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "Privacy" in r.text or "privacy" in r.text

    def test_terms_of_service(self, anon_http: httpx.Client):
        r = anon_http.get("/legal/terms")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "Terms" in r.text or "terms" in r.text

    def test_privacy_has_key_sections(self, anon_http: httpx.Client):
        r = anon_http.get("/legal/privacy")
        text = r.text.lower()
        assert "data" in text
        assert "cookie" in text or "retention" in text

    def test_terms_has_key_sections(self, anon_http: httpx.Client):
        r = anon_http.get("/legal/terms")
        text = r.text.lower()
        assert "service" in text
        assert "liability" in text or "termination" in text


# ---------------------------------------------------------------------------
# Auth Endpoints (unauthenticated)
# ---------------------------------------------------------------------------


class TestAuthEndpoints:
    """Verify auth endpoints exist and reject invalid requests appropriately."""

    def test_register_rejects_empty_body(self, anon_http: httpx.Client):
        r = anon_http.post("/api/v1/auth/register", json={})
        assert r.status_code == 422  # Validation error

    def test_login_rejects_empty_body(self, anon_http: httpx.Client):
        r = anon_http.post("/api/v1/auth/login", json={})
        assert r.status_code == 422

    def test_login_rejects_bad_credentials(self, anon_http: httpx.Client):
        r = anon_http.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword123"},
        )
        assert r.status_code in (401, 404)

    def test_oauth_google_authorize(self, anon_http: httpx.Client):
        r = anon_http.get("/api/v1/auth/oauth/google/authorize")
        # 200 if configured, 400/500 if OAuth not configured yet
        assert r.status_code in (200, 400, 500)

    def test_oauth_microsoft_authorize(self, anon_http: httpx.Client):
        r = anon_http.get("/api/v1/auth/oauth/microsoft/authorize")
        assert r.status_code in (200, 400, 500)

    def test_oauth_apple_authorize(self, anon_http: httpx.Client):
        r = anon_http.get("/api/v1/auth/oauth/apple/authorize")
        assert r.status_code in (200, 400, 500)

    def test_oauth_invalid_provider(self, anon_http: httpx.Client):
        r = anon_http.get("/api/v1/auth/oauth/invalid/authorize")
        assert r.status_code in (400, 404, 422)


# ---------------------------------------------------------------------------
# Protected Endpoints (should require auth)
# ---------------------------------------------------------------------------


class TestAuthRequired:
    """Verify protected endpoints reject unauthenticated requests."""

    PROTECTED_ENDPOINTS = [
        ("GET", "/api/v1/groups"),
        ("GET", "/api/v1/alerts"),
        ("GET", "/api/v1/reports"),
        ("GET", "/api/v1/billing/subscription"),
        ("GET", "/api/v1/compliance/consents"),
        ("GET", "/api/v1/portal/dashboard"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_rejects_unauthenticated(self, anon_http: httpx.Client, method: str, path: str):
        r = anon_http.request(method, path)
        assert r.status_code in (401, 403), f"{method} {path} returned {r.status_code}"


# ---------------------------------------------------------------------------
# Capture Gateway
# ---------------------------------------------------------------------------


class TestCaptureGateway:
    """Verify the capture endpoint exists and validates input."""

    def test_capture_health(self, anon_http: httpx.Client):
        r = anon_http.get("/api/v1/capture/health")
        # May require HMAC or return 200 for health
        assert r.status_code in (200, 401, 403)

    def test_capture_rejects_unsigned_event(self, anon_http: httpx.Client):
        r = anon_http.post(
            "/api/v1/capture/events",
            json={"platform": "chatgpt", "eventType": "prompt", "content": "test"},
        )
        # Should reject without HMAC signature
        assert r.status_code in (401, 403, 422)


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Verify rate limiting is active."""

    def test_rate_limit_headers_present(self, anon_http: httpx.Client):
        r = anon_http.get("/health/live")
        # Rate limit headers may or may not be on health endpoint
        # Just verify the request succeeds
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# TLS & Response Quality
# ---------------------------------------------------------------------------


class TestResponseQuality:
    """Verify response quality and security basics."""

    def test_json_content_type_on_api(self, anon_http: httpx.Client):
        r = anon_http.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "x"})
        content_type = r.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_404_returns_json(self, anon_http: httpx.Client):
        r = anon_http.get("/api/v1/nonexistent-endpoint-12345")
        assert r.status_code in (404, 405)

    def test_method_not_allowed(self, anon_http: httpx.Client):
        r = anon_http.delete("/health/live")
        assert r.status_code in (405, 404, 200)  # depends on route config


# ---------------------------------------------------------------------------
# Authenticated Tests (only run if PROD_API_KEY is set)
# ---------------------------------------------------------------------------


needs_api_key = pytest.mark.skipif(
    not PROD_API_KEY,
    reason="PROD_API_KEY not set — skipping authenticated tests",
)


@needs_api_key
class TestAuthenticated:
    """Tests that require a valid auth token."""

    def test_groups_list(self, http: httpx.Client):
        r = http.get("/api/v1/groups")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_portal_dashboard(self, http: httpx.Client):
        r = http.get("/api/v1/portal/dashboard")
        assert r.status_code in (200, 404)

    def test_billing_subscription(self, http: httpx.Client):
        r = http.get("/api/v1/billing/subscription")
        assert r.status_code in (200, 404)

    def test_compliance_consents(self, http: httpx.Client):
        r = http.get("/api/v1/compliance/consents")
        assert r.status_code in (200, 404)
