"""Reporting service — business logic for report generation and scheduling."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError
from src.reporting.models import ReportExport, ScheduledReport
from src.reporting.schemas import ReportRequest, ScheduleConfig

logger = structlog.get_logger()


async def generate_report(
    db: AsyncSession, data: ReportRequest
) -> ReportExport:
    """Generate a report export.

    In production, this would trigger async report generation (PDF/CSV).
    For now, creates the export record and a placeholder file path.
    """
    export = ReportExport(
        id=uuid4(),
        group_id=data.group_id,
        report_type=data.report_type,
        format=data.format,
        file_path=f"reports/{data.group_id}/{data.report_type}_{uuid4().hex[:8]}.{data.format}",
        generated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(export)
    await db.flush()
    await db.refresh(export)

    logger.info(
        "report_generated",
        export_id=str(export.id),
        group_id=str(data.group_id),
        report_type=data.report_type,
        format=data.format,
    )
    return export


async def list_reports(
    db: AsyncSession,
    group_id: UUID,
    offset: int = 0,
    limit: int = 50,
) -> list[ReportExport]:
    """List generated reports for a group."""
    result = await db.execute(
        select(ReportExport)
        .where(ReportExport.group_id == group_id)
        .order_by(ReportExport.generated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_report(db: AsyncSession, report_id: UUID) -> ReportExport:
    """Get a single report export by ID."""
    result = await db.execute(
        select(ReportExport).where(ReportExport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundError("Report", str(report_id))
    return report


async def create_schedule(
    db: AsyncSession, data: ScheduleConfig
) -> ScheduledReport:
    """Create a report generation schedule."""
    # Calculate next generation time based on schedule
    now = datetime.now(timezone.utc)
    if data.schedule == "daily":
        next_gen = now + timedelta(days=1)
    elif data.schedule == "weekly":
        next_gen = now + timedelta(weeks=1)
    else:  # monthly
        next_gen = now + timedelta(days=30)

    schedule = ScheduledReport(
        id=uuid4(),
        group_id=data.group_id,
        report_type=data.report_type,
        schedule=data.schedule,
        recipients=data.recipients,
        next_generation=next_gen,
    )
    db.add(schedule)
    await db.flush()
    await db.refresh(schedule)

    logger.info(
        "report_schedule_created",
        schedule_id=str(schedule.id),
        group_id=str(data.group_id),
        report_type=data.report_type,
        schedule=data.schedule,
    )
    return schedule


async def list_schedules(
    db: AsyncSession, group_id: UUID
) -> list[ScheduledReport]:
    """List all report schedules for a group."""
    result = await db.execute(
        select(ScheduledReport).where(ScheduledReport.group_id == group_id)
    )
    return list(result.scalars().all())
