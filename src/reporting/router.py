"""Reporting API endpoints."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription
from src.dependencies import resolve_group_id as _gid
from src.reporting.models import ReportExport, ScheduledReport
from src.reporting.schemas import CreateReportRequest, ReportRequest, ScheduleConfig, UpdateScheduleRequest
from src.reporting.service import (
    create_schedule,
    generate_report,
    get_report,
    list_schedules,
)
from src.schemas import GroupContext

router = APIRouter(dependencies=[Depends(require_active_trial_or_subscription)])

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "csv": "text/csv",
    "json": "application/json",
}


def _report_to_frontend(report: ReportExport) -> dict:
    """Convert backend ReportExport to frontend Report shape."""
    # Map report_type: backend "risk" → frontend "safety"
    type_map = {"risk": "safety", "activity": "activity", "spend": "spend", "compliance": "compliance"}
    report_type = type_map.get(report.report_type, report.report_type)

    return {
        "id": str(report.id),
        "group_id": str(report.group_id),
        "title": f"{report_type.capitalize()} Report",
        "description": f"{report_type.capitalize()} report in {report.format.upper()} format",
        "type": report_type,
        "status": "ready" if report.file_path else "generating",
        "format": report.format,
        "period_start": "",
        "period_end": "",
        "download_url": f"/api/v1/reports/{report.id}/download",
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "created_at": report.created_at.isoformat() if report.created_at else "",
    }


def _schedule_to_frontend(schedule: ScheduledReport) -> dict:
    """Convert backend ScheduledReport to frontend ReportScheduleConfig shape."""
    return {
        "type": schedule.report_type,
        "schedule": schedule.schedule,
        "format": "pdf",
        "recipients": schedule.recipients or [],
    }


@router.post("", status_code=201)
async def create_report(
    body: CreateReportRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a report (frontend calls POST /api/v1/reports)."""
    gid = _gid(None, auth)
    # Map frontend "safety" back to backend "risk"
    type_map = {"safety": "risk", "activity": "activity", "spend": "spend", "compliance": "compliance"}
    report_type = type_map.get(body.type, body.type)

    data = ReportRequest(
        group_id=gid,
        report_type=report_type,
        format=body.format,
        period_start=body.period_start,
        period_end=body.period_end,
    )
    export = await generate_report(db, data)
    return _report_to_frontend(export)


@router.post("/generate", status_code=201)
async def generate_report_endpoint(
    data: ReportRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a report (legacy endpoint, FR-041)."""
    export = await generate_report(db, data)
    return _report_to_frontend(export)


@router.get("")
async def list_reports_endpoint(
    group_id: UUID | None = Query(None, description="Group ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    type: str | None = Query(None, description="Filter by report type"),
    status: str | None = Query(None, description="Filter by status"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List generated reports with pagination matching frontend PaginatedResponse."""
    gid = _gid(group_id, auth)

    base = select(ReportExport).where(ReportExport.group_id == gid)
    count_q = select(func.count(ReportExport.id)).where(ReportExport.group_id == gid)

    if type:
        type_map = {"safety": "risk", "activity": "activity", "spend": "spend", "compliance": "compliance"}
        backend_type = type_map.get(type, type)
        base = base.where(ReportExport.report_type == backend_type)
        count_q = count_q.where(ReportExport.report_type == backend_type)

    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size
    rows = await db.execute(
        base.order_by(ReportExport.generated_at.desc()).offset(offset).limit(page_size)
    )
    items = [_report_to_frontend(r) for r in rows.scalars().all()]
    total_pages = max((total + page_size - 1) // page_size, 1)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post("/schedule", status_code=201)
async def create_schedule_endpoint(
    data: ScheduleConfig,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a report schedule (POST /schedule)."""
    schedule = await create_schedule(db, data)
    return _schedule_to_frontend(schedule)


@router.get("/schedules")
async def list_schedules_endpoint(
    group_id: UUID | None = Query(None, description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List report schedules for a group."""
    schedules = await list_schedules(db, _gid(group_id, auth))
    return [_schedule_to_frontend(s) for s in schedules]


@router.put("/schedules")
async def update_schedule_endpoint(
    body: UpdateScheduleRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update/create a report schedule (frontend PUT /schedules)."""
    gid = _gid(None, auth)
    type_map = {"safety": "risk", "activity": "activity", "spend": "spend", "compliance": "compliance"}
    report_type = type_map.get(body.type, body.type)

    data = ScheduleConfig(
        group_id=gid,
        report_type=report_type,
        schedule=body.schedule,
        recipients=body.recipients,
    )
    schedule = await create_schedule(db, data)
    return _schedule_to_frontend(schedule)


# ---------------------------------------------------------------------------
# Weekly Family Report
# ---------------------------------------------------------------------------


@router.get("/weekly-family")
async def get_weekly_family_report(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get latest weekly family report data."""
    from src.dependencies import resolve_group_id as _resolve
    from src.reporting.family_report import generate_family_weekly_report

    gid = _resolve(None, auth)
    return await generate_family_weekly_report(db, gid)


@router.post("/weekly-family/send", status_code=200)
async def send_weekly_family_report(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger on-demand send of the weekly family report."""
    from src.dependencies import resolve_group_id as _resolve
    from src.reporting.family_report import send_family_weekly_report

    gid = _resolve(None, auth)
    sent = await send_family_weekly_report(db, gid)
    return {"sent": sent}


@router.get("/school-board/{school_id}")
async def school_board_report(
    school_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate school board compliance PDF report."""
    from src.reporting.service import generate_school_board_report

    pdf_bytes = await generate_school_board_report(db, school_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="school-board-report-{school_id}.pdf"',
        },
    )


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a generated report (FR-042)."""
    report = await get_report(db, report_id)

    if report.file_path:
        file_path = Path(report.file_path)
        if file_path.exists():
            content_type = CONTENT_TYPES.get(report.format, "application/octet-stream")
            content = file_path.read_bytes()
            filename = f"{report.report_type}_report.{report.format}"
            return Response(
                content=content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )

    return JSONResponse(
        content={
            "id": str(report.id),
            "file_path": report.file_path,
            "format": report.format,
            "generated_at": report.generated_at.isoformat(),
            "expires_at": report.expires_at.isoformat() if report.expires_at else None,
            "download_url": f"/api/v1/reports/{report.id}/download",
        }
    )
