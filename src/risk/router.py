"""Risk & safety engine API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import resolve_group_id as _gid
from src.risk.schemas import (
    RiskConfigResponse,
    RiskConfigUpdate,
    RiskEventAcknowledge,
    RiskEventListResponse,
    RiskEventResponse,
)
from src.risk.service import (
    acknowledge_risk_event,
    get_risk_config,
    get_risk_event,
    list_risk_events,
    risk_config_to_response,
    risk_event_to_response,
    update_risk_config,
)
from src.schemas import GroupContext

router = APIRouter()


@router.get("/events", response_model=RiskEventListResponse)
async def list_events(
    group_id: UUID | None = Query(None, description="Group ID to filter events"),
    category: str | None = Query(None, description="Filter by risk category"),
    severity: str | None = Query(None, description="Filter by severity level"),
    member_id: UUID | None = Query(None, description="Filter by member ID"),
    acknowledged: bool | None = Query(None, description="Filter by acknowledgement status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List risk events for a group with optional filters."""
    events, total = await list_risk_events(
        db,
        group_id=_gid(group_id, auth),
        category=category,
        severity=severity,
        member_id=member_id,
        acknowledged=acknowledged,
        limit=limit,
        offset=offset,
    )
    return RiskEventListResponse(
        items=[risk_event_to_response(e) for e in events],
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + limit) < total,
    )


@router.get("/events/{event_id}", response_model=RiskEventResponse)
async def get_event(
    event_id: UUID,
    group_id: UUID | None = Query(None, description="Group ID for access control"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single risk event by ID."""
    event = await get_risk_event(db, event_id, _gid(group_id, auth))
    return risk_event_to_response(event)


@router.post("/events/{event_id}/acknowledge", response_model=RiskEventResponse)
async def acknowledge_event(
    event_id: UUID,
    data: RiskEventAcknowledge,
    group_id: UUID | None = Query(None, description="Group ID for access control"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge a risk event."""
    event = await acknowledge_risk_event(db, event_id, _gid(group_id, auth), data)
    return risk_event_to_response(event)


@router.get("/config", response_model=list[RiskConfigResponse])
async def get_config(
    group_id: UUID | None = Query(None, description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all risk category configurations for a group."""
    configs = await get_risk_config(db, _gid(group_id, auth))
    return [risk_config_to_response(c) for c in configs]


@router.patch("/config/{category}", response_model=RiskConfigResponse)
async def update_config(
    category: str,
    data: RiskConfigUpdate,
    group_id: UUID | None = Query(None, description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update risk configuration for a specific category."""
    config = await update_risk_config(db, _gid(group_id, auth), category, data)
    return risk_config_to_response(config)
