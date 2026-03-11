"""Multi-layer risk processing pipeline orchestrator.

The pipeline processes capture events through four layers:

Layer 1 — PII Detection:
    Scans content for personally identifiable information (emails, phone
    numbers, credit cards, etc.) and emits PII_EXPOSURE risk events when
    found.

Layer 2 — Safety Classification:
    Classifies content against the full risk taxonomy using Vertex AI /
    Gemini (or keyword-based fallback).

Layer 3 — Rules Engine:
    Applies deterministic keyword watchlists with age-band scaling and
    per-group sensitivity thresholds.

Layer 4 — Risk Event Emission:
    De-duplicates and merges classifications from all layers, then emits
    the final list of risk events for persistence and alerting.
"""

from __future__ import annotations

import structlog

from src.risk.pii_detector import PIIEntity
from src.risk.pii_detector import detect as detect_pii
from src.risk.rules_engine import evaluate as evaluate_rules
from src.risk.safety_classifier import classify as classify_safety
from src.risk.schemas import RiskClassification

logger = structlog.get_logger()


async def process_event(
    capture_event_data: dict,
    member_age: int | None = None,
    config: dict[str, dict] | None = None,
) -> list[RiskClassification]:
    """Run a capture event through the full risk pipeline.

    Parameters
    ----------
    capture_event_data:
        Dictionary with at least a ``content`` key containing the text to
        analyse.  May also include ``platform``, ``event_type``, ``session_id``
        for context.
    member_age:
        The member's age in years (used for age-band scaling).
    config:
        Per-category risk configuration dict.  Keys are category names, values
        have ``sensitivity``, ``enabled``, ``custom_keywords``.

    Returns
    -------
    list[RiskClassification]
        Merged, de-duplicated risk classifications sorted by severity.
    """
    content = capture_event_data.get("content", "")
    if not content or not content.strip():
        logger.debug("risk_pipeline_skip", reason="empty_content")
        return []

    config = config or {}
    all_classifications: list[RiskClassification] = []

    # --- Layer 1: PII Detection ---
    pii_classifications = await _layer_pii_detection(content, config)
    all_classifications.extend(pii_classifications)

    # --- Layer 1.5: Deepfake Detection ---
    # Check text content for deepfake/voice-cloning keywords
    deepfake_text_classifications = _layer_deepfake_text_detection(content)
    all_classifications.extend(deepfake_text_classifications)

    # If media URLs present, submit to Hive/Sensity API
    media_urls = capture_event_data.get("media_urls", [])
    if media_urls:
        deepfake_classifications = await _layer_deepfake_detection(media_urls)
        all_classifications.extend(deepfake_classifications)

    # --- Layer 2: Safety Classification ---
    safety_classifications = await _layer_safety_classification(content)
    all_classifications.extend(safety_classifications)

    # --- Layer 3: Rules Engine ---
    rules_classifications = _layer_rules_engine(content, member_age, config)
    all_classifications.extend(rules_classifications)

    # --- Layer 4: Merge, De-duplicate, Emit ---
    merged = _merge_classifications(all_classifications)

    deepfake_count = len(media_urls) if media_urls else 0
    logger.info(
        "risk_pipeline_complete",
        content_length=len(content),
        pii_count=len(pii_classifications),
        deepfake_text_count=len(deepfake_text_classifications),
        deepfake_urls=deepfake_count,
        safety_count=len(safety_classifications),
        rules_count=len(rules_classifications),
        final_count=len(merged),
        categories=[c.category for c in merged],
    )

    return merged


