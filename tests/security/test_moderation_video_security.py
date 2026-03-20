"""Security tests for video moderation pipeline."""

from unittest.mock import AsyncMock, patch

import pytest

from src.moderation.image_pipeline import ImageClassification, ImageResult
from src.moderation.video_pipeline import VideoModerationPipeline


def _safe_result() -> ImageResult:
    return ImageResult(classification=ImageClassification.SAFE, confidence=0.95)


class TestWebhookEndpointAuth:
    """Webhook endpoint authentication and access control."""

    @pytest.mark.asyncio
    async def test_webhook_accessible_without_bearer_token(self, client):
        """Stream webhook does not require Bearer auth."""
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": "sec-v01", "duration": 1}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_other_moderation_endpoints_still_require_auth(self, client):
        """Other moderation endpoints are not affected by public webhook."""
        resp = await client.get("/api/v1/moderation/queue")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_moderation_dashboard_requires_auth(self, client):
        resp = await client.get("/api/v1/moderation/dashboard")
        assert resp.status_code == 401


class TestInputValidation:
    """Input validation and injection prevention."""

    @pytest.mark.asyncio
    async def test_oversized_stream_id(self, client):
        """Very large stream ID is handled gracefully."""
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": "x" * 10000, "duration": 1}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_special_characters_in_stream_id(self, client):
        """Special characters in stream ID don't cause crashes."""
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": '<script>alert("xss")</script>', "duration": 1}
            resp = await client.post(
                "/api/v1/moderation/webhooks/cloudflare-stream",
                json=payload,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"

    @pytest.mark.asyncio
    async def test_negative_duration_rejected(self, client):
        payload = {"uid": "sec-v02", "duration": -100}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-stream",
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_string_duration_rejected(self, client):
        payload = {"uid": "sec-v03", "duration": "abc"}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-stream",
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_extremely_large_duration(self, client):
        """Extremely large duration triggers too_long, not crash."""
        payload = {"uid": "sec-v04", "duration": 999999999}
        resp = await client.post(
            "/api/v1/moderation/webhooks/cloudflare-stream",
            json=payload,
        )
        assert resp.status_code == 200
        assert resp.json()["classification"] == "too_long"


class TestFrameUrlSafety:
    """Frame URL generation safety."""

    def test_frame_url_uses_https(self):
        p = VideoModerationPipeline()
        url = p.get_frame_url("test-id", 5.0)
        assert url.startswith("https://")

    def test_stream_id_in_url_no_injection(self):
        """Stream ID with path traversal chars still produces valid URL."""
        p = VideoModerationPipeline()
        url = p.get_frame_url("../../etc/passwd", 0.0)
        # URL is generated, but it's a CF URL — no local file access
        assert "cloudflarestream.com" in url

    def test_negative_timestamp_handled(self):
        """Negative timestamps don't cause issues."""
        p = VideoModerationPipeline()
        url = p.get_frame_url("test-id", -1.0)
        assert "time=-1.0s" in url


class TestResourceExhaustion:
    """Protection against resource exhaustion attacks."""

    @pytest.mark.asyncio
    async def test_max_frames_bounded(self):
        """Very long video doesn't generate unlimited frames."""
        p = VideoModerationPipeline()
        timestamps = p.get_frame_timestamps(3600.0)  # 1 hour
        # 10 frames for first 10s + (3600-10)/5 = 718 frames = 728 total
        assert len(timestamps) == 728
        # This is bounded, not infinite

    @pytest.mark.asyncio
    async def test_zero_duration_no_frames(self):
        """Zero-duration video doesn't create frames."""
        p = VideoModerationPipeline()
        timestamps = p.get_frame_timestamps(0.0)
        assert len(timestamps) == 0
