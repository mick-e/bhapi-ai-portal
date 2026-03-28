"""Unit tests for the background jobs module: runner, registry, scheduling."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.jobs.runner import (
    JobDefinition,
    _JOB_REGISTRY,
    _init_registry,
    get_registered_jobs,
    register_job,
    run_job,
    run_schedule,
)
from src.jobs.__main__ import _due_schedules


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the job registry before each test to avoid leaking state."""
    _JOB_REGISTRY.clear()
    yield
    _JOB_REGISTRY.clear()


# ===========================================================================
# Job Registration
# ===========================================================================

class TestJobRegistration:
    """Test the job registry system."""

    def test_register_job(self):
        """A registered job appears in the registry."""
        async def handler(db):
            return {"ok": True}

        register_job("test_job", "A test job", "daily", handler)
        jobs = get_registered_jobs()
        assert "test_job" in jobs
        assert jobs["test_job"].description == "A test job"
        assert jobs["test_job"].schedule == "daily"

    def test_register_multiple_jobs(self):
        """Multiple jobs can be registered."""
        async def h1(db):
            return 1

        async def h2(db):
            return 2

        register_job("job_a", "Job A", "hourly", h1)
        register_job("job_b", "Job B", "daily", h2)
        jobs = get_registered_jobs()
        assert len(jobs) == 2

    def test_get_registered_jobs_returns_copy(self):
        """get_registered_jobs returns a copy, not the original dict."""
        async def h(db):
            return 0

        register_job("orig", "Orig", "daily", h)
        copy = get_registered_jobs()
        copy["injected"] = None
        assert "injected" not in _JOB_REGISTRY

    def test_job_definition_dataclass(self):
        """JobDefinition fields are accessible."""
        async def h(db):
            return {}

        jd = JobDefinition(name="jd_test", description="desc", schedule="hourly", handler=h)
        assert jd.name == "jd_test"
        assert jd.schedule == "hourly"


# ===========================================================================
# Scheduling Logic
# ===========================================================================

class TestSchedulingLogic:
    """Test _due_schedules from __main__."""

    def test_every_5m_always_due(self):
        """every_5m runs on every invocation."""
        now = datetime(2026, 3, 26, 14, 37, 0, tzinfo=timezone.utc)
        schedules = _due_schedules(now)
        assert "every_5m" in schedules

    def test_hourly_at_minute_0(self):
        """hourly runs when minute < 5."""
        now = datetime(2026, 3, 26, 14, 3, 0, tzinfo=timezone.utc)
        schedules = _due_schedules(now)
        assert "hourly" in schedules

    def test_hourly_not_at_minute_10(self):
        """hourly does NOT run when minute >= 5."""
        now = datetime(2026, 3, 26, 14, 10, 0, tzinfo=timezone.utc)
        schedules = _due_schedules(now)
        assert "hourly" not in schedules

    def test_daily_at_midnight(self):
        """daily runs at hour 0, minute < 5."""
        now = datetime(2026, 3, 26, 0, 2, 0, tzinfo=timezone.utc)
        schedules = _due_schedules(now)
        assert "daily" in schedules
        assert "hourly" in schedules

    def test_daily_not_at_noon(self):
        """daily does NOT run at hour 12."""
        now = datetime(2026, 3, 26, 12, 0, 0, tzinfo=timezone.utc)
        schedules = _due_schedules(now)
        assert "daily" not in schedules

    def test_weekly_on_monday_midnight(self):
        """weekly runs on Monday at midnight."""
        # 2026-03-23 is a Monday
        now = datetime(2026, 3, 23, 0, 1, 0, tzinfo=timezone.utc)
        assert now.weekday() == 0  # Monday
        schedules = _due_schedules(now)
        assert "weekly" in schedules

    def test_weekly_not_on_tuesday(self):
        """weekly does NOT run on Tuesday."""
        # 2026-03-24 is a Tuesday
        now = datetime(2026, 3, 24, 0, 1, 0, tzinfo=timezone.utc)
        assert now.weekday() == 1  # Tuesday
        schedules = _due_schedules(now)
        assert "weekly" not in schedules


