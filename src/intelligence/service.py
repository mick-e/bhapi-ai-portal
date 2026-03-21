"""Intelligence module business logic — graph analysis, abuse signals, baselines."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError
from src.intelligence.models import AbuseSignal, BehavioralBaseline, SocialGraphEdge
from src.intelligence.schemas import SocialGraphEdgeCreate, AbuseSignalCreate
from src.social.graph_analysis import (
    analyze_contacts,
    detect_age_inappropriate_pattern,
    detect_isolation,
    map_influence,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Social Graph Edges
# ---------------------------------------------------------------------------


async def create_graph_edge(
    db: AsyncSession,
    data: SocialGraphEdgeCreate,
) -> SocialGraphEdge:
    """Create a social graph edge."""
    if data.source_id == data.target_id:
        raise ValidationError("source_id and target_id must be different")

    edge = SocialGraphEdge(
        id=uuid4(),
        source_id=data.source_id,
        target_id=data.target_id,
        edge_type=data.edge_type,
        weight=data.weight,
        last_interaction=data.last_interaction,
    )
    db.add(edge)
    await db.flush()
    await db.refresh(edge)

    logger.info(
        "graph_edge_created",
        edge_id=str(edge.id),
        source_id=str(data.source_id),
        target_id=str(data.target_id),
        edge_type=data.edge_type,
    )
    return edge


async def get_member_edges(
    db: AsyncSession,
    member_id: UUID,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[SocialGraphEdge], int]:
    """Get all graph edges for a member."""
    base = select(SocialGraphEdge).where(
        (SocialGraphEdge.source_id == member_id)
        | (SocialGraphEdge.target_id == member_id)
    )

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = await db.execute(
        base.order_by(SocialGraphEdge.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(rows.scalars().all()), total


# ---------------------------------------------------------------------------
# Abuse Signals
# ---------------------------------------------------------------------------


async def create_abuse_signal(
    db: AsyncSession,
    data: AbuseSignalCreate,
) -> AbuseSignal:
    """Create an abuse signal."""
    signal = AbuseSignal(
        id=uuid4(),
        member_id=data.member_id,
        signal_type=data.signal_type,
        severity=data.severity,
        details=data.details,
        resolved=False,
    )
    db.add(signal)
    await db.flush()
    await db.refresh(signal)

    logger.info(
        "abuse_signal_created",
        signal_id=str(signal.id),
        member_id=str(data.member_id),
        signal_type=data.signal_type,
        severity=data.severity,
    )
    return signal


async def get_abuse_signals(
    db: AsyncSession,
    member_id: UUID,
    offset: int = 0,
    limit: int = 50,
    include_resolved: bool = False,
) -> tuple[list[AbuseSignal], int]:
    """Get abuse signals for a member."""
    base = select(AbuseSignal).where(AbuseSignal.member_id == member_id)

    if not include_resolved:
        base = base.where(AbuseSignal.resolved.is_(False))

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = await db.execute(
        base.order_by(AbuseSignal.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(rows.scalars().all()), total


async def resolve_abuse_signal(
    db: AsyncSession,
    signal_id: UUID,
    resolved_by: UUID,
) -> AbuseSignal:
    """Mark an abuse signal as resolved."""
    result = await db.execute(
        select(AbuseSignal).where(AbuseSignal.id == signal_id)
    )
    signal = result.scalar_one_or_none()
    if not signal:
        raise NotFoundError("AbuseSignal")

    signal.resolved = True
    signal.resolved_at = datetime.now(timezone.utc)
    signal.resolved_by = resolved_by
    await db.flush()
    await db.refresh(signal)

    logger.info(
        "abuse_signal_resolved",
        signal_id=str(signal_id),
        resolved_by=str(resolved_by),
    )
    return signal


# ---------------------------------------------------------------------------
# Graph Analysis (delegates to src.social.graph_analysis)
# ---------------------------------------------------------------------------


async def run_graph_analysis(db: AsyncSession, member_id: UUID) -> dict:
    """Run full graph analysis for a member."""
    return await analyze_contacts(db, member_id)


async def run_isolation_check(db: AsyncSession, member_id: UUID) -> dict:
    """Run isolation detection for a member."""
    return await detect_isolation(db, member_id)


async def run_influence_mapping(db: AsyncSession, member_id: UUID) -> dict:
    """Run influence mapping for a member."""
    return await map_influence(db, member_id)


async def run_age_pattern_check(db: AsyncSession, member_id: UUID) -> dict:
    """Run age-inappropriate pattern detection."""
    return await detect_age_inappropriate_pattern(db, member_id)


# ---------------------------------------------------------------------------
# Behavioral Baselines
# ---------------------------------------------------------------------------


async def get_baseline(
    db: AsyncSession,
    member_id: UUID,
    window_days: int = 30,
) -> BehavioralBaseline | None:
    """Get the latest behavioral baseline for a member."""
    result = await db.execute(
        select(BehavioralBaseline)
        .where(
            BehavioralBaseline.member_id == member_id,
            BehavioralBaseline.window_days == window_days,
        )
        .order_by(BehavioralBaseline.computed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_baseline(
    db: AsyncSession,
    member_id: UUID,
    window_days: int,
    metrics: dict,
    sample_count: int,
) -> BehavioralBaseline:
    """Create a new behavioral baseline."""
    baseline = BehavioralBaseline(
        id=uuid4(),
        member_id=member_id,
        window_days=window_days,
        metrics=metrics,
        computed_at=datetime.now(timezone.utc),
        sample_count=sample_count,
    )
    db.add(baseline)
    await db.flush()
    await db.refresh(baseline)

    logger.info(
        "baseline_created",
        member_id=str(member_id),
        window_days=window_days,
        sample_count=sample_count,
    )
    return baseline


# ---------------------------------------------------------------------------
# Behavioral Baseline Analysis (delegates to src.social.behavioral)
# ---------------------------------------------------------------------------


async def compute_member_baseline(
    db: AsyncSession,
    member_id: UUID,
    window_days: int = 14,
) -> BehavioralBaseline:
    """Compute behavioral baseline for a member from activity data."""
    from src.social.behavioral import compute_baseline as _compute
    return await _compute(db, member_id, window_days=window_days)


async def detect_member_deviation(
    db: AsyncSession,
    member_id: UUID,
    threshold: float = 2.0,
) -> list[dict]:
    """Detect behavioral deviations for a member against their baseline."""
    from src.social.behavioral import detect_deviation as _detect
    return await _detect(db, member_id, threshold=threshold)


async def get_member_baseline_summary(
    db: AsyncSession,
    member_id: UUID,
) -> dict:
    """Get human-readable baseline summary for parent dashboard."""
    from src.social.behavioral import get_baseline_summary as _summary
    return await _summary(db, member_id)


async def run_baseline_batch(
    db: AsyncSession,
    window_days: int = 14,
) -> list[BehavioralBaseline]:
    """Scheduled job: recompute baselines for all active children."""
    from src.social.behavioral import update_baselines_batch as _batch
    return await _batch(db, window_days=window_days)
