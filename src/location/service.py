"""Location service — tracking, geofencing, kill switch, audit log, GDPR erasure."""

import math
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.encryption import decrypt_credential, encrypt_credential
from src.exceptions import NotFoundError, ValidationError
from src.intelligence import EVENT_LOCATION, publish_event
from src.location.models import (
    Geofence,
    GeofenceEvent,
    LocationAuditLog,
    LocationKillSwitch,
    LocationRecord,
    SchoolCheckIn,
)

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_GEOFENCES_PER_MEMBER = 10
MAX_HISTORY_DAYS = 30


# ---------------------------------------------------------------------------
# Haversine helper
# ---------------------------------------------------------------------------


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two points using Haversine formula."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Kill switch
# ---------------------------------------------------------------------------


async def _is_kill_switch_active(db: AsyncSession, member_id: UUID) -> bool:
    """Return True if the location kill switch is currently active for this member."""
    result = await db.execute(
        select(LocationKillSwitch).where(LocationKillSwitch.member_id == member_id)
    )
    ks = result.scalar_one_or_none()
    if ks is None:
        return False
    return ks.deactivated_at is None


async def activate_kill_switch(
    db: AsyncSession, member_id: UUID, parent_id: UUID
) -> LocationKillSwitch:
    """Activate (or re-activate) the location kill switch for a child member."""
    result = await db.execute(
        select(LocationKillSwitch).where(LocationKillSwitch.member_id == member_id)
    )
    ks = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if ks is None:
        ks = LocationKillSwitch(
            id=uuid4(),
            member_id=member_id,
            activated_by=parent_id,
            activated_at=now,
            deactivated_at=None,
        )
        db.add(ks)
    else:
        ks.activated_by = parent_id
        ks.activated_at = now
        ks.deactivated_at = None

    await db.flush()
    await db.refresh(ks)

    logger.info("kill_switch_activated", member_id=str(member_id), parent_id=str(parent_id))
    return ks


async def deactivate_kill_switch(
    db: AsyncSession, member_id: UUID, parent_id: UUID
) -> LocationKillSwitch:
    """Deactivate the location kill switch for a child member."""
    result = await db.execute(
        select(LocationKillSwitch).where(LocationKillSwitch.member_id == member_id)
    )
    ks = result.scalar_one_or_none()
    if ks is None:
        raise NotFoundError("LocationKillSwitch")

    ks.deactivated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(ks)

    logger.info("kill_switch_deactivated", member_id=str(member_id), parent_id=str(parent_id))
    return ks