# ===========================================================================
# Job Execution
# ===========================================================================

class TestJobExecution:
    """Test run_job and run_schedule."""

    @pytest.mark.asyncio
    async def test_run_job_success(self, test_session):
        """Successful job returns completed status."""
        async def good_job(db):
            return {"processed": 42}

        register_job("good_job", "A good job", "daily", good_job)
        result = await run_job(test_session, "good_job")
        assert result["status"] == "completed"
        assert result["job"] == "good_job"
        assert result["result"]["processed"] == 42
        assert "duration_seconds" in result

    @pytest.mark.asyncio
    async def test_run_job_failure_isolated(self, test_session):
        """Failed job returns error status but does not raise."""
        async def bad_job(db):
            raise ValueError("Something went wrong")

        register_job("bad_job", "A bad job", "hourly", bad_job)
        result = await run_job(test_session, "bad_job")
        assert result["status"] == "failed"
        assert "Something went wrong" in result["error"]

    @pytest.mark.asyncio
    async def test_run_unknown_job(self, test_session):
        """Running an unknown job returns an error dict."""
        result = await run_job(test_session, "nonexistent")
        assert "error" in result
        assert "Unknown job" in result["error"]

    @pytest.mark.asyncio
    async def test_run_schedule_filters_by_schedule(self, test_session):
        """run_schedule only runs jobs matching the given schedule."""
        call_log = []

        async def hourly_handler(db):
            call_log.append("hourly")
            return {}

        async def daily_handler(db):
            call_log.append("daily")
            return {}

        register_job("h_job", "Hourly", "hourly", hourly_handler)
        register_job("d_job", "Daily", "daily", daily_handler)

        results = await run_schedule(test_session, "hourly")
        assert len(results) == 1
        assert "hourly" in call_log
        assert "daily" not in call_log

    @pytest.mark.asyncio
    async def test_run_schedule_empty(self, test_session):
        """Running a schedule with no matching jobs returns empty list."""
        results = await run_schedule(test_session, "nonexistent_schedule")
        assert results == []

    @pytest.mark.asyncio
    async def test_error_isolation_in_schedule(self, test_session):
        """One failing job in a schedule doesn't block others."""
        call_log = []

        async def failing_job(db):
            call_log.append("fail")
            raise RuntimeError("fail")

        async def passing_job(db):
            call_log.append("pass")
            return {"ok": True}

        register_job("fail_first", "Fails", "hourly", failing_job)
        register_job("pass_second", "Passes", "hourly", passing_job)

        results = await run_schedule(test_session, "hourly")
        assert len(results) == 2
        statuses = {r["job"]: r["status"] for r in results}
        assert statuses["fail_first"] == "failed"
        assert statuses["pass_second"] == "completed"
        assert "fail" in call_log
        assert "pass" in call_log


# ===========================================================================
# Init Registry
# ===========================================================================

class TestInitRegistry:
    """Test _init_registry populates the registry."""

    def test_init_registry_populates_jobs(self):
        """After _init_registry, the registry has known jobs."""
        _init_registry()
        jobs = get_registered_jobs()
        # Spot-check a few well-known jobs
        assert "hourly_digest" in jobs
        assert "daily_digest" in jobs
        assert "spend_sync" in jobs
        assert "excerpt_cleanup" in jobs
        assert "auto_block_check" in jobs

    def test_init_registry_idempotent(self):
        """Calling _init_registry twice doesn't duplicate jobs."""
        _init_registry()
        count1 = len(get_registered_jobs())
        _init_registry()
        count2 = len(get_registered_jobs())
        assert count1 == count2

    def test_all_jobs_have_valid_schedule(self):
        """All registered jobs have a recognized schedule type."""
        _init_registry()
        valid_schedules = {"every_5m", "hourly", "daily", "weekly"}
        for job in get_registered_jobs().values():
            assert job.schedule in valid_schedules, f"{job.name} has invalid schedule: {job.schedule}"
