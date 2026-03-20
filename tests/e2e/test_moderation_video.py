"""E2E tests for video moderation pipeline webhook endpoint."""

import pytest
from unittest.mock import AsyncMock, patch

from src.moderation.image_pipeline import ImageClassification, ImageResult


def _safe_result() -> ImageResult:
    return ImageResult(classification=ImageClassification.SAFE, confidence=0.95)


def _unsafe_result() -> ImageResult:
    return ImageResult(classification=ImageClassification.UNSAFE, confidence=0.92)


def _needs_review_result() -> ImageResult:
    return ImageResult(classification=ImageClassification.NEEDS_REVIEW, confidence=0.5)


class TestCFStreamWebhookEndpoint:
    """Test POST /api/v1/moderation/webhooks/cloudflare-stream."""

    @pytest.mark.asyncio
    async def test_valid_webhook_safe_video(self, client):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": "stream-e2e-001", "duration": 5}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"
        assert data["stream_id"] == "stream-e2e-001"
        assert data["classification"] == "safe"

    @pytest.mark.asyncio
    async def test_unsafe_video_detected(self, client):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.side_effect = [_safe_result(), _unsafe_result()]
            payload = {"uid": "stream-e2e-002", "duration": 3}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        assert resp.status_code == 200
        assert resp.json()["classification"] == "unsafe"

    @pytest.mark.asyncio
    async def test_missing_stream_id(self, client):
        payload = {"duration": 10}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-stream",
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_too_long_for_young(self, client):
        payload = {"uid": "stream-e2e-003", "duration": 35, "meta": {"age_tier": "young"}}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-stream",
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["classification"] == "too_long"

    @pytest.mark.asyncio
    async def test_too_long_for_preteen(self, client):
        payload = {"uid": "stream-e2e-004", "duration": 65, "meta": {"age_tier": "preteen"}}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-stream",
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["classification"] == "too_long"

    @pytest.mark.asyncio
    async def test_within_limit_for_teen(self, client):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": "stream-e2e-005", "duration": 170, "meta": {"age_tier": "teen"}}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        assert resp.status_code == 200
        assert resp.json()["classification"] == "safe"

    @pytest.mark.asyncio
    async def test_empty_body(self, client):
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-stream",
            json={},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_needs_review_propagated(self, client):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _needs_review_result()
            payload = {"uid": "stream-e2e-006", "duration": 2}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        assert resp.status_code == 200
        assert resp.json()["classification"] == "needs_review"

    @pytest.mark.asyncio
    async def test_id_fallback_when_uid_missing(self, client):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"id": "stream-e2e-007", "duration": 1}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        assert resp.status_code == 200
        assert resp.json()["stream_id"] == "stream-e2e-007"

    @pytest.mark.asyncio
    async def test_webhook_no_auth_required(self, client):
        """Webhook endpoint is accessible without auth token."""
        payload = {"uid": "stream-e2e-008", "duration": 1}
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        assert resp.status_code != 401
        assert resp.status_code != 403

    @pytest.mark.asyncio
    async def test_response_includes_frames_analyzed(self, client):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": "stream-e2e-009", "duration": 5}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        data = resp.json()
        assert "frames_analyzed" in data
        assert data["frames_analyzed"] == 5

    @pytest.mark.asyncio
    async def test_response_includes_confidence(self, client):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": "stream-e2e-010", "duration": 1}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        data = resp.json()
        assert "confidence" in data
        assert isinstance(data["confidence"], (int, float))

    @pytest.mark.asyncio
    async def test_zero_duration_returns_safe(self, client):
        payload = {"uid": "stream-e2e-011", "duration": 0}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-stream",
            json=payload,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["classification"] == "safe"
        assert data["frames_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_meta_age_tier_applied(self, client):
        """Young age tier enforces 30s limit."""
        payload = {"uid": "stream-e2e-012", "duration": 31, "meta": {"age_tier": "young"}}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-stream",
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["classification"] == "too_long"

    @pytest.mark.asyncio
    async def test_invalid_meta_handled(self, client):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": "stream-e2e-013", "duration": 1, "meta": "not-a-dict"}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"

    @pytest.mark.asyncio
    async def test_early_exit_on_unsafe_fewer_frames(self, client):
        """Unsafe frame causes early exit, resulting in fewer frames analyzed."""
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.side_effect = [_safe_result(), _safe_result(), _unsafe_result(), _safe_result(), _safe_result()]
            payload = {"uid": "stream-e2e-014", "duration": 5}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        data = resp.json()
        assert data["classification"] == "unsafe"
        assert data["frames_analyzed"] == 3  # 3rd frame was unsafe, early exit
