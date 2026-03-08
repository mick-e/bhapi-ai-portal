"""EU AI Act compliance service — algorithmic transparency, human review, appeals."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.compliance.eu_ai_act_models import AppealRecord, HumanReviewRequest
from src.exceptions import ForbiddenError, NotFoundError, ValidationError
from src.risk.models import RiskConfig, RiskEvent

logger = structlog.get_logger()


async def get_algorithmic_transparency(db: AsyncSession, group_id: UUID) -> dict:
    """Return explanation of risk classification algorithms, categories, thresholds.

    EU AI Act requires transparency about how automated decisions are made.
    """
    from src.risk.taxonomy import RISK_CATEGORIES

    # Load group risk configs
    result = await db.execute(
        select(RiskConfig).where(RiskConfig.group_id == group_id)
    )
    configs = {c.category: c for c in result.scalars().all()}

    categories = []
    for cat_name, cat_meta in RISK_CATEGORIES.items():
        config = configs.get(cat_name)
        categories.append({
            "category": cat_name,
            "description": cat_meta.get("description", cat_name),
            "severity_levels": ["critical", "high", "medium", "low"],
            "sensitivity": config.sensitivity if config else 50,
            "enabled": config.enabled if config else True,
            "classification_method": "keyword_matching_with_optional_ai",
            "human_review_available": True,
            "appeal_available": True,
        })

    return {
        "system_name": "Bhapi AI Safety Monitor",
        "system_version": "1.0.0",
        "classification_approach": (
            "Multi-layer pipeline: PII detection, safety keyword matching, "
            "configurable AI-assisted classification (Vertex AI/Gemini), "
            "and custom rules engine. Age-band sensitivity scaling applied."
        ),
        "data_sources": [
            "AI platform interaction content (prompts and responses)",
            "Session metadata (platform, timestamps, session IDs)",
        ],
        "decision_types": [
            "Risk classification (category + severity)",
            "Alert generation and routing",
            "Content flagging",
        ],
        "human_oversight": (
            "All automated classifications can be reviewed by a human administrator. "
            "Group members can submit appeals against any automated decision. "
            "Administrators can override classifications."
        ),
        "categories": categories,
        "right_to_explanation": True,
        "right_to_human_review": True,
        "right_to_appeal": True,
    }


async def request_human_review(
    db: AsyncSession, risk_event_id: UUID, user_id: UUID, group_id: UUID
) -> HumanReviewRequest:
    """Request human review of an automated risk classification."""
    # Verify the risk event exists and belongs to the group
    result = await db.execute(
        select(RiskEvent).where(
            RiskEvent.id == risk_event_id,
            RiskEvent.group_id == group_id,
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("RiskEvent", str(risk_event_id))

    # Check for existing pending review
    existing = await db.execute(
        select(HumanReviewRequest).where(
            HumanReviewRequest.risk_event_id == risk_event_id,
            HumanReviewRequest.status.in_(["pending", "in_review"]),
        )
    )
    if existing.scalar_one_or_none():
        raise ValidationError("A human review is already pending for this risk event")

    review = HumanReviewRequest(
        id=uuid4(),
        risk_event_id=risk_event_id,
        group_id=group_id,
        requested_by=user_id,
        status="pending",
    )
    db.add(review)
    await db.flush()
    await db.refresh(review)

    logger.info("human_review_requested", risk_event_id=str(risk_event_id), user_id=str(user_id))
    return review


async def submit_appeal(
    db: AsyncSession, risk_event_id: UUID, user_id: UUID, group_id: UUID, reason: str
) -> AppealRecord:
    """Submit an appeal against an automated risk classification."""
    result = await db.execute(
        select(RiskEvent).where(
            RiskEvent.id == risk_event_id,
            RiskEvent.group_id == group_id,
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("RiskEvent", str(risk_event_id))

    # Check for existing pending appeal
    existing = await db.execute(
        select(AppealRecord).where(
            AppealRecord.risk_event_id == risk_event_id,
            AppealRecord.user_id == user_id,
            AppealRecord.status.in_(["pending", "under_review"]),
        )
    )
    if existing.scalar_one_or_none():
        raise ValidationError("You already have a pending appeal for this risk event")

    appeal = AppealRecord(
        id=uuid4(),
        risk_event_id=risk_event_id,
        group_id=group_id,
        user_id=user_id,
        reason=reason,
        status="pending",
    )
    db.add(appeal)
    await db.flush()
    await db.refresh(appeal)

    logger.info("appeal_submitted", risk_event_id=str(risk_event_id), user_id=str(user_id))
    return appeal


async def list_appeals(
    db: AsyncSession, group_id: UUID, status: str | None = None,
    limit: int = 50, offset: int = 0
) -> tuple[list[AppealRecord], int]:
    """List appeals for a group."""
    from sqlalchemy import func

    query = select(AppealRecord).where(AppealRecord.group_id == group_id)
    count_q = select(func.count(AppealRecord.id)).where(AppealRecord.group_id == group_id)

    if status:
        query = query.where(AppealRecord.status == status)
        count_q = count_q.where(AppealRecord.status == status)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        query.order_by(AppealRecord.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total


async def resolve_appeal(
    db: AsyncSession, appeal_id: UUID, reviewer_id: UUID,
    resolution: str, notes: str | None = None
) -> AppealRecord:
    """Resolve an appeal (admin action)."""
    result = await db.execute(
        select(AppealRecord).where(AppealRecord.id == appeal_id)
    )
    appeal = result.scalar_one_or_none()
    if not appeal:
        raise NotFoundError("Appeal", str(appeal_id))

    if appeal.status == "resolved":
        raise ValidationError("Appeal is already resolved")

    valid_resolutions = {"upheld", "overturned", "modified"}
    if resolution not in valid_resolutions:
        raise ValidationError(f"Resolution must be one of: {valid_resolutions}")

    appeal.status = "resolved"
    appeal.resolved_by = reviewer_id
    appeal.resolution = resolution
    appeal.resolution_notes = notes
    appeal.resolved_at = datetime.now(timezone.utc)

    # If overturned, acknowledge the risk event
    if resolution == "overturned":
        risk_result = await db.execute(
            select(RiskEvent).where(RiskEvent.id == appeal.risk_event_id)
        )
        risk_event = risk_result.scalar_one_or_none()
        if risk_event and not risk_event.acknowledged:
            risk_event.acknowledged = True
            risk_event.acknowledged_by = reviewer_id
            risk_event.acknowledged_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(appeal)

    logger.info("appeal_resolved", appeal_id=str(appeal_id), resolution=resolution)
    return appeal
