"""Video moderation pipeline.

CF Stream -> frame extraction -> per-frame classification -> worst-frame decision.
"""

from dataclasses import dataclass

import structlog

from src.moderation.image_pipeline import (
    ImageClassification,
    ImageResult,
    classify_image,
)

logger = structlog.get_logger()

# Video length limits per age tier (seconds)
VIDEO_LENGTH_LIMITS: dict[str, int] = {
    "young": 30,
    "preteen": 60,
    "teen": 180,
}


@dataclass
class VideoResult:
    """Result of video classification."""

    classification: str  # safe/unsafe/needs_review/too_long
    confidence: float
    frames_analyzed: int
    worst_frame_index: int | None
    worst_frame_result: ImageResult | None
    duration_seconds: float | None


class VideoModerationPipeline:
    """Classifies videos by extracting frames and running image classification."""

    def get_frame_timestamps(self, duration: float) -> list[float]:
        """Generate frame extraction timestamps.

        1fps for first 10s, then every 5s after that.
        """
        if duration <= 0:
            return []

        timestamps: list[float] = []
        t = 0.0
        while t < min(duration, 10.0):
            timestamps.append(round(t, 1))
            t += 1.0
        t = 10.0
        while t < duration:
            timestamps.append(round(t, 1))
            t += 5.0
        return timestamps

    def get_frame_url(self, stream_id: str, timestamp: float) -> str:
        """Generate CF Stream thumbnail URL for a specific timestamp."""
        return (
            f"https://customer-{stream_id}.cloudflarestream.com/"
            f"{stream_id}/thumbnails/thumbnail.jpg?time={timestamp}s&width=640"
        )

    async def classify_video(
        self,
        stream_id: str,
        duration: float,
        age_tier: str | None = None,
    ) -> VideoResult:
        """Classify a video by analyzing extracted frames.

        Returns the worst classification across all frames.
        """
        # Check duration limit
        max_duration = VIDEO_LENGTH_LIMITS.get(age_tier or "", 180)
        if duration > max_duration:
            return VideoResult(
                classification="too_long",
                confidence=1.0,
                frames_analyzed=0,
                worst_frame_index=None,
                worst_frame_result=None,
                duration_seconds=duration,
            )

        timestamps = self.get_frame_timestamps(duration)
        if not timestamps:
            return VideoResult(
                classification="safe",
                confidence=0.5,
                frames_analyzed=0,
                worst_frame_index=None,
                worst_frame_result=None,
                duration_seconds=duration,
            )

        worst_result: ImageResult | None = None
        worst_index: int | None = None
        frames_checked = 0

        severity_order = {
            ImageClassification.UNSAFE: 3,
            ImageClassification.NEEDS_REVIEW: 2,
            ImageClassification.ERROR: 1,
            ImageClassification.SAFE: 0,
        }

        for i, ts in enumerate(timestamps):
            frame_url = self.get_frame_url(stream_id, ts)
            result = await classify_image(frame_url, age_tier)
            frames_checked = i + 1

            if worst_result is None or severity_order.get(
                result.classification, 0
            ) > severity_order.get(worst_result.classification, 0):
                worst_result = result
                worst_index = i

            # Early exit on unsafe
            if result.classification == ImageClassification.UNSAFE:
                break

        classification = (
            worst_result.classification if worst_result else "safe"
        )
        confidence = worst_result.confidence if worst_result else 0.5

        return VideoResult(
            classification=classification,
            confidence=confidence,
            frames_analyzed=frames_checked,
            worst_frame_index=worst_index,
            worst_frame_result=worst_result,
            duration_seconds=duration,
        )

    async def handle_cf_stream_webhook(self, payload: dict) -> dict:
        """Handle CF Stream ready webhook."""
        if not isinstance(payload, dict):
            return {"status": "error", "reason": "invalid payload type"}

        stream_id = payload.get("uid") or payload.get("id")
        duration = payload.get("duration", 0)

        if not stream_id:
            return {"status": "ignored", "reason": "missing stream id"}

        if not isinstance(duration, (int, float)) or duration < 0:
            return {"status": "ignored", "reason": "invalid duration"}

        age_tier = (
            payload.get("meta", {}).get("age_tier")
            if isinstance(payload.get("meta"), dict)
            else None
        )

        result = await self.classify_video(
            stream_id, duration, age_tier=age_tier
        )

        logger.info(
            "video_classified",
            stream_id=stream_id,
            classification=result.classification,
            frames=result.frames_analyzed,
        )

        return {
            "status": "processed",
            "stream_id": stream_id,
            "classification": result.classification,
            "confidence": result.confidence,
            "frames_analyzed": result.frames_analyzed,
        }


# Module-level singleton
pipeline = VideoModerationPipeline()


async def classify_video(
    stream_id: str,
    duration: float,
    age_tier: str | None = None,
) -> VideoResult:
    """Classify video using default pipeline."""
    return await pipeline.classify_video(stream_id, duration, age_tier)
