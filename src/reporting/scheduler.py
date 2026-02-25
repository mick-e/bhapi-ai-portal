"""Scheduled report delivery — background job that generates and emails due reports."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.email.service import send_email
from src.email.templates import report_ready
from src.reporting.models import ScheduledReport
from src.reporting.schemas import ReportRequest
from src.reporting.service import generate_report

logger = structlog.get_logger()


async def run_scheduled_reports(db: AsyncSession) -> int:
    """Check for and process due scheduled reports.

    Returns the number of reports generated and delivered.
    """
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(ScheduledReport).where(
            ScheduledReport.next_generation <= now,
            ScheduledReport.next_generation.isnot(None),
        )
    )
    schedules = list(result.scalars().all())

    delivered = 0
    for schedule in schedules:
        try:
            # Generate the report
            report = await generate_report(
                db,
                ReportRequest(
                    group_id=schedule.group_id,
                    report_type=schedule.report_type,
                    format="pdf",
                ),
            )

            # Email to recipients
            recipients = schedule.recipients or []
            if recipients:
                download_url = f"https://bhapi.ai/api/v1/reports/{report.id}/download"
                subject, html, plain = report_ready(
                    report_type=schedule.report_type,
                    download_url=download_url,
                )
                for email in recipients:
                    await send_email(
                        to_email=email,
                        subject=subject,
                        html_content=html,
                        plain_content=plain,
                        group_id=schedule.group_id,
                    )

            # Advance schedule
            schedule.last_generated = now
            if schedule.schedule == "daily":
                schedule.next_generation = now + timedelta(days=1)
            elif schedule.schedule == "weekly":
                schedule.next_generation = now + timedelta(weeks=1)
            else:  # monthly
                schedule.next_generation = now + timedelta(days=30)

            await db.flush()
            delivered += 1

            logger.info(
                "scheduled_report_delivered",
                schedule_id=str(schedule.id),
                report_type=schedule.report_type,
                recipients=len(recipients),
            )
        except Exception as exc:
            logger.error(
                "scheduled_report_failed",
                schedule_id=str(schedule.id),
                error=str(exc),
            )

    logger.info("scheduled_reports_completed", checked=len(schedules), delivered=delivered)
    return delivered
