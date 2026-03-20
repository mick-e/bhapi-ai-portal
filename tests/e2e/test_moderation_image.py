"""E2E tests for image moderation pipeline webhook endpoint."""

import hmac
import hashlib
import json

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch


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


def _hive_response(classes: list[dict]) -> dict:
    return {
        "status": [
            {
                "response": {
                    "output": [{"classes": classes}]
                }
            }
        ]
    }


class TestCFImagesWebhookEndpoint:
    """Test POST /api/v1/moderation/webhooks/cloudflare-images."""

    @pytest.mark.asyncio
    async def test_valid_webhook_no_api_key(self, client):
        """Without Hive API key, images are classified as needs_review."""
        payload = {
            "id": "cf-img-001",
            "variants": ["https://imagedelivery.net/abc/public"],
        }
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"
        assert data["image_id"] == "cf-img-001"
        assert data["classification"] == "needs_review"

    @pytest.mark.asyncio
    async def test_missing_image_id(self, client):
        payload = {"variants": ["https://imagedelivery.net/abc/public"]}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_missing_variants(self, client):
        payload = {"id": "cf-img-002"}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_empty_variants(self, client):
        payload = {"id": "cf-img-003", "variants": []}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_empty_body(self, client):
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_webhook_with_meta_age_tier(self, client):
        payload = {
            "id": "cf-img-004",
            "variants": ["https://imagedelivery.net/abc/public"],
            "meta": {"age_tier": "young"},
        }
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"

    @pytest.mark.asyncio
    async def test_webhook_with_hive_safe_image(self, client):
        """With Hive API key and safe response, image classified as safe."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(hive_api_key="test-key")

        hive_resp = _hive_response([
            {"class": "nsfw", "score": 0.01},
            {"class": "violence", "score": 0.02},
        ])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            payload = {
                "id": "cf-img-005",
                "variants": ["https://imagedelivery.net/safe/public"],
            }
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-images",
                json=payload,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["classification"] == "safe"
        assert data["image_id"] == "cf-img-005"

    @pytest.mark.asyncio
    async def test_webhook_with_hive_unsafe_image(self, client):
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(hive_api_key="test-key")

        hive_resp = _hive_response([
            {"class": "nsfw", "score": 0.95},
        ])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            payload = {
                "id": "cf-img-006",
                "variants": ["https://imagedelivery.net/nsfw/public"],
            }
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-images",
                json=payload,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["classification"] == "unsafe"

    @pytest.mark.asyncio
    async def test_webhook_hive_timeout(self, client):
        """Hive API timeout falls back to needs_review."""
        import httpx as httpx_mod
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(hive_api_key="test-key")

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx_mod.TimeoutException("timeout")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            payload = {
                "id": "cf-img-007",
                "variants": ["https://imagedelivery.net/slow/public"],
            }
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-images",
                json=payload,
            )

        assert resp.status_code == 200
        assert resp.json()["classification"] == "needs_review"

    @pytest.mark.asyncio
    async def test_webhook_young_tier_stricter(self, client):
        """Young age tier uses lower thresholds, so moderate content is flagged."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(hive_api_key="test-key")

        # Score of 0.5 is safe for teens (threshold 0.8) but unsafe for young (threshold 0.48)
        hive_resp = _hive_response([{"class": "nsfw", "score": 0.5}])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            payload = {
                "id": "cf-img-008",
                "variants": ["https://imagedelivery.net/mod/public"],
                "meta": {"age_tier": "young"},
            }
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-images",
                json=payload,
            )

        assert resp.status_code == 200
        assert resp.json()["classification"] == "unsafe"

    @pytest.mark.asyncio
    async def test_webhook_teen_tier_same_score_safe(self, client):
        """Same score as above but teen tier — should be safe."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(hive_api_key="test-key")

        hive_resp = _hive_response([{"class": "nsfw", "score": 0.5}])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            payload = {
                "id": "cf-img-009",
                "variants": ["https://imagedelivery.net/mod/public"],
                "meta": {"age_tier": "teen"},
            }
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-images",
                json=payload,
            )

        assert resp.status_code == 200
        assert resp.json()["classification"] == "safe"

    @pytest.mark.asyncio
    async def test_webhook_no_auth_required(self, client):
        """Webhook endpoint is accessible without auth token."""
        payload = {
            "id": "cf-img-010",
            "variants": ["https://imagedelivery.net/abc/public"],
        }
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
        )
        # Should NOT return 401/403 for auth
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_signature_required_when_secret_set(self, client):
        """When CF webhook secret is configured, invalid signature is rejected."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(cf_webhook_secret="my-secret")

        payload = {
            "id": "cf-img-011",
            "variants": ["https://imagedelivery.net/abc/public"],
        }
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
            headers={"cf-webhook-auth": "invalid-signature"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_webhook_valid_signature_accepted(self, client):
        """Valid HMAC signature passes verification."""
        from src.moderation.image_pipeline import pipeline

        secret = "webhook-secret-123"
        pipeline.configure(cf_webhook_secret=secret)

        payload = {
            "id": "cf-img-012",
            "variants": ["https://imagedelivery.net/abc/public"],
        }
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
        assert resp.json()["status"] == "processed"

    @pytest.mark.asyncio
    async def test_webhook_response_includes_categories(self, client):
        """Response includes category scores from Hive."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(hive_api_key="test-key")

        hive_resp = _hive_response([
            {"class": "nsfw", "score": 0.1},
            {"class": "violence", "score": 0.2},
            {"class": "drugs", "score": 0.05},
        ])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            payload = {
                "id": "cf-img-013",
                "variants": ["https://imagedelivery.net/cats/public"],
            }
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-images",
                json=payload,
            )

        data = resp.json()
        assert "categories" in data
        assert data["categories"]["nsfw"] == 0.1
        assert data["categories"]["violence"] == 0.2

    @pytest.mark.asyncio
    async def test_webhook_multiple_variants_uses_first(self, client):
        """Pipeline uses first variant URL for classification."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(hive_api_key="test-key")

        hive_resp = _hive_response([{"class": "nsfw", "score": 0.01}])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            payload = {
                "id": "cf-img-014",
                "variants": [
                    "https://imagedelivery.net/abc/public",
                    "https://imagedelivery.net/abc/thumbnail",
                ],
            }
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-images",
                json=payload,
            )

        assert resp.status_code == 200
        # Verify only called once with first URL
        mock_instance.post.assert_called_once()
        call_json = mock_instance.post.call_args[1]["json"]
        assert call_json["url"] == "https://imagedelivery.net/abc/public"

    @pytest.mark.asyncio
    async def test_webhook_preteen_tier_sensitivity(self, client):
        """Preteen age tier uses 0.8 multiplier — violence threshold drops from 0.7 to 0.56."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(hive_api_key="test-key")

        # Score 0.6 is safe for teen (threshold 0.7) but unsafe for preteen (threshold 0.56)
        hive_resp = _hive_response([{"class": "violence", "score": 0.6}])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            payload = {
                "id": "cf-img-015",
                "variants": ["https://imagedelivery.net/v/public"],
                "meta": {"age_tier": "preteen"},
            }
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-images",
                json=payload,
            )

        assert resp.status_code == 200
        assert resp.json()["classification"] == "unsafe"

    @pytest.mark.asyncio
    async def test_webhook_self_harm_category(self, client):
        """Self-harm has lower threshold (0.6) — catches more content."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(hive_api_key="test-key")

        hive_resp = _hive_response([{"class": "self_harm", "score": 0.65}])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            payload = {
                "id": "cf-img-016",
                "variants": ["https://imagedelivery.net/sh/public"],
            }
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-images",
                json=payload,
            )

        assert resp.status_code == 200
        assert resp.json()["classification"] == "unsafe"

    @pytest.mark.asyncio
    async def test_webhook_drugs_category(self, client):
        """Drugs category at threshold 0.7 is detected."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(hive_api_key="test-key")

        hive_resp = _hive_response([{"class": "drugs", "score": 0.75}])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            payload = {
                "id": "cf-img-017",
                "variants": ["https://imagedelivery.net/d/public"],
            }
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-images",
                json=payload,
            )

        assert resp.status_code == 200
        assert resp.json()["classification"] == "unsafe"

    @pytest.mark.asyncio
    async def test_webhook_hate_category(self, client):
        """Hate content above threshold is flagged."""
        from src.moderation.image_pipeline import pipeline

        pipeline.configure(hive_api_key="test-key")

        hive_resp = _hive_response([{"class": "hate", "score": 0.8}])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            payload = {
                "id": "cf-img-018",
                "variants": ["https://imagedelivery.net/h/public"],
            }
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-images",
                json=payload,
            )

        assert resp.status_code == 200
        assert resp.json()["classification"] == "unsafe"

    @pytest.mark.asyncio
    async def test_webhook_confidence_in_response(self, client):
        """Confidence score is included in response."""
        payload = {
            "id": "cf-img-019",
            "variants": ["https://imagedelivery.net/abc/public"],
        }
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-images",
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "confidence" in data
        assert isinstance(data["confidence"], (int, float))
