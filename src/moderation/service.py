"""Moderation service — business logic for content moderation pipeline."""

from datetime import datetime, time, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.moderation.keyword_filter import FilterAction, classify_text
from src.moderation.models import ContentReport, ModerationDecision, ModerationQueue

logger = structlog.get_logger()

# Age tiers that require pre-publish moderation
_PRE_PUBLISH_TIERS = {"young", "preteen"}


def _resolve_pipeline(age_tier: str | None) -> str:
    """Route to pre_publish or post_publish based on age tier."""
    if age_tier and age_tier in _PRE_PUBLISH_TIERS:
        return "pre_publish"
    return "post_publish"


async def submit_for_moderation(
    db: AsyncSession,
    content_type: str,
    content_id: UUID,
    author_age_tier: str | None = None,
    content_text: str | None = None,
    media_ids: list[UUID] | None = None,
) -> ModerationQueue:
    """Submit content for moderation.

    Routes to pre_publish or post_publish pipeline based on the author's
    age tier. Young (5-9) and preteen (10-12) go through pre-publish;
    teen (13-15) goes through post-publish.
    """
    valid_types = {"post", "comment", "message", "media"}
    if content_type not in valid_types:
        raise ValidationError(
            f"Invalid content_type '{content_type}'. Must be one of: {', '.join(sorted(valid_types))}"
        )

    pipeline = _resolve_pipeline(author_age_tier)

    risk_scores: dict | None = None
    status = "pending"

    # Run keyword filter on text content
    filter_result = None
    if content_text:
        filter_result = classify_text(content_text, author_age_tier)
        risk_scores = {
            "keyword_filter": {
                "action": filter_result.action.value,
                "severity": filter_result.severity,
                "confidence": filter_result.confidence,
                "matched_keywords": filter_result.matched_keywords,
            }
        }

        if filter_result.action == FilterAction.BLOCK:
            status = "rejected"
        elif (
            filter_result.action == FilterAction.ALLOW
            and pipeline == "pre_publish"
        ):
            status = "approved"
        # UNCERTAIN: stays as "pending" for AI/human review

    entry = ModerationQueue(
        id=uuid4(),
        content_type=content_type,
        content_id=content_id,
        pipeline=pipeline,
        status=status,
        risk_scores=risk_scores,
        age_tier=author_age_tier,
    )
    db.add(entry)
    await db.flush()

    # Create auto-decision for keyword filter blocks/approvals
    if filter_result and filter_result.action == FilterAction.BLOCK:
        decision = ModerationDecision(
            id=uuid4(),
            queue_id=entry.id,
            action="reject",
            reason=f"Auto-blocked: keyword filter ({filter_result.severity})",
        )
        db.add(decision)
        await db.flush()
    elif (
        filter_result
        and filter_result.action == FilterAction.ALLOW
        and pipeline == "pre_publish"
    ):
        decision = ModerationDecision(
            id=uuid4(),
            queue_id=entry.id,
            action="approve",
            reason="Auto-approved: keyword filter (no concerns)",
        )
        db.add(decision)
        await db.flush()

    await db.refresh(entry)

    logger.info(
        "moderation_submitted",
        queue_id=str(entry.id),
        content_type=content_type,
        pipeline=pipeline,
        status=status,
        age_tier=author_age_tier,
        keyword_action=filter_result.action.value if filter_result else None,
    )
    return entry


