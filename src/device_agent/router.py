"""Device agent FastAPI router — sessions, app usage, screen time, sync."""

from datetime import date
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import resolve_group_id
from src.device_agent import schemas, service
from src.schemas import GroupContext

logger = structlog.get_logger()

router = APIRouter()


# ---------------------------------------------------------------------------
# Device Sessions
# ---------------------------------------------------------------------------


@router.post("/sessions", response_model=schemas.DeviceSessionResponse, status_code=201)
async def record_device_session(
    data: schemas.DeviceSessionCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
):
    """Record a device session from the safety agent."""
    gid = resolve_group_id(group_id, auth)
    session = await service.record_device_session(db, gid, data)
    await db.commit()
    return session


# ---------------------------------------------------------------------------
# App Usage
# ---------------------------------------------------------------------------


@router.post("/usage", response_model=schemas.AppUsageResponse, status_code=201)
async def record_app_usage(
    data: schemas.AppUsageCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
):
    """Record an app usage event."""
    gid = resolve_group_id(group_id, auth)
    record = await service.record_app_usage(db, gid, data)
    await db.commit()
    return record


@router.get("/usage", response_model=schemas.AppUsageListResponse)
async def get_app_usage(
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    """Get app usage history for a member."""
    gid = resolve_group_id(group_id, auth)
    items, total = await service.get_app_usage_history(
        db, gid, member_id,
        offset=offset, limit=limit,
        category=category, start_date=start_date, end_date=end_date,
    )
    return schemas.AppUsageListResponse(
        items=items, total=total, offset=offset, limit=limit,
        has_more=(offset + limit) < total,
    )


# ---------------------------------------------------------------------------
# Screen Time
# ---------------------------------------------------------------------------


@router.get("/screen-time", response_model=schemas.ScreenTimeSummary)
async def get_screen_time(
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
    target_date: date | None = None,
):
    """Get screen time summary for a member on a specific date."""
    gid = resolve_group_id(group_id, auth)
    return await service.get_screen_time_summary(db, gid, member_id, target_date)


@router.get("/screen-time/range", response_model=schemas.ScreenTimeListResponse)
async def get_screen_time_range(
    member_id: UUID,
    start_date: date,
    end_date: date,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
):
    """Get screen time summaries for a date range."""
    gid = resolve_group_id(group_id, auth)
    items = await service.get_screen_time_range(db, gid, member_id, start_date, end_date)
    return schemas.ScreenTimeListResponse(items=items, total=len(items))


# ---------------------------------------------------------------------------
# Batch Sync
# ---------------------------------------------------------------------------


@router.post("/sync", response_model=schemas.DeviceSyncResponse, status_code=201)
async def sync_device_data(
    data: schemas.DeviceSyncRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    group_id: UUID | None = None,
):
    """Batch sync device data — sessions + usage records."""
    gid = resolve_group_id(group_id, auth)
    result = await service.sync_device_data(db, gid, data)
    await db.commit()
    return schemas.DeviceSyncResponse(**result)
