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


async def generate_school_board_report(
    db: AsyncSession,
    school_id: UUID,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> bytes:
    """Generate a school board compliance PDF report.

    Includes:
    - Executive summary
    - AI governance policy compliance status
    - AI tool inventory summary
    - Risk assessment results
    - Student safety metrics (anonymized)
    - Recommendations

    Uses ReportLab for PDF generation. Note: use unique style names
    to avoid conflicts with ReportLab's built-in "Bullet" style.
    """
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, topMargin=1 * inch, bottomMargin=1 * inch
    )
    styles = getSampleStyleSheet()

    # Use unique style names (CLAUDE.md: "Bullet" name conflicts with ReportLab)
    title_style = ParagraphStyle(
        "SchoolBoardTitle", parent=styles["Title"], fontSize=18, spaceAfter=20
    )
    heading_style = ParagraphStyle(
        "SchoolBoardHeading", parent=styles["Heading2"], fontSize=14, spaceAfter=10
    )
    body_style = ParagraphStyle(
        "SchoolBoardBody", parent=styles["Normal"], fontSize=11, spaceAfter=6
    )

    elements = []

    # Title
    elements.append(Paragraph("School Board AI Governance Report", title_style))
    elements.append(
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
            body_style,
        )
    )
    elements.append(Spacer(1, 20))

    # Date range info
    if date_from or date_to:
        from_str = date_from.strftime("%B %d, %Y") if date_from else "inception"
        to_str = date_to.strftime("%B %d, %Y") if date_to else "present"
        elements.append(
            Paragraph(f"Report Period: {from_str} to {to_str}", body_style)
        )
        elements.append(Spacer(1, 10))

    # Executive Summary
    elements.append(Paragraph("Executive Summary", heading_style))
    elements.append(
        Paragraph(
            "This report provides an overview of AI governance compliance for the school district, "
            "including policy status, AI tool inventory, risk assessments, and student safety metrics.",
            body_style,
        )
    )
    elements.append(Spacer(1, 15))

    # Policy Compliance (query governance module if available)
    elements.append(Paragraph("AI Governance Policy Status", heading_style))

    # Try to get governance data
    try:
        from src.governance.service import get_compliance_dashboard

        dashboard = await get_compliance_dashboard(db, school_id)
        policy_data = [
            ["Metric", "Value"],
            ["Total Policies", str(dashboard.get("policy_count", 0))],
            ["Active Policies", str(dashboard.get("active_count", 0))],
            ["Risk Score", f"{dashboard.get('risk_score', 'N/A')}/100"],
            ["AI Tools Inventoried", str(dashboard.get("tool_count", 0))],
        ]
    except Exception:
        policy_data = [
            ["Metric", "Value"],
            ["Total Policies", "N/A"],
            ["Active Policies", "N/A"],
            ["Risk Score", "N/A"],
            ["AI Tools Inventoried", "N/A"],
        ]

    table = Table(policy_data, colWidths=[3 * inch, 2 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FF6B35")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#FFF3ED")],
                ),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 15))

    # Student Safety Metrics (anonymized)
    elements.append(Paragraph("Student Safety Metrics (Anonymized)", heading_style))

    try:
        from sqlalchemy import func
        from sqlalchemy import select as sa_select

        from src.risk.models import RiskEvent

        risk_query = sa_select(func.count(RiskEvent.id)).where(
            RiskEvent.group_id == school_id
        )
        if date_from:
            risk_query = risk_query.where(RiskEvent.created_at >= date_from)
        if date_to:
            risk_query = risk_query.where(RiskEvent.created_at <= date_to)
        risk_count = (await db.execute(risk_query)).scalar() or 0

        safety_data = [
            ["Metric", "Value"],
            ["Total Risk Events", str(risk_count)],
            ["Monitoring Status", "Active"],
        ]
    except Exception:
        safety_data = [
            ["Metric", "Value"],
            ["Total Risk Events", "N/A"],
            ["Monitoring Status", "N/A"],
        ]

    safety_table = Table(safety_data, colWidths=[3 * inch, 2 * inch])
    safety_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D9488")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F0FDFA")],
                ),
            ]
        )
    )
    elements.append(safety_table)
    elements.append(Spacer(1, 15))

    # Recommendations
    elements.append(Paragraph("Recommendations", heading_style))
    elements.append(
        Paragraph(
            "1. Review and update AI usage policies annually per state mandate.",
            body_style,
        )
    )
    elements.append(
        Paragraph(
            "2. Ensure all AI tools are inventoried with risk assessments.", body_style
        )
    )
    elements.append(
        Paragraph(
            "3. Provide staff training on approved AI tool usage.", body_style
        )
    )
    elements.append(
        Paragraph(
            "4. Monitor student AI usage patterns through Bhapi Safety platform.",
            body_style,
        )
    )
    elements.append(Spacer(1, 15))

    # Footer
    elements.append(
        Paragraph(
            "Generated by Bhapi AI Governance Platform — bhapi.ai", body_style
        )
    )

    doc.build(elements)
    return buffer.getvalue()


async def list_schedules(
    db: AsyncSession, group_id: UUID
) -> list[ScheduledReport]:
    """List all report schedules for a group."""
    result = await db.execute(
        select(ScheduledReport).where(ScheduledReport.group_id == group_id)
    )
    return list(result.scalars().all())
