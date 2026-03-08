"""Analytics service — trend analysis, usage patterns, member baselines."""

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
