"""Location FastAPI router — tracking, geofencing, kill switch, audit log, GDPR."""

from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.billing.feature_gate import check_feature_gate
from src.database import get_db
from src.dependencies import resolve_group_id
from src.location import schemas, service
from src.schemas import GroupContext

logger = structlog.get_logger()

router = APIRouter()

_FEATURE = "location_tracking"


# ---------------------------------------------------------------------------
# Location Reporting
# ---------------------------------------------------------------------------


@router.post("/report", response_model=schemas.LocationRecordResponse | None, status_code=201)
async def report_location(
    data: schemas.LocationReportCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
    _gate: None = Depends(check_feature_gate(_FEATURE)),
):
    """Device agent reports a location data point (batch, signed).

    Returns None (204 effectively) if the kill switch is active.
    """
    gid = resolve_group_id(group_id, auth)
    record = await service.report_location(
        db,
        member_id=data.member_id,
        group_id=gid,
        lat=data.latitude,
        lng=data.longitude,
        accuracy=data.accuracy,
        source=data.source,
        recorded_at=data.recorded_at,
    )
    await db.commit()
    return record


# ---------------------------------------------------------------------------
# Current Location
# ---------------------------------------------------------------------------


@router.get("/{child_id}/current")
async def get_current_location(
    child_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate(_FEATURE)),
):
    """Parent: get the latest location for a child (decrypted coordinates)."""
    location = await service.get_current_location(db, member_id=child_id, accessor_id=auth.user_id)
    await db.commit()
    return location


# ---------------------------------------------------------------------------
# Location History
# ---------------------------------------------------------------------------


@router.get("/{child_id}/history")
async def get_location_history(
    child_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _gate: None = Depends(check_feature_gate(_FEATURE)),
):
    """Parent: 30-day paginated location history (decrypted)."""
    items, total = await service.get_location_history(
        db,
        member_id=child_id,
        accessor_id=auth.user_id,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
    )
    await db.commit()
    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": (offset + limit) < total,
    }


# ---------------------------------------------------------------------------
# Geofences
# ---------------------------------------------------------------------------


@router.post("/geofences", response_model=schemas.GeofenceResponse, status_code=201)
async def create_geofence(
    data: schemas.GeofenceCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
    _gate: None = Depends(check_feature_gate(_FEATURE)),
):
    """Parent: create a geofence boundary (max 10 per child)."""
    gid = resolve_group_id(group_id, auth)
    fence = await service.create_geofence(
        db,
        group_id=gid,
        member_id=data.member_id,
        name=data.name,
        lat=data.latitude,
        lng=data.longitude,
        radius=data.radius_meters,
        notify_enter=data.notify_on_enter,
        notify_exit=data.notify_on_exit,
    )
    await db.commit()
    await db.refresh(fence)
    return fence


@router.get("/geofences", response_model=schemas.GeofenceListResponse)
async def list_geofences(
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
    _gate: None = Depends(check_feature_gate(_FEATURE)),
):
    """Parent: list all geofences for a child."""
    gid = resolve_group_id(group_id, auth)
    fences = await service.list_geofences(db, group_id=gid, member_id=member_id)
    return schemas.GeofenceListResponse(items=fences, total=len(fences))


@router.delete("/geofences/{geofence_id}", status_code=204)
async def delete_geofence(
    geofence_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate(_FEATURE)),
):
    """Parent: remove a geofence."""
    await service.delete_geofence(db, geofence_id=geofence_id)
    await db.commit()


# ---------------------------------------------------------------------------
# Kill Switch
# ---------------------------------------------------------------------------


@router.post("/{child_id}/kill-switch", response_model=schemas.KillSwitchResponse, status_code=201)
async def activate_kill_switch(
    child_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate(_FEATURE)),
):
    """Parent: immediately disable all location tracking for a child."""
    ks = await service.activate_kill_switch(db, member_id=child_id, parent_id=auth.user_id)
    await db.commit()
    await db.refresh(ks)
    return ks


@router.delete("/{child_id}/kill-switch", status_code=204)
async def deactivate_kill_switch(
    child_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate(_FEATURE)),
):
    """Parent: re-enable location tracking for a child."""
    await service.deactivate_kill_switch(db, member_id=child_id, parent_id=auth.user_id)
    await db.commit()


@router.get("/{child_id}/kill-switch", response_model=schemas.KillSwitchResponse | None)
async def get_kill_switch_status(
    child_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate(_FEATURE)),
):
    """Get current kill switch status for a child."""
    return await service.get_kill_switch_status(db, member_id=child_id)


# ---------------------------------------------------------------------------
# GDPR Erasure
# ---------------------------------------------------------------------------


@router.delete("/{child_id}/history", status_code=200)
async def delete_location_history(
    child_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _gate: None = Depends(check_feature_gate(_FEATURE)),
):
    """Parent: purge all location data for a child (GDPR Article 17 erasure)."""
    result = await service.delete_location_history(db, member_id=child_id)
    await db.commit()
    return result


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------


@router.get("/{child_id}/audit-log", response_model=schemas.AuditLogListResponse)
async def get_audit_log(
    child_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _gate: None = Depends(check_feature_gate(_FEATURE)),
):
    """Parent: who accessed location data and when."""
    items, total = await service.get_audit_log(db, member_id=child_id, offset=offset, limit=limit)
    return schemas.AuditLogListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + limit) < total,
    )
