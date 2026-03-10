"""Risk & safety engine API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription, resolve_group_id as _gid
from src.exceptions import ValidationError
from src.groups.models import GroupMember
from src.risk.schemas import (
    GroupScoreResponse,
    MemberScoreItem,
    RiskConfigResponse,
    RiskConfigUpdate,
    RiskEventAcknowledge,
    RiskEventListResponse,
    RiskEventResponse,
    SafetyScoreResponse,
    ScoreHistoryEntry,
    ScoreHistoryResponse,
)
from src.risk.score import (
    calculate_group_score,
    calculate_member_score,
    get_score_history,
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

router = APIRouter(dependencies=[Depends(require_active_trial_or_subscription)])


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

    # Enrich with member names
    member_ids = list({e.member_id for e in events})
    member_names: dict[UUID, str] = {}
    if member_ids:
        mr = await db.execute(
            select(GroupMember.id, GroupMember.display_name).where(
                GroupMember.id.in_(member_ids)
            )
        )
        member_names = {row[0]: row[1] for row in mr.all()}

    items = []
    for e in events:
        resp = risk_event_to_response(e)
        item = resp.model_dump()
        item["member_name"] = member_names.get(e.member_id, "Unknown")
        item["description"] = (e.details or {}).get("reasoning", e.category)
        items.append(item)

    return {
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": (offset + limit) < total,
    }


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


@router.post("/classify")
async def classify_text(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
):
    """Classify text content and return risk assessment (preview/testing)."""
    from src.risk.classifier import classify_content

    text = data.get("text", "")
    if not text:
        raise ValidationError("Text is required")
    result = await classify_content(text)
    return {
        "severity": result.severity,
        "categories": result.categories,
        "confidence": result.confidence,
        "source": result.source,
    }


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


# ---------------------------------------------------------------------------
# Safety score endpoints
# ---------------------------------------------------------------------------


@router.get("/score", response_model=SafetyScoreResponse)
async def get_member_score(
    group_id: UUID | None = Query(None, description="Group ID"),
    member_id: UUID = Query(..., description="Member ID"),
    days: int = Query(30, ge=1, le=365, description="Lookback period in days"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the safety score for a single member."""
    result = await calculate_member_score(db, _gid(group_id, auth), member_id, days)
    return SafetyScoreResponse(
        score=result.score,
        trend=result.trend,
        top_categories=result.top_categories,
        risk_count_by_severity=result.risk_count_by_severity,
        member_id=result.member_id,
        group_id=result.group_id,
    )


@router.get("/score/group", response_model=GroupScoreResponse)
async def get_group_score(
    group_id: UUID | None = Query(None, description="Group ID"),
    days: int = Query(30, ge=1, le=365, description="Lookback period in days"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the aggregate safety score for a group."""
    result = await calculate_group_score(db, _gid(group_id, auth), days)
    return GroupScoreResponse(
        average_score=result.average_score,
        group_id=result.group_id,
        member_scores=[
            MemberScoreItem(
                member_id=ms.member_id,
                score=ms.score,
                trend=ms.trend,
            )
            for ms in result.member_scores
        ],
    )


@router.get("/score/history", response_model=ScoreHistoryResponse)
async def get_member_score_history(
    group_id: UUID | None = Query(None, description="Group ID"),
    member_id: UUID = Query(..., description="Member ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily score history for a member over N days."""
    gid = _gid(group_id, auth)
    entries = await get_score_history(db, gid, member_id, days)
    return ScoreHistoryResponse(
        member_id=member_id,
        group_id=gid,
        days=days,
        history=[
            ScoreHistoryEntry(date=e.date, score=e.score)
            for e in entries
        ],
    )
