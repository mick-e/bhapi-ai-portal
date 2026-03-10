"""Deepfake detection via external APIs (Hive, Sensity).

Provides a provider abstraction so the backend can switch between
deepfake detection services via the DEEPFAKE_PROVIDER env var.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class DeepfakeResult:
    """Result from a deepfake detection analysis."""

    is_deepfake: bool
    confidence: float  # 0.0 - 1.0
    provider: str
    details: dict


class DeepfakeDetector(ABC):
    """Base class for deepfake detection providers."""

    @abstractmethod
    async def detect(self, media_url: str) -> DeepfakeResult:
        ...


class HiveDetector(DeepfakeDetector):
    """Hive Moderation deepfake detection."""

    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPFAKE_API_KEY", "")
        self.base_url = "https://api.thehive.ai/api/v2"

    async def detect(self, media_url: str) -> DeepfakeResult:
        if not self.api_key:
            logger.warning("hive_detector_no_key")
            return DeepfakeResult(
                is_deepfake=False,
                confidence=0.0,
                provider="hive",
                details={"error": "No API key configured"},
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/task/sync",
                headers={"Authorization": f"Token {self.api_key}"},
                json={"url": media_url},
                timeout=30.0,
            )
            if response.status_code != 200:
                logger.error("hive_api_error", status=response.status_code)
                return DeepfakeResult(
                    is_deepfake=False,
                    confidence=0.0,
                    provider="hive",
                    details={"error": f"API error: {response.status_code}"},
                )

            data = response.json()
            classes = (
                data.get("status", [{}])[0]
                .get("response", {})
                .get("output", [{}])[0]
                .get("classes", [])
            )
            deepfake_class = next(
                (c for c in classes if c.get("class") == "deepfake"), None
            )
            confidence = deepfake_class.get("score", 0.0) if deepfake_class else 0.0

            return DeepfakeResult(
                is_deepfake=confidence > 0.7,
                confidence=confidence,
                provider="hive",
                details=data,
            )


class SensityDetector(DeepfakeDetector):
    """Sensity AI deepfake detection."""

    def __init__(self) -> None:
        self.api_key = os.getenv("DEEPFAKE_API_KEY", "")
        self.base_url = "https://api.sensity.ai/api/v1"

    async def detect(self, media_url: str) -> DeepfakeResult:
        if not self.api_key:
            logger.warning("sensity_detector_no_key")
            return DeepfakeResult(
                is_deepfake=False,
                confidence=0.0,
                provider="sensity",
                details={"error": "No API key configured"},
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/detect",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"url": media_url},
                timeout=30.0,
            )
            if response.status_code != 200:
                return DeepfakeResult(
                    is_deepfake=False,
                    confidence=0.0,
                    provider="sensity",
                    details={"error": f"API error: {response.status_code}"},
                )

            data = response.json()
            confidence = data.get("deepfake_probability", 0.0)

            return DeepfakeResult(
                is_deepfake=confidence > 0.7,
                confidence=confidence,
                provider="sensity",
                details=data,
            )


def get_detector() -> DeepfakeDetector:
    """Get the configured deepfake detector instance."""
    provider = os.getenv("DEEPFAKE_PROVIDER", "hive")
    if provider == "sensity":
        return SensityDetector()
    return HiveDetector()


async def analyze_media(media_url: str) -> DeepfakeResult:
    """Analyze a media URL for deepfake content."""
    detector = get_detector()
    return await detector.detect(media_url)
