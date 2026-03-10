"""Risk category taxonomy — 12 categories across 4 severity tiers.

This module defines the canonical list of risk categories monitored by the
Bhapi safety engine.  Each category maps to a default severity level and a
human-readable description used in alerts, reports, and the parent dashboard.
"""

# ---------------------------------------------------------------------------
# Critical severity — immediate danger, requires instant parent notification
# ---------------------------------------------------------------------------
SELF_HARM = "SELF_HARM"
VIOLENCE = "VIOLENCE"
RADICALISATION = "RADICALISATION"
CSAM_ADJACENT = "CSAM_ADJACENT"

# ---------------------------------------------------------------------------
# High severity — serious concern, notification within minutes
# ---------------------------------------------------------------------------
ADULT_CONTENT = "ADULT_CONTENT"
SCAM_MANIPULATION = "SCAM_MANIPULATION"
PII_EXPOSURE = "PII_EXPOSURE"
DEEPFAKE_CONTENT = "DEEPFAKE_CONTENT"

# ---------------------------------------------------------------------------
# Medium severity — warrants review, batched notification
# ---------------------------------------------------------------------------
ACADEMIC_DISHONESTY = "ACADEMIC_DISHONESTY"
BULLYING_HARASSMENT = "BULLYING_HARASSMENT"
SPEND_ANOMALY = "SPEND_ANOMALY"
EMOTIONAL_DEPENDENCY = "EMOTIONAL_DEPENDENCY"

# ---------------------------------------------------------------------------
# Low severity — informational, included in weekly digest
# ---------------------------------------------------------------------------
EXCESSIVE_USAGE = "EXCESSIVE_USAGE"
UNKNOWN_PLATFORM = "UNKNOWN_PLATFORM"

# ---------------------------------------------------------------------------
# Master category dictionary
# ---------------------------------------------------------------------------
RISK_CATEGORIES: dict[str, dict[str, str]] = {
    SELF_HARM: {
        "severity": "critical",
        "description": "Content indicating self-harm ideation, suicide, or eating disorders",
    },
    VIOLENCE: {
        "severity": "critical",
        "description": "Content depicting or encouraging violence, weapons, or physical harm",
    },
    RADICALISATION: {
        "severity": "critical",
        "description": "Content promoting extremist ideologies or radicalisation pathways",
    },
    CSAM_ADJACENT: {
        "severity": "critical",
        "description": "Content that is adjacent to or indicative of child sexual exploitation material",
    },
    ADULT_CONTENT: {
        "severity": "high",
        "description": "Sexually explicit or age-inappropriate content",
    },
    SCAM_MANIPULATION: {
        "severity": "high",
        "description": "Scam attempts, social engineering, or manipulative interactions",
    },
    PII_EXPOSURE: {
        "severity": "high",
        "description": "Personal identifiable information shared with an AI platform",
    },
    DEEPFAKE_CONTENT: {
        "severity": "high",
        "description": "AI-generated deepfake, face swap, or synthetic media content detected",
    },
    ACADEMIC_DISHONESTY: {
        "severity": "medium",
        "description": "Using AI to complete homework, essays, or exams without attribution",
    },
    BULLYING_HARASSMENT: {
        "severity": "medium",
        "description": "Content involving bullying, harassment, or targeted abuse",
    },
    SPEND_ANOMALY: {
        "severity": "medium",
        "description": "Unusual spending patterns on AI platform subscriptions or API usage",
    },
    EMOTIONAL_DEPENDENCY: {
        "severity": "medium",
        "description": "Patterns suggesting emotional dependency on AI companions or chatbots",
    },
    EXCESSIVE_USAGE: {
        "severity": "low",
        "description": "AI usage significantly above the normal baseline for this member",
    },
    UNKNOWN_PLATFORM: {
        "severity": "low",
        "description": "Interaction detected on an unrecognised or newly-added AI platform",
    },
}

# Convenience sets for severity-based filtering
CRITICAL_CATEGORIES = frozenset(
    cat for cat, meta in RISK_CATEGORIES.items() if meta["severity"] == "critical"
)
HIGH_CATEGORIES = frozenset(
    cat for cat, meta in RISK_CATEGORIES.items() if meta["severity"] == "high"
)
MEDIUM_CATEGORIES = frozenset(
    cat for cat, meta in RISK_CATEGORIES.items() if meta["severity"] == "medium"
)
LOW_CATEGORIES = frozenset(
    cat for cat, meta in RISK_CATEGORIES.items() if meta["severity"] == "low"
)

ALL_CATEGORIES = frozenset(RISK_CATEGORIES.keys())
ALL_SEVERITIES = frozenset(("critical", "high", "medium", "low"))
