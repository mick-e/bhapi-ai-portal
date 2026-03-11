"""Deepfake detection via external APIs (Hive, Sensity).

Provides a provider abstraction so the backend can switch between
deepfake detection services via the DEEPFAKE_PROVIDER env var.
"""

from __future__ import annotations

import os
import re
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


VOICE_CLONING_PATTERNS: list[str] = [
    r"\b(clone\s+(?:my|her|his|their|a)\s+voice)\b",
    r"\b(voice\s+cloning)\b",
    r"\b(voice\s+sample\s+for\s+(?:ai|cloning|replication))\b",
    r"\b(voice\s+recording\s+for\s+(?:ai|cloning))\b",
    r"\b(replicate\s+(?:my|her|his|their)\s+voice)\b",
    r"\b(text\s+to\s+speech\s+(?:clone|copy|mimic))\b",
    r"\b(ai\s+voice\s+(?:generator|clone|copy))\b",
    r"\b(deepfake\s+(?:voice|audio|call))\b",
]

_VOICE_CLONING_RE = [re.compile(p, re.IGNORECASE) for p in VOICE_CLONING_PATTERNS]


@dataclass
class VoiceCloningRisk:
    """Result of voice cloning risk assessment."""

    is_risk: bool
    confidence: float
    matched_patterns: list[str]
    recommendation: str


def detect_voice_cloning_risk(text: str) -> VoiceCloningRisk:
    """Check text for voice-cloning-related patterns and return a risk assessment.

    This is a synchronous, keyword-based check — no external API required.
    """
    if not text or not text.strip():
        return VoiceCloningRisk(
            is_risk=False,
            confidence=0.0,
            matched_patterns=[],
            recommendation="",
        )

    matched: list[str] = []
    for regex in _VOICE_CLONING_RE:
        m = regex.search(text)
        if m:
            matched.append(m.group(0))

    if not matched:
        return VoiceCloningRisk(
            is_risk=False,
            confidence=0.0,
            matched_patterns=[],
            recommendation="",
        )

    confidence = min(0.90 + 0.02 * (len(matched) - 1), 1.0)

    return VoiceCloningRisk(
        is_risk=True,
        confidence=round(confidence, 3),
        matched_patterns=matched,
        recommendation=(
            "Voice cloning technology can be used for fraud and impersonation. "
            "Discuss with your child why creating voice clones of others "
            "without consent is harmful and potentially illegal."
        ),
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
