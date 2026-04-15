"""Risk & safety engine API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription
from src.dependencies import resolve_group_id as _gid
from src.exceptions import ValidationError
from src.groups.models import GroupMember
from src.risk.deepfake_guidance import get_deepfake_guidance
from src.risk.schemas import (
    DependencyHistoryEntry,
    DependencyHistoryResponse,
    DependencyScoreResponse,
    GroupScoreResponse,
    MemberScoreItem,
    PlatformRatingsListResponse,
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
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
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
        page=page,
        page_size=page_size,
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

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
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


# ---------------------------------------------------------------------------
# Emotional dependency endpoints
# ---------------------------------------------------------------------------


@router.get("/dependency-score", response_model=DependencyScoreResponse)
async def get_dependency_score(
    group_id: UUID | None = Query(None, description="Group ID"),
    member_id: UUID = Query(..., description="Member ID"),
    days: int = Query(30, ge=1, le=365, description="Lookback period in days"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the emotional dependency score for a member."""
    from src.risk.emotional_dependency import calculate_dependency_score

    gid = _gid(group_id, auth)
    result = await calculate_dependency_score(db, gid, member_id, days)
    return DependencyScoreResponse(
        score=result.score,
        session_duration_score=result.session_duration_score,
        frequency_score=result.frequency_score,
        attachment_language_score=result.attachment_language_score,
        time_pattern_score=result.time_pattern_score,
        trend=result.trend,
        risk_factors=result.risk_factors,
        platform_breakdown=result.platform_breakdown,
        recommendation=result.recommendation,
    )


@router.get("/dependency-score/history", response_model=DependencyHistoryResponse)
async def get_dependency_score_history(
    group_id: UUID | None = Query(None, description="Group ID"),
    member_id: UUID = Query(..., description="Member ID"),
    days: int = Query(90, ge=7, le=365, description="Number of days of history"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get weekly dependency score history for a member."""
    from src.risk.emotional_dependency import get_dependency_history

    gid = _gid(group_id, auth)
    entries = await get_dependency_history(db, gid, member_id, days)
    return DependencyHistoryResponse(
        member_id=member_id,
        group_id=gid,
        days=days,
        history=[
            DependencyHistoryEntry(
                week_start=e["week_start"],
                week_end=e["week_end"],
                score=e["score"],
            )
            for e in entries
        ],
    )


# ---------------------------------------------------------------------------
# Public endpoints (no auth)
# ---------------------------------------------------------------------------

public_router = APIRouter()


@public_router.get("/platform-ratings", response_model=PlatformRatingsListResponse)
async def platform_ratings_endpoint(
    db: AsyncSession = Depends(get_db),
):
    """Return safety ratings for monitored AI platforms. Public, no auth required."""
    from src.risk.platform_ratings import get_platform_ratings

    ratings = await get_platform_ratings(db)
    return PlatformRatingsListResponse(platforms=ratings)


@public_router.get("/deepfake-guidance")
async def deepfake_guidance_endpoint():
    """Return parent-facing deepfake education content. Public, no auth required."""
    return await get_deepfake_guidance()


# ─── Enterprise Policies ────────────────────────────────────────────────────


@router.post("/policies", status_code=201)
async def create_policy_endpoint(
    data: dict,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an AI usage policy."""
    from src.dependencies import resolve_group_id as _gid2
    from src.risk.enterprise_policy import create_policy
    gid = _gid2(None, auth)
    policy = await create_policy(
        db, group_id=gid, name=data.get("name", ""),
        policy_type=data.get("policy_type", "acceptable_use"),
        description=data.get("description"),
        rules=data.get("rules"),
        enforcement_level=data.get("enforcement_level", "warn"),
        applies_to=data.get("applies_to"),
    )
    return {"id": str(policy.id), "name": policy.name, "active": policy.active}


@router.get("/policies")
async def list_policies_endpoint(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List AI usage policies."""
    from src.risk.enterprise_policy import list_policies
    gid = _gid(None, auth)
    policies = await list_policies(db, gid)
    return {"policies": [
        {"id": str(p.id), "name": p.name, "policy_type": p.policy_type,
         "enforcement_level": p.enforcement_level, "active": p.active}
        for p in policies
    ]}


@router.get("/violations")
async def list_violations_endpoint(
    resolved: bool | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List policy violations."""
    from src.risk.enterprise_policy import list_violations
    gid = _gid(None, auth)
    violations = await list_violations(db, gid, resolved=resolved)
    return {"violations": [
        {"id": str(v.id), "violation_type": v.violation_type, "severity": v.severity,
         "action_taken": v.action_taken, "resolved": v.resolved}
        for v in violations
    ]}
