"""SLA metrics service for moderation pipeline performance.

Computes live SLA metrics consumed by the portal dashboard:
- Pre-publish pipeline (under-13): <2s SLA target
- Post-publish pipeline (13-15): <60s SLA target
"""

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.moderation.models import ModerationDecision, ModerationQueue
from src.moderation.sla_schemas import SLAMetrics

logger = structlog.get_logger()

# SLA budgets (ms) — must match service.py constants
_PRE_PUBLISH_BUDGET_MS = 2_000    # <2s for pre-publish (children under 13)
_POST_PUBLISH_BUDGET_MS = 60_000  # <60s for post-publish takedown (teens 13-15)


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Return the given percentile from a pre-sorted list. Returns 0 if empty."""
    if not sorted_values:
        return 0.0
    idx = int(len(sorted_values) * pct)
    if idx >= len(sorted_values):
        idx = len(sorted_values) - 1
    return round(sorted_values[idx], 2)


async def get_sla_metrics(db: AsyncSession) -> SLAMetrics:
    """Calculate live SLA metrics for both moderation pipelines.

    Queries:
    - ModerationQueue for current queue depth and oldest pending item.
    - ModerationDecision joined with ModerationQueue for latency percentiles
      and SLA breach counts in the last 24 hours.

    Latency is derived from (decision.timestamp - queue.created_at) because
    ModerationDecision has no standalone latency_ms column.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)

    # ── Queue depth and oldest pending ────────────────────────────────────────
    queue_stmt = select(
        func.count(ModerationQueue.id).label("depth"),
        func.min(ModerationQueue.created_at).label("oldest"),
    ).where(ModerationQueue.status == "pending")

    queue_row = (await db.execute(queue_stmt)).one()
    queue_depth: int = queue_row.depth or 0
    oldest_pending_age_seconds = 0
    if queue_row.oldest is not None:
        oldest_dt: datetime = queue_row.oldest
        if oldest_dt.tzinfo is None:
            oldest_dt = oldest_dt.replace(tzinfo=timezone.utc)
        oldest_pending_age_seconds = max(0, int((now - oldest_dt).total_seconds()))

    # ── Per-pipeline latency and breach counts (last 24h) ─────────────────────
    decisions_stmt = (
        select(
            ModerationQueue.pipeline,
            ModerationQueue.created_at.label("queued_at"),
            ModerationDecision.timestamp.label("decided_at"),
        )
        .join(ModerationDecision, ModerationDecision.queue_id == ModerationQueue.id)
        .where(ModerationDecision.timestamp >= window_start)
    )

    rows = (await db.execute(decisions_stmt)).all()

    pre_times: list[float] = []
    post_times: list[float] = []

    for pipeline, queued_at, decided_at in rows:
        # Normalise naive datetimes from SQLite test sessions
        if queued_at is not None and queued_at.tzinfo is None:
            queued_at = queued_at.replace(tzinfo=timezone.utc)
        if decided_at is not None and decided_at.tzinfo is None:
            decided_at = decided_at.replace(tzinfo=timezone.utc)

        if queued_at is None or decided_at is None:
            continue

        delta_ms = (decided_at - queued_at).total_seconds() * 1000
        if pipeline == "pre_publish":
            pre_times.append(delta_ms)
        elif pipeline == "post_publish":
            post_times.append(delta_ms)

    pre_times.sort()
    post_times.sort()

    total_reviewed = len(pre_times) + len(post_times)

    # SLA breach = any item that exceeded its pipeline budget
    breach_count = sum(1 for t in pre_times if t > _PRE_PUBLISH_BUDGET_MS) + sum(
        1 for t in post_times if t > _POST_PUBLISH_BUDGET_MS
    )

    metrics = SLAMetrics(
        pre_publish_p50_ms=_percentile(pre_times, 0.50),
        pre_publish_p95_ms=_percentile(pre_times, 0.95),
        post_publish_p50_ms=_percentile(post_times, 0.50),
        post_publish_p95_ms=_percentile(post_times, 0.95),
        queue_depth=queue_depth,
        oldest_pending_age_seconds=oldest_pending_age_seconds,
        sla_breach_count_24h=breach_count,
        total_reviewed_24h=total_reviewed,
    )

    logger.info(
        "sla_metrics_computed",
        queue_depth=queue_depth,
        total_reviewed_24h=total_reviewed,
        breach_count_24h=breach_count,
        pre_p95_ms=metrics.pre_publish_p95_ms,
        post_p95_ms=metrics.post_publish_p95_ms,
    )

    return metrics
