"""Analytics API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.service import (
    detect_anomalies,
    get_member_baselines,
    get_peer_comparison,
    get_trends,
    get_usage_patterns,
)
from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription, resolve_group_id as _gid
from src.schemas import GroupContext

router = APIRouter(dependencies=[Depends(require_active_trial_or_subscription)])


@router.get("/trends")
async def trends(
    group_id: UUID | None = Query(None),
    days: int = Query(30, ge=7, le=90),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get activity and risk trend data."""
    return await get_trends(db, _gid(group_id, auth), days)


@router.get("/usage-patterns")
async def usage_patterns(
    group_id: UUID | None = Query(None),
    days: int = Query(30, ge=7, le=90),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get usage patterns by time and platform."""
    return await get_usage_patterns(db, _gid(group_id, auth), days)


@router.get("/member-baselines")
async def member_baselines(
    group_id: UUID | None = Query(None),
    days: int = Query(30, ge=7, le=90),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get per-member behavior baselines."""
    return await get_member_baselines(db, _gid(group_id, auth), days)


@router.get("/peer-comparison")
async def peer_comparison(
    group_id: UUID | None = Query(None),
    days: int = Query(30, ge=7, le=90),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get peer comparison percentile ranks per member."""
    return await get_peer_comparison(db, _gid(group_id, auth), days)


@router.get("/anomalies")
async def anomalies(
    group_id: UUID | None = Query(None),
    threshold_sd: float = Query(2.0, ge=1.0, le=5.0),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect anomalous usage patterns."""
    return await detect_anomalies(db, _gid(group_id, auth), threshold_sd)
