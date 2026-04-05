"""Moderation API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.exceptions import ForbiddenError
from src.moderation.schemas import (
    AppealCreate,
    AppealDecisionRequest,
    AppealResponse,
    AssignModeratorRequest,
    AssignModeratorResponse,
    BulkActionRequest,
    BulkActionResponse,
    ContentReportCreate,
    ContentReportResponse,
    ContentReportStatusUpdate,
    ModerationDashboard,
    ModerationDecisionCreate,
    ModerationQueueCreate,
    ModerationQueueResponse,
    PatternsResponse,
    QueueListResponse,
    ReportListResponse,
    SLAMetricsResponse,
    TakedownRequest,
)
from src.moderation.service import (
    REPORT_REASON_LABELS,
    ReportReason,
    create_appeal,
    create_content_report,
    decide_appeal,
    get_dashboard_stats,
    get_queue_entry,
    get_report,
    list_queue,
    list_reports,
    process_queue_entry,
    submit_for_moderation,
    takedown_content,
    update_report_status,
)
from src.moderation.sla_schemas import SLAMetrics
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
        content_text=data.content_text,
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


# ---------------------------------------------------------------------------
# Appeal endpoints
# ---------------------------------------------------------------------------


@router.post("/queue/{queue_id}/appeal", response_model=AppealResponse, status_code=201)
async def appeal_queue_entry(
    queue_id: UUID,
    data: AppealCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Appeal a moderation decision.

    Any authenticated user can appeal once per queue item.
    The queue entry must be in 'rejected' status.
    Creates an escalated entry for human re-review.
    """
    appeal = await create_appeal(
        db,
        queue_id=queue_id,
        appellant_id=auth.user_id,
        reason=data.reason,
    )
    return appeal


