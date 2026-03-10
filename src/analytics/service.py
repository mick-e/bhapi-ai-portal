"""Analytics service — trend analysis, usage patterns, member baselines."""

import math
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.capture.models import CaptureEvent
from src.groups.models import GroupMember
from src.risk.models import RiskEvent

logger = structlog.get_logger()


async def get_trends(db: AsyncSession, group_id: UUID, days: int = 30) -> dict:
    """Calculate weekly rolling averages and trend direction."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    # Daily event counts
    result = await db.execute(
        select(
            func.date(CaptureEvent.timestamp).label("day"),
            func.count(CaptureEvent.id).label("count"),
        ).where(
            CaptureEvent.group_id == group_id,
            CaptureEvent.timestamp >= start,
        ).group_by(func.date(CaptureEvent.timestamp))
        .order_by(func.date(CaptureEvent.timestamp))
    )
    daily_counts = [(str(row[0]), int(row[1])) for row in result.all()]

    # Daily risk counts
    risk_result = await db.execute(
        select(
            func.date(RiskEvent.created_at).label("day"),
            func.count(RiskEvent.id).label("count"),
        ).where(
            RiskEvent.group_id == group_id,
            RiskEvent.created_at >= start,
        ).group_by(func.date(RiskEvent.created_at))
        .order_by(func.date(RiskEvent.created_at))
    )
    daily_risks = [(str(row[0]), int(row[1])) for row in risk_result.all()]

    def calc_direction(points: list) -> str:
        if len(points) < 7:
            return "stable"
        recent = sum(v for _, v in points[-7:]) / 7
        older = sum(v for _, v in points[-14:-7]) / max(len(points[-14:-7]), 1)
        if recent > older * 1.1:
            return "increasing"
        elif recent < older * 0.9:
            return "decreasing"
        return "stable"

    return {
        "group_id": str(group_id),
        "period_days": days,
        "activity": {
            "data_points": [{"date": d, "value": c} for d, c in daily_counts],
            "direction": calc_direction(daily_counts),
        },
        "risk_events": {
            "data_points": [{"date": d, "value": c} for d, c in daily_risks],
            "direction": calc_direction(daily_risks),
        },
    }


async def get_usage_patterns(db: AsyncSession, group_id: UUID, days: int = 30) -> dict:
    """Analyze usage patterns by time-of-day, day-of-week, and platform."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    result = await db.execute(
        select(CaptureEvent).where(
            CaptureEvent.group_id == group_id,
            CaptureEvent.timestamp >= start,
        )
    )
    events = list(result.scalars().all())

    by_hour: dict[str, int] = {str(h): 0 for h in range(24)}
    by_day: dict[str, int] = {"Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0, "Sat": 0, "Sun": 0}
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    by_platform: dict[str, int] = {}

    for event in events:
        ts = event.timestamp
        if ts:
            by_hour[str(ts.hour)] = by_hour.get(str(ts.hour), 0) + 1
            day_name = day_names[ts.weekday()]
            by_day[day_name] = by_day.get(day_name, 0) + 1
        by_platform[event.platform] = by_platform.get(event.platform, 0) + 1

    return {
        "group_id": str(group_id),
        "period_days": days,
        "by_hour": by_hour,
        "by_day_of_week": by_day,
        "by_platform": by_platform,
    }


async def get_member_baselines(db: AsyncSession, group_id: UUID, days: int = 30) -> list[dict]:
    """Calculate per-member behavior baselines."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    members_result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    members = list(members_result.scalars().all())

    baselines = []
    for member in members:
        # Event count
        event_count_result = await db.execute(
            select(func.count(CaptureEvent.id)).where(
                CaptureEvent.group_id == group_id,
                CaptureEvent.member_id == member.id,
                CaptureEvent.timestamp >= start,
            )
        )
        event_count = event_count_result.scalar() or 0

        # Risk count
        risk_result = await db.execute(
            select(func.count(RiskEvent.id)).where(
                RiskEvent.group_id == group_id,
                RiskEvent.member_id == member.id,
                RiskEvent.created_at >= start,
            )
        )
        risk_count = risk_result.scalar() or 0

        # Primary platform
        platform_result = await db.execute(
            select(CaptureEvent.platform, func.count(CaptureEvent.id).label("cnt")).where(
                CaptureEvent.group_id == group_id,
                CaptureEvent.member_id == member.id,
                CaptureEvent.timestamp >= start,
            ).group_by(CaptureEvent.platform).order_by(func.count(CaptureEvent.id).desc()).limit(1)
        )
        platform_row = platform_result.first()

        avg_daily = event_count / max(days, 1)
        avg_risk = risk_count / max(event_count, 1)

        baselines.append({
            "member_id": str(member.id),
            "member_name": member.display_name,
            "avg_daily_events": round(avg_daily, 2),
            "avg_risk_score": round(avg_risk, 4),
            "primary_platform": platform_row[0] if platform_row else "none",
            "total_events": event_count,
            "total_risks": risk_count,
            "trend_direction": "stable",
        })

    return baselines


async def detect_anomalies(
    db: AsyncSession, group_id: UUID, threshold_sd: float = 2.0
) -> dict:
    """Detect members with usage >threshold_sd standard deviations from baseline.

    Compares a recent 7-day window against a 30-day baseline to find anomalous
    usage spikes or drops.

    Returns dict with group_id, threshold_sd, and list of anomalies.
    """
    now = datetime.now(timezone.utc)
    baseline_start = now - timedelta(days=30)
    recent_start = now - timedelta(days=7)

    members_result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    members = list(members_result.scalars().all())

    anomalies = []
    for member in members:
        # Get daily counts for the baseline period (30 days)
        daily_result = await db.execute(
            select(
                func.date(CaptureEvent.timestamp).label("day"),
                func.count(CaptureEvent.id).label("count"),
            ).where(
                CaptureEvent.group_id == group_id,
                CaptureEvent.member_id == member.id,
                CaptureEvent.timestamp >= baseline_start,
            ).group_by(func.date(CaptureEvent.timestamp))
        )
        daily_rows = daily_result.all()
        daily_counts = [int(row[1]) for row in daily_rows]

        # Need at least a few data points for meaningful statistics
        if len(daily_counts) < 3:
            continue

        baseline_mean = sum(daily_counts) / len(daily_counts)
        variance = sum((c - baseline_mean) ** 2 for c in daily_counts) / len(daily_counts)
        baseline_sd = math.sqrt(variance)

        if baseline_sd == 0:
            # No variance — skip unless there are no events at all
            continue

        # Recent 7-day average
        recent_result = await db.execute(
            select(func.count(CaptureEvent.id)).where(
                CaptureEvent.group_id == group_id,
                CaptureEvent.member_id == member.id,
                CaptureEvent.timestamp >= recent_start,
            )
        )
        recent_total = recent_result.scalar() or 0
        recent_daily_avg = recent_total / 7.0

        # How many SDs from baseline?
        deviation = (recent_daily_avg - baseline_mean) / baseline_sd
        abs_deviation = abs(deviation)

        if abs_deviation >= threshold_sd:
            direction = "above" if deviation > 0 else "below"
            severity = "critical" if abs_deviation >= threshold_sd * 1.5 else "warning"

            anomalies.append({
                "member_id": str(member.id),
                "member_name": member.display_name,
                "recent_daily_avg": round(recent_daily_avg, 2),
                "baseline_daily_avg": round(baseline_mean, 2),
                "standard_deviations": round(abs_deviation, 2),
                "direction": direction,
                "severity": severity,
            })

    logger.info(
        "anomaly_detection_complete",
        group_id=str(group_id),
        anomaly_count=len(anomalies),
    )

    return {
        "group_id": str(group_id),
        "threshold_sd": threshold_sd,
        "anomalies": anomalies,
    }


async def get_peer_comparison(
    db: AsyncSession, group_id: UUID, days: int = 30
) -> dict:
    """Get percentile ranks for each member within their group.

    Returns dict with group_id, period_days, and list of member comparisons
    including event_count, percentile, and usage_level classification.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    members_result = await db.execute(
        select(GroupMember).where(GroupMember.group_id == group_id)
    )
    members = list(members_result.scalars().all())

    if not members:
        return {
            "group_id": str(group_id),
            "period_days": days,
            "members": [],
        }

    # Get event counts per member
    member_counts: list[tuple[str, str, int]] = []
    for member in members:
        count_result = await db.execute(
            select(func.count(CaptureEvent.id)).where(
                CaptureEvent.group_id == group_id,
                CaptureEvent.member_id == member.id,
                CaptureEvent.timestamp >= start,
            )
        )
        count = count_result.scalar() or 0
        member_counts.append((str(member.id), member.display_name, count))

    # Sort by count to calculate percentiles
    sorted_counts = sorted([c for _, _, c in member_counts])
    total_members = len(sorted_counts)

    def calc_percentile(value: int) -> float:
        """Calculate percentile rank using the 'less than' method."""
        if total_members <= 1:
            return 50.0
        below = sum(1 for c in sorted_counts if c < value)
        return round((below / total_members) * 100, 1)

    def classify_usage(percentile: float) -> str:
        if percentile >= 90:
            return "very_high"
        elif percentile >= 60:
            return "high"
        elif percentile >= 30:
            return "moderate"
        return "low"

    comparison = []
    for member_id, member_name, event_count in member_counts:
        percentile = calc_percentile(event_count)
        comparison.append({
            "member_id": member_id,
            "member_name": member_name,
            "event_count": event_count,
            "percentile": percentile,
            "usage_level": classify_usage(percentile),
        })

    # Sort by percentile descending for display
    comparison.sort(key=lambda x: x["percentile"], reverse=True)

    return {
        "group_id": str(group_id),
        "period_days": days,
        "members": comparison,
    }
