"""Behavioral baselines — per-child norms, deviation alerting.

Computes activity baselines from social posts, messages, and device sessions
over a configurable time window, then detects deviations beyond a threshold
(default: 2 standard deviations) to generate alerts for parents.
"""

import math
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.device_agent.models import DeviceSession
from src.groups.models import GroupMember
from src.intelligence.models import BehavioralBaseline
from src.messaging.models import Message
from src.social.models import SocialPost

logger = structlog.get_logger()

# Deviation threshold (number of standard deviations)
DEFAULT_DEVIATION_THRESHOLD = 2.0


async def _resolve_user_id(db: AsyncSession, member_id: UUID) -> UUID | None:
    """Resolve a group_member_id to a user_id.

    SocialPost.author_id and Message.sender_id reference users.id,
    while DeviceSession.member_id references group_members.id.
    This helper bridges the gap.
    """
    result = await db.execute(
        select(GroupMember.user_id).where(GroupMember.id == member_id)
    )
    row = result.one_or_none()
    return row[0] if row else None


async def compute_baseline(
    db: AsyncSession,
    member_id: UUID,
    window_days: int = 14,
) -> BehavioralBaseline:
    """Compute behavioral baseline from activity over the given window.

    Aggregates daily counts of posts, messages, and session durations,
    then stores mean and std per metric in a BehavioralBaseline record.

    ``member_id`` is a group_members.id. For posts and messages (which
    reference users.id), the member's user_id is resolved automatically.
    If user_id is None (child without a linked user account), posts and
    messages are queried directly by member_id for flexibility.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=window_days)

    # Resolve the user_id for social queries (posts / messages)
    user_id = await _resolve_user_id(db, member_id)
    author_id = user_id if user_id is not None else member_id

    # --- Posts per day ---
    post_rows = await db.execute(
        select(
            func.date(SocialPost.created_at).label("day"),
            func.count(SocialPost.id).label("cnt"),
        )
        .where(
            SocialPost.author_id == author_id,
            SocialPost.created_at >= window_start,
        )
        .group_by(func.date(SocialPost.created_at))
    )
    post_daily = [row.cnt for row in post_rows.all()]

    # --- Messages per day ---
    msg_rows = await db.execute(
        select(
            func.date(Message.created_at).label("day"),
            func.count(Message.id).label("cnt"),
        )
        .where(
            Message.sender_id == author_id,
            Message.created_at >= window_start,
        )
        .group_by(func.date(Message.created_at))
    )
    msg_daily = [row.cnt for row in msg_rows.all()]

    # --- Device session durations per day (minutes) ---
    session_rows = await db.execute(
        select(DeviceSession)
        .where(
            DeviceSession.member_id == member_id,
            DeviceSession.started_at >= window_start,
            DeviceSession.ended_at.isnot(None),
        )
    )
    sessions = list(session_rows.scalars().all())

    # Group session durations by day
    session_daily: dict[str, float] = {}
    active_hours_set: set[int] = set()
    for s in sessions:
        day_key = s.started_at.strftime("%Y-%m-%d")
        duration_min = (s.ended_at - s.started_at).total_seconds() / 60.0
        session_daily[day_key] = session_daily.get(day_key, 0.0) + duration_min
        # Track active hours
        active_hours_set.add(s.started_at.hour)
        if s.ended_at:
            active_hours_set.add(s.ended_at.hour)

    session_daily_list = list(session_daily.values())

    # Pad with zeros for days with no activity up to window_days
    post_daily_padded = _pad_daily(post_daily, window_days)
    msg_daily_padded = _pad_daily(msg_daily, window_days)
    session_daily_padded = _pad_daily(session_daily_list, window_days)

    # Compute stats
    post_mean, post_std = _mean_std(post_daily_padded)
    msg_mean, msg_std = _mean_std(msg_daily_padded)
    session_mean, session_std = _mean_std(session_daily_padded)

    # Content sentiment average (placeholder — requires NLP pipeline)
    # For now, neutral 0.0
    sentiment_avg = 0.0

    sample_count = len(post_daily) + len(msg_daily) + len(sessions)

    metrics = {
        "avg_posts_per_day": {"mean": post_mean, "std": post_std},
        "avg_messages_per_day": {"mean": msg_mean, "std": msg_std},
        "avg_session_duration": {"mean": session_mean, "std": session_std},
        "active_hours": sorted(active_hours_set),
        "content_sentiment_avg": sentiment_avg,
    }

    baseline = BehavioralBaseline(
        id=uuid4(),
        member_id=member_id,
        window_days=window_days,
        metrics=metrics,
        computed_at=now,
        sample_count=sample_count,
    )
    db.add(baseline)
    await db.flush()
    await db.refresh(baseline)

    logger.info(
        "baseline_computed",
        member_id=str(member_id),
        window_days=window_days,
        sample_count=sample_count,
    )
    return baseline


async def detect_deviation(
    db: AsyncSession,
    member_id: UUID,
    threshold: float = DEFAULT_DEVIATION_THRESHOLD,
    lookback_days: int = 1,
) -> list[dict]:
    """Compare recent activity (last `lookback_days`) against baseline.

    Returns a list of deviations where the current value exceeds
    `threshold` standard deviations from the baseline mean.
    """
    # Get latest baseline
    result = await db.execute(
        select(BehavioralBaseline)
        .where(BehavioralBaseline.member_id == member_id)
        .order_by(BehavioralBaseline.computed_at.desc())
        .limit(1)
    )
    baseline = result.scalar_one_or_none()
    if not baseline or not baseline.metrics:
        return []

    metrics = baseline.metrics
    now = datetime.now(timezone.utc)
    lookback_start = now - timedelta(days=lookback_days)

    # Resolve user_id for social queries
    user_id = await _resolve_user_id(db, member_id)
    author_id = user_id if user_id is not None else member_id

    # Current posts count
    post_count_result = await db.execute(
        select(func.count(SocialPost.id)).where(
            SocialPost.author_id == author_id,
            SocialPost.created_at >= lookback_start,
        )
    )
    current_posts = (post_count_result.scalar() or 0) / max(lookback_days, 1)

    # Current messages count
    msg_count_result = await db.execute(
        select(func.count(Message.id)).where(
            Message.sender_id == author_id,
            Message.created_at >= lookback_start,
        )
    )
    current_messages = (msg_count_result.scalar() or 0) / max(lookback_days, 1)

    # Current session duration
    session_rows = await db.execute(
        select(DeviceSession).where(
            DeviceSession.member_id == member_id,
            DeviceSession.started_at >= lookback_start,
            DeviceSession.ended_at.isnot(None),
        )
    )
    sessions = list(session_rows.scalars().all())
    total_session_min = sum(
        (s.ended_at - s.started_at).total_seconds() / 60.0 for s in sessions
    )
    current_session_avg = total_session_min / max(lookback_days, 1)

    deviations = []

    # Check each metric
    for metric_name, current_value in [
        ("avg_posts_per_day", current_posts),
        ("avg_messages_per_day", current_messages),
        ("avg_session_duration", current_session_avg),
    ]:
        metric_data = metrics.get(metric_name)
        if not metric_data or not isinstance(metric_data, dict):
            continue

        mean = metric_data.get("mean", 0.0)
        std = metric_data.get("std", 0.0)

        if std == 0:
            # No variability — flag only if current is significantly different
            if mean > 0 and current_value > mean * 2:
                deviations.append({
                    "metric": metric_name,
                    "current_value": round(current_value, 2),
                    "baseline_value": round(mean, 2),
                    "std_deviations": float("inf"),
                })
            elif mean == 0 and current_value > 0:
                deviations.append({
                    "metric": metric_name,
                    "current_value": round(current_value, 2),
                    "baseline_value": round(mean, 2),
                    "std_deviations": float("inf"),
                })
            continue

        num_std = abs(current_value - mean) / std
        if num_std > threshold:
            deviations.append({
                "metric": metric_name,
                "current_value": round(current_value, 2),
                "baseline_value": round(mean, 2),
                "std_deviations": round(num_std, 2),
            })

    logger.info(
        "deviation_check",
        member_id=str(member_id),
        deviations_found=len(deviations),
    )
    return deviations


async def update_baselines_batch(
    db: AsyncSession,
    window_days: int = 14,
) -> list[BehavioralBaseline]:
    """Scheduled job: recompute baselines for all active group members.

    "Active" means the member has at least one post, message, or device
    session in the last `window_days` period.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=window_days)

    # Collect distinct active member IDs.
    # Posts/messages use user_id, sessions use member_id.
    # We need to map user_ids back to group_member_ids for consistency.

    # Direct: device sessions reference group_members.id
    session_members = await db.execute(
        select(DeviceSession.member_id.distinct()).where(
            DeviceSession.started_at >= window_start,
        )
    )

    active_ids: set[UUID] = set()
    for row in session_members.all():
        active_ids.add(row[0])

    # Posts: author_id is a users.id — find group_members with matching user_id
    post_user_ids_result = await db.execute(
        select(SocialPost.author_id.distinct()).where(
            SocialPost.created_at >= window_start,
        )
    )
    post_user_ids = {row[0] for row in post_user_ids_result.all()}

    msg_user_ids_result = await db.execute(
        select(Message.sender_id.distinct()).where(
            Message.created_at >= window_start,
        )
    )
    msg_user_ids = {row[0] for row in msg_user_ids_result.all()}

    all_user_ids = post_user_ids | msg_user_ids
    if all_user_ids:
        member_rows = await db.execute(
            select(GroupMember.id).where(
                GroupMember.user_id.in_(all_user_ids),
            )
        )
        for row in member_rows.all():
            active_ids.add(row[0])

    baselines = []
    for mid in active_ids:
        try:
            baseline = await compute_baseline(db, mid, window_days=window_days)
            baselines.append(baseline)
        except Exception:
            logger.exception("baseline_batch_error", member_id=str(mid))

    logger.info(
        "baselines_batch_updated",
        total_members=len(active_ids),
        baselines_created=len(baselines),
    )
    return baselines