@router.patch("/appeals/{appeal_id}/decide", response_model=AppealResponse)
async def decide_appeal_endpoint(
    appeal_id: UUID,
    data: AppealDecisionRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept or deny an appeal (moderators only)."""
    _require_moderator(auth)
    appeal = await decide_appeal(
        db,
        appeal_id=appeal_id,
        decision=data.decision,
        reviewer_id=auth.user_id,
        review_note=data.review_note,
    )
    return appeal


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


# ---------------------------------------------------------------------------
# Dashboard endpoints — queue assignment, bulk actions, SLA, patterns
# ---------------------------------------------------------------------------


@router.post("/queue/{queue_id}/assign", response_model=AssignModeratorResponse)
async def assign_moderator_endpoint(
    queue_id: UUID,
    data: AssignModeratorRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a moderator to a queue item."""
    _require_moderator(auth)
    from src.moderation.dashboard_service import assign_moderator

    assignment = await assign_moderator(db, queue_id=queue_id, moderator_id=data.moderator_id)
    return assignment


@router.post("/bulk-action", response_model=BulkActionResponse)
async def bulk_action_endpoint(
    data: BulkActionRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Perform a bulk moderation action on multiple queue items."""
    _require_moderator(auth)
    from src.moderation.dashboard_service import bulk_action

    result = await bulk_action(
        db,
        queue_ids=data.queue_ids,
        action=data.action,
        moderator_id=auth.user_id,
        reason=data.reason,
    )
    return result


@router.get("/sla", response_model=SLAMetricsResponse)
async def sla_metrics_endpoint(
    pipeline: str | None = Query(None, description="Filter by pipeline"),
    hours: int = Query(24, ge=1, le=720, description="Lookback window in hours"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get SLA metrics for moderation pipelines."""
    from src.moderation.dashboard_service import get_sla_metrics

    metrics = await get_sla_metrics(db, pipeline=pipeline, hours=hours)
    return metrics


@router.get("/sla/live", response_model=SLAMetrics)
async def sla_live_endpoint(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SLAMetrics:
    """Get live SLA metrics for the moderation pipeline dashboard.

    Returns flat p50/p95 latency for pre-publish and post-publish pipelines,
    current queue depth, oldest pending item age, breach count and total
    reviewed in the last 24 hours.
    """
    from src.moderation.sla_service import get_sla_metrics as get_live_sla_metrics

    return await get_live_sla_metrics(db)


@router.get("/patterns", response_model=PatternsResponse)
async def patterns_endpoint(
    hours: int = Query(24, ge=1, le=720, description="Lookback window in hours"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detect content moderation patterns."""
    from src.moderation.dashboard_service import detect_patterns

    patterns = await detect_patterns(db, hours=hours)
    return {"patterns": patterns, "total": len(patterns)}


@router.get("/reports/reasons")
async def list_report_reasons():
    """Get the taxonomy of report reasons with age-appropriate labels."""
    return {
        "reasons": [
            {"value": r.value, "label": REPORT_REASON_LABELS[r]}
            for r in ReportReason
        ]
    }


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
        description=data.description,
    )
    return report


@router.get("/reports/{report_id}", response_model=ContentReportResponse)
async def get_report_endpoint(
    report_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific content report."""
    report = await get_report(db, report_id)
    # Non-moderators can only see their own reports
    if auth.role not in _MODERATOR_ROLES and report.reporter_id != auth.user_id:
        raise ForbiddenError("You can only view your own reports")
    return report


@router.patch("/reports/{report_id}/status", response_model=ContentReportResponse)
async def update_report_status_endpoint(
    report_id: UUID,
    data: ContentReportStatusUpdate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a report's status (moderators only)."""
    _require_moderator(auth)
    report = await update_report_status(
        db,
        report_id=report_id,
        new_status=data.status,
        moderator_id=auth.user_id,
    )
    return report


@router.post("/webhooks/cloudflare-images")
async def cloudflare_images_webhook(
    request: Request,
):
    """Handle Cloudflare Images ready webhook.

    This endpoint is public (no auth) — protected by webhook signature validation.
    """
    from src.moderation.image_pipeline import pipeline

    body = await request.body()
    signature = request.headers.get("cf-webhook-auth", "")

    if not pipeline.verify_cf_signature(body, signature):
        raise ForbiddenError("Invalid webhook signature")

    payload = await request.json()
    result = await pipeline.handle_cf_images_webhook(payload)
    return result


@router.post("/webhooks/cloudflare-stream")
async def cloudflare_stream_webhook(
    request: Request,
):
    """Handle Cloudflare Stream ready webhook.

    This endpoint is public (no auth) — protected by webhook signature validation.
    """
    from src.moderation.video_pipeline import pipeline as video_pipeline

    payload = await request.json()
    result = await video_pipeline.handle_cf_stream_webhook(payload)
    return result


# ---------------------------------------------------------------------------
# eSafety Commissioner endpoints (Australian compliance)
# ---------------------------------------------------------------------------


@router.post("/esafety/complaints")
async def submit_esafety_complaint(
    body: dict,
    auth: GroupContext = Depends(get_current_user),
):
    """Submit a complaint to the eSafety Commissioner."""
    from src.moderation.esafety import ESafetyCategory
    from src.moderation.esafety import pipeline as esafety

    _require_moderator(auth)

    content_id = body.get("content_id")
    category = body.get("category")
    evidence = body.get("evidence", "")

    if not content_id or not category:
        from src.exceptions import ValidationError
        raise ValidationError("content_id and category are required")

    try:
        cat = ESafetyCategory(category)
    except ValueError:
        from src.exceptions import ValidationError
        raise ValidationError(f"Invalid category: {category}")

    result = await esafety.submit_complaint(
        content_id=content_id,
        category=cat,
        evidence_description=evidence,
        reporter_info=body.get("reporter_info"),
    )
    return {
        "complaint_id": result.complaint_id,
        "status": result.status,
        "deadline": result.takedown_deadline.isoformat(),
    }


@router.post("/esafety/takedown/{content_id}")
async def mark_esafety_takedown(
    content_id: str,
    auth: GroupContext = Depends(get_current_user),
):
    """Mark content as taken down for eSafety SLA tracking."""
    from src.moderation.esafety import pipeline as esafety

    _require_moderator(auth)
    found = esafety.mark_taken_down(content_id)
    if not found:
        from src.exceptions import NotFoundError
        raise NotFoundError(f"No pending takedown for content {content_id}")
    return {"status": "taken_down", "content_id": content_id}


@router.get("/esafety/status/{content_id}")
async def get_esafety_status(
    content_id: str,
    auth: GroupContext = Depends(get_current_user),
):
    """Get takedown SLA status for a specific content item."""
    from src.moderation.esafety import pipeline as esafety

    status = esafety.get_takedown_status(content_id)
    if not status:
        from src.exceptions import NotFoundError
        raise NotFoundError(f"No takedown record for content {content_id}")
    return {
        "content_id": status.content_id,
        "deadline": status.deadline.isoformat(),
        "is_overdue": status.is_overdue,
        "time_remaining_seconds": status.time_remaining_seconds,
        "taken_down": status.taken_down,
        "taken_down_at": status.taken_down_at.isoformat() if status.taken_down_at else None,
    }


@router.get("/esafety/dashboard")
async def esafety_dashboard(
    auth: GroupContext = Depends(get_current_user),
):
    """Get eSafety SLA compliance dashboard."""
    from src.moderation.esafety import pipeline as esafety

    return esafety.get_sla_dashboard()


@router.get("/esafety/overdue")
async def esafety_overdue(
    auth: GroupContext = Depends(get_current_user),
):
    """Get all overdue takedowns (SLA breached)."""
    from src.moderation.esafety import pipeline as esafety

    _require_moderator(auth)
    overdue = esafety.get_overdue_takedowns()
    return {
        "items": [
            {
                "content_id": s.content_id,
                "deadline": s.deadline.isoformat(),
                "is_overdue": s.is_overdue,
            }
            for s in overdue
        ],
        "total": len(overdue),
    }


@router.get("/reports", response_model=ReportListResponse)
async def list_reports_endpoint(
    status: str | None = Query(None, description="Filter by report status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List content reports. Non-moderators only see their own reports."""
    reporter_id = None
    if auth.role not in _MODERATOR_ROLES:
        reporter_id = auth.user_id
    result = await list_reports(
        db, reporter_id=reporter_id, status=status, page=page, page_size=page_size,
    )
    return result
