"""Moderation dashboard service — queue assignment, bulk actions, SLA, patterns.

Provides moderator-facing tools for efficient content moderation at scale:
- Queue assignment: assign/reassign moderators to queue items
- Bulk actions: approve/reject multiple items in one operation
- SLA metrics: track p95 latency and breach rates per pipeline
- Pattern detection: surface trending keywords, repeat offenders, surges
"""

import time as _time
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.moderation.models import (
    ModerationDecision,
    ModerationQueue,
    ModeratorAssignment,
    PatternDetection,
    SLAMetric,
)

logger = structlog.get_logger()

# SLA targets (ms)
_PRE_PUBLISH_SLA_MS = 2000   # <2s for pre-publish (under-13)
_POST_PUBLISH_SLA_MS = 60000  # <60s for post-publish (13-15)

_SLA_TARGETS = {
    "pre_publish": _PRE_PUBLISH_SLA_MS,
    "post_publish": _POST_PUBLISH_SLA_MS,
}


async def assign_moderator(
    db: AsyncSession,
    queue_id: UUID,
    moderator_id: UUID,
) -> ModeratorAssignment:
    """Assign a moderator to a queue item.

    Updates the ModerationQueue.assigned_to field and creates an assignment record.
    If already assigned, reassigns (marks old assignment as 'reassigned').
    """
    # Verify queue entry exists
    result = await db.execute(
        select(ModerationQueue).where(ModerationQueue.id == queue_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise NotFoundError("ModerationQueue", str(queue_id))

    if entry.status in ("approved", "rejected"):
        raise ConflictError(
            f"Cannot assign moderator to already-processed item (status: {entry.status})"
        )

    # Mark any existing assignment as reassigned
    existing_result = await db.execute(
        select(ModeratorAssignment).where(
            ModeratorAssignment.queue_id == queue_id,
            ModeratorAssignment.status == "assigned",
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        existing.status = "reassigned"

    # Create new assignment
    assignment = ModeratorAssignment(
        id=uuid4(),
        queue_id=queue_id,
        moderator_id=moderator_id,
        status="assigned",
    )
    db.add(assignment)

    # Update queue entry
    entry.assigned_to = moderator_id
    await db.flush()
    await db.refresh(assignment)

    logger.info(
        "moderator_assigned",
        queue_id=str(queue_id),
        moderator_id=str(moderator_id),
        reassigned=existing is not None,
    )
    return assignment


async def bulk_action(
    db: AsyncSession,
    queue_ids: list[UUID],
    action: str,
    moderator_id: UUID,
    reason: str | None = None,
) -> dict:
    """Perform a bulk moderation action on multiple queue items.

    Returns a summary with counts of successful and failed operations.
    """
    valid_actions = {"approve", "reject", "escalate"}
    if action not in valid_actions:
        raise ValidationError(
            f"Invalid action '{action}'. Must be one of: {', '.join(sorted(valid_actions))}"
        )

    if not queue_ids:
        raise ValidationError("At least one queue_id is required")

    if len(queue_ids) > 100:
        raise ValidationError("Maximum 100 items per bulk action")

    status_map = {
        "approve": "approved",
        "reject": "rejected",
        "escalate": "escalated",
    }
    new_status = status_map[action]

    succeeded = []
    failed = []

    for qid in queue_ids:
        result = await db.execute(
            select(ModerationQueue).where(ModerationQueue.id == qid)
        )
        entry = result.scalar_one_or_none()

        if not entry:
            failed.append({"id": str(qid), "error": "not_found"})
            continue

        if entry.status in ("approved", "rejected"):
            failed.append({
                "id": str(qid),
                "error": f"already_{entry.status}",
            })
            continue

        entry.status = new_status

        decision = ModerationDecision(
            id=uuid4(),
            queue_id=qid,
            moderator_id=moderator_id,
            action=action,
            reason=reason or f"Bulk {action}",
        )
        db.add(decision)

        # Mark assignment as completed if one exists
        assign_result = await db.execute(
            select(ModeratorAssignment).where(
                ModeratorAssignment.queue_id == qid,
                ModeratorAssignment.status == "assigned",
            )
        )
        assign = assign_result.scalar_one_or_none()
        if assign:
            assign.status = "completed"
            assign.completed_at = datetime.now(timezone.utc)

        succeeded.append(str(qid))

    await db.flush()

    logger.info(
        "bulk_action_completed",
        action=action,
        succeeded_count=len(succeeded),
        failed_count=len(failed),
        moderator_id=str(moderator_id),
    )

    return {
        "action": action,
        "succeeded": succeeded,
        "failed": failed,
        "total_succeeded": len(succeeded),
        "total_failed": len(failed),
    }


async def get_sla_metrics(
    db: AsyncSession,
    pipeline: str | None = None,
    hours: int = 24,
) -> dict:
    """Calculate SLA metrics for moderation pipelines.

    Computes p95 processing time and SLA compliance from decision timestamps.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=hours)

    pipelines = [pipeline] if pipeline else ["pre_publish", "post_publish"]
    metrics = {}

    for pipe in pipelines:
        sla_target_ms = _SLA_TARGETS.get(pipe, _POST_PUBLISH_SLA_MS)

        # Get queue entries with decisions in the window
        # Processing time = decision.timestamp - queue.created_at
        stmt = (
            select(
                ModerationQueue.created_at,
                ModerationDecision.timestamp,
            )
            .join(
                ModerationDecision,
                ModerationDecision.queue_id == ModerationQueue.id,
            )
            .where(
                ModerationQueue.pipeline == pipe,
                ModerationDecision.timestamp >= window_start,
            )
            .order_by(ModerationDecision.timestamp.asc())
        )

        rows = (await db.execute(stmt)).all()
        if not rows:
            metrics[pipe] = {
                "pipeline": pipe,
                "p95_ms": 0.0,
                "items_total": 0,
                "items_in_sla": 0,
                "items_breached_sla": 0,
                "sla_target_ms": sla_target_ms,
                "compliance_pct": 100.0,
            }
            continue

        # Calculate processing times in ms
        processing_times = []
        for created_at, decided_at in rows:
            # Handle naive datetimes from SQLite tests
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if decided_at.tzinfo is None:
                decided_at = decided_at.replace(tzinfo=timezone.utc)
            delta_ms = (decided_at - created_at).total_seconds() * 1000
            processing_times.append(delta_ms)

        processing_times.sort()
        total = len(processing_times)

        # p95 calculation
        p95_index = int(total * 0.95)
        if p95_index >= total:
            p95_index = total - 1
        p95_ms = processing_times[p95_index]

        in_sla = sum(1 for t in processing_times if t <= sla_target_ms)
        breached = total - in_sla
        compliance_pct = round((in_sla / total) * 100, 2) if total > 0 else 100.0

        metrics[pipe] = {
            "pipeline": pipe,
            "p95_ms": round(p95_ms, 2),
            "items_total": total,
            "items_in_sla": in_sla,
            "items_breached_sla": breached,
            "sla_target_ms": sla_target_ms,
            "compliance_pct": compliance_pct,
        }

    return {
        "window_hours": hours,
        "window_start": window_start.isoformat(),
        "window_end": now.isoformat(),
        "pipelines": metrics,
    }


async def detect_patterns(
    db: AsyncSession,
    hours: int = 24,
) -> list[dict]:
    """Detect content moderation patterns in the specified time window.

    Patterns detected:
    1. keyword_spike: high-frequency keywords in rejected content
    2. user_repeat_offender: users with multiple rejected items
    3. content_type_surge: unusual volume in a content type
    4. risk_category_trend: trending risk categories
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=hours)

    patterns = []

    # ---- Pattern 1: Keyword spikes in rejected content ----
    rejected_stmt = select(ModerationQueue.risk_scores).where(
        ModerationQueue.status == "rejected",
        ModerationQueue.created_at >= window_start,
        ModerationQueue.risk_scores.isnot(None),
    )
    rejected_rows = (await db.execute(rejected_stmt)).scalars().all()

    keyword_counts: Counter = Counter()
    for risk_scores in rejected_rows:
        if isinstance(risk_scores, dict):
            kf = risk_scores.get("keyword_filter", {})
            matched = kf.get("matched_keywords", [])
            if isinstance(matched, list):
                keyword_counts.update(matched)

    for keyword, count in keyword_counts.most_common(5):
        if count >= 3:  # threshold: 3+ occurrences
            patterns.append({
                "pattern_type": "keyword_spike",
                "description": f"Keyword '{keyword}' appeared in {count} rejected items",
                "severity": "high" if count >= 10 else "medium" if count >= 5 else "low",
                "details": {"keyword": keyword, "count": count},
                "window_start": window_start.isoformat(),
                "window_end": now.isoformat(),
            })

    # ---- Pattern 2: Repeat offenders (content submitted by same assigned_to) ----
    # Use content_id grouping to detect repeated rejections from same source
    repeat_stmt = (
        select(
            ModerationQueue.content_type,
            func.count(ModerationQueue.id).label("rejection_count"),
        )
        .where(
            ModerationQueue.status == "rejected",
            ModerationQueue.created_at >= window_start,
        )
        .group_by(ModerationQueue.content_type)
        .having(func.count(ModerationQueue.id) >= 3)
    )
    repeat_rows = (await db.execute(repeat_stmt)).all()

    for content_type, count in repeat_rows:
        if count >= 5:
            patterns.append({
                "pattern_type": "content_type_surge",
                "description": f"High rejection rate for '{content_type}' content: {count} items",
                "severity": "high" if count >= 10 else "medium",
                "details": {"content_type": content_type, "rejection_count": count},
                "window_start": window_start.isoformat(),
                "window_end": now.isoformat(),
            })

    # ---- Pattern 3: Risk category trends ----
    all_risk_stmt = select(ModerationQueue.risk_scores).where(
        ModerationQueue.created_at >= window_start,
        ModerationQueue.risk_scores.isnot(None),
    )
    all_risk_rows = (await db.execute(all_risk_stmt)).scalars().all()

    risk_category_counts: Counter = Counter()
    for risk_scores in all_risk_rows:
        if isinstance(risk_scores, dict):
            sr = risk_scores.get("social_risk", {})
            category = sr.get("category")
            if category:
                risk_category_counts[category] += 1

    for category, count in risk_category_counts.most_common(3):
        if count >= 3:
            patterns.append({
                "pattern_type": "risk_category_trend",
                "description": f"Risk category '{category}' trending with {count} detections",
                "severity": "high" if count >= 10 else "medium" if count >= 5 else "low",
                "details": {"category": category, "count": count},
                "window_start": window_start.isoformat(),
                "window_end": now.isoformat(),
            })

    # ---- Pattern 4: Escalation surge ----
    escalated_count_result = await db.execute(
        select(func.count(ModerationQueue.id)).where(
            ModerationQueue.status == "escalated",
            ModerationQueue.created_at >= window_start,
        )
    )
    escalated_count = escalated_count_result.scalar() or 0

    if escalated_count >= 5:
        patterns.append({
            "pattern_type": "escalation_surge",
            "description": f"{escalated_count} items escalated in the last {hours}h",
            "severity": "critical" if escalated_count >= 20 else "high" if escalated_count >= 10 else "medium",
            "details": {"escalated_count": escalated_count},
            "window_start": window_start.isoformat(),
            "window_end": now.isoformat(),
        })

    logger.info(
        "pattern_detection_complete",
        window_hours=hours,
        patterns_found=len(patterns),
    )

    return patterns


async def persist_patterns(
    db: AsyncSession,
    patterns: list[dict],
) -> list[PatternDetection]:
    """Persist detected patterns to the database."""
    records = []
    for p in patterns:
        record = PatternDetection(
            id=uuid4(),
            pattern_type=p["pattern_type"],
            description=p["description"],
            severity=p["severity"],
            details=p.get("details"),
            window_start=datetime.fromisoformat(p["window_start"]),
            window_end=datetime.fromisoformat(p["window_end"]),
        )
        db.add(record)
        records.append(record)

    if records:
        await db.flush()

    return records


async def persist_sla_snapshot(
    db: AsyncSession,
    sla_data: dict,
) -> list[SLAMetric]:
    """Persist SLA metrics snapshot to the database."""
    records = []
    for pipe_name, pipe_data in sla_data.get("pipelines", {}).items():
        record = SLAMetric(
            id=uuid4(),
            pipeline=pipe_name,
            period_start=datetime.fromisoformat(sla_data["window_start"]),
            period_end=datetime.fromisoformat(sla_data["window_end"]),
            p95_ms=pipe_data["p95_ms"],
            items_total=pipe_data["items_total"],
            items_in_sla=pipe_data["items_in_sla"],
            items_breached_sla=pipe_data["items_breached_sla"],
        )
        db.add(record)
        records.append(record)

    if records:
        await db.flush()

    return records
