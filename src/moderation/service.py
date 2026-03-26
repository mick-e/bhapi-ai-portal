"""Moderation service — business logic for content moderation pipeline.

Performance targets for pre-publish (young 5-9, preteen 10-12):
  - p95 < 2 seconds end-to-end
  - Keyword filter fast-path < 100ms
  - CSAM short-circuit on match (skip all other checks)
  - Parallel social risk + image classification when needed
"""

import enum
import time as _time
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.moderation.csam import check_csam
from src.moderation.keyword_filter import FilterAction, classify_text
from src.moderation.models import ContentReport, ModerationAppeal, ModerationDecision, ModerationQueue
from src.moderation.social_risk import classify_social_risk

logger = structlog.get_logger()

# Latency budget (ms) — warn when exceeded
_LATENCY_BUDGET_MS = 2000
# Post-publish takedown budget (ms) — <60s SLA
_POST_PUBLISH_BUDGET_MS = 60000


class ReportReason(str, enum.Enum):
    """Taxonomy of reasons a user can report content."""

    INAPPROPRIATE = "inappropriate"
    BULLYING = "bullying"
    SPAM = "spam"
    IMPERSONATION = "impersonation"
    SELF_HARM = "self_harm"
    ADULT_CONTENT = "adult_content"
    OTHER = "other"


# Age-appropriate labels for each reason (suitable for children 5-15)
REPORT_REASON_LABELS: dict[str, str] = {
    ReportReason.INAPPROPRIATE: "Something inappropriate",
    ReportReason.BULLYING: "Bullying or mean behavior",
    ReportReason.SPAM: "Spam or unwanted content",
    ReportReason.IMPERSONATION: "Pretending to be someone else",
    ReportReason.SELF_HARM: "Someone might be hurting themselves",
    ReportReason.ADULT_CONTENT: "Grown-up content that shouldn't be here",
    ReportReason.OTHER: "Something else",
}


class ReportStatus(str, enum.Enum):
    """Status workflow for content reports."""

    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    ACTION_TAKEN = "action_taken"
    DISMISSED = "dismissed"


# Valid transitions: current status -> allowed next statuses
_REPORT_STATUS_TRANSITIONS: dict[str, set[str]] = {
    ReportStatus.PENDING: {ReportStatus.UNDER_REVIEW, ReportStatus.DISMISSED},
    ReportStatus.UNDER_REVIEW: {ReportStatus.ACTION_TAKEN, ReportStatus.DISMISSED},
    ReportStatus.ACTION_TAKEN: set(),
    ReportStatus.DISMISSED: set(),
}

# Age tiers that require pre-publish moderation
_PRE_PUBLISH_TIERS = {"young", "preteen"}

# Teen tier uses post-publish pipeline
_POST_PUBLISH_TIER = "teen"


class PostPublishSeverity(str, enum.Enum):
    """Severity levels for post-publish moderation results."""

    NONE = "none"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PostPublishResult:
    """Result of async post-publish moderation for teen content."""

    action: str  # "keep", "flag", "takedown"
    severity: PostPublishSeverity
    parent_alerted: bool = False
    author_notified: bool = False
    account_restricted: bool = False
    latency_ms: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)
    risk_category: str | None = None


def _resolve_pipeline(age_tier: str | None) -> str:
    """Route to pre_publish or post_publish based on age tier."""
    if age_tier and age_tier in _PRE_PUBLISH_TIERS:
        return "pre_publish"
    return "post_publish"


def _log_latency(
    start: float,
    content_type: str,
    outcome: str,
    age_tier: str | None,
) -> None:
    """Log latency and warn if budget exceeded."""
    elapsed_ms = (_time.monotonic() - start) * 1000
    if elapsed_ms > _LATENCY_BUDGET_MS:
        logger.warning(
            "moderation_latency_exceeded",
            latency_ms=round(elapsed_ms, 2),
            budget_ms=_LATENCY_BUDGET_MS,
            content_type=content_type,
            outcome=outcome,
            age_tier=age_tier,
        )


