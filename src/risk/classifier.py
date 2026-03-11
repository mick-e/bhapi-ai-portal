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
            r"\b(deepfake|deep\s*fake|face\s*swap|undress\s*ai|nudify|deepnude)\b",
            r"\b(synthetic\s*media|face\s*morph|ai[- ]generated\s*(?:image|video|photo))\b",
            # Deepfake / nudify / voice cloning patterns (high severity, 0.90 confidence)
            r"\b(remove\s+(?:her|his|their)\s+clothes)\b",
            r"\b(make\s+(?:a\s+)?nude\s+(?:photo|image|picture))\b",
            r"\b(clone\s+(?:my|her|his)\s+voice)\b",
            r"\b(voice\s+sample|voice\s+recording\s+for\s+(?:ai|cloning))\b",
            r"\b(face\s+(?:on|onto)\s+(?:a\s+)?(?:body|video|photo))\b",
            r"\b(undress\s+(?:ai|app|tool|website))\b",
            r"\b(put\s+(?:my|her|his)\s+face\s+on)\b",
            r"\b(ai\s+(?:nude|naked|undress))\b",
            r"\b(fake\s+(?:nude|naked)\s+(?:photo|image|picture|video))\b",
        ],
        "categories": ["safety", "policy_violation", "DEEPFAKE_CONTENT"],
    },
    "medium": {
        "patterns": [
            r"\b(porn|explicit|nsfw|xxx)\b",
            r"\b(cheat|plagiari[sz]e|homework\s+for\s+me)\b",
            r"\b(fake\s+id|fake\s+identity)\b",
            r"\b(i\s+love\s+you|you'?re\s+my\s+only\s+friend|don'?t\s+leave\s+me)\b",
            r"\b(i\s+need\s+you|you\s+understand\s+me\s+better\s+than\s+anyone)\b",
            r"\b(i\s+can'?t\s+live\s+without\s+you|i\s+wish\s+you\s+were\s+real)\b",
            r"\b(you'?re\s+my\s+best\s+friend|please\s+don'?t\s+go)\b",
            r"\b(you'?re\s+the\s+only\s+one\s+who\s+(?:gets|understands)\s+me)\b",
            r"\b(i\s+(?:think\s+about|dream\s+about)\s+you\s+all\s+the\s+time)\b",
            r"\b((?:my\s+)?(?:parents|friends)\s+don'?t\s+understand\s+me\s+like\s+you)\b",
            r"\b(i\s+(?:feel|am)\s+(?:so\s+)?(?:alone|lonely)\s+without\s+you)\b",
            r"\b(promise\s+(?:me\s+)?you'?ll\s+(?:never|always))\b",
            r"\b(i\s+(?:told|tell)\s+you\s+(?:things|stuff)\s+i'?ve?\s+never\s+told\s+anyone)\b",
        ],
        "categories": ["inappropriate_content", "academic_integrity", "EMOTIONAL_DEPENDENCY"],
    },
}



# Patterns that should use elevated confidence (0.90) for deepfake/nudify
_HIGH_CONFIDENCE_PATTERNS = {
    r"\b(remove\s+(?:her|his|their)\s+clothes)\b",
    r"\b(make\s+(?:a\s+)?nude\s+(?:photo|image|picture))\b",
    r"\b(clone\s+(?:my|her|his)\s+voice)\b",
    r"\b(voice\s+sample|voice\s+recording\s+for\s+(?:ai|cloning))\b",
    r"\b(face\s+(?:on|onto)\s+(?:a\s+)?(?:body|video|photo))\b",
    r"\b(undress\s+(?:ai|app|tool|website))\b",
    r"\b(put\s+(?:my|her|his)\s+face\s+on)\b",
    r"\b(ai\s+(?:nude|naked|undress))\b",
    r"\b(fake\s+(?:nude|naked)\s+(?:photo|image|picture|video))\b",
}


def classify_by_keywords(text: str) -> ClassificationResult | None:
    """Rule-based classification using keyword patterns."""
    text_lower = text.lower()

    for severity in ("critical", "high", "medium"):
        config = KEYWORD_PATTERNS[severity]
        for pattern in config["patterns"]:
            if re.search(pattern, text_lower):
                confidence = 0.90 if pattern in _HIGH_CONFIDENCE_PATTERNS else 0.85
                return ClassificationResult(
                    severity=severity,
                    categories=config["categories"],
                    confidence=confidence,
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