async def get_kill_switch_status(
    db: AsyncSession, member_id: UUID
) -> LocationKillSwitch | None:
    """Return the current kill switch record for a member, or None if never set."""
    result = await db.execute(
        select(LocationKillSwitch).where(LocationKillSwitch.member_id == member_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Location reporting
# ---------------------------------------------------------------------------


async def report_location(
    db: AsyncSession,
    member_id: UUID,
    group_id: UUID,
    lat: float,
    lng: float,
    accuracy: float,
    source: str,
    recorded_at: datetime | None = None,
) -> LocationRecord | None:
    """Record a location data point from the device agent.

    Returns None silently if the kill switch is active (privacy control).
    Encrypts lat/lng before storage and publishes to the intelligence event bus.
    """
    if await _is_kill_switch_active(db, member_id):
        logger.info("location_report_blocked_kill_switch", member_id=str(member_id))
        return None

    if recorded_at is None:
        recorded_at = datetime.now(timezone.utc)

    record = LocationRecord(
        id=uuid4(),
        member_id=member_id,
        group_id=group_id,
        latitude=encrypt_credential(str(lat)),
        longitude=encrypt_credential(str(lng)),
        accuracy=accuracy,
        source=source,
        recorded_at=recorded_at,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    # Publish to intelligence event bus (gracefully degrades if Redis unavailable)
    await publish_event(EVENT_LOCATION, {
        "member_id": str(member_id),
        "group_id": str(group_id),
        "source": source,
        "recorded_at": recorded_at.isoformat(),
    })

    logger.info(
        "location_reported",
        record_id=str(record.id),
        member_id=str(member_id),
        source=source,
    )
    return record


# ---------------------------------------------------------------------------
# Audit log helper
# ---------------------------------------------------------------------------


async def _create_audit_log(
    db: AsyncSession, member_id: UUID, accessor_id: UUID, data_type: str
) -> None:
    """Create a LocationAuditLog entry for every location data access."""
    log = LocationAuditLog(
        id=uuid4(),
        member_id=member_id,
        accessor_id=accessor_id,
        data_type=data_type,
        accessed_at=datetime.now(timezone.utc),
    )
    db.add(log)
    await db.flush()


# ---------------------------------------------------------------------------
# Location reading
# ---------------------------------------------------------------------------


async def get_current_location(
    db: AsyncSession, member_id: UUID, accessor_id: UUID
) -> dict | None:
    """Get the latest location record with decrypted coordinates.

    Creates an audit log entry on every access.
    Returns None if no location has been recorded yet.
    """
    result = await db.execute(
        select(LocationRecord)
        .where(LocationRecord.member_id == member_id)
        .order_by(LocationRecord.recorded_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None

    # Audit every access
    await _create_audit_log(db, member_id, accessor_id, "current")

    return {
        "id": record.id,
        "member_id": record.member_id,
        "group_id": record.group_id,
        "latitude": float(decrypt_credential(record.latitude)),
        "longitude": float(decrypt_credential(record.longitude)),
        "accuracy": record.accuracy,
        "source": record.source,
        "recorded_at": record.recorded_at,
        "created_at": record.created_at,
    }


async def get_location_history(
    db: AsyncSession,
    member_id: UUID,
    accessor_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    """Get paginated location history with decrypted coordinates.

    Max 30 days of history. Creates an audit log entry.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_HISTORY_DAYS)

    if start_date is None:
        start_date = cutoff
    else:
        # Enforce max 30 days
        start_date = max(start_date, cutoff)

    if end_date is None:
        end_date = now

    base = select(LocationRecord).where(
        LocationRecord.member_id == member_id,
        LocationRecord.recorded_at >= start_date,
        LocationRecord.recorded_at <= end_date,
    )

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = await db.execute(
        base.order_by(LocationRecord.recorded_at.desc()).offset(offset).limit(limit)
    )
    records = list(rows.scalars().all())

    # Audit the history access
    await _create_audit_log(db, member_id, accessor_id, "history")

    items = [
        {
            "id": r.id,
            "member_id": r.member_id,
            "group_id": r.group_id,
            "latitude": float(decrypt_credential(r.latitude)),
            "longitude": float(decrypt_credential(r.longitude)),
            "accuracy": r.accuracy,
            "source": r.source,
            "recorded_at": r.recorded_at,
            "created_at": r.created_at,
        }
        for r in records
    ]

    return items, total


# ---------------------------------------------------------------------------
# Geofence management
# ---------------------------------------------------------------------------


async def create_geofence(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    name: str,
    lat: float,
    lng: float,
    radius: float,
    notify_enter: bool = True,
    notify_exit: bool = True,
) -> Geofence:
    """Create a new geofence for a child. Enforces max 10 per child."""
    count_result = await db.execute(
        select(func.count()).where(
            Geofence.group_id == group_id,
            Geofence.member_id == member_id,
        )
    )
    count = count_result.scalar() or 0
    if count >= MAX_GEOFENCES_PER_MEMBER:
        raise ValidationError(
            f"Maximum of {MAX_GEOFENCES_PER_MEMBER} geofences per child exceeded. "
            "Delete an existing geofence to create a new one."
        )

    fence = Geofence(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        name=name,
        latitude=lat,
        longitude=lng,
        radius_meters=radius,
        notify_on_enter=notify_enter,
        notify_on_exit=notify_exit,
    )
    db.add(fence)
    await db.flush()
    await db.refresh(fence)

    logger.info(
        "geofence_created",
        geofence_id=str(fence.id),
        member_id=str(member_id),
        name=name,
    )
    return fence


async def list_geofences(
    db: AsyncSession, group_id: UUID, member_id: UUID
) -> list[Geofence]:
    """List all geofences for a child."""
    result = await db.execute(
        select(Geofence)
        .where(Geofence.group_id == group_id, Geofence.member_id == member_id)
        .order_by(Geofence.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_geofence(db: AsyncSession, geofence_id: UUID) -> None:
    """Hard-delete a geofence and its associated events."""
    result = await db.execute(select(Geofence).where(Geofence.id == geofence_id))
    fence = result.scalar_one_or_none()
    if fence is None:
        raise NotFoundError("Geofence")

    await db.delete(fence)
    await db.flush()

    logger.info("geofence_deleted", geofence_id=str(geofence_id))


# ---------------------------------------------------------------------------
# Geofence boundary check
# ---------------------------------------------------------------------------


async def check_geofence(
    db: AsyncSession, member_id: UUID, lat: float, lng: float
) -> list[dict]:
    """Check if the member's location triggers any geofence boundaries.

    Uses Haversine distance. Creates GeofenceEvent records for crossings.
    Returns list of triggered geofence info dicts.
    """
    result = await db.execute(
        select(Geofence).where(Geofence.member_id == member_id)
    )
    fences = list(result.scalars().all())

    triggered = []
    now = datetime.now(timezone.utc)

    for fence in fences:
        distance = haversine_distance(lat, lng, fence.latitude, fence.longitude)
        if distance <= fence.radius_meters:
            # Child is inside the fence — record an "enter" event
            geo_event = GeofenceEvent(
                id=uuid4(),
                geofence_id=fence.id,
                member_id=member_id,
                event_type="enter",
                recorded_at=now,
            )
            db.add(geo_event)
            await db.flush()

            triggered.append({
                "geofence_id": fence.id,
                "geofence_name": fence.name,
                "event_type": "enter",
                "distance_meters": distance,
            })

            logger.info(
                "geofence_triggered",
                geofence_id=str(fence.id),
                member_id=str(member_id),
                event_type="enter",
                distance_meters=round(distance, 2),
            )

    return triggered


# ---------------------------------------------------------------------------
# GDPR Article 17 — right to erasure
# ---------------------------------------------------------------------------


async def delete_location_history(db: AsyncSession, member_id: UUID) -> dict:
    """GDPR Article 17: delete all LocationRecords and SchoolCheckIns for a member.

    Scheduled to complete within 24h (compliance requirement). In this
    implementation the deletion is synchronous and immediate.
    """
    # Delete all location records
    records_result = await db.execute(
        delete(LocationRecord).where(LocationRecord.member_id == member_id)
    )
    records_deleted = records_result.rowcount

    # Delete school check-ins
    checkins_result = await db.execute(
        delete(SchoolCheckIn).where(SchoolCheckIn.member_id == member_id)
    )
    checkins_deleted = checkins_result.rowcount

    # Delete audit logs (part of complete erasure)
    await db.execute(
        delete(LocationAuditLog).where(LocationAuditLog.member_id == member_id)
    )

    # Delete geofence events for this member
    await db.execute(
        delete(GeofenceEvent).where(GeofenceEvent.member_id == member_id)
    )

    await db.flush()

    logger.info(
        "gdpr_erasure_complete",
        member_id=str(member_id),
        records_deleted=records_deleted,
        checkins_deleted=checkins_deleted,
    )

    return {
        "member_id": member_id,
        "records_deleted": records_deleted,
        "checkins_deleted": checkins_deleted,
        "status": "erased",
    }


# ---------------------------------------------------------------------------
# Cron helper — purge expired records
# ---------------------------------------------------------------------------


async def purge_expired_locations(db: AsyncSession) -> int:
    """Cron helper: delete LocationRecords older than 30 days.

    Returns the number of records deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_HISTORY_DAYS)
    # Use naive cutoff for SQLite compatibility (aiosqlite stores without tz)
    cutoff_naive = cutoff.replace(tzinfo=None)
    result = await db.execute(
        delete(LocationRecord).where(
            LocationRecord.recorded_at < cutoff_naive
        )
    )
    count = result.rowcount
    await db.flush()

    logger.info("purge_expired_locations", deleted=count, cutoff=cutoff.isoformat())
    return count


# ---------------------------------------------------------------------------
# Audit log retrieval
# ---------------------------------------------------------------------------


async def get_audit_log(
    db: AsyncSession,
    member_id: UUID,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[LocationAuditLog], int]:
    """Get paginated audit log for a member's location data accesses."""
    base = select(LocationAuditLog).where(LocationAuditLog.member_id == member_id)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = await db.execute(
        base.order_by(LocationAuditLog.accessed_at.desc()).offset(offset).limit(limit)
    )
    return list(rows.scalars().all()), total