async def get_baseline_summary(
    db: AsyncSession,
    member_id: UUID,
) -> dict:
    """Human-readable summary for parent dashboard.

    Returns a dict with a narrative description plus key metrics.
    """
    result = await db.execute(
        select(BehavioralBaseline)
        .where(BehavioralBaseline.member_id == member_id)
        .order_by(BehavioralBaseline.computed_at.desc())
        .limit(1)
    )
    baseline = result.scalar_one_or_none()
    if not baseline or not baseline.metrics:
        return {
            "member_id": str(member_id),
            "has_baseline": False,
            "summary": "Not enough activity data to establish a baseline yet.",
            "metrics": {},
        }

    metrics = baseline.metrics
    posts = metrics.get("avg_posts_per_day", {})
    messages = metrics.get("avg_messages_per_day", {})
    sessions = metrics.get("avg_session_duration", {})
    active_hours = metrics.get("active_hours", [])
    sentiment = metrics.get("content_sentiment_avg", 0.0)

    post_mean = posts.get("mean", 0.0) if isinstance(posts, dict) else 0.0
    msg_mean = messages.get("mean", 0.0) if isinstance(messages, dict) else 0.0
    session_mean = sessions.get("mean", 0.0) if isinstance(sessions, dict) else 0.0

    # Build narrative
    parts = []
    parts.append(
        f"Over the last {baseline.window_days} days, your child typically "
        f"posts about {post_mean:.1f} times per day and sends "
        f"{msg_mean:.1f} messages per day."
    )
    if session_mean > 0:
        parts.append(
            f"Average daily device time is {session_mean:.0f} minutes."
        )
    if active_hours:
        parts.append(
            f"Most active hours: {', '.join(str(h) for h in active_hours[:5])}."
        )

    # Detect recent deviations
    deviations = await detect_deviation(db, member_id)
    if deviations:
        dev_names = [d["metric"].replace("avg_", "").replace("_", " ") for d in deviations]
        parts.append(
            f"Recent activity shows unusual patterns in: {', '.join(dev_names)}."
        )

    return {
        "member_id": str(member_id),
        "has_baseline": True,
        "summary": " ".join(parts),
        "metrics": {
            "avg_posts_per_day": post_mean,
            "avg_messages_per_day": msg_mean,
            "avg_session_duration_minutes": session_mean,
            "active_hours": active_hours,
            "content_sentiment_avg": sentiment,
            "sample_count": baseline.sample_count,
            "computed_at": baseline.computed_at.isoformat(),
            "window_days": baseline.window_days,
        },
        "deviations": deviations,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _pad_daily(values: list[float | int], window_days: int) -> list[float]:
    """Pad a list of daily values with zeros up to window_days."""
    padded = [float(v) for v in values]
    while len(padded) < window_days:
        padded.append(0.0)
    return padded


def _mean_std(values: list[float]) -> tuple[float, float]:
    """Compute mean and population standard deviation."""
    if not values:
        return 0.0, 0.0
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance)
    return round(mean, 4), round(std, 4)
