"""Vendor risk scoring — evaluates AI platform safety for child use."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

_PROFILES_PATH = Path(__file__).parent / "vendor_profiles.json"
_profiles: dict | None = None


def _load_profiles() -> dict:
    global _profiles
    if _profiles is None:
        with open(_PROFILES_PATH) as f:
            _profiles = json.load(f)
    return _profiles


class VendorRiskScore(BaseModel):
    """Risk assessment for a single AI vendor."""

    provider: str
    name: str
    overall_score: int = Field(ge=0, le=100, description="0-100, 100=safest")
    grade: str  # A, B, C, D, F
    category_scores: dict[str, int]
    recommendations: list[str]


def calculate_vendor_risk(provider: str) -> VendorRiskScore | None:
    """Calculate risk score for a specific AI vendor."""
    profiles = _load_profiles()
    profile = profiles.get(provider)
    if not profile:
        return None

    privacy_score = _score_privacy(profile)
    compliance_score = _score_compliance(profile)
    security_score = _score_security(profile)
    safety_score = _score_child_safety(profile)
    transparency_score = _score_transparency(profile)

    overall = int(
        privacy_score * 0.25
        + compliance_score * 0.25
        + security_score * 0.20
        + safety_score * 0.20
        + transparency_score * 0.10
    )

    return VendorRiskScore(
        provider=provider,
        name=profile["name"],
        overall_score=overall,
        grade=_grade(overall),
        category_scores={
            "privacy": privacy_score,
            "compliance": compliance_score,
            "security": security_score,
            "child_safety": safety_score,
            "transparency": transparency_score,
        },
        recommendations=_get_recommendations(profile),
    )


def get_all_vendor_risks() -> list[VendorRiskScore]:
    """Get risk assessments for all known vendors, sorted by score."""
    profiles = _load_profiles()
    results = []
    for provider in profiles:
        score = calculate_vendor_risk(provider)
        if score:
            results.append(score)
    results.sort(key=lambda x: x.overall_score, reverse=True)
    return results


def _score_privacy(p: dict) -> int:
    score = 50
    if p.get("data_retention_days", 999) <= 30:
        score += 20
    elif p.get("data_retention_days", 999) <= 90:
        score += 10
    if p.get("eu_data_residency"):
        score += 15
    if p.get("data_processing_agreement"):
        score += 15
    return min(score, 100)


def _score_compliance(p: dict) -> int:
    score = 0
    if p.get("gdpr_compliant"):
        score += 35
    if p.get("coppa_compliant"):
        score += 35
    if p.get("soc2_certified"):
        score += 15
    if p.get("iso27001"):
        score += 15
    return min(score, 100)


def _score_security(p: dict) -> int:
    score = 0
    if p.get("encryption_at_rest"):
        score += 35
    if p.get("encryption_in_transit"):
        score += 35
    if p.get("soc2_certified"):
        score += 15
    if p.get("iso27001"):
        score += 15
    return min(score, 100)


def _score_child_safety(p: dict) -> int:
    score = 0
    if p.get("child_safety_features"):
        score += 50
    if p.get("content_moderation"):
        score += 30
    incidents = p.get("incident_history", 0)
    score += max(0, 20 - incidents * 7)
    return min(max(score, 0), 100)


def _score_transparency(p: dict) -> int:
    score = 0
    if p.get("transparency_report"):
        score += 50
    if p.get("data_processing_agreement"):
        score += 50
    return min(score, 100)


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _get_recommendations(p: dict) -> list[str]:
    recs = []
    if not p.get("coppa_compliant"):
        recs.append(
            f"Caution: {p['name']} is not COPPA-certified. Monitor child usage closely."
        )
    if not p.get("gdpr_compliant"):
        recs.append(
            f"{p['name']} lacks GDPR compliance. Consider data residency implications for EU users."
        )
    if not p.get("child_safety_features"):
        recs.append(
            f"{p['name']} does not offer built-in child safety features. Rely on Bhapi blocking rules."
        )
    if p.get("data_retention_days", 0) > 60:
        recs.append(
            f"{p['name']} retains data for {p['data_retention_days']} days. Review data minimisation policies."
        )
    if not p.get("content_moderation"):
        recs.append(
            f"{p['name']} lacks content moderation. Extra vigilance recommended."
        )
    if not recs:
        recs.append(
            f"{p['name']} meets all key safety and compliance requirements."
        )
    return recs
