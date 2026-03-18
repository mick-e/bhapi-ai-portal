"""CLI entry point for the background job runner.

Invoked by Render cron: `python -m src.jobs.runner`
Schedule: every 5 minutes (render.yaml)

Determines which job schedules are due based on the current time
and runs them sequentially.
"""

import asyncio
import sys
from datetime import datetime, timezone

import structlog

from src.database import get_db_context
from src.jobs.runner import run_schedule

logger = structlog.get_logger()


def _due_schedules(now: datetime) -> list[str]:
    """Return which schedules should run based on current UTC time."""
    schedules = ["every_5m"]

    if now.minute < 5:
        schedules.append("hourly")

    if now.hour == 0 and now.minute < 5:
        schedules.append("daily")

    if now.weekday() == 0 and now.hour == 0 and now.minute < 5:
        schedules.append("weekly")

    return schedules


async def main() -> None:
    now = datetime.now(timezone.utc)
    due = _due_schedules(now)
    logger.info("job_runner_started", utc_time=now.isoformat(), due_schedules=due)

    total_jobs = 0
    total_failures = 0

    async with get_db_context() as db:
        for schedule in due:
            results = await run_schedule(db, schedule)
            for r in results:
                total_jobs += 1
                if r.get("status") == "failed":
                    total_failures += 1

    logger.info(
        "job_runner_finished",
        total_jobs=total_jobs,
        failures=total_failures,
        schedules_run=due,
    )

    if total_failures > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
