"""Unit tests for video moderation pipeline."""

from unittest.mock import AsyncMock, patch

import pytest

from src.moderation.image_pipeline import ImageClassification, ImageResult
from src.moderation.video_pipeline import (
    VIDEO_LENGTH_LIMITS,
    VideoModerationPipeline,
    VideoResult,
    classify_video,
    pipeline,
)


@pytest.fixture
def vid_pipeline() -> VideoModerationPipeline:
    """Fresh pipeline instance for each test."""
    return VideoModerationPipeline()


def _safe_result() -> ImageResult:
    return ImageResult(classification=ImageClassification.SAFE, confidence=0.95)


def _unsafe_result() -> ImageResult:
    return ImageResult(classification=ImageClassification.UNSAFE, confidence=0.92)


def _needs_review_result() -> ImageResult:
    return ImageResult(classification=ImageClassification.NEEDS_REVIEW, confidence=0.5)


def _error_result() -> ImageResult:
    return ImageResult(classification=ImageClassification.ERROR, confidence=0.0)


# --- VideoResult dataclass ---

class TestVideoResult:
    def test_defaults(self):
        r = VideoResult(
            classification="safe",
            confidence=0.9,
            frames_analyzed=5,
            worst_frame_index=None,
            worst_frame_result=None,
            duration_seconds=10.0,
        )
        assert r.classification == "safe"
        assert r.frames_analyzed == 5

    def test_with_worst_frame(self):
        img = _unsafe_result()
        r = VideoResult(
            classification="unsafe",
            confidence=0.92,
            frames_analyzed=3,
            worst_frame_index=2,
            worst_frame_result=img,
            duration_seconds=5.0,
        )
        assert r.worst_frame_result is img
        assert r.worst_frame_index == 2


# --- Frame timestamp generation ---

class TestFrameTimestamps:
    def test_short_video_1fps(self, vid_pipeline):
        ts = vid_pipeline.get_frame_timestamps(5.0)
        assert ts == [0.0, 1.0, 2.0, 3.0, 4.0]

    def test_exactly_10s(self, vid_pipeline):
        ts = vid_pipeline.get_frame_timestamps(10.0)
        assert ts == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]

    def test_beyond_10s_switches_to_5fps(self, vid_pipeline):
        ts = vid_pipeline.get_frame_timestamps(22.0)
        # First 10s at 1fps: 0,1,2,...,9
        # Then every 5s: 10,15,20
        assert ts[:10] == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        assert ts[10:] == [10.0, 15.0, 20.0]

    def test_zero_duration(self, vid_pipeline):
        ts = vid_pipeline.get_frame_timestamps(0.0)
        assert ts == []

    def test_negative_duration(self, vid_pipeline):
        ts = vid_pipeline.get_frame_timestamps(-5.0)
        assert ts == []

    def test_very_short_video(self, vid_pipeline):
        ts = vid_pipeline.get_frame_timestamps(0.5)
        assert ts == [0.0]

    def test_long_video(self, vid_pipeline):
        ts = vid_pipeline.get_frame_timestamps(180.0)
        # 10 frames for first 10s + (180-10)/5 = 34 frames
        assert len(ts) == 10 + 34


# --- Frame URL generation ---

class TestFrameUrl:
    def test_url_format(self, vid_pipeline):
        url = vid_pipeline.get_frame_url("abc123", 5.0)
        assert "abc123" in url
        assert "time=5.0s" in url
        assert "width=640" in url
        assert url.startswith("https://")

    def test_url_at_zero(self, vid_pipeline):
        url = vid_pipeline.get_frame_url("xyz", 0.0)
        assert "time=0.0s" in url


# --- Duration limits ---

