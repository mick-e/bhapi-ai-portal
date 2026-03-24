"""Device agent business logic — sessions, app usage, screen time."""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError
from src.device_agent.models import AppUsageRecord, DeviceSession, ScreenTimeRecord
from src.device_agent.schemas import (
    AppUsageCreate,
    DeviceSessionCreate,
    DeviceSyncRequest,
)

logger = structlog.get_logger()

# AI-related app bundle IDs that trigger intelligence events
AI_APP_BUNDLES = {
    "com.openai.chatgpt", "com.anthropic.claude", "com.google.android.apps.bard",
    "com.microsoft.copilot", "com.character.ai", "ai.replika",
}


async def _publish_intelligence_event(channel: str, event_data: dict) -> None:
    """Best-effort publish to intelligence event bus."""
    try:
        from src.intelligence import publish_event
        await publish_event(channel, event_data)
    except Exception:
        logger.warning("event_bus_publish_failed", channel=channel)


# ---------------------------------------------------------------------------
# Device Sessions
# ---------------------------------------------------------------------------


async def record_device_session(
    db: AsyncSession,
    group_id: UUID,
    data: DeviceSessionCreate,
) -> DeviceSession:
    """Record a device session."""
    session = DeviceSession(
        id=uuid4(),
        member_id=data.member_id,
        group_id=group_id,
        device_id=data.device_id,
        device_type=data.device_type,
        os_version=data.os_version,
        app_version=data.app_version,
        started_at=data.started_at,
        ended_at=data.ended_at,
        battery_level=data.battery_level,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    logger.info(
        "device_session_recorded",
        session_id=str(session.id),
        member_id=str(data.member_id),
        device_type=data.device_type,
    )
    return session


async def get_device_sessions(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[DeviceSession], int]:
    """Get device sessions for a member."""
    base = select(DeviceSession).where(
        DeviceSession.group_id == group_id,
        DeviceSession.member_id == member_id,
    )

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = await db.execute(
        base.order_by(DeviceSession.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(rows.scalars().all()), total


# ---------------------------------------------------------------------------
# App Usage
# ---------------------------------------------------------------------------


async def record_app_usage(
    db: AsyncSession,
    group_id: UUID,
    data: AppUsageCreate,
) -> AppUsageRecord:
    """Record an app usage event."""
    if data.foreground_minutes < 0:
        raise ValidationError("foreground_minutes must be non-negative")

    record = AppUsageRecord(
        id=uuid4(),
        member_id=data.member_id,
        group_id=group_id,
        session_id=data.session_id,
        app_name=data.app_name,
        bundle_id=data.bundle_id,
        category=data.category,
        started_at=data.started_at,
        ended_at=data.ended_at,
        foreground_minutes=data.foreground_minutes,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    logger.info(
        "app_usage_recorded",
        record_id=str(record.id),
        member_id=str(data.member_id),
        app_name=data.app_name,
        minutes=data.foreground_minutes,
    )

    if data.bundle_id in AI_APP_BUNDLES:
        await _publish_intelligence_event("ai_session", {
            "type": "ai_app_usage",
            "member_id": str(data.member_id),
            "app_name": data.app_name,
            "bundle_id": data.bundle_id,
            "foreground_minutes": data.foreground_minutes,
        })

    return record


async def get_app_usage_history(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    offset: int = 0,
    limit: int = 50,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[list[AppUsageRecord], int]:
    """Get app usage history for a member with optional filters."""
    base = select(AppUsageRecord).where(
        AppUsageRecord.group_id == group_id,
        AppUsageRecord.member_id == member_id,
    )

    if category:
        base = base.where(AppUsageRecord.category == category)

    if start_date:
        start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
        base = base.where(AppUsageRecord.started_at >= start_dt)

    if end_date:
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)
        base = base.where(AppUsageRecord.started_at <= end_dt)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = await db.execute(
        base.order_by(AppUsageRecord.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(rows.scalars().all()), total


# ---------------------------------------------------------------------------
# Screen Time
# ---------------------------------------------------------------------------


async def get_screen_time_summary(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    target_date: date | None = None,
) -> ScreenTimeRecord:
    """Get screen time summary for a member on a specific date."""
    if target_date is None:
        target_date = date.today()

    result = await db.execute(
        select(ScreenTimeRecord).where(
            ScreenTimeRecord.group_id == group_id,
            ScreenTimeRecord.member_id == member_id,
            ScreenTimeRecord.date == target_date,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise NotFoundError("ScreenTimeRecord")
    return record


async def get_screen_time_range(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    start_date: date,
    end_date: date,
) -> list[ScreenTimeRecord]:
    """Get screen time summaries for a date range."""
    result = await db.execute(
        select(ScreenTimeRecord).where(
            ScreenTimeRecord.group_id == group_id,
            ScreenTimeRecord.member_id == member_id,
            ScreenTimeRecord.date >= start_date,
            ScreenTimeRecord.date <= end_date,
        ).order_by(ScreenTimeRecord.date)
    )
    return list(result.scalars().all())


async def update_screen_time(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    target_date: date,
) -> ScreenTimeRecord:
    """Recalculate and update screen time summary from app usage records.

    Creates or updates the ScreenTimeRecord for the given date by aggregating
    all AppUsageRecord entries for that member on that date.
    """
    # Calculate date boundaries
    start_dt = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    end_dt = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)

    # Fetch usage records for the date
    result = await db.execute(
        select(AppUsageRecord).where(
            AppUsageRecord.group_id == group_id,
            AppUsageRecord.member_id == member_id,
            AppUsageRecord.started_at >= start_dt,
            AppUsageRecord.started_at <= end_dt,
        )
    )
    records = list(result.scalars().all())

    # Build breakdowns
    total_minutes = 0.0
    app_breakdown: dict[str, float] = {}
    category_breakdown: dict[str, float] = {}

    for rec in records:
        total_minutes += rec.foreground_minutes
        app_breakdown[rec.app_name] = app_breakdown.get(rec.app_name, 0.0) + rec.foreground_minutes
        category_breakdown[rec.category] = category_breakdown.get(rec.category, 0.0) + rec.foreground_minutes

    # Upsert screen time record
    existing = await db.execute(
        select(ScreenTimeRecord).where(
            ScreenTimeRecord.group_id == group_id,
            ScreenTimeRecord.member_id == member_id,
            ScreenTimeRecord.date == target_date,
        )
    )
    screen_time = existing.scalar_one_or_none()

    if screen_time:
        screen_time.total_minutes = total_minutes
        screen_time.app_breakdown = app_breakdown
        screen_time.category_breakdown = category_breakdown
    else:
        screen_time = ScreenTimeRecord(
            id=uuid4(),
            member_id=member_id,
            group_id=group_id,
            date=target_date,
            total_minutes=total_minutes,
            app_breakdown=app_breakdown,
            category_breakdown=category_breakdown,
            pickups=0,
        )
        db.add(screen_time)

    await db.flush()
    await db.refresh(screen_time)

    logger.info(
        "screen_time_updated",
        member_id=str(member_id),
        date=str(target_date),
        total_minutes=total_minutes,
    )
    return screen_time


# ---------------------------------------------------------------------------
# Batch Sync
# ---------------------------------------------------------------------------


async def sync_device_data(
    db: AsyncSession,
    group_id: UUID,
    data: DeviceSyncRequest,
) -> dict:
    """Batch sync device data — sessions + usage records + screen time update."""
    sessions_created = 0
    usage_created = 0
    dates_to_update: set[date] = set()

    # Record sessions
    for session_data in data.sessions:
        session_data.member_id = data.member_id
        await record_device_session(db, group_id, session_data)
        sessions_created += 1

    # Record usage
    for usage_data in data.usage_records:
        usage_data.member_id = data.member_id
        await record_app_usage(db, group_id, usage_data)
        usage_created += 1
        # Track dates that need screen time update
        usage_date = usage_data.started_at.date() if hasattr(usage_data.started_at, 'date') else usage_data.started_at
        dates_to_update.add(usage_date)

    # Update screen time for affected dates
    screen_time_updated = False
    for d in dates_to_update:
        await update_screen_time(db, group_id, data.member_id, d)
        screen_time_updated = True

    logger.info(
        "device_sync_complete",
        member_id=str(data.member_id),
        sessions=sessions_created,
        usage=usage_created,
        dates_updated=len(dates_to_update),
    )

    await _publish_intelligence_event("device", {
        "type": "device_sync",
        "member_id": str(data.member_id),
        "group_id": str(group_id),
        "sessions_count": len(data.sessions),
        "usage_count": len(data.usage_records),
    })

    return {
        "sessions_created": sessions_created,
        "usage_records_created": usage_created,
        "screen_time_updated": screen_time_updated,
    }
