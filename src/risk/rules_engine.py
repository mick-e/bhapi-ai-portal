"""Deterministic rules engine for risk classification.

Applies keyword watchlists, age-band risk scaling, and sensitivity threshold
checking to produce risk classifications without requiring any external ML model.
"""

from __future__ import annotations

import re

import structlog

from src.risk.schemas import RiskClassification
from src.risk.taxonomy import RISK_CATEGORIES

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Keyword watchlists by category
# ---------------------------------------------------------------------------
# Each list is intentionally kept broad — false positives are filtered by
# the confidence threshold set in the group's RiskConfig.

KEYWORD_WATCHLISTS: dict[str, list[str]] = {
    "SELF_HARM": [
        "kill myself",
        "want to die",
        "end my life",
        "suicide",
        "self harm",
        "self-harm",
        "cutting myself",
        "overdose",
        "don't want to live",
        "not worth living",
        "slit my wrists",
        "hang myself",
        "jump off",
        "no reason to live",
        "better off dead",
    ],
    "VIOLENCE": [
        "how to make a bomb",
        "how to make a weapon",
        "how to hurt someone",
        "kill someone",
        "school shooting",
        "mass shooting",
        "stab someone",
        "poison someone",
        "attack plan",
        "hit list",
        "torture",
    ],
    "RADICALISATION": [
        "join the cause",
        "holy war",
        "jihad",
        "white power",
        "race war",
        "ethnic cleansing",
        "supremacist",
        "radicalise",
        "radicalize",
        "manifesto",
        "lone wolf",
        "martyrdom",
        "infidel",
    ],
    "CSAM_ADJACENT": [
        "underage",
        "child exploitation",
        "minor explicit",
        "inappropriate child",
        "young body",
    ],
    "ADULT_CONTENT": [
        "explicit content",
        "pornography",
        "sexual content",
        "nude",
        "nsfw",
        "xxx",
        "erotic",
        "sexually explicit",
        "only fans",
        "onlyfans",
    ],
    "SCAM_MANIPULATION": [
        "send me money",
        "gift card",
        "wire transfer",
        "bank details",
        "account number",
        "social engineering",
        "phishing",
        "you've won",
        "nigerian prince",
        "lottery winner",
        "urgent transfer",
        "crypto investment",
        "guaranteed returns",
    ],
    "ACADEMIC_DISHONESTY": [
        "write my essay",
        "do my homework",
        "complete my assignment",
        "answer my exam",
        "write this paper for me",
        "solve my test",
        "take my quiz",
        "cheat on",
        "plagiarise",
        "plagiarize",
        "copy paste this",
        "submit as my own",
    ],
    "BULLYING_HARASSMENT": [
        "you're ugly",
        "kill yourself",
        "kys",
        "nobody likes you",
        "you're worthless",
        "hate you",
        "loser",
        "go die",
        "fat pig",
        "retard",
        "harass",
        "bully",
        "threaten",
    ],
}

# Pre-compile keyword patterns for performance
_COMPILED_WATCHLISTS: dict[str, list[re.Pattern]] = {
    category: [re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords]
    for category, keywords in KEYWORD_WATCHLISTS.items()
}

# ---------------------------------------------------------------------------
# Age-band scaling: younger children get stricter (lower) thresholds
# ---------------------------------------------------------------------------
# Age band -> multiplier applied to sensitivity threshold.
# A lower multiplier means the threshold is reduced, so less confident
# matches are still flagged.

AGE_BAND_MULTIPLIERS: dict[str, float] = {
    "under_8": 0.40,   # Very strict — flag almost everything
    "8_to_10": 0.55,
    "11_to_13": 0.70,
    "14_to_16": 0.85,
    "17_plus": 1.00,    # Standard threshold
}


def _get_age_band(age: int | None) -> str:
    """Map a member's age to an age band."""
    if age is None:
        return "11_to_13"  # Conservative default
    if age < 8:
        return "under_8"
    if age <= 10:
        return "8_to_10"
    if age <= 13:
        return "11_to_13"
    if age <= 16:
        return "14_to_16"
    return "17_plus"


def _effective_threshold(sensitivity: int, age: int | None) -> float:
    """Compute the effective confidence threshold for a category.

    sensitivity is 0-100 (higher = more sensitive = lower threshold).
    Returns a float 0.0-1.0 representing the minimum confidence required
    to flag a match.
    """
    # Convert sensitivity to a base threshold: sensitivity 100 → threshold 0.0
    # sensitivity 0 → threshold 1.0 (i.e. nothing passes)
    base_threshold = 1.0 - (sensitivity / 100.0)

    # Apply age-band multiplier (makes the threshold lower for younger children)
    band = _get_age_band(age)
    multiplier = AGE_BAND_MULTIPLIERS[band]

    return base_threshold * multiplier


def evaluate(
    text: str,
    member_age: int | None = None,
    config: dict[str, dict] | None = None,
) -> list[RiskClassification]:
    """Run all deterministic rules against *text*.

    Parameters
    ----------
    text:
        The content to evaluate.
    member_age:
        The member's age in years (used for age-band scaling). ``None``
        uses a conservative default.
    config:
        Optional per-category configuration dict, keyed by category name.
        Each value should have ``sensitivity`` (int 0-100) and ``enabled`` (bool).
        Categories not present in *config* use defaults.

    Returns
    -------
    list[RiskClassification]
        One classification per triggered category, sorted by severity.
    """
    if not text or not text.strip():
        return []

    config = config or {}
    results: list[RiskClassification] = []
    text.lower()

    for category, patterns in _COMPILED_WATCHLISTS.items():
        # Check if category is enabled
        cat_config = config.get(category, {})
        if not cat_config.get("enabled", True):
            continue

        sensitivity = cat_config.get("sensitivity", 50)
        threshold = _effective_threshold(sensitivity, member_age)

        # Also check custom keywords from config
        custom_keywords = cat_config.get("custom_keywords", {})
        custom_patterns = [
            re.compile(re.escape(kw), re.IGNORECASE)
            for kw in custom_keywords.get("keywords", [])
        ] if custom_keywords else []

        all_patterns = patterns + custom_patterns

        # Count matches across all patterns for this category
        match_count = 0
        matched_keywords: list[str] = []

        for pattern in all_patterns:
            matches = pattern.findall(text)
            if matches:
                match_count += len(matches)
                matched_keywords.append(pattern.pattern.replace("\\", ""))

        if match_count == 0:
            continue

        # Compute confidence based on match density
        # More matches and longer keyword matches = higher confidence
        word_count = max(len(text.split()), 1)
        density = min(match_count / word_count, 1.0)
        # Base confidence: single match = 0.5, scales up with density
        confidence = min(0.5 + (density * 0.5), 1.0)

        # Boost confidence for critical categories with exact phrase matches
        category_meta = RISK_CATEGORIES.get(category, {})
        severity = category_meta.get("severity", "medium")
        if severity == "critical" and match_count >= 1:
            confidence = min(confidence + 0.15, 1.0)

        # Apply threshold
        if confidence < threshold:
            logger.debug(
                "risk_below_threshold",
                category=category,
                confidence=confidence,
                threshold=threshold,
                member_age=member_age,
            )
            continue

        results.append(
            RiskClassification(
                category=category,
                severity=severity,
                confidence=round(confidence, 3),
                reasoning=f"Keyword match: {', '.join(matched_keywords[:5])}",
            )
        )

    # Sort by severity priority: critical > high > medium > low
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    results.sort(key=lambda r: severity_order.get(r.severity, 4))

    return results
