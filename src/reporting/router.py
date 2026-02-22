"""Reporting API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.reporting.schemas import (
    ReportRequest,
    ReportResponse,
    ScheduleConfig,
    ScheduleResponse,
)
from src.reporting.service import (
    create_schedule,
    generate_report,
    get_report,
    list_reports,
    list_schedules,
)
from src.schemas import GroupContext

router = APIRouter()


@router.post("/generate", response_model=ReportResponse, status_code=201)
async def generate_report_endpoint(
    data: ReportRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a report (FR-041)."""
    export = await generate_report(db, data)
    return export


@router.get("", response_model=list[ReportResponse])
async def list_reports_endpoint(
    group_id: UUID = Query(..., description="Group ID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List generated reports for a group."""
    reports = await list_reports(db, group_id, offset=offset, limit=limit)
    return reports


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a generated report (FR-042).

    In production, this would return a signed URL or stream the file.
    For now, returns the file path metadata.
    """
    report = await get_report(db, report_id)
    return JSONResponse(
        content={
            "id": str(report.id),
            "file_path": report.file_path,
            "format": report.format,
            "generated_at": report.generated_at.isoformat(),
            "expires_at": report.expires_at.isoformat() if report.expires_at else None,
            "download_url": f"/api/v1/reports/files/{report.file_path}",
        }
    )


@router.post("/schedule", response_model=ScheduleResponse, status_code=201)
async def create_schedule_endpoint(
    data: ScheduleConfig,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a report generation schedule (FR-043)."""
    schedule = await create_schedule(db, data)
    return schedule


@router.get("/schedules", response_model=list[ScheduleResponse])
async def list_schedules_endpoint(
    group_id: UUID = Query(..., description="Group ID"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List report schedules for a group."""
    schedules = await list_schedules(db, group_id)
    return schedules
