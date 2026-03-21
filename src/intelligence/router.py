"""Intelligence module FastAPI router — graph analysis, abuse signals, isolation, influence."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import resolve_group_id
from src.intelligence import schemas, service
from src.schemas import GroupContext

logger = structlog.get_logger()

router = APIRouter()


# ---------------------------------------------------------------------------
# Graph Analysis
# ---------------------------------------------------------------------------


@router.get("/graph-analysis", response_model=schemas.GraphAnalysisResponse)
async def get_graph_analysis(
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get social graph analysis for a member, including age-gap flags."""
    result = await service.run_graph_analysis(db, member_id)
    return schemas.GraphAnalysisResponse(
        member_id=member_id,
        age_gap_flags=[schemas.AgeGapFlag(**f) for f in result["age_gap_flags"]],
        total_contacts=result["total_contacts"],
        flagged_count=result["flagged_count"],
    )


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------


@router.get("/isolation", response_model=schemas.IsolationResponse)
async def get_isolation(
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get isolation analysis for a member."""
    result = await service.run_isolation_check(db, member_id)
    return schemas.IsolationResponse(
        member_id=member_id,
        isolation_score=result["isolation_score"],
        indicators=[schemas.IsolationIndicator(**i) for i in result["indicators"]],
        contact_count=result["contact_count"],
        interaction_count=result["interaction_count"],
    )


# ---------------------------------------------------------------------------
# Influence
# ---------------------------------------------------------------------------


@router.get("/influence", response_model=schemas.InfluenceResponse)
async def get_influence(
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get influence mapping for a member."""
    result = await service.run_influence_mapping(db, member_id)
    return schemas.InfluenceResponse(
        member_id=member_id,
        influencers=[schemas.Influencer(**i) for i in result["influencers"]],
        influence_score=result["influence_score"],
        total_connections=result["total_connections"],
    )


# ---------------------------------------------------------------------------
# Abuse Signals
# ---------------------------------------------------------------------------


@router.get("/abuse-signals", response_model=schemas.AbuseSignalListResponse)
async def get_abuse_signals(
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    include_resolved: bool = Query(default=False),
):
    """Get abuse signals for a member."""
    items, total = await service.get_abuse_signals(
        db, member_id, offset=offset, limit=limit,
        include_resolved=include_resolved,
    )
    return schemas.AbuseSignalListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + limit) < total,
    )


@router.post("/abuse-signals/{signal_id}/resolve", response_model=schemas.AbuseSignalResponse)
async def resolve_abuse_signal(
    signal_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark an abuse signal as resolved."""
    signal = await service.resolve_abuse_signal(db, signal_id, auth.user_id)
    await db.commit()
    return signal


# ---------------------------------------------------------------------------
# Age-Inappropriate Pattern Detection
# ---------------------------------------------------------------------------


@router.get("/age-pattern")
async def get_age_pattern(
    member_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect age-inappropriate contact patterns for a member."""
    result = await service.run_age_pattern_check(db, member_id)
    await db.commit()
    return result