async def get_queue_entry(db: AsyncSession, queue_id: UUID) -> ModerationQueue:
    """Get a single queue entry by ID."""
    result = await db.execute(
        select(ModerationQueue).where(ModerationQueue.id == queue_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise NotFoundError("ModerationQueue", str(queue_id))
    return entry


async def process_queue_entry(
    db: AsyncSession,
    queue_id: UUID,
    action: str,
    moderator_id: UUID | None = None,
    reason: str | None = None,
) -> ModerationDecision:
    """Process a queue entry: approve, reject, or escalate.

    Creates a ModerationDecision record and updates the queue entry status.
    """
    valid_actions = {"approve", "reject", "escalate"}
    if action not in valid_actions:
        raise ValidationError(
            f"Invalid action '{action}'. Must be one of: {', '.join(sorted(valid_actions))}"
        )

    entry = await get_queue_entry(db, queue_id)

    if entry.status in ("approved", "rejected"):
        raise ConflictError(
            f"Queue entry already processed with status '{entry.status}'"
        )

    # Map action to queue status
    status_map = {
        "approve": "approved",
        "reject": "rejected",
        "escalate": "escalated",
    }
    entry.status = status_map[action]

    decision = ModerationDecision(
        id=uuid4(),
        queue_id=queue_id,
        moderator_id=moderator_id,
        action=action,
        reason=reason,
    )
    db.add(decision)
    await db.flush()
    await db.refresh(entry)
    await db.refresh(decision)

    logger.info(
        "moderation_decided",
        queue_id=str(queue_id),
        action=action,
        moderator_id=str(moderator_id) if moderator_id else None,
    )
    return decision


async def takedown_content(
    db: AsyncSession,
    content_type: str,
    content_id: UUID,
    reason: str,
    moderator_id: UUID | None = None,
) -> ModerationDecision:
    """Emergency takedown — mark content as removed.

    Creates a queue entry (if none exists) and a reject decision.
    """
    valid_types = {"post", "comment", "message", "media"}
    if content_type not in valid_types:
        raise ValidationError(
            f"Invalid content_type '{content_type}'. Must be one of: {', '.join(sorted(valid_types))}"
        )

    # Find or create a queue entry for this content
    result = await db.execute(
        select(ModerationQueue).where(
            ModerationQueue.content_type == content_type,
            ModerationQueue.content_id == content_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        entry = ModerationQueue(
            id=uuid4(),
            content_type=content_type,
            content_id=content_id,
            pipeline="takedown",
            status="rejected",
        )
        db.add(entry)
        await db.flush()
    else:
        entry.status = "rejected"

    decision = ModerationDecision(
        id=uuid4(),
        queue_id=entry.id,
        moderator_id=moderator_id,
        action="reject",
        reason=f"[TAKEDOWN] {reason}",
    )
    db.add(decision)
    await db.flush()
    await db.refresh(decision)

    logger.info(
        "content_takedown",
        content_type=content_type,
        content_id=str(content_id),
        moderator_id=str(moderator_id) if moderator_id else None,
    )
    return decision


async def list_queue(
    db: AsyncSession,
    status: str | None = None,
    pipeline: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List moderation queue entries with pagination and optional filters."""
    base = select(ModerationQueue)
    count_q = select(func.count(ModerationQueue.id))

    if status:
        base = base.where(ModerationQueue.status == status)
        count_q = count_q.where(ModerationQueue.status == status)
    if pipeline:
        base = base.where(ModerationQueue.pipeline == pipeline)
        count_q = count_q.where(ModerationQueue.pipeline == pipeline)

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size

    rows = await db.execute(
        base.order_by(ModerationQueue.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(rows.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_dashboard_stats(db: AsyncSession) -> dict:
    """Get moderation dashboard statistics."""
    # Pending count
    pending_count = (
        await db.execute(
            select(func.count(ModerationQueue.id)).where(
                ModerationQueue.status == "pending"
            )
        )
    ).scalar() or 0

    # Processed today
    today_start = datetime.combine(
        datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc
    )
    total_processed_today = (
        await db.execute(
            select(func.count(ModerationDecision.id)).where(
                ModerationDecision.timestamp >= today_start
            )
        )
    ).scalar() or 0

    # Severity breakdown by status
    status_rows = await db.execute(
        select(ModerationQueue.status, func.count(ModerationQueue.id)).group_by(
            ModerationQueue.status
        )
    )
    severity_breakdown = {row[0]: row[1] for row in status_rows.all()}

    return {
        "pending_count": pending_count,
        "total_processed_today": total_processed_today,
        "avg_processing_time_ms": 0.0,  # Placeholder — requires timestamp diff
        "severity_breakdown": severity_breakdown,
    }


async def create_content_report(
    db: AsyncSession,
    reporter_id: UUID,
    target_type: str,
    target_id: UUID,
    reason: str,
) -> ContentReport:
    """Create a content report from a user.

    Prevents duplicate reports by the same user on the same target.
    """
    valid_types = {"post", "comment", "message", "user"}
    if target_type not in valid_types:
        raise ValidationError(
            f"Invalid target_type '{target_type}'. Must be one of: {', '.join(sorted(valid_types))}"
        )

    # Check for duplicate
    existing = await db.execute(
        select(ContentReport).where(
            ContentReport.reporter_id == reporter_id,
            ContentReport.target_type == target_type,
            ContentReport.target_id == target_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("You have already reported this content")

    report = ContentReport(
        id=uuid4(),
        reporter_id=reporter_id,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        status="pending",
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    logger.info(
        "content_report_created",
        report_id=str(report.id),
        target_type=target_type,
        target_id=str(target_id),
    )
    return report


async def list_reports(
    db: AsyncSession,
    reporter_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List content reports with pagination."""
    base = select(ContentReport)
    count_q = select(func.count(ContentReport.id))

    if reporter_id:
        base = base.where(ContentReport.reporter_id == reporter_id)
        count_q = count_q.where(ContentReport.reporter_id == reporter_id)

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size

    rows = await db.execute(
        base.order_by(ContentReport.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = list(rows.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
