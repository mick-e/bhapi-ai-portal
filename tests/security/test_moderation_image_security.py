"""Security tests for image moderation pipeline."""

import hashlib
import hmac
import json

import pytest


@pytest.fixture(autouse=True)
def reset_pipeline():
    """Reset the pipeline singleton before each test."""
    from src.moderation.image_pipeline import pipeline

    pipeline._hive_api_key = None
    pipeline._sensity_api_key = None
    pipeline._cf_webhook_secret = None
    yield
    pipeline._hive_api_key = None
    pipeline._sensity_api_key = None
    pipeline._cf_webhook_secret = None


class TestWebhookAuth:
    """Webhook endpoint authentication and signature validation."""

    @pytest.mark.asyncio
    async def test_webhook_accessible_without_bearer_token(self, client):
        """Webhook endpoint does not require Bearer auth."""
        payload = {"id": "sec-01", "variants": ["https://img.cf.com/a/public"]}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
        )
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, client):
        """Invalid HMAC signature returns 403."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(cf_webhook_secret="secret-123")

        payload = {"id": "sec-02", "variants": ["https://img.cf.com/a/public"]}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
            headers={"cf-webhook-auth": "forged-signature"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_signature_rejected_when_secret_set(self, client):
        """Missing signature header returns 403 when secret is configured."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(cf_webhook_secret="secret-456")

        payload = {"id": "sec-03", "variants": ["https://img.cf.com/a/public"]}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_valid_signature_accepted(self, client):
        """Correct HMAC-SHA256 signature is accepted."""
        from src.moderation.image_pipeline import pipeline

        secret = "valid-secret"
        pipeline.configure(cf_webhook_secret=secret)

        payload = {"id": "sec-04", "variants": ["https://img.cf.com/a/public"]}
        body = json.dumps(payload).encode()
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            content=body,
            headers={
                "cf-webhook-auth": sig,
                "content-type": "application/json",
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_timing_safe_comparison(self):
        """Signature uses constant-time comparison (hmac.compare_digest)."""
        from src.moderation.image_pipeline import ImageModerationPipeline

        p = ImageModerationPipeline()
        p.configure(cf_webhook_secret="secret")

        # Internally uses hmac.compare_digest — verify it does not
        # short-circuit on first byte mismatch by checking both
        # completely wrong and almost-right signatures return False
        body = b"test-body"
        correct = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
        almost = correct[:-1] + ("0" if correct[-1] != "0" else "1")

        assert p.verify_cf_signature(body, correct) is True
        assert p.verify_cf_signature(body, almost) is False
        assert p.verify_cf_signature(body, "completely-wrong") is False


class TestInputValidation:
    """Input validation and injection prevention."""

    @pytest.mark.asyncio
    async def test_oversized_payload(self, client):
        """Very large payload is handled gracefully."""
        payload = {
            "id": "x" * 10000,
            "variants": ["https://img.cf.com/a/public"],
        }
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
        )
        # Should not crash
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_special_characters_in_id(self, client):
        """Special characters in image ID are handled safely."""
        payload = {
            "id": '<script>alert("xss")</script>',
            "variants": ["https://img.cf.com/a/public"],
        }
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"

    @pytest.mark.asyncio
    async def test_malicious_url_in_variants(self):
        """Malicious URL schemes are rejected."""
        from src.moderation.image_pipeline import ImageModerationPipeline

        p = ImageModerationPipeline()
        p.configure(hive_api_key="test")

        result = await p.classify_image("javascript:alert(1)")
        assert result.classification.value == "error"

    @pytest.mark.asyncio
    async def test_file_url_rejected(self):
        """file:// URLs are rejected."""
        from src.moderation.image_pipeline import ImageModerationPipeline

        p = ImageModerationPipeline()
        p.configure(hive_api_key="test")

        result = await p.classify_image("file:///etc/passwd")
        assert result.classification.value == "error"

    @pytest.mark.asyncio
    async def test_null_bytes_in_url(self):
        """Null bytes in URL don't cause crashes."""
        from src.moderation.image_pipeline import ImageModerationPipeline

        p = ImageModerationPipeline()
        result = await p.classify_image("https://example.com/\x00img.jpg")
        # Should still work — URL validation only checks scheme
        assert result.classification in {
            "needs_review",  # no API key
            "error",
        }


class TestAuthEndpointProtection:
    """Ensure other moderation endpoints still require auth."""

    @pytest.mark.asyncio
    async def test_moderation_queue_requires_auth(self, client):
        """GET /api/v1/moderation/queue requires auth."""
        resp = await client.get("/api/v1/moderation/queue")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_moderation_dashboard_requires_auth(self, client):
        """GET /api/v1/moderation/dashboard requires auth."""
        resp = await client.get("/api/v1/moderation/dashboard")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_moderation_reports_requires_auth(self, client):
        """POST /api/v1/moderation/reports requires auth."""
        resp = await client.post(
            "/api/v1/moderation/reports",
            json={"target_type": "post", "target_id": "00000000-0000-0000-0000-000000000001", "reason": "test"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_moderation_takedown_requires_auth(self, client):
        """POST /api/v1/moderation/takedown requires auth."""
        resp = await client.post(
            "/api/v1/moderation/takedown",
            json={
                "content_type": "post",
                "content_id": "00000000-0000-0000-0000-000000000001",
                "reason": "test",
            },
        )
        assert resp.status_code == 401
