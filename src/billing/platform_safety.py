"""AI Platform Safety Ratings — child safety assessments for popular AI platforms."""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class PlatformSafetyProfile:
    """Safety profile for an AI platform."""

    key: str
    name: str
    overall_grade: str  # A-F
    min_age_recommended: int
    has_parental_controls: bool
    has_content_filters: bool
    data_retention_days: int
    coppa_compliant: bool
    known_incidents: int
    strengths: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    last_updated: str = ""


PLATFORM_SAFETY_PROFILES: dict[str, PlatformSafetyProfile] = {
    "chatgpt": PlatformSafetyProfile(
        key="chatgpt",
        name="ChatGPT (OpenAI)",
        overall_grade="B",
        min_age_recommended=13,
        has_parental_controls=True,
        has_content_filters=True,
        data_retention_days=30,
        coppa_compliant=False,
        known_incidents=3,
        strengths=[
            "Strong content moderation system",
            "Family Link parental controls available",
            "Data export and deletion supported",
            "Regular safety updates and red-teaming",
        ],
        concerns=[
            "Not COPPA-certified for under-13 use",
            "Potential for prompt injection bypasses",
            "Chat history retained for 30 days by default",
        ],
        last_updated="2026-01-15",
    ),
    "claude": PlatformSafetyProfile(
        key="claude",
        name="Claude (Anthropic)",
        overall_grade="A",
        min_age_recommended=13,
        has_parental_controls=False,
        has_content_filters=True,
        data_retention_days=30,
        coppa_compliant=False,
        known_incidents=1,
        strengths=[
            "Constitutional AI safety approach",
            "Strong refusal of harmful content",
            "SOC 2 Type II certified",
            "Transparent safety documentation",
        ],
        concerns=[
            "Limited parental control features",
            "Not COPPA-certified for under-13 use",
            "No dedicated family plan",
        ],
        last_updated="2026-01-15",
    ),
    "gemini": PlatformSafetyProfile(
        key="gemini",
        name="Gemini (Google)",
        overall_grade="B",
        min_age_recommended=13,
        has_parental_controls=True,
        has_content_filters=True,
        data_retention_days=90,
        coppa_compliant=False,
        known_incidents=2,
        strengths=[
            "Google Family Link integration",
            "Robust content safety filters",
            "Enterprise-grade security (ISO 27001, SOC 2)",
            "Workspace for Education with admin controls",
        ],
        concerns=[
            "Longer data retention (90 days)",
            "Data used for model improvement by default",
            "Complex privacy settings for parents",
        ],
        last_updated="2026-01-15",
    ),
    "copilot": PlatformSafetyProfile(
        key="copilot",
        name="Copilot (Microsoft)",
        overall_grade="B",
        min_age_recommended=13,
        has_parental_controls=True,
        has_content_filters=True,
        data_retention_days=60,
        coppa_compliant=False,
        known_incidents=2,
        strengths=[
            "Microsoft Family Safety integration",
            "Enterprise compliance certifications",
            "Content filtering with multiple strictness levels",
            "Education-specific features (Copilot for Education)",
        ],
        concerns=[
            "Embedded in many Microsoft products (broad surface area)",
            "Data retention of 60 days",
            "Not COPPA-certified for under-13 use",
        ],
        last_updated="2026-01-15",
    ),
    "grok": PlatformSafetyProfile(
        key="grok",
        name="Grok (xAI)",
        overall_grade="D",
        min_age_recommended=18,
        has_parental_controls=False,
        has_content_filters=False,
        data_retention_days=180,
        coppa_compliant=False,
        known_incidents=5,
        strengths=[
            "Real-time information access",
            "Transparent about limitations",
        ],
        concerns=[
            "No content filtering by default",
            "No parental controls",
            "Long data retention (180 days)",
            "Multiple reported safety incidents",
            "Not recommended for children under 18",
        ],
        last_updated="2026-01-15",
    ),
    "characterai": PlatformSafetyProfile(
        key="characterai",
        name="Character.AI",
        overall_grade="C",
        min_age_recommended=16,
        has_parental_controls=True,
        has_content_filters=True,
        data_retention_days=90,
        coppa_compliant=False,
        known_incidents=4,
        strengths=[
            "Added parental controls after public pressure",
            "Content filters for minors enabled by default",
            "Teen-specific safeguards introduced",
        ],
        concerns=[
            "History of inappropriate character responses",
            "Emotional attachment risks for young users",
            "Multiple safety incidents involving minors",
            "Roleplay features can bypass safety filters",
        ],
        last_updated="2026-01-15",
    ),
    "replika": PlatformSafetyProfile(
        key="replika",
        name="Replika",
        overall_grade="D",
        min_age_recommended=18,
        has_parental_controls=False,
        has_content_filters=True,
        data_retention_days=365,
        coppa_compliant=False,
        known_incidents=6,
        strengths=[
            "Content filters added after regulatory action",
            "Emotional support features",
        ],
        concerns=[
            "Designed for intimate companionship — inappropriate for children",
            "Very long data retention (365 days)",
            "No parental controls",
            "Multiple regulatory actions in EU",
            "Emotional dependency risks for minors",
            "Not recommended for children under 18",
        ],
        last_updated="2026-01-15",
    ),
    "pi": PlatformSafetyProfile(
        key="pi",
        name="Pi (Inflection AI)",
        overall_grade="B",
        min_age_recommended=13,
        has_parental_controls=False,
        has_content_filters=True,
        data_retention_days=30,
        coppa_compliant=False,
        known_incidents=0,
        strengths=[
            "Conversational AI with strong safety guardrails",
            "No reported safety incidents to date",
            "Short data retention (30 days)",
            "Designed for safe, supportive conversations",
        ],
        concerns=[
            "No parental controls",
            "Relatively new platform — limited track record",
            "Not COPPA-certified for under-13 use",
        ],
        last_updated="2026-01-15",
    ),
}


