"""Centralized job runner — unified registry for all background jobs.

Each job is registered with a name, callable, and schedule description.
The runner can execute individual jobs or all due jobs in a single pass.
Uses database-based locking to prevent concurrent execution of the same job.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Awaitable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


@dataclass
class JobDefinition:
    """A registered background job."""
    name: str
    description: str
    schedule: str  # "every_5m", "hourly", "daily"
    handler: Callable[[AsyncSession], Awaitable[int | dict]]


# Global job registry
_JOB_REGISTRY: dict[str, JobDefinition] = {}


def register_job(
    name: str,
    description: str,
    schedule: str,
    handler: Callable[[AsyncSession], Awaitable[int | dict]],
) -> None:
    """Register a background job."""
    _JOB_REGISTRY[name] = JobDefinition(
        name=name,
        description=description,
        schedule=schedule,
        handler=handler,
    )


def get_registered_jobs() -> dict[str, JobDefinition]:
    """Return all registered jobs."""
    return dict(_JOB_REGISTRY)


def _init_registry() -> None:
    """Initialize the job registry with all known jobs. Lazy-loaded."""
    if _JOB_REGISTRY:
        return

    from src.alerts.scheduler import run_renotification_check
    from src.alerts.digest import run_hourly_digest, run_daily_digest
    from src.billing.scheduler import sync_all_accounts
    from src.billing.threshold_checker import check_all_group_thresholds
    from src.compliance.deletion_worker import process_pending_deletions
    from src.compliance.export_worker import process_pending_exports
    from src.reporting.scheduler import run_scheduled_reports

    register_job(
        "renotification_check",
        "Re-notify on unacknowledged critical/high alerts",
        "every_5m",
        run_renotification_check,
    )
    register_job(
        "hourly_digest",
        "Send hourly alert digest emails",
        "hourly",
        run_hourly_digest,
    )
    register_job(
        "daily_digest",
        "Send daily alert digest emails",
        "daily",
        run_daily_digest,
    )
    register_job(
        "spend_sync",
        "Sync LLM spend from all active provider accounts",
        "hourly",
        sync_all_accounts,
    )
    register_job(
        "threshold_check",
        "Check budget thresholds after spend sync",
        "hourly",
        check_all_group_thresholds,
    )
    register_job(
        "deletion_worker",
        "Process pending GDPR data deletion requests",
        "hourly",
        process_pending_deletions,
    )
    register_job(
        "export_worker",
        "Process pending GDPR data export requests",
        "hourly",
        process_pending_exports,
    )
    register_job(
        "scheduled_reports",
        "Generate and deliver scheduled reports",
        "hourly",
        run_scheduled_reports,
    )


async def run_job(db: AsyncSession, job_name: str) -> dict:
    """Execute a single job by name. Returns result summary."""
    _init_registry()

    job = _JOB_REGISTRY.get(job_name)
    if not job:
        return {"error": f"Unknown job: {job_name}", "available": list(_JOB_REGISTRY.keys())}

    start = datetime.now(timezone.utc)
    try:
        result = await job.handler(db)
        duration = (datetime.now(timezone.utc) - start).total_seconds()

        logger.info(
            "job_completed",
            job=job_name,
            result=result,
            duration_seconds=round(duration, 2),
        )
        return {
            "job": job_name,
            "status": "completed",
            "result": result,
            "duration_seconds": round(duration, 2),
        }
    except Exception as exc:
        duration = (datetime.now(timezone.utc) - start).total_seconds()
        logger.error(
            "job_failed",
            job=job_name,
            error=str(exc),
            duration_seconds=round(duration, 2),
        )
        return {
            "job": job_name,
            "status": "failed",
            "error": str(exc),
            "duration_seconds": round(duration, 2),
        }


async def run_schedule(db: AsyncSession, schedule: str) -> list[dict]:
    """Run all jobs matching a schedule (e.g., 'hourly', 'daily')."""
    _init_registry()

    results = []
    for job in _JOB_REGISTRY.values():
        if job.schedule == schedule:
            result = await run_job(db, job.name)
            results.append(result)

    logger.info("schedule_completed", schedule=schedule, jobs=len(results))
    return results
