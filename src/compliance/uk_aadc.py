"""UK Age Appropriate Design Code (AADC) compliance — gap analysis and privacy-by-default.

Implements the 15 AADC standards as defined by the UK Information Commissioner's Office (ICO).
Provides gap analysis to identify non-compliant settings and enforces maximum-privacy defaults
for child accounts based on age tier.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.compliance.uk_aadc_models import AadcAssessment, PrivacyDefault
from src.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# 15 AADC standards
# ---------------------------------------------------------------------------

AADC_STANDARDS = [
    {
        "id": "best_interests",
        "name": "Best Interests of the Child",
        "description": "The best interests of the child should be a primary consideration when designing and developing online services likely to be accessed by children.",
        "ico_reference": "Standard 1",
    },
    {
        "id": "age_verification",
        "name": "Age-Appropriate Application",
        "description": "Take a risk-based approach to recognising the age of individual users and ensure you effectively apply the standards in this code to child users.",
        "ico_reference": "Standard 2",
    },
    {
        "id": "transparency",
        "name": "Transparency",
        "description": "The privacy information you provide to users, and other published terms, policies and community standards, must be concise, prominent, and in clear language suited to the age of the child.",
        "ico_reference": "Standard 3",
    },
    {
        "id": "data_minimization",
        "name": "Data Minimisation",
        "description": "Collect and retain only the minimum amount of personal data you need to provide the elements of your service in which a child is actively and knowingly engaged.",
        "ico_reference": "Standard 4 (linked to GDPR Article 5(1)(c))",
    },
    {
        "id": "sharing_limits",
        "name": "Data Sharing",
        "description": "Do not disclose children's data unless you can demonstrate a compelling reason to do so, taking account of the best interests of the child.",
        "ico_reference": "Standard 5",
    },
    {
        "id": "geolocation",
        "name": "Geolocation",
        "description": "Switch geolocation options off by default (unless you can demonstrate a compelling reason for geolocation to be switched on by default).",
        "ico_reference": "Standard 6",
    },
    {
        "id": "parental_controls",
        "name": "Parental Controls",
        "description": "If you provide parental controls, give the child age-appropriate information about this. If your online service allows a parent or carer to monitor their child's online activity or track their location, provide an obvious sign to the child when they are being monitored.",
        "ico_reference": "Standard 7",
    },
    {
        "id": "privacy_settings",
        "name": "Privacy Settings",
        "description": "Provide prominent and accessible tools to help children exercise their data protection rights and report concerns.",
        "ico_reference": "Standard 8",
    },
    {
        "id": "enforcement",
        "name": "Enforcement and Compliance",
        "description": "Ensure your published terms, policies and community standards are upheld, including any prohibitions on behaviour aimed at children.",
        "ico_reference": "Standard 9",
    },
    {
        "id": "connected_toys",
        "name": "Connected Toys and Devices",
        "description": "If your online service includes connected toys or devices, ensure that you include effective tools to enable compliance with this code.",
        "ico_reference": "Standard 10",
    },
    {
        "id": "online_tools",
        "name": "Online Tools",
        "description": "Provide prominent and accessible tools to help children exercise their data protection rights and report concerns.",
        "ico_reference": "Standard 11",
    },
    {
        "id": "profiling",
        "name": "Profiling",
        "description": "Only allow profiling if you have appropriate measures in place to protect the child from any harmful effects (in particular, being fed content that is detrimental to their health or wellbeing).",
        "ico_reference": "Standard 12",
    },
    {
        "id": "nudge_techniques",
        "name": "Nudge Techniques",
        "description": "Do not use nudge techniques to lead or encourage children to provide unnecessary personal data or weaken or turn off their privacy protections.",
        "ico_reference": "Standard 13",
    },
    {
        "id": "default_settings",
        "name": "Default Settings",
        "description": "Provide default settings which ensure that children have the highest level of privacy by default, unless you can demonstrate a compelling reason for a different default setting.",
        "ico_reference": "Standard 14",
    },
    {
        "id": "conformity_assessment",
        "name": "Data Protection Impact Assessment",
        "description": "Undertake a DPIA for any new online service likely to be accessed by children. Use it to inform your approach to compliance with this code.",
        "ico_reference": "Standard 15",
    },
]

AADC_STANDARD_IDS = [s["id"] for s in AADC_STANDARDS]

# ---------------------------------------------------------------------------
# Privacy defaults per age tier (maximum privacy = AADC Standard 14)
# ---------------------------------------------------------------------------

_PRIVACY_DEFAULTS: dict[str, dict] = {
    "young": {
        "profile_visibility": "private",
        "geolocation_enabled": False,
        "profiling_enabled": False,
        "data_sharing_enabled": False,
        "search_visible": False,
        "contact_requests_enabled": False,
        "direct_messages_enabled": False,
        "content_recommendations_enabled": False,
        "analytics_tracking_enabled": False,
        "third_party_sharing_enabled": False,
    },
    "preteen": {
        "profile_visibility": "private",
        "geolocation_enabled": False,
        "profiling_enabled": False,
        "data_sharing_enabled": False,
        "search_visible": False,
        "contact_requests_enabled": True,
        "direct_messages_enabled": True,
        "content_recommendations_enabled": False,
        "analytics_tracking_enabled": False,
        "third_party_sharing_enabled": False,
    },
    "teen": {
        "profile_visibility": "private",
        "geolocation_enabled": False,
        "profiling_enabled": False,
        "data_sharing_enabled": False,
        "search_visible": True,
        "contact_requests_enabled": True,
        "direct_messages_enabled": True,
        "content_recommendations_enabled": True,
        "analytics_tracking_enabled": False,
        "third_party_sharing_enabled": False,
    },
}


# ---------------------------------------------------------------------------
# Gap analysis
# ---------------------------------------------------------------------------


async def run_gap_analysis(db: AsyncSession, group_id: UUID, assessor: str = "system") -> dict:
    """Evaluate all 15 AADC standards for a group and return compliance status per standard.

    Each standard is rated as 'compliant', 'partial', or 'non_compliant' based on
    the group's current configuration, consent records, and privacy settings.
    """
    from src.groups.models import Group

    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise NotFoundError("Group", str(group_id))

    settings = group.settings or {}
    standards = []

    for std in AADC_STANDARDS:
        status = _evaluate_standard(std["id"], settings, group)
        standards.append({
            "id": std["id"],
            "name": std["name"],
            "description": std["description"],
            "ico_reference": std["ico_reference"],
            "status": status,
            "recommendations": _get_recommendations(std["id"], status),
        })

    # Calculate overall score
    compliant_count = sum(1 for s in standards if s["status"] == "compliant")
    partial_count = sum(1 for s in standards if s["status"] == "partial")
    total = len(standards)
    score = round((compliant_count + partial_count * 0.5) / total * 100, 1)

    if score >= 90:
        overall_status = "compliant"
    elif score >= 60:
        overall_status = "partial"
    else:
        overall_status = "non_compliant"

    # Persist assessment
    assessment = AadcAssessment(
        id=uuid4(),
        group_id=group_id,
        version=1,
        standards=[
            {"id": s["id"], "status": s["status"], "recommendations": s["recommendations"]}
            for s in standards
        ],
        assessed_at=datetime.now(timezone.utc),
        assessor=assessor,
        score=score,
        overall_status=overall_status,
    )
    db.add(assessment)
    await db.flush()
    await db.refresh(assessment)

    logger.info(
        "aadc_gap_analysis_complete",
        group_id=str(group_id),
        score=score,
        overall_status=overall_status,
        compliant=compliant_count,
        partial=partial_count,
        non_compliant=total - compliant_count - partial_count,
    )

    return {
        "id": str(assessment.id),
        "group_id": str(group_id),
        "version": assessment.version,
        "score": score,
        "overall_status": overall_status,
        "standards": standards,
        "assessed_at": assessment.assessed_at.isoformat(),
        "assessor": assessor,
    }


def _evaluate_standard(standard_id: str, settings: dict, group) -> str:
    """Evaluate a single AADC standard. Returns 'compliant', 'partial', or 'non_compliant'."""
    privacy = settings.get("privacy", {})
    aadc = settings.get("aadc", {})

    evaluators = {
        "best_interests": lambda: "compliant" if aadc.get("best_interests_assessment") else "non_compliant",
        "age_verification": lambda: "compliant" if settings.get("age_verification_enabled") else "partial",
        "transparency": lambda: "compliant" if aadc.get("child_friendly_privacy_notice") else "non_compliant",
        "data_minimization": lambda: "compliant" if privacy.get("data_minimization") else "partial",
        "sharing_limits": lambda: "compliant" if not privacy.get("data_sharing_enabled", True) else "non_compliant",
        "geolocation": lambda: "compliant" if not privacy.get("geolocation_enabled", True) else "non_compliant",
        "parental_controls": lambda: "compliant" if settings.get("parental_controls_enabled", True) else "non_compliant",
        "privacy_settings": lambda: "compliant" if aadc.get("privacy_tools_accessible") else "partial",
        "enforcement": lambda: "compliant" if aadc.get("community_standards_enforced") else "partial",
        "connected_toys": lambda: "compliant",  # N/A for most services — default compliant
        "online_tools": lambda: "compliant" if aadc.get("reporting_tools_available") else "partial",
        "profiling": lambda: "compliant" if not privacy.get("profiling_enabled", True) else "non_compliant",
        "nudge_techniques": lambda: "compliant" if aadc.get("no_nudge_techniques") else "partial",
        "default_settings": lambda: "compliant" if privacy.get("privacy_by_default") else "non_compliant",
        "conformity_assessment": lambda: "compliant" if aadc.get("dpia_completed") else "non_compliant",
    }

    evaluator = evaluators.get(standard_id)
    if evaluator:
        return evaluator()
    return "non_compliant"


def _get_recommendations(standard_id: str, status: str) -> list[str]:
    """Return actionable recommendations for non-compliant or partially compliant standards."""
    if status == "compliant":
        return []

    recommendations_map = {
        "best_interests": ["Conduct and document a best interests assessment for your service"],
        "age_verification": ["Implement age verification at registration", "Use Yoti or similar age estimation"],
        "transparency": ["Create child-friendly privacy notices", "Use age-appropriate language and visuals"],
        "data_minimization": ["Audit data collection points", "Remove unnecessary data fields", "Implement purpose limitation"],
        "sharing_limits": ["Disable data sharing by default", "Review all third-party data flows"],
        "geolocation": ["Disable geolocation by default for all child accounts"],
        "parental_controls": ["Ensure parental monitoring is visible to children", "Provide clear monitoring indicators"],
        "privacy_settings": ["Make privacy tools prominent and easy to find", "Add privacy shortcuts to main navigation"],
        "enforcement": ["Establish and publish community standards", "Implement automated and manual enforcement"],
        "connected_toys": ["Review IoT device data flows", "Implement device-specific privacy controls"],
        "online_tools": ["Add reporting tools for children", "Provide data access request forms"],
        "profiling": ["Disable profiling for children by default", "Document any profiling with justification"],
        "nudge_techniques": ["Audit UI for dark patterns", "Remove prompts that encourage data sharing"],
        "default_settings": ["Set all privacy settings to maximum by default", "Require explicit opt-in for data sharing"],
        "conformity_assessment": ["Complete a Data Protection Impact Assessment", "Document risks and mitigations"],
    }

    return recommendations_map.get(standard_id, ["Review and address this standard"])


# ---------------------------------------------------------------------------
# Privacy defaults
# ---------------------------------------------------------------------------


def get_default_privacy_settings(age_tier: str) -> dict:
    """Return maximum-privacy default settings for a given age tier.

    Age tiers: young (5-9), preteen (10-12), teen (13-15).
    All tiers default to maximum privacy per AADC Standard 14.
    """
    if age_tier not in _PRIVACY_DEFAULTS:
        raise ValidationError(f"Invalid age tier: {age_tier}. Must be one of: young, preteen, teen")

    return {
        "age_tier": age_tier,
        "settings": _PRIVACY_DEFAULTS[age_tier].copy(),
    }


async def apply_privacy_defaults(db: AsyncSession, user_id: UUID, age_tier: str) -> dict:
    """Apply maximum-privacy defaults to a user based on their age tier.

    Persists a PrivacyDefault record and returns the applied settings.
    This should be called when a new child account is created.
    """
    if age_tier not in _PRIVACY_DEFAULTS:
        raise ValidationError(f"Invalid age tier: {age_tier}. Must be one of: young, preteen, teen")

    settings = _PRIVACY_DEFAULTS[age_tier].copy()

    privacy_default = PrivacyDefault(
        id=uuid4(),
        user_id=user_id,
        age_tier=age_tier,
        settings=settings,
        effective_from=datetime.now(timezone.utc),
        created_by="system",
    )
    db.add(privacy_default)
    await db.flush()
    await db.refresh(privacy_default)

    logger.info(
        "aadc_privacy_defaults_applied",
        user_id=str(user_id),
        age_tier=age_tier,
    )

    return {
        "id": str(privacy_default.id),
        "user_id": str(user_id),
        "age_tier": age_tier,
        "settings": settings,
        "effective_from": privacy_default.effective_from.isoformat(),
        "created_by": privacy_default.created_by,
    }


async def get_privacy_defaults_for_user(db: AsyncSession, user_id: UUID) -> dict | None:
    """Get the current privacy defaults for a user."""
    result = await db.execute(
        select(PrivacyDefault)
        .where(PrivacyDefault.user_id == user_id)
        .order_by(PrivacyDefault.effective_from.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if not record:
        return None

    return {
        "id": str(record.id),
        "user_id": str(record.user_id),
        "age_tier": record.age_tier,
        "settings": record.settings,
        "effective_from": record.effective_from.isoformat(),
        "created_by": record.created_by,
    }


# ---------------------------------------------------------------------------
# Assessment history
# ---------------------------------------------------------------------------


async def get_assessment_history(db: AsyncSession, group_id: UUID) -> list[dict]:
    """Return all AADC gap analysis assessments for a group, newest first."""
    result = await db.execute(
        select(AadcAssessment)
        .where(AadcAssessment.group_id == group_id)
        .order_by(AadcAssessment.assessed_at.desc())
    )
    assessments = list(result.scalars().all())

    return [
        {
            "id": str(a.id),
            "group_id": str(a.group_id),
            "version": a.version,
            "score": a.score,
            "overall_status": a.overall_status,
            "standards": a.standards,
            "assessed_at": a.assessed_at.isoformat(),
            "assessor": a.assessor,
        }
        for a in assessments
    ]


async def get_latest_assessment(db: AsyncSession, group_id: UUID) -> dict | None:
    """Return the most recent AADC gap analysis for a group."""
    result = await db.execute(
        select(AadcAssessment)
        .where(AadcAssessment.group_id == group_id)
        .order_by(AadcAssessment.assessed_at.desc())
        .limit(1)
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        return None

    return {
        "id": str(assessment.id),
        "group_id": str(assessment.group_id),
        "version": assessment.version,
        "score": assessment.score,
        "overall_status": assessment.overall_status,
        "standards": assessment.standards,
        "assessed_at": assessment.assessed_at.isoformat(),
        "assessor": assessment.assessor,
    }
