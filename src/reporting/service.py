"""Reporting service — business logic for report generation and scheduling."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError
from src.reporting.generators import GENERATORS
from src.reporting.models import ReportExport, ScheduledReport
from src.reporting.schemas import ReportRequest, ScheduleConfig

logger = structlog.get_logger()

# Report output directory — configurable via env
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", "data/reports"))


def _ensure_reports_dir(group_id: UUID) -> Path:
    """Ensure the reports directory exists for a group."""
    group_dir = REPORTS_DIR / str(group_id)
    group_dir.mkdir(parents=True, exist_ok=True)
    return group_dir


async def generate_report(
    db: AsyncSession, data: ReportRequest
) -> ReportExport:
    """Generate a report export with real PDF/CSV/JSON content."""
    generator_cls = GENERATORS.get(data.report_type)
    if not generator_cls:
        from src.exceptions import ValidationError
        raise ValidationError(f"Unknown report type: {data.report_type}")

    generator = generator_cls(db, data.group_id)

    # Generate the report content
    content = await generator.generate(
        fmt=data.format,
        period_start=data.period_start,
        period_end=data.period_end,
    )

    # Save to filesystem
    file_name = f"{data.report_type}_{uuid4().hex[:8]}.{data.format}"
    group_dir = _ensure_reports_dir(data.group_id)
    file_path = group_dir / file_name
    file_path.write_bytes(content)

    # Create database record
    export = ReportExport(
        id=uuid4(),
        group_id=data.group_id,
        report_type=data.report_type,
        format=data.format,
        file_path=str(file_path),
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
        size_bytes=len(content),
    )
    return export


async def generate_report_bytes(
    db: AsyncSession, data: ReportRequest
) -> tuple[bytes, str]:
    """Generate report content in memory without saving. Returns (content, filename)."""
    generator_cls = GENERATORS.get(data.report_type)
    if not generator_cls:
        from src.exceptions import ValidationError
        raise ValidationError(f"Unknown report type: {data.report_type}")

    generator = generator_cls(db, data.group_id)
    content = await generator.generate(
        fmt=data.format,
        period_start=data.period_start,
        period_end=data.period_end,
    )
    file_name = f"{data.report_type}_{uuid4().hex[:8]}.{data.format}"
    return content, file_name


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
