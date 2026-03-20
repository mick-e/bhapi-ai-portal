"""Analytics API endpoints."""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.academic import (
    classify_prompt_intent,
    generate_academic_report,
)
from src.analytics.schemas import AcademicReportResponse, IntentClassificationResponse
from src.analytics.service import (
    detect_anomalies,
    get_member_baselines,
    get_peer_comparison,
    get_trends,
    get_usage_patterns,
)
from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription
from src.dependencies import resolve_group_id as _gid
from src.exceptions import ValidationError
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


# ---------------------------------------------------------------------------
# Academic Integrity
# ---------------------------------------------------------------------------


@router.get("/academic", response_model=AcademicReportResponse)
async def academic_report(
    group_id: UUID | None = Query(None, description="Group ID"),
    member_id: UUID = Query(..., description="Member ID"),
    start_date: date | None = Query(None, description="Period start (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Period end (YYYY-MM-DD)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an academic integrity report for a member."""
    gid = _gid(group_id, auth)

    today = date.today()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = end_date - timedelta(days=7)

    if start_date > end_date:
        raise ValidationError("start_date must be before end_date")

    report = await generate_academic_report(db, gid, member_id, start_date, end_date)

    return AcademicReportResponse(
        member_id=report.member_id,
        period_start=report.period_start,
        period_end=report.period_end,
        total_ai_sessions=report.total_ai_sessions,
        study_hour_sessions=report.study_hour_sessions,
        learning_count=report.learning_count,
        doing_count=report.doing_count,
        unclassified_count=report.unclassified_count,
        learning_ratio=report.learning_ratio,
        top_subjects=report.top_subjects,
        daily_breakdown=[
            {"date": d["date"], "learning": d["learning"], "doing": d["doing"], "unclassified": d["unclassified"]}
            for d in report.daily_breakdown
        ],
        recommendation=report.recommendation,
    )


class IntentClassifyRequest(BaseModel):
    text: str


@router.get("/academic/intent", response_model=IntentClassificationResponse)
async def classify_intent(
    text: str = Query(..., min_length=1, description="Prompt text to classify"),
    auth: GroupContext = Depends(get_current_user),
):
    """Classify a single prompt text for testing purposes."""
    intent = await classify_prompt_intent(text)
    return IntentClassificationResponse(text=text, intent=intent)
