"""Moderation API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.exceptions import ForbiddenError
from src.moderation.schemas import (
    ContentReportCreate,
    ContentReportResponse,
    ModerationDashboard,
    ModerationDecisionCreate,
    ModerationQueueCreate,
    ModerationQueueResponse,
    QueueListResponse,
    ReportListResponse,
    TakedownRequest,
)
from src.moderation.service import (
    create_content_report,
    get_dashboard_stats,
    get_queue_entry,
    list_queue,
    list_reports,
    process_queue_entry,
    submit_for_moderation,
    takedown_content,
)
from src.schemas import GroupContext

router = APIRouter()

# Roles allowed to process moderation decisions
_MODERATOR_ROLES = {"admin", "moderator", "parent", "owner"}


def _require_moderator(auth: GroupContext) -> None:
    """Raise ForbiddenError if user is not a moderator/admin."""
    if auth.role not in _MODERATOR_ROLES:
        raise ForbiddenError("Only moderators or admins can perform this action")


@router.post("/queue", response_model=ModerationQueueResponse, status_code=201)
async def submit_to_queue(
    data: ModerationQueueCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit content for moderation."""
    entry = await submit_for_moderation(
        db,
        content_type=data.content_type,
        content_id=data.content_id,
        author_age_tier=data.age_tier,
    )
    return entry


@router.get("/queue", response_model=QueueListResponse)
async def list_queue_endpoint(
    status: str | None = Query(None, description="Filter by status"),
    pipeline: str | None = Query(None, description="Filter by pipeline"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List moderation queue entries with optional filters."""
    result = await list_queue(db, status=status, pipeline=pipeline, page=page, page_size=page_size)
    return result


@router.get("/queue/{queue_id}", response_model=ModerationQueueResponse)
async def get_queue_entry_endpoint(
    queue_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific moderation queue entry."""
    entry = await get_queue_entry(db, queue_id)
    return entry


@router.patch("/queue/{queue_id}/decide")
async def decide_queue_entry(
    queue_id: UUID,
    data: ModerationDecisionCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve, reject, or escalate a queue entry."""
    _require_moderator(auth)
    decision = await process_queue_entry(
        db,
        queue_id=queue_id,
        action=data.action,
        moderator_id=auth.user_id,
        reason=data.reason,
    )
    return {
        "id": str(decision.id),
        "queue_id": str(decision.queue_id),
        "action": decision.action,
        "reason": decision.reason,
        "moderator_id": str(decision.moderator_id) if decision.moderator_id else None,
        "timestamp": decision.timestamp.isoformat() if decision.timestamp else None,
    }


@router.post("/takedown")
async def takedown_endpoint(
    data: TakedownRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Emergency content takedown."""
    _require_moderator(auth)
    decision = await takedown_content(
        db,
        content_type=data.content_type,
        content_id=data.content_id,
        reason=data.reason,
        moderator_id=auth.user_id,
    )
    return {
        "id": str(decision.id),
        "queue_id": str(decision.queue_id),
        "action": decision.action,
        "reason": decision.reason,
        "status": "taken_down",
    }


@router.get("/dashboard", response_model=ModerationDashboard)
async def dashboard_endpoint(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get moderation dashboard statistics."""
    stats = await get_dashboard_stats(db)
    return stats


@router.post("/reports", response_model=ContentReportResponse, status_code=201)
async def create_report_endpoint(
    data: ContentReportCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a content report."""
    report = await create_content_report(
        db,
        reporter_id=auth.user_id,
        target_type=data.target_type,
        target_id=data.target_id,
        reason=data.reason,
    )
    return report


@router.get("/reports", response_model=ReportListResponse)
async def list_reports_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List content reports. Non-moderators only see their own reports."""
    reporter_id = None
    if auth.role not in _MODERATOR_ROLES:
        reporter_id = auth.user_id
    result = await list_reports(db, reporter_id=reporter_id, page=page, page_size=page_size)
    return result