def get_platform_safety_ratings() -> list[dict]:
    """Return safety ratings for all platforms."""
    results = []
    for profile in PLATFORM_SAFETY_PROFILES.values():
        results.append(_profile_to_dict(profile))
    results.sort(key=lambda x: x["overall_grade"])
    return results


def get_platform_safety_rating(platform: str) -> dict | None:
    """Return safety rating for a single platform."""
    profile = PLATFORM_SAFETY_PROFILES.get(platform)
    if not profile:
        return None
    return _profile_to_dict(profile)


def get_age_recommendations(age: int) -> list[dict]:
    """Return platforms filtered by minimum age recommendation."""
    results = []
    for profile in PLATFORM_SAFETY_PROFILES.values():
        item = _profile_to_dict(profile)
        if age >= profile.min_age_recommended:
            item["recommendation"] = "recommended"
        elif age >= profile.min_age_recommended - 3:
            item["recommendation"] = "use_with_caution"
        else:
            item["recommendation"] = "not_recommended"
        results.append(item)
    results.sort(key=lambda x: (
        0 if x["recommendation"] == "recommended" else
        1 if x["recommendation"] == "use_with_caution" else 2,
        x["overall_grade"],
    ))
    return results


def _profile_to_dict(profile: PlatformSafetyProfile) -> dict:
    """Convert profile to serializable dict."""
    return {
        "key": profile.key,
        "name": profile.name,
        "overall_grade": profile.overall_grade,
        "min_age_recommended": profile.min_age_recommended,
        "has_parental_controls": profile.has_parental_controls,
        "has_content_filters": profile.has_content_filters,
        "data_retention_days": profile.data_retention_days,
        "coppa_compliant": profile.coppa_compliant,
        "known_incidents": profile.known_incidents,
        "strengths": profile.strengths,
        "concerns": profile.concerns,
        "last_updated": profile.last_updated,
    }
