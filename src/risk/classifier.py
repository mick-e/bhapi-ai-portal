"""Risk classification engine with pluggable backends."""

import re
from dataclasses import dataclass

import structlog

from src.config import get_settings

logger = structlog.get_logger()

settings = get_settings()


@dataclass
class ClassificationResult:
    severity: str  # low, medium, high, critical
    categories: list[str]
    confidence: float  # 0.0 - 1.0
    source: str  # keyword, vertex_ai, hybrid
    details: dict | None = None


# Keyword patterns for rule-based classification
KEYWORD_PATTERNS = {
    "critical": {
        "patterns": [
            r"\b(suicide|self[- ]?harm|kill\s+(?:my|your)?self)\b",
            r"\b(child\s+(?:abuse|exploitation|porn))\b",
            r"\b(bomb|weapon)\s+(?:make|build|create)\b",
        ],
        "categories": ["safety", "harmful_content"],
    },
    "high": {
        "patterns": [
            r"\b(drugs?|cocaine|heroin|meth)\s+(?:buy|sell|make|cook)\b",
            r"\b(hack|exploit|breach)\s+(?:into|password|account)\b",
            r"\b(bully|harass|threaten)\b",
        ],
        "categories": ["safety", "policy_violation"],
    },
    "medium": {
        "patterns": [
            r"\b(porn|explicit|nsfw|xxx)\b",
            r"\b(cheat|plagiari[sz]e|homework\s+for\s+me)\b",
            r"\b(fake\s+id|fake\s+identity)\b",
        ],
        "categories": ["inappropriate_content", "academic_integrity"],
    },
}


def classify_by_keywords(text: str) -> ClassificationResult | None:
    """Rule-based classification using keyword patterns."""
    text_lower = text.lower()

    for severity in ("critical", "high", "medium"):
        config = KEYWORD_PATTERNS[severity]
        for pattern in config["patterns"]:
            if re.search(pattern, text_lower):
                return ClassificationResult(
                    severity=severity,
                    categories=config["categories"],
                    confidence=0.85,
                    source="keyword",
                    details={"matched_pattern": pattern},
                )

    return None


async def classify_by_ai(text: str) -> ClassificationResult | None:
    """AI-based classification using Vertex AI or similar.

    Currently returns None (not implemented).
    Enable by setting SAFETY_CLASSIFIER_MODE=vertex_ai or auto.
    """
    mode = getattr(settings, "safety_classifier_mode", "keyword_only")

    if mode == "keyword_only":
        return None

    # Vertex AI integration placeholder
    # In production, this would call Vertex AI Safety API
    logger.info("ai_classification_skipped", reason="vertex_ai not configured")
    return None


async def classify_content(text: str) -> ClassificationResult:
    """Classify content using the configured classification pipeline.

    Pipeline order depends on SAFETY_CLASSIFIER_MODE:
    - keyword_only: keywords only (default)
    - vertex_ai: AI only
    - auto: keywords first, then AI for uncertain results
    """
    mode = getattr(settings, "safety_classifier_mode", "keyword_only")

    # Try keyword classification first
    keyword_result = classify_by_keywords(text)

    if mode == "keyword_only":
        return keyword_result or ClassificationResult(
            severity="low",
            categories=[],
            confidence=0.5,
            source="keyword",
        )

    if mode == "vertex_ai":
        ai_result = await classify_by_ai(text)
        if ai_result:
            return ai_result
        # Fallback to keywords if AI fails
        return keyword_result or ClassificationResult(
            severity="low",
            categories=[],
            confidence=0.3,
            source="keyword",
        )

    # auto mode: use keywords, enhance with AI for non-critical
    if keyword_result and keyword_result.severity in ("critical", "high"):
        return keyword_result  # Trust keywords for clear matches

    ai_result = await classify_by_ai(text)
    if ai_result:
        if keyword_result:
            # Hybrid: combine both results
            return ClassificationResult(
                severity=max(
                    keyword_result.severity,
                    ai_result.severity,
                    key=lambda s: ["low", "medium", "high", "critical"].index(s),
                ),
                categories=list(set(keyword_result.categories + ai_result.categories)),
                confidence=max(keyword_result.confidence, ai_result.confidence),
                source="hybrid",
                details={
                    "keyword": keyword_result.details,
                    "ai": ai_result.details,
                },
            )
        return ai_result

    return keyword_result or ClassificationResult(
        severity="low",
        categories=[],
        confidence=0.5,
        source="keyword",
    )