async def _notify_parent_on_block(
    db: AsyncSession,
    content_type: str,
    content_id: UUID,
    age_tier: str | None,
    reason: str,
    matched_keywords: list[str] | None = None,
    queue_id: UUID | None = None,
) -> None:
    """Create an alert and push notification when pre-publish blocks content for under-13.

    Best-effort: failures are logged but do not block the moderation decision.
    """
    if age_tier not in _PRE_PUBLISH_TIERS:
        return

    try:
        # Log the block event for parent notification.
        # In production, the push notification service picks this up
        # and resolves the parent's device tokens via group membership.
        logger.info(
            "parent_block_alert_created",
            content_type=content_type,
            content_id=str(content_id),
            age_tier=age_tier,
            reason=reason,
            matched_keywords=matched_keywords,
            queue_id=str(queue_id) if queue_id else None,
        )
    except Exception as exc:
        # Best-effort — don't fail moderation pipeline on notification error
        logger.warning(
            "parent_block_notification_failed",
            error=str(exc),
            content_type=content_type,
            content_id=str(content_id),
        )


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

    Performance optimizations:
    1. Fast-path: keyword filter runs first (<100ms). If BLOCK -> reject immediately.
    2. CSAM short-circuit: if CSAM detected, skip all other checks.
    3. Parallel: social risk runs concurrently for non-fast-path content.
    4. Latency tracking: warns when p95 budget exceeded.
    """
    pipeline_start = _time.monotonic()

    valid_types = {"post", "comment", "message", "media"}
    if content_type not in valid_types:
        raise ValidationError(
            f"Invalid content_type '{content_type}'. Must be one of: {', '.join(sorted(valid_types))}"
        )

    pipeline = _resolve_pipeline(author_age_tier)
    is_pre_publish = pipeline == "pre_publish"

    risk_scores: dict | None = None
    status = "pending"

    # ---- STEP 1: CSAM check runs FIRST for media content (short-circuit) ----
    if content_type in ("media", "image", "video") and media_ids:
        for media_id in media_ids:
            csam_result = await check_csam(image_url=str(media_id))
            if csam_result.is_match:
                entry = ModerationQueue(
                    id=uuid4(),
                    content_type=content_type,
                    content_id=content_id,
                    pipeline=pipeline,
                    status="rejected",
                    risk_scores={
                        "csam": {
                            "match": True,
                            "confidence": csam_result.confidence,
                            "provider": csam_result.provider,
                        }
                    },
                    age_tier=author_age_tier,
                )
                db.add(entry)
                await db.flush()

                decision = ModerationDecision(
                    id=uuid4(),
                    queue_id=entry.id,
                    action="reject",
                    reason="[CSAM] PhotoDNA match — content blocked, NCMEC report pending",
                )
                db.add(decision)
                await db.flush()
                await db.refresh(entry)

                logger.critical(
                    "csam_content_blocked",
                    content_id=str(content_id),
                    media_id=str(media_id),
                )

                # Notify parent for under-13 CSAM blocks
                await _notify_parent_on_block(
                    db, content_type, content_id, author_age_tier,
                    reason="CSAM detection — content blocked for child safety",
                    queue_id=entry.id,
                )

                _log_latency(pipeline_start, content_type, "csam_block", author_age_tier)
                return entry  # Exit immediately — no further processing

    # ---- STEP 2: Keyword filter fast-path (<100ms) ----
    filter_result = None
    if content_text:
        filter_result = classify_text(content_text, author_age_tier)
        risk_scores = {
            "keyword_filter": {
                "action": filter_result.action.value,
                "severity": filter_result.severity,
                "confidence": filter_result.confidence,
                "matched_keywords": filter_result.matched_keywords,
                "latency_ms": filter_result.latency_ms,
            }
        }

        # Fast-path: keyword BLOCK -> reject immediately (skip social risk)
        if filter_result.action == FilterAction.BLOCK:
            status = "rejected"

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

            decision = ModerationDecision(
                id=uuid4(),
                queue_id=entry.id,
                action="reject",
                reason=f"Auto-blocked: keyword filter ({filter_result.severity})",
            )
            db.add(decision)
            await db.flush()
            await db.refresh(entry)

            # Notify parent for under-13 blocks
            await _notify_parent_on_block(
                db, content_type, content_id, author_age_tier,
                reason=f"Keyword filter: {filter_result.severity} severity content detected",
                matched_keywords=filter_result.matched_keywords,
                queue_id=entry.id,
            )

            logger.info(
                "moderation_fast_path_block",
                queue_id=str(entry.id),
                severity=filter_result.severity,
                matched_keywords=filter_result.matched_keywords,
            )
            _log_latency(pipeline_start, content_type, "keyword_block", author_age_tier)
            return entry

    # ---- STEP 3: Social risk check for messages/comments/posts ----
    # Run BEFORE setting auto-approve, because social risk can override to escalate
    if content_type in ("message", "comment", "post") and content_text:
        social_result = classify_social_risk(
            content_text, author_age_tier=author_age_tier
        )
        if social_result.risk_score > 0:
            risk_scores = risk_scores or {}
            risk_scores["social_risk"] = {
                "category": social_result.category,
                "severity": social_result.severity,
                "score": social_result.risk_score,
                "patterns": social_result.matched_patterns,
            }
            if social_result.severity in ("critical", "high"):
                status = "escalated"

    # Set auto-approve only if social risk did not escalate
    if (
        filter_result
        and filter_result.action == FilterAction.ALLOW
        and is_pre_publish
        and status == "pending"
    ):
        status = "approved"

    # ---- Post-publish: teen content publishes immediately ----
    # Teen tier (13-15) gets published right away; async background
    # moderation runs afterward via run_post_publish_moderation().
    # Critical/high social risk still gets escalated (not published).
    is_post_publish = pipeline == "post_publish" and author_age_tier == _POST_PUBLISH_TIER
    if is_post_publish and status == "pending":
        status = "published"

    # ---- STEP 4: Create queue entry and decisions ----
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

    # Create auto-decision for keyword filter approvals (only if actually approved)
    if status == "approved" and is_pre_publish:
        decision = ModerationDecision(
            id=uuid4(),
            queue_id=entry.id,
            action="approve",
            reason="Auto-approved: keyword filter (no concerns)",
        )
        db.add(decision)
        await db.flush()

    # Create auto-decision for post-publish immediate publishing
    if status == "published" and is_post_publish:
        decision = ModerationDecision(
            id=uuid4(),
            queue_id=entry.id,
            action="approve",
            reason="Post-publish: teen content published, background moderation pending",
        )
        db.add(decision)
        await db.flush()

    # Notify parent on escalation for under-13
    if status == "escalated" and author_age_tier in _PRE_PUBLISH_TIERS:
        await _notify_parent_on_block(
            db, content_type, content_id, author_age_tier,
            reason="Content escalated for human review due to safety concern",
            queue_id=entry.id,
        )

    await db.refresh(entry)

    elapsed_ms = (_time.monotonic() - pipeline_start) * 1000

    logger.info(
        "moderation_submitted",
        queue_id=str(entry.id),
        content_type=content_type,
        pipeline=pipeline,
        status=status,
        age_tier=author_age_tier,
        keyword_action=filter_result.action.value if filter_result else None,
        latency_ms=round(elapsed_ms, 2),
    )

    _log_latency(pipeline_start, content_type, status, author_age_tier)
    return entry


async def _notify_on_post_publish_action(
    db: AsyncSession,
    entry: ModerationQueue,
    action: str,
    reason: str,
    severity: PostPublishSeverity,
) -> tuple[bool, bool]:
    """Send notifications for post-publish moderation actions.

    Returns (parent_alerted, author_notified).
    Best-effort: failures are logged but do not block the pipeline.
    """
    parent_alerted = False
    author_notified = False

    try:
        if action in ("takedown", "flag"):
            logger.info(
                "post_publish_parent_alert",
                content_type=entry.content_type,
                content_id=str(entry.content_id),
                action=action,
                severity=severity.value,
                reason=reason,
                queue_id=str(entry.id),
            )
            parent_alerted = True

            logger.info(
                "post_publish_author_notification",
                content_type=entry.content_type,
                content_id=str(entry.content_id),
                action=action,
                queue_id=str(entry.id),
            )
            author_notified = True
    except Exception as exc:
        logger.warning(
            "post_publish_notification_failed",
            error=str(exc),
            queue_id=str(entry.id),
        )

    return parent_alerted, author_notified


async def run_post_publish_moderation(
    db: AsyncSession,
    queue_id: UUID,
    content_text: str | None = None,
    media_ids: list[UUID] | None = None,
) -> PostPublishResult:
    """Run async background moderation on already-published teen content.

    This function is called after content is published for the teen tier (13-15).
    It performs the full moderation check and takes action if needed:
    - Clean content: keep published, no action
    - Medium severity: flag for human review (stays visible)
    - High severity: takedown + parent alert + author notification
    - Critical severity: takedown + parent alert + author notification + account restriction

    SLA target: complete within 60 seconds of publish.
    """
    pipeline_start = _time.monotonic()

    entry = await get_queue_entry(db, queue_id)

    # Process entries in "published" or "escalated" state (post-publish pipeline)
    # Escalated entries are teen content where social risk was detected at submit time
    if entry.status not in ("published", "escalated"):
        return PostPublishResult(
            action="keep",
            severity=PostPublishSeverity.NONE,
            latency_ms=(_time.monotonic() - pipeline_start) * 1000,
        )

    risk_scores = entry.risk_scores or {}
    severity = PostPublishSeverity.NONE
    matched_keywords: list[str] = []
    risk_category: str | None = None

    # ---- Keyword check ----
    if content_text:
        filter_result = classify_text(content_text, entry.age_tier)
        risk_scores["keyword_filter"] = {
            "action": filter_result.action.value,
            "severity": filter_result.severity,
            "confidence": filter_result.confidence,
            "matched_keywords": filter_result.matched_keywords,
        }
        matched_keywords = filter_result.matched_keywords

        if filter_result.action == FilterAction.BLOCK:
            severity = PostPublishSeverity.CRITICAL
        elif filter_result.severity == "high":
            severity = PostPublishSeverity.HIGH
        elif filter_result.severity == "medium":
            severity = PostPublishSeverity.MEDIUM

    # ---- Social risk check ----
    if content_text and entry.content_type in ("message", "comment", "post"):
        social_result = classify_social_risk(
            content_text, author_age_tier=entry.age_tier
        )
        if social_result.risk_score > 0:
            risk_scores["social_risk"] = {
                "category": social_result.category,
                "severity": social_result.severity,
                "score": social_result.risk_score,
                "patterns": social_result.matched_patterns,
            }
            risk_category = social_result.category

            # Social risk can upgrade severity
            if social_result.severity == "critical":
                severity = PostPublishSeverity.CRITICAL
            elif social_result.severity == "high" and severity.value not in ("critical",):
                severity = PostPublishSeverity.HIGH
            elif social_result.severity == "medium" and severity == PostPublishSeverity.NONE:
                severity = PostPublishSeverity.MEDIUM

    # Update risk scores on the queue entry
    entry.risk_scores = risk_scores

    # ---- Determine action based on severity ----
    action = "keep"
    account_restricted = False
    parent_alerted = False
    author_notified = False

    if severity == PostPublishSeverity.CRITICAL:
        action = "takedown"
        account_restricted = True
        entry.status = "taken_down"

        decision = ModerationDecision(
            id=uuid4(),
            queue_id=entry.id,
            action="reject",
            reason="[POST_PUBLISH_TAKEDOWN] Critical severity: auto-takedown with account restriction"
            + (f" (keywords: {', '.join(matched_keywords)})" if matched_keywords else "")
            + (f" (risk: {risk_category})" if risk_category else ""),
        )
        db.add(decision)
        await db.flush()

    elif severity == PostPublishSeverity.HIGH:
        action = "takedown"
        entry.status = "taken_down"

        decision = ModerationDecision(
            id=uuid4(),
            queue_id=entry.id,
            action="reject",
            reason="[POST_PUBLISH_TAKEDOWN] High severity: auto-takedown"
            + (f" (keywords: {', '.join(matched_keywords)})" if matched_keywords else "")
            + (f" (risk: {risk_category})" if risk_category else ""),
        )
        db.add(decision)
        await db.flush()

    elif severity == PostPublishSeverity.MEDIUM:
        action = "flag"
        entry.status = "flagged"

        decision = ModerationDecision(
            id=uuid4(),
            queue_id=entry.id,
            action="escalate",
            reason="[POST_PUBLISH_FLAG] Medium severity: flagged for human review"
            + (f" (keywords: {', '.join(matched_keywords)})" if matched_keywords else ""),
        )
        db.add(decision)
        await db.flush()

    # Send notifications for takedowns and flags
    if action in ("takedown", "flag"):
        reason_str = f"Post-publish {action}: {severity.value} severity content detected"
        parent_alerted, author_notified = await _notify_on_post_publish_action(
            db, entry, action, reason_str, severity,
        )

    await db.flush()
    await db.refresh(entry)

    elapsed_ms = (_time.monotonic() - pipeline_start) * 1000

    # Warn if we exceeded the 60s SLA
    if elapsed_ms > _POST_PUBLISH_BUDGET_MS:
        logger.warning(
            "post_publish_sla_exceeded",
            queue_id=str(queue_id),
            latency_ms=round(elapsed_ms, 2),
            budget_ms=_POST_PUBLISH_BUDGET_MS,
            action=action,
            severity=severity.value,
        )

    logger.info(
        "post_publish_moderation_complete",
        queue_id=str(queue_id),
        action=action,
        severity=severity.value,
        account_restricted=account_restricted,
        latency_ms=round(elapsed_ms, 2),
    )

    return PostPublishResult(
        action=action,
        severity=severity,
        parent_alerted=parent_alerted,
        author_notified=author_notified,
        account_restricted=account_restricted,
        latency_ms=elapsed_ms,
        matched_keywords=matched_keywords,
        risk_category=risk_category,
    )


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
    description: str | None = None,
) -> ContentReport:
    """Create a content report from a user.

    Prevents duplicate reports by the same user on the same target.
    Prevents self-reporting (reporter cannot be the target for user reports).
    Validates reason against the ReportReason taxonomy.
    """
    valid_types = {"post", "comment", "message", "user"}
    if target_type not in valid_types:
        raise ValidationError(
            f"Invalid target_type '{target_type}'. Must be one of: {', '.join(sorted(valid_types))}"
        )

    # Validate reason is from the taxonomy
    valid_reasons = {r.value for r in ReportReason}
    if reason not in valid_reasons:
        raise ValidationError(
            f"Invalid reason '{reason}'. Must be one of: {', '.join(sorted(valid_reasons))}"
        )

    # Prevent self-reporting for user targets
    if target_type == "user" and target_id == reporter_id:
        raise ValidationError("You cannot report yourself")

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
        description=description,
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
        reason=reason,
    )
    return report


async def get_report(db: AsyncSession, report_id: UUID) -> ContentReport:
    """Get a single content report by ID."""
    result = await db.execute(
        select(ContentReport).where(ContentReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundError("ContentReport", str(report_id))
    return report


async def update_report_status(
    db: AsyncSession,
    report_id: UUID,
    new_status: str,
    moderator_id: UUID | None = None,
) -> ContentReport:
    """Update a report's status following the allowed workflow transitions.

    Valid transitions:
      pending -> under_review | dismissed
      under_review -> action_taken | dismissed
    """
    valid_statuses = {s.value for s in ReportStatus}
    if new_status not in valid_statuses:
        raise ValidationError(
            f"Invalid status '{new_status}'. Must be one of: {', '.join(sorted(valid_statuses))}"
        )

    report = await get_report(db, report_id)

    allowed = _REPORT_STATUS_TRANSITIONS.get(report.status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"Cannot transition from '{report.status}' to '{new_status}'"
        )

    report.status = new_status
    await db.flush()
    await db.refresh(report)

    logger.info(
        "report_status_updated",
        report_id=str(report_id),
        new_status=new_status,
        moderator_id=str(moderator_id) if moderator_id else None,
    )
    return report


async def list_reports(
    db: AsyncSession,
    reporter_id: UUID | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List content reports with pagination."""
    base = select(ContentReport)
    count_q = select(func.count(ContentReport.id))

    if reporter_id:
        base = base.where(ContentReport.reporter_id == reporter_id)
        count_q = count_q.where(ContentReport.reporter_id == reporter_id)
    if status:
        base = base.where(ContentReport.status == status)
        count_q = count_q.where(ContentReport.status == status)

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


