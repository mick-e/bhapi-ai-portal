"""Unit tests for centralized job runner."""

import pytest

from src.jobs.runner import (
    _JOB_REGISTRY,
    JobDefinition,
    _init_registry,
    get_registered_jobs,
    register_job,
)


class TestJobRegistry:
    def setup_method(self):
        _JOB_REGISTRY.clear()

    def test_register_job(self):
        async def dummy_handler(db):
            return 0

        register_job("test_job", "A test job", "hourly", dummy_handler)
        assert "test_job" in _JOB_REGISTRY
        assert _JOB_REGISTRY["test_job"].description == "A test job"
        assert _JOB_REGISTRY["test_job"].schedule == "hourly"

    def test_get_registered_jobs(self):
        async def dummy_handler(db):
            return 0

        register_job("job1", "First", "hourly", dummy_handler)
        register_job("job2", "Second", "daily", dummy_handler)

        jobs = get_registered_jobs()
        assert len(jobs) == 2
        assert "job1" in jobs
        assert "job2" in jobs

    def test_init_registry_loads_all_jobs(self):
        _init_registry()
        jobs = get_registered_jobs()
        assert len(jobs) >= 7  # All registered jobs
        assert "renotification_check" in jobs
        assert "hourly_digest" in jobs
        assert "daily_digest" in jobs
        assert "spend_sync" in jobs
        assert "threshold_check" in jobs
        assert "deletion_worker" in jobs
        assert "export_worker" in jobs
        assert "scheduled_reports" in jobs

    def test_init_registry_idempotent(self):
        _init_registry()
        count1 = len(get_registered_jobs())
        _init_registry()
        count2 = len(get_registered_jobs())
        assert count1 == count2

    def test_job_definition_fields(self):
        async def handler(db):
            return 42

        job = JobDefinition(
            name="test",
            description="Test job",
            schedule="every_5m",
            handler=handler,
        )
        assert job.name == "test"
        assert job.schedule == "every_5m"


class TestRunJob:
    @pytest.mark.asyncio
    async def test_run_unknown_job(self):
        from src.jobs.runner import run_job
        _JOB_REGISTRY.clear()
        _init_registry()

        result = await run_job(None, "nonexistent_job")
        assert result["error"] is not None
        assert "available" in result

    @pytest.mark.asyncio
    async def test_run_job_returns_result(self):
        from src.jobs.runner import run_job
        _JOB_REGISTRY.clear()

        async def mock_handler(db):
            return 42

        register_job("mock_job", "Mock", "hourly", mock_handler)
        result = await run_job(None, "mock_job")
        assert result["status"] == "completed"
        assert result["result"] == 42
        assert result["duration_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_run_job_handles_error(self):
        from src.jobs.runner import run_job
        _JOB_REGISTRY.clear()

        async def failing_handler(db):
            raise ValueError("Intentional failure")

        register_job("fail_job", "Fail", "hourly", failing_handler)
        result = await run_job(None, "fail_job")
        assert result["status"] == "failed"
        assert "Intentional failure" in result["error"]


class TestRunSchedule:
    @pytest.mark.asyncio
    async def test_run_schedule_filters(self):
        from src.jobs.runner import run_schedule
        _JOB_REGISTRY.clear()

        async def handler1(db):
            return 1

        async def handler2(db):
            return 2

        register_job("hourly1", "H1", "hourly", handler1)
        register_job("daily1", "D1", "daily", handler2)

        results = await run_schedule(None, "hourly")
        assert len(results) == 1
        assert results[0]["job"] == "hourly1"

    @pytest.mark.asyncio
    async def test_run_schedule_no_matches(self):
        from src.jobs.runner import run_schedule
        _JOB_REGISTRY.clear()

        results = await run_schedule(None, "yearly")
        assert results == []