class TestDurationLimits:
    def test_limits_exist(self):
        assert VIDEO_LENGTH_LIMITS["young"] == 30
        assert VIDEO_LENGTH_LIMITS["preteen"] == 60
        assert VIDEO_LENGTH_LIMITS["teen"] == 180

    @pytest.mark.asyncio
    async def test_too_long_for_young(self, vid_pipeline):
        result = await vid_pipeline.classify_video("s1", 31.0, age_tier="young")
        assert result.classification == "too_long"
        assert result.confidence == 1.0
        assert result.frames_analyzed == 0

    @pytest.mark.asyncio
    async def test_too_long_for_preteen(self, vid_pipeline):
        result = await vid_pipeline.classify_video("s2", 61.0, age_tier="preteen")
        assert result.classification == "too_long"

    @pytest.mark.asyncio
    async def test_too_long_for_teen(self, vid_pipeline):
        result = await vid_pipeline.classify_video("s3", 181.0, age_tier="teen")
        assert result.classification == "too_long"

    @pytest.mark.asyncio
    async def test_at_limit_not_too_long(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            result = await vid_pipeline.classify_video("s4", 30.0, age_tier="young")
            assert result.classification != "too_long"

    @pytest.mark.asyncio
    async def test_no_age_tier_uses_teen_default(self, vid_pipeline):
        """No age tier defaults to 180s limit."""
        result = await vid_pipeline.classify_video("s5", 181.0, age_tier=None)
        assert result.classification == "too_long"

    @pytest.mark.asyncio
    async def test_unknown_age_tier_uses_teen_default(self, vid_pipeline):
        result = await vid_pipeline.classify_video("s6", 181.0, age_tier="adult")
        assert result.classification == "too_long"


# --- classify_video (with mocked image classification) ---

class TestClassifyVideo:
    @pytest.mark.asyncio
    async def test_all_frames_safe(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            result = await vid_pipeline.classify_video("vid1", 5.0)
            assert result.classification == ImageClassification.SAFE
            assert result.frames_analyzed == 5
            assert result.duration_seconds == 5.0

    @pytest.mark.asyncio
    async def test_unsafe_frame_early_exit(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.side_effect = [_safe_result(), _unsafe_result(), _safe_result()]
            result = await vid_pipeline.classify_video("vid2", 3.0)
            assert result.classification == ImageClassification.UNSAFE
            assert result.frames_analyzed == 2  # Early exit
            assert result.worst_frame_index == 1

    @pytest.mark.asyncio
    async def test_needs_review_no_early_exit(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.side_effect = [_safe_result(), _needs_review_result(), _safe_result()]
            result = await vid_pipeline.classify_video("vid3", 3.0)
            assert result.classification == ImageClassification.NEEDS_REVIEW
            assert result.frames_analyzed == 3  # No early exit
            assert result.worst_frame_index == 1

    @pytest.mark.asyncio
    async def test_worst_frame_result_stored(self, vid_pipeline):
        unsafe = _unsafe_result()
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.side_effect = [_safe_result(), unsafe]
            result = await vid_pipeline.classify_video("vid4", 2.0)
            assert result.worst_frame_result is unsafe

    @pytest.mark.asyncio
    async def test_zero_duration_returns_safe(self, vid_pipeline):
        result = await vid_pipeline.classify_video("vid5", 0.0)
        assert result.classification == "safe"
        assert result.confidence == 0.5
        assert result.frames_analyzed == 0

    @pytest.mark.asyncio
    async def test_error_frame_lower_than_unsafe(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.side_effect = [_error_result(), _safe_result()]
            result = await vid_pipeline.classify_video("vid6", 2.0)
            assert result.classification == ImageClassification.ERROR
            assert result.worst_frame_index == 0

    @pytest.mark.asyncio
    async def test_age_tier_passed_to_image_classifier(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            await vid_pipeline.classify_video("vid7", 1.0, age_tier="young")
            mock.assert_called_once()
            assert mock.call_args[0][1] == "young"

    @pytest.mark.asyncio
    async def test_confidence_from_worst_frame(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            result = await vid_pipeline.classify_video("vid8", 1.0)
            assert result.confidence == 0.95


# --- CF Stream webhook handling ---

class TestCFStreamWebhook:
    @pytest.mark.asyncio
    async def test_valid_payload_with_uid(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": "stream-001", "duration": 5}
            result = await vid_pipeline.handle_cf_stream_webhook(payload)
            assert result["status"] == "processed"
            assert result["stream_id"] == "stream-001"

    @pytest.mark.asyncio
    async def test_valid_payload_with_id_fallback(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"id": "stream-002", "duration": 5}
            result = await vid_pipeline.handle_cf_stream_webhook(payload)
            assert result["stream_id"] == "stream-002"

    @pytest.mark.asyncio
    async def test_missing_stream_id(self, vid_pipeline):
        result = await vid_pipeline.handle_cf_stream_webhook({"duration": 5})
        assert result["status"] == "ignored"
        assert "missing" in result["reason"]

    @pytest.mark.asyncio
    async def test_invalid_payload_type(self, vid_pipeline):
        result = await vid_pipeline.handle_cf_stream_webhook("not a dict")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_invalid_duration(self, vid_pipeline):
        result = await vid_pipeline.handle_cf_stream_webhook(
            {"uid": "s1", "duration": "not_a_number"}
        )
        assert result["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_negative_duration(self, vid_pipeline):
        result = await vid_pipeline.handle_cf_stream_webhook(
            {"uid": "s1", "duration": -10}
        )
        assert result["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_meta_age_tier_passed(self, vid_pipeline):
        with patch.object(vid_pipeline, "classify_video", new_callable=AsyncMock) as mock:
            mock.return_value = VideoResult(
                classification="safe",
                confidence=0.9,
                frames_analyzed=1,
                worst_frame_index=None,
                worst_frame_result=None,
                duration_seconds=5.0,
            )
            payload = {
                "uid": "s3",
                "duration": 5,
                "meta": {"age_tier": "young"},
            }
            await vid_pipeline.handle_cf_stream_webhook(payload)
            mock.assert_called_once_with("s3", 5, age_tier="young")

    @pytest.mark.asyncio
    async def test_invalid_meta_type(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": "s4", "duration": 1, "meta": "invalid"}
            result = await vid_pipeline.handle_cf_stream_webhook(payload)
            assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_response_includes_frames_analyzed(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": "s5", "duration": 3}
            result = await vid_pipeline.handle_cf_stream_webhook(payload)
            assert result["frames_analyzed"] == 3

    @pytest.mark.asyncio
    async def test_response_includes_confidence(self, vid_pipeline):
        with patch("src.moderation.video_pipeline.classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = _safe_result()
            payload = {"uid": "s6", "duration": 1}
            result = await vid_pipeline.handle_cf_stream_webhook(payload)
            assert "confidence" in result
            assert isinstance(result["confidence"], float)


# --- Module-level classify_video function ---

class TestModuleLevelFunction:
    @pytest.mark.asyncio
    async def test_classify_video_delegates_to_pipeline(self):
        with patch.object(pipeline, "classify_video", new_callable=AsyncMock) as mock:
            mock.return_value = VideoResult(
                classification="safe",
                confidence=0.9,
                frames_analyzed=5,
                worst_frame_index=None,
                worst_frame_result=None,
                duration_seconds=10.0,
            )
            result = await classify_video("stream-x", 10.0, age_tier="teen")
            mock.assert_called_once_with("stream-x", 10.0, "teen")
            assert result.classification == "safe"
