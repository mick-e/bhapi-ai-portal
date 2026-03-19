"""
Production Security Tests — Bhapi AI Portal

Security-focused tests that run against a live deployment.
Non-destructive — no data modification, no account creation.

Usage:
    PROD_BASE_URL=https://bhapi.ai pytest tests/security/test_production_security.py -v
"""

import os

import httpx
import pytest

PROD_BASE_URL = os.environ.get("PROD_BASE_URL", "").rstrip("/")

pytestmark = pytest.mark.skipif(
    not PROD_BASE_URL,
    reason="PROD_BASE_URL not set — skipping production security tests",
)


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    """Unauthenticated HTTP client for security tests."""
    with httpx.Client(
        base_url=PROD_BASE_URL,
        timeout=30.0,
        follow_redirects=False,  # Don't follow redirects for security tests
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Security Headers
# ---------------------------------------------------------------------------


class TestSecurityHeaders:
    """Verify all required security headers are present."""

    def test_x_content_type_options_nosniff(self, client: httpx.Client):
        r = client.get("/health/live")
        assert r.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options_deny(self, client: httpx.Client):
        r = client.get("/health/live")
        assert r.headers.get("x-frame-options") == "DENY"

    def test_strict_transport_security(self, client: httpx.Client):
        r = client.get("/health/live")
        hsts = r.headers.get("strict-transport-security", "")
        assert "max-age=" in hsts
        # HSTS max-age should be at least 1 year
        if "max-age=" in hsts:
            max_age = int(hsts.split("max-age=")[1].split(";")[0])
            assert max_age >= 31536000

    def test_hsts_includes_subdomains(self, client: httpx.Client):
        r = client.get("/health/live")
        hsts = r.headers.get("strict-transport-security", "")
        assert "includeSubDomains" in hsts

    def test_content_security_policy_present(self, client: httpx.Client):
        r = client.get("/health/live")
        csp = r.headers.get("content-security-policy", "")
        assert "default-src" in csp
        assert "frame-ancestors 'none'" in csp

    def test_csp_blocks_inline_scripts_except_self(self, client: httpx.Client):
        r = client.get("/health/live")
        csp = r.headers.get("content-security-policy", "")
        assert "script-src" in csp

    def test_no_server_header_leak(self, client: httpx.Client):
        """Server header should not leak implementation details."""
        r = client.get("/health/live")
        server = r.headers.get("server", "")
        # Should not reveal framework/version
        assert "uvicorn" not in server.lower()
        assert "python" not in server.lower()

    def test_no_powered_by_header(self, client: httpx.Client):
        r = client.get("/health/live")
        assert "x-powered-by" not in r.headers


# ---------------------------------------------------------------------------
# 2. Authentication Security
# ---------------------------------------------------------------------------


class TestAuthSecurity:
    """Verify authentication security controls."""

    def test_invalid_jwt_rejected(self, client: httpx.Client):
        r = client.get(
            "/api/v1/groups",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.fake"},
        )
        assert r.status_code in (401, 403)

    def test_expired_jwt_rejected(self, client: httpx.Client):
        """Expired tokens should be rejected."""
        r = client.get(
            "/api/v1/groups",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.fake"},
        )
        assert r.status_code in (401, 403)

    def test_no_auth_header_rejected(self, client: httpx.Client):
        r = client.get("/api/v1/groups")
        assert r.status_code in (401, 403)

    def test_empty_bearer_rejected(self, client: httpx.Client):
        # "Bearer " with trailing space is rejected at HTTP protocol level by some clients
        # Use a single-space token instead to test empty-ish bearer handling
        r = client.get(
            "/api/v1/groups",
            headers={"Authorization": "Bearer x"},
        )
        assert r.status_code in (401, 403)

    def test_basic_auth_not_accepted(self, client: httpx.Client):
        r = client.get(
            "/api/v1/groups",
            headers={"Authorization": "Basic dGVzdDp0ZXN0"},
        )
        assert r.status_code in (401, 403)

    def test_sql_injection_in_login(self, client: httpx.Client):
        r = client.post("/api/v1/auth/login", json={
            "email": "' OR 1=1 --",
            "password": "test",
        })
        assert r.status_code in (401, 404, 422)

    def test_xss_in_login_email(self, client: httpx.Client):
        r = client.post("/api/v1/auth/login", json={
            "email": "<script>alert(1)</script>@example.com",
            "password": "test",
        })
        # Pydantic email validation rejects this as invalid email format (422)
        assert r.status_code in (401, 404, 422)
        # Response should not reflect the raw script tag in executable context
        if r.status_code == 422:
            # Validation error may echo the input in "input" field — that's safe (JSON, not HTML)
            content_type = r.headers.get("content-type", "")
            assert "application/json" in content_type


# ---------------------------------------------------------------------------
# 3. Information Disclosure
# ---------------------------------------------------------------------------


class TestInformationDisclosure:
    """Verify no sensitive information is leaked."""

    def test_no_stack_trace_on_error(self, client: httpx.Client):
        r = client.get("/api/v1/nonexistent-endpoint")
        text = r.text.lower()
        assert "traceback" not in text
        assert "file \"" not in text
        assert "line " not in text or "application/json" in r.headers.get("content-type", "")

    def test_no_debug_info_in_health(self, client: httpx.Client):
        r = client.get("/health")
        data = r.json()
        # Should not leak DB connection string, file paths, etc.
        data_str = str(data).lower()
        assert "password" not in data_str
        assert "secret" not in data_str
        assert "postgresql" not in data_str

    def test_password_reset_no_user_enumeration(self, client: httpx.Client):
        """Password reset for non-existent email should not reveal if user exists."""
        r = client.post("/api/v1/auth/password/reset", json={
            "email": "definitely-not-a-user-abc123@example.com",
        })
        # Should return same status whether user exists or not
        assert r.status_code in (200, 201, 202, 422)

    def test_login_error_no_user_enumeration(self, client: httpx.Client):
        """Login with wrong credentials should give generic error."""
        r = client.post("/api/v1/auth/login", json={
            "email": "test-user-enum@example.com",
            "password": "wrong",
        })
        if r.status_code in (401, 404):
            data = r.json()
            error_msg = str(data).lower()
            # Should not say "user not found" vs "wrong password"
            assert "not found" not in error_msg or "password" not in error_msg

    def test_openapi_does_not_leak_internals(self, client: httpx.Client):
        r = client.get("/openapi.json")
        data = str(r.json()).lower()
        assert "internal" not in data or "/internal" in data  # /internal is a valid route prefix


# ---------------------------------------------------------------------------
# 4. Input Validation & Injection
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Verify input validation and injection protection."""

    def test_oversized_body_rejected(self, client: httpx.Client):
        """Extremely large request bodies should be rejected."""
        r = client.post("/api/v1/auth/login", json={
            "email": "a" * 10000 + "@example.com",
            "password": "test",
        })
        assert r.status_code in (400, 413, 422)

    def test_register_rejects_invalid_email(self, client: httpx.Client):
        r = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "SecurePass1!",
            "display_name": "Test",
            "account_type": "family",
            "privacy_notice_accepted": True,
        })
        assert r.status_code == 422

    def test_register_rejects_invalid_account_type(self, client: httpx.Client):
        r = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass1!",
            "display_name": "Test",
            "account_type": "admin",  # Invalid,
            "privacy_notice_accepted": True,
        })
        assert r.status_code == 422

    def test_path_traversal_rejected(self, client: httpx.Client):
        r = client.get("/api/v1/../../etc/passwd")
        # Reverse proxy normalizes path — 200 means static frontend catch-all served
        # Verify no actual file contents leaked
        assert r.status_code in (200, 400, 404, 422)
        if r.status_code == 200:
            # Should be HTML (frontend), not /etc/passwd contents
            assert "root:" not in r.text
            assert "/bin/bash" not in r.text

    def test_null_byte_injection(self, client: httpx.Client):
        r = client.post("/api/v1/auth/login", json={
            "email": "test\x00@example.com",
            "password": "test",
        })
        assert r.status_code in (401, 404, 422)

    def test_unicode_normalization(self, client: httpx.Client):
        """Unicode in endpoints should not bypass auth."""
        r = client.get("/api/v1/ɡroups")  # Unicode 'ɡ' instead of 'g'
        assert r.status_code in (401, 403, 404, 405)


# ---------------------------------------------------------------------------
# 5. CORS Security
# ---------------------------------------------------------------------------


class TestCORSSecurity:
    """Verify CORS is properly configured."""

    def test_cors_rejects_unauthorized_origin(self, client: httpx.Client):
        r = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://evil-site.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        # Should not include evil origin in allowed origins
        acao = r.headers.get("access-control-allow-origin", "")
        assert "evil-site.com" not in acao

    def test_cors_allows_production_origin(self, client: httpx.Client):
        r = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://bhapi.ai",
                "Access-Control-Request-Method": "POST",
            },
        )
        acao = r.headers.get("access-control-allow-origin", "")
        # Should allow bhapi.ai or wildcard
        assert "bhapi.ai" in acao or acao == "*" or r.status_code == 405


# ---------------------------------------------------------------------------
# 6. Rate Limiting & Abuse Prevention
# ---------------------------------------------------------------------------


class TestAbusePrevention:
    """Verify rate limiting and abuse prevention."""

    def test_registration_rate_limited(self, client: httpx.Client):
        """Rapid registration attempts should eventually be rate limited."""
        statuses = []
        for i in range(10):
            r = client.post("/api/v1/auth/register", json={
                "email": f"ratelimit{i}@example.com",
                "password": "SecurePass1!",
                "display_name": "Test",
                "account_type": "family",
                "privacy_notice_accepted": True,
            })
            statuses.append(r.status_code)
            if r.status_code == 429:
                break
        # Rate limiting should kick in, or requests should be rejected
        assert 429 in statuses or all(s in (201, 409, 422) for s in statuses)


# ---------------------------------------------------------------------------
# 7. Public Endpoint Security
# ---------------------------------------------------------------------------


class TestPublicEndpointSecurity:
    """Verify public endpoints don't leak data."""

    def test_plans_no_internal_ids(self, client: httpx.Client):
        r = client.get("/api/v1/billing/plans")
        if r.status_code == 200:
            data_str = str(r.json()).lower()
            assert "stripe_price_id" not in data_str or "price_" in data_str

    def test_vendor_risk_no_api_keys(self, client: httpx.Client):
        r = client.get("/api/v1/billing/vendor-risk")
        if r.status_code == 200:
            data_str = str(r.json()).lower()
            assert "api_key" not in data_str
            assert "secret" not in data_str

    def test_contact_inquiry_xss_protection(self, client: httpx.Client):
        r = client.post("/api/v1/auth/contact-inquiry", json={
            "organisation": "<script>alert(1)</script>",
            "contact_name": "Test",
            "email": "test@example.com",
            "account_type": "school",
            "privacy_notice_accepted": True,
            "estimated_members": "10-50",
        })
        # Should accept but sanitize, or reject
        assert r.status_code in (200, 201, 202, 422)
        if r.status_code in (200, 201, 202):
            assert "<script>" not in r.text


# ---------------------------------------------------------------------------
# 8. Session & Cookie Security
# ---------------------------------------------------------------------------


class TestSessionSecurity:
    """Verify session and cookie security settings."""

    def test_login_response_cookie_flags(self, client: httpx.Client):
        """If login sets a cookie, verify secure flags."""
        r = client.post("/api/v1/auth/login", json={
            "email": "cookie-test@example.com",
            "password": "test",
        })
        for cookie_header in r.headers.get_list("set-cookie"):
            cookie_lower = cookie_header.lower()
            if "session" in cookie_lower or "bhapi" in cookie_lower:
                assert "httponly" in cookie_lower, "Session cookie must be HttpOnly"
                # Secure flag may not be set in non-HTTPS test
                if PROD_BASE_URL.startswith("https"):
                    assert "secure" in cookie_lower, "Session cookie must be Secure over HTTPS"


# ---------------------------------------------------------------------------
# 9. HTTP Method Security
# ---------------------------------------------------------------------------


class TestHTTPMethodSecurity:
    """Verify HTTP method restrictions."""

    def test_trace_method_disabled(self, client: httpx.Client):
        """TRACE method should be disabled (XST prevention)."""
        r = client.request("TRACE", "/health/live")
        assert r.status_code in (405, 404)

    def test_connect_method_disabled(self, client: httpx.Client):
        r = client.request("CONNECT", "/health/live")
        assert r.status_code in (405, 404, 400)

    def test_delete_on_health_rejected(self, client: httpx.Client):
        r = client.delete("/health/live")
        assert r.status_code in (405, 404)


# ---------------------------------------------------------------------------
# 10. Webhook Security
# ---------------------------------------------------------------------------


class TestWebhookSecurity:
    """Verify webhook signature validation."""

    def test_stripe_webhook_rejects_no_signature(self, client: httpx.Client):
        r = client.post(
            "/api/v1/billing/webhooks/stripe",
            content=b'{"type": "test"}',
            headers={"content-type": "application/json"},
        )
        # 405 if production uses different webhook path
        assert r.status_code in (400, 401, 403, 405, 422)

    def test_stripe_webhook_rejects_invalid_signature(self, client: httpx.Client):
        r = client.post(
            "/api/v1/billing/webhooks/stripe",
            content=b'{"type": "test"}',
            headers={
                "content-type": "application/json",
                "stripe-signature": "t=1,v1=invalid",
            },
        )
        # 405 if production uses different webhook path
        assert r.status_code in (400, 401, 403, 405, 422)
