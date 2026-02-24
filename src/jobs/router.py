"""Internal job runner endpoints — not exposed to public API."""

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_db
from src.jobs.runner import get_registered_jobs, run_job, run_schedule, _init_registry

router = APIRouter()


def _verify_internal_token(x_internal_token: str = Header(None)):
    """Verify the internal job runner token.

    In production, cron jobs include this header. In dev/test, skip.
    """
    settings = get_settings()
    if settings.environment in ("development", "test"):
        return
    if not x_internal_token or x_internal_token != settings.secret_key:
        from src.exceptions import UnauthorizedError
        raise UnauthorizedError("Invalid internal token")


@router.get("/jobs")
async def list_jobs(
    _: None = Depends(_verify_internal_token),
):
    """List all registered background jobs."""
    _init_registry()
    jobs = get_registered_jobs()
    return {
        "jobs": [
            {
                "name": j.name,
                "description": j.description,
                "schedule": j.schedule,
            }
            for j in jobs.values()
        ]
    }


@router.post("/jobs/run")
async def run_single_job(
    job_name: str = Query(..., description="Job name to execute"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_internal_token),
):
    """Execute a single background job by name."""
    result = await run_job(db, job_name)
    return result


@router.post("/jobs/schedule")
async def run_by_schedule(
    schedule: str = Query(..., description="Schedule to run: every_5m, hourly, daily"),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_internal_token),
):
    """Run all jobs matching a schedule."""
    results = await run_schedule(db, schedule)
    return {"schedule": schedule, "results": results}
