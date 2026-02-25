"""Alerts API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.schemas import (
    AlertResponse,
    PreferenceResponse,
    PreferenceUpdate,
)
from src.alerts.service import (
    acknowledge_alert,
    get_alert,
    get_preferences,
    list_alerts,
    update_preferences,
)
from src.auth.middleware import get_current_user
from src.database import get_db
from src.schemas import GroupContext

router = APIRouter()


@router.get("", response_model=list[AlertResponse])
async def list_alerts_endpoint(
    group_id: UUID = Query(..., description="Group ID to list alerts for"),
    severity: str | None = Query(None, description="Filter by severity"),
    status: str | None = Query(None, description="Filter by status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts for a group (FR-021)."""
    alerts = await list_alerts(db, group_id, severity=severity, status=status, offset=offset, limit=limit)
    return alerts


# Static paths MUST come before /{alert_id} to avoid "preferences" being parsed as UUID
@router.get("/preferences", response_model=list[PreferenceResponse])
async def get_preferences_endpoint(
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notification preferences for the current user in a group."""
    prefs = await get_preferences(db, group_id, auth.user_id)
    return prefs


@router.put("/preferences", response_model=list[PreferenceResponse])
async def update_preferences_endpoint(
    data: PreferenceUpdate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update notification preferences (FR-023)."""
    prefs = await update_preferences(db, data.group_id, auth.user_id, data.preferences)
    return prefs


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert_endpoint(
    alert_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific alert."""
    alert = await get_alert(db, alert_id)
    return alert


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert_endpoint(
    alert_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge an alert (FR-022)."""
    alert = await acknowledge_alert(db, alert_id, auth.user_id)
    return alert
