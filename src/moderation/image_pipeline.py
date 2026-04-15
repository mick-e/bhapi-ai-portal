"""Image moderation pipeline.

Cloudflare Images webhook -> Hive/Sensity classification -> approve/reject.
"""

import hashlib
import hmac
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

import httpx
import structlog

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class ImageClassification(StrEnum):
    SAFE = "safe"
    UNSAFE = "unsafe"
    NEEDS_REVIEW = "needs_review"
    ERROR = "error"


@dataclass
class ImageResult:
    """Result of image classification."""

    classification: ImageClassification
    confidence: float
    categories: dict[str, float] = field(default_factory=dict)
    provider: str = "none"


# Default thresholds for content categories
DEFAULT_THRESHOLDS: dict[str, float] = {
    "nsfw": 0.8,
    "violence": 0.7,
    "self_harm": 0.6,
    "hate": 0.7,
    "drugs": 0.7,
}

# Age tier multipliers — lower = more sensitive
_AGE_TIER_MULTIPLIERS: dict[str, float] = {
    "young": 0.6,
    "preteen": 0.8,
    "teen": 1.0,
}


class ImageModerationPipeline:
    """Classifies images using Hive/Sensity AI moderation APIs."""

    def __init__(self) -> None:
        self._hive_api_key: str | None = None
        self._sensity_api_key: str | None = None
        self._cf_webhook_secret: str | None = None
        self._thresholds: dict[str, float] = dict(DEFAULT_THRESHOLDS)
        self._hive_url: str = "https://api.thehive.ai/api/v2/task/sync"
        self._timeout: float = 10.0

    def configure(
        self,
        hive_api_key: str | None = None,
        sensity_api_key: str | None = None,
        cf_webhook_secret: str | None = None,
    ) -> None:
        """Configure API keys and secrets."""
        if hive_api_key is not None:
            self._hive_api_key = hive_api_key
        if sensity_api_key is not None:
            self._sensity_api_key = sensity_api_key
        if cf_webhook_secret is not None:
            self._cf_webhook_secret = cf_webhook_secret

    def set_thresholds(self, thresholds: dict[str, float]) -> None:
        """Override default thresholds."""
        self._thresholds.update(thresholds)

    def _adjust_thresholds(self, age_tier: str | None) -> dict[str, float]:
        """Return thresholds adjusted for the given age tier."""
        multiplier = _AGE_TIER_MULTIPLIERS.get(age_tier or "teen", 1.0)
        return {k: v * multiplier for k, v in self._thresholds.items()}

    def verify_cf_signature(self, body: bytes, signature: str) -> bool:
        """Verify Cloudflare Images webhook signature.

        Uses HMAC-SHA256 with the configured webhook secret.
        """
        if not self._cf_webhook_secret:
            logger.warning("cf_webhook_no_secret", action="skip_verification")
            return True  # No secret configured — accept (dev mode)

        expected = hmac.new(
            self._cf_webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def classify_image(
        self,
        image_url: str,
        age_tier: str | None = None,
        group_id: "UUID | None" = None,
        member_id: "UUID | None" = None,
        db: "AsyncSession | None" = None,
    ) -> ImageResult:
        """Classify an image using Hive API.

        Falls back to NEEDS_REVIEW if API unavailable.
        Adjusts thresholds for younger age tiers.
        COPPA 2026: if group_id/member_id/db are provided, gates the Hive
        call on third-party consent for the ``hive_sensity`` provider.
        """
        if not image_url or not image_url.strip():
            logger.warning("image_pipeline_empty_url")
            return ImageResult(
                classification=ImageClassification.ERROR,
                confidence=0.0,
                provider="none",
            )

        # Validate URL scheme
        if not image_url.startswith(("https://", "http://")):
            logger.warning("image_pipeline_invalid_url", url=image_url[:50])
            return ImageResult(
                classification=ImageClassification.ERROR,
                confidence=0.0,
                provider="none",
            )

        thresholds = self._adjust_thresholds(age_tier)

        if not self._hive_api_key:
            logger.warning("image_pipeline_no_api_key", action="needs_review")
            return ImageResult(
                classification=ImageClassification.NEEDS_REVIEW,
                confidence=0.0,
                categories={},
                provider="none",
            )

        # COPPA 2026: Check third-party consent before calling Hive/Sensity
        if group_id and member_id and db:
            from src.compliance.coppa_2026 import check_third_party_consent

            has_consent = await check_third_party_consent(
                db, group_id, member_id, "hive_sensity"
            )
            if not has_consent:
                logger.info(
                    "image_moderation_skipped_no_consent",
                    consent_degraded=True,
                    provider="hive_sensity",
                    group_id=str(group_id),
                    member_id=str(member_id),
                )
                return ImageResult(
                    classification=ImageClassification.NEEDS_REVIEW,
                    confidence=0.0,
                    categories={},
                    provider="none",
                )

        try:
            return await self._call_hive(image_url, thresholds)
        except httpx.TimeoutException:
            logger.error("image_pipeline_timeout", url=image_url[:80])
            return ImageResult(
                classification=ImageClassification.NEEDS_REVIEW,
                confidence=0.0,
                categories={},
                provider="hive",
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "image_pipeline_http_error",
                status_code=e.response.status_code,
            )
            return ImageResult(
                classification=ImageClassification.NEEDS_REVIEW,
                confidence=0.0,
                categories={},
                provider="hive",
            )
        except Exception as e:
            logger.error("image_pipeline_error", error=str(e))
            return ImageResult(
                classification=ImageClassification.NEEDS_REVIEW,
                confidence=0.0,
                categories={},
                provider="hive",
            )

    async def _call_hive(
        self, image_url: str, thresholds: dict[str, float]
    ) -> ImageResult:
        """Call Hive API for image classification."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                self._hive_url,
                headers={"Authorization": f"Token {self._hive_api_key}"},
                json={"url": image_url},
            )
            resp.raise_for_status()
            data = resp.json()

        return self._parse_hive_response(data, thresholds)

    def _parse_hive_response(
        self, data: dict, thresholds: dict[str, float]
    ) -> ImageResult:
        """Parse Hive API response and apply thresholds."""
        categories: dict[str, float] = {}

        status_list = data.get("status", [])
        if not status_list:
            return ImageResult(
                classification=ImageClassification.NEEDS_REVIEW,
                confidence=0.0,
                categories={},
                provider="hive",
            )

        for output in status_list[0].get("response", {}).get("output", []):
            for cls in output.get("classes", []):
                class_name = cls.get("class", "")
                score = cls.get("score", 0.0)
                if class_name:
                    categories[class_name] = score

        # Check against thresholds — any category exceeding its threshold is unsafe
        max_score = 0.0
        for category, threshold in thresholds.items():
            score = categories.get(category, 0.0)
            if score > threshold:
                return ImageResult(
                    classification=ImageClassification.UNSAFE,
                    confidence=score,
                    categories=categories,
                    provider="hive",
                )
            max_score = max(max_score, score)

        # Check for borderline scores (within 10% of threshold) -> needs review
        for category, threshold in thresholds.items():
            score = categories.get(category, 0.0)
            if score > threshold * 0.9:
                return ImageResult(
                    classification=ImageClassification.NEEDS_REVIEW,
                    confidence=score,
                    categories=categories,
                    provider="hive",
                )

        return ImageResult(
            classification=ImageClassification.SAFE,
            confidence=1.0 - max_score,
            categories=categories,
            provider="hive",
        )

    async def handle_cf_images_webhook(self, payload: dict) -> dict:
        """Handle Cloudflare Images ready webhook.

        When CF Images finishes processing, classify the image
        and update the moderation queue.
        """
        if not isinstance(payload, dict):
            return {"status": "error", "reason": "invalid payload type"}

        image_id = payload.get("id")
        variants = payload.get("variants", [])

        if not image_id:
            return {"status": "ignored", "reason": "missing image id"}

        if not variants or not isinstance(variants, list):
            return {"status": "ignored", "reason": "missing or invalid variants"}

        # Use the first variant URL for classification
        image_url = variants[0] if variants else None
        if not image_url or not isinstance(image_url, str):
            return {"status": "error", "reason": "no valid variant URL"}

        age_tier = payload.get("meta", {}).get("age_tier") if isinstance(
            payload.get("meta"), dict
        ) else None

        result = await self.classify_image(image_url, age_tier=age_tier)

        logger.info(
            "image_classified",
            image_id=image_id,
            classification=result.classification,
            confidence=result.confidence,
            provider=result.provider,
        )

        return {
            "status": "processed",
            "image_id": image_id,
            "classification": result.classification.value,
            "confidence": result.confidence,
            "categories": result.categories,
        }


# Module-level singleton
pipeline = ImageModerationPipeline()


async def classify_image(
    image_url: str, age_tier: str | None = None
) -> ImageResult:
    """Classify image using default pipeline."""
    return await pipeline.classify_image(image_url, age_tier)