async def _layer_pii_detection(
    content: str,
    config: dict[str, dict],
) -> list[RiskClassification]:
    """Layer 1: Detect PII and emit PII_EXPOSURE classifications."""
    pii_config = config.get("PII_EXPOSURE", {})
    if not pii_config.get("enabled", True):
        return []

    try:
        entities: list[PIIEntity] = detect_pii(content)
    except Exception as exc:
        logger.error("pii_detection_error", error=str(exc))
        return []

    if not entities:
        return []

    # Group entities by type for a cleaner classification
    entity_types = set(e.entity_type for e in entities)
    max_confidence = max(e.confidence for e in entities)

    return [
        RiskClassification(
            category="PII_EXPOSURE",
            severity="high",
            confidence=round(max_confidence, 3),
            reasoning=f"Detected PII: {', '.join(sorted(entity_types))} ({len(entities)} instance(s))",
        )
    ]


def _layer_deepfake_text_detection(
    content: str,
) -> list[RiskClassification]:
    """Layer 1.5a: Check content for deepfake / voice-cloning keywords."""
    try:
        from src.risk.deepfake_detector import detect_voice_cloning_risk

        result = detect_voice_cloning_risk(content)
        if result.is_risk and result.confidence > 0.7:
            return [
                RiskClassification(
                    category="DEEPFAKE_CONTENT",
                    severity="high",
                    confidence=result.confidence,
                    reasoning=(
                        f"Voice cloning risk detected: {', '.join(result.matched_patterns)}"
                    ),
                )
            ]
    except Exception as exc:
        logger.error("deepfake_text_detection_error", error=str(exc))
    return []


async def _layer_deepfake_detection(
    media_urls: list[str],
) -> list[RiskClassification]:
    """Layer 1.5: Analyse media URLs for deepfake content."""
    import os

    if not os.getenv("DEEPFAKE_API_KEY"):
        return []

    try:
        from src.risk.deepfake_detector import analyze_media

        classifications = []
        for url in media_urls[:5]:  # Limit to 5 URLs per event
            result = await analyze_media(url)
            if result.is_deepfake:
                classifications.append(
                    RiskClassification(
                        category="DEEPFAKE_CONTENT",
                        severity="high",
                        confidence=round(result.confidence, 3),
                        reasoning=f"Deepfake detected by {result.provider} (confidence: {result.confidence:.1%})",
                    )
                )
        return classifications
    except Exception as exc:
        logger.error("deepfake_detection_error", error=str(exc))
        return []


async def _layer_safety_classification(
    content: str,
) -> list[RiskClassification]:
    """Layer 2: Run safety classifier (Vertex AI or fallback)."""
    try:
        return await classify_safety(content)
    except Exception as exc:
        logger.error("safety_classification_error", error=str(exc))
        return []


def _layer_rules_engine(
    content: str,
    member_age: int | None,
    config: dict[str, dict],
) -> list[RiskClassification]:
    """Layer 3: Run deterministic rules engine."""
    try:
        return evaluate_rules(content, member_age=member_age, config=config)
    except Exception as exc:
        logger.error("rules_engine_error", error=str(exc))
        return []


def _merge_classifications(
    classifications: list[RiskClassification],
) -> list[RiskClassification]:
    """Layer 4: Merge and de-duplicate classifications.

    When multiple layers flag the same category, keep the classification
    with the highest confidence and combine their reasoning.
    """
    if not classifications:
        return []

    # Group by category
    by_category: dict[str, list[RiskClassification]] = {}
    for c in classifications:
        by_category.setdefault(c.category, []).append(c)

    merged: list[RiskClassification] = []
    for category, group in by_category.items():
        # Pick the highest-confidence classification
        best = max(group, key=lambda c: c.confidence)

        # Combine reasoning from all layers
        all_reasons = list(dict.fromkeys(c.reasoning for c in group))  # preserve order, deduplicate
        combined_reasoning = " | ".join(all_reasons)

        merged.append(
            RiskClassification(
                category=best.category,
                severity=best.severity,
                confidence=best.confidence,
                reasoning=combined_reasoning,
            )
        )

    # Sort by severity priority
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    merged.sort(key=lambda r: severity_order.get(r.severity, 4))

    return merged
