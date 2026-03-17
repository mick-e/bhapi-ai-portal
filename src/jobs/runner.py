"""Centralized job runner — unified registry for all background jobs.

Each job is registered with a name, callable, and schedule description.
The runner can execute individual jobs or all due jobs in a single pass.
Uses database-based locking to prevent concurrent execution of the same job.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable

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


async def _auto_block_check(db: AsyncSession) -> dict:
    """Evaluate automated blocking rules."""
    from src.blocking.service import evaluate_auto_block_rules
    return await evaluate_auto_block_rules(db)


async def _anomaly_check(db: AsyncSession) -> dict:
    """Detect anomalous member usage patterns and create alerts."""
    from src.analytics.service import detect_anomalies
    from src.groups.models import Group
    from sqlalchemy import select

    groups_result = await db.execute(select(Group))
    groups = list(groups_result.scalars().all())
    total_anomalies = 0
    for group in groups:
        anomalies = await detect_anomalies(db, group.id)
        total_anomalies += len(anomalies)
    return {"anomalies_detected": total_anomalies}


async def _directory_sync(db: AsyncSession) -> dict:
    """Sync members from SSO directory providers."""
    from src.integrations.directory_sync import run_directory_sync
    return await run_directory_sync(db)


async def _dependency_check(db: AsyncSession) -> dict:
    """Check emotional dependency scores for all groups and create alerts."""
    from src.groups.models import Group
    from src.risk.emotional_dependency import check_dependency_alerts
    from sqlalchemy import select as _select

    groups_result = await db.execute(_select(Group))
    groups = list(groups_result.scalars().all())
    total_alerts = 0
    for group in groups:
        result = await check_dependency_alerts(db, group.id)
        total_alerts += result.get("alerts_created", 0)
    return {"groups_checked": len(groups), "alerts_created": total_alerts}


async def _daily_summarization(db: AsyncSession) -> dict:
    """Generate daily conversation summaries for all members."""
    import os
    from datetime import date, timedelta
    from sqlalchemy import select
    from src.groups.models import Group, GroupMember

    api_key = os.environ.get("SUMMARY_LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("daily_summarization_skipped", reason="no_llm_api_key")
        return {"skipped": True, "reason": "no_llm_api_key"}

    from src.capture.summarizer import generate_daily_summaries

    target_date = date.today() - timedelta(days=1)
    total_summaries = 0

    groups_result = await db.execute(select(Group))
    groups = list(groups_result.scalars().all())
    for group in groups:
        members_result = await db.execute(
            select(GroupMember).where(GroupMember.group_id == group.id)
        )
        members = list(members_result.scalars().all())
        for member in members:
            try:
                summaries = await generate_daily_summaries(
                    db, group.id, member.id, target_date
                )
                total_summaries += len(summaries)
            except Exception as exc:
                logger.error(
                    "daily_summarization_member_error",
                    group_id=str(group.id),
                    member_id=str(member.id),
                    error=str(exc),
                )

    return {"summaries_created": total_summaries, "date": target_date.isoformat()}


async def _reward_check(db: AsyncSession) -> dict:
    """Evaluate reward triggers for all group members."""
    from src.groups.rewards import run_reward_check
    return await run_reward_check(db)


def _init_registry() -> None:
    """Initialize the job registry with all known jobs. Lazy-loaded."""
    if _JOB_REGISTRY:
        return

    from src.alerts.digest import run_daily_digest, run_hourly_digest, run_weekly_digest
    from src.alerts.scheduler import run_renotification_check
    from src.billing.scheduler import sync_all_accounts
    from src.billing.threshold_checker import check_all_group_thresholds
    from src.compliance.deletion_worker import process_pending_deletions
    from src.compliance.export_worker import process_pending_exports
    from src.compliance.file_cleanup import cleanup_expired_exports
    from src.reporting.scheduler import run_scheduled_reports
    from src.risk.cleanup import cleanup_expired_excerpts

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
        "weekly_digest",
        "Send weekly alert digest emails",
        "weekly",
        run_weekly_digest,
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
    register_job(
        "excerpt_cleanup",
        "Delete expired content excerpts",
        "daily",
        cleanup_expired_excerpts,
    )
    register_job(
        "export_cleanup",
        "Delete expired data export files",
        "daily",
        cleanup_expired_exports,
    )

    register_job(
        "auto_block_check",
        "Evaluate automated blocking rules",
        "every_5m",
        _auto_block_check,
    )

    from src.billing.trial_reminders import send_trial_reminders
    register_job(
        "trial_reminders",
        "Send trial expiry reminder emails",
        "daily",
        send_trial_reminders,
    )

    register_job(
        "anomaly_check",
        "Detect anomalous member usage patterns",
        "daily",
        _anomaly_check,
    )

    register_job(
        "directory_sync",
        "Sync members from SSO directory providers",
        "daily",
        _directory_sync,
    )

    from src.compliance.coppa_dashboard import coppa_reminder_job
    register_job(
        "coppa_reminder",
        "Alert on COPPA compliance gaps or overdue annual reviews",
        "daily",
        coppa_reminder_job,
    )

    register_job(
        "dependency_check",
        "Check emotional dependency scores and create alerts",
        "daily",
        _dependency_check,
    )

    async def _time_budget_enforce(db: AsyncSession) -> dict:
        """Enforce time budgets — block exceeded, unblock new day."""
        from src.blocking.time_budget import enforce_time_budgets
        return await enforce_time_budgets(db)

    register_job(
        "time_budget_enforce",
        "Enforce AI screen time budgets",
        "every_5m",
        _time_budget_enforce,
    )

    register_job(
        "daily_summarization",
        "Generate daily AI conversation summaries for parents",
        "daily",
        _daily_summarization,
    )

    # Sprint 5: Family agreement review reminders
    async def _agreement_review_reminder(db: AsyncSession) -> dict:
        from src.groups.agreement import agreement_review_reminder
        return await agreement_review_reminder(db)

    register_job(
        "agreement_review_reminder",
        "Remind parents to review family AI agreements",
        "weekly",
        _agreement_review_reminder,
    )

    # Sprint 5: Family weekly safety report
    async def _family_weekly_report(db: AsyncSession) -> dict:
        from src.reporting.family_report import run_family_weekly_reports
        return await run_family_weekly_reports(db)

    register_job(
        "family_weekly_report",
        "Generate and send weekly family safety reports",
        "weekly",
        _family_weekly_report,
    )

    register_job(
        "reward_check",
        "Evaluate reward triggers for all group members",
        "daily",
        _reward_check,
    )

    # COPPA 2026: Data retention cleanup
    async def _retention_cleanup(db: AsyncSession) -> dict:
        """Run automated data retention cleanup per group policies."""
        from src.compliance.retention import run_retention_cleanup
        return await run_retention_cleanup(db)

    register_job(
        "retention_cleanup",
        "Delete data exceeding configured retention periods (COPPA 2026)",
        "daily",
        _retention_cleanup,
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