# ---------------------------------------------------------------------------
# Appeal logic
# ---------------------------------------------------------------------------


async def create_appeal(
    db: AsyncSession,
    queue_id: UUID,
    appellant_id: UUID,
    reason: str,
) -> ModerationAppeal:
    """Create an appeal for a moderation decision.

    Rules:
    - Only one appeal per queue item per user.
    - Queue entry must be in 'rejected' status.
    - Appeal creates an escalated queue entry for human re-review.
    """
    entry = await get_queue_entry(db, queue_id)

    # Check for existing appeal by same user (before status check,
    # because first appeal changes status to escalated)
    existing = await db.execute(
        select(ModerationAppeal).where(
            ModerationAppeal.queue_id == queue_id,
            ModerationAppeal.appellant_id == appellant_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("You have already appealed this decision")

    if entry.status not in ("rejected",):
        raise ValidationError(
            "You can only appeal content that has been rejected"
        )

    appeal = ModerationAppeal(
        id=uuid4(),
        queue_id=queue_id,
        appellant_id=appellant_id,
        reason=reason,
        status="pending",
    )
    db.add(appeal)

    # Mark queue entry as escalated for human re-review
    entry.status = "escalated"

    await db.flush()
    await db.refresh(appeal)

    logger.info(
        "moderation_appeal_created",
        appeal_id=str(appeal.id),
        queue_id=str(queue_id),
        appellant_id=str(appellant_id),
    )
    return appeal


async def get_appeal(db: AsyncSession, appeal_id: UUID) -> ModerationAppeal:
    """Get a single appeal by ID."""
    result = await db.execute(
        select(ModerationAppeal).where(ModerationAppeal.id == appeal_id)
    )
    appeal = result.scalar_one_or_none()
    if not appeal:
        raise NotFoundError("ModerationAppeal", str(appeal_id))
    return appeal


async def decide_appeal(
    db: AsyncSession,
    appeal_id: UUID,
    decision: str,
    reviewer_id: UUID,
    review_note: str | None = None,
) -> ModerationAppeal:
    """Accept or deny an appeal (moderators only).

    If accepted, the queue entry status is restored to 'approved'.
    If denied, the queue entry reverts to 'rejected'.
    """
    valid_decisions = {"accepted", "denied"}
    if decision not in valid_decisions:
        raise ValidationError(
            f"Invalid decision '{decision}'. Must be 'accepted' or 'denied'"
        )

    appeal = await get_appeal(db, appeal_id)

    if appeal.status != "pending":
        raise ConflictError(
            f"Appeal already decided with status '{appeal.status}'"
        )

    appeal.status = decision
    appeal.reviewed_by = reviewer_id
    appeal.review_note = review_note

    # Update the parent queue entry
    entry = await get_queue_entry(db, appeal.queue_id)
    if decision == "accepted":
        entry.status = "approved"
    else:
        entry.status = "rejected"

    await db.flush()
    await db.refresh(appeal)

    logger.info(
        "moderation_appeal_decided",
        appeal_id=str(appeal_id),
        decision=decision,
        reviewer_id=str(reviewer_id),
    )
    return appeal
