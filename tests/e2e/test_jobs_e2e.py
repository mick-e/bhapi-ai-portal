"""E2E tests for the jobs module: internal endpoints, status reporting, graceful error handling."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


@pytest_asyncio.fixture(scope="function")
async def jobs_client():
    """Client with DB override for jobs endpoint tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()

    async def override_get_db():
        async_session_maker = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ===========================================================================
# /internal/jobs — List Jobs
# ===========================================================================

class TestListJobsEndpoint:
    """Test GET /internal/jobs endpoint."""

    @pytest.mark.asyncio
    async def test_list_jobs_returns_200(self, jobs_client):
        """GET /internal/jobs returns 200 with job list."""
        resp = await jobs_client.get("/internal/jobs")
        assert resp.status_code == 200
        body = resp.json()
        assert "jobs" in body
        assert isinstance(body["jobs"], list)
        assert len(body["jobs"]) > 0

    @pytest.mark.asyncio
    async def test_list_jobs_has_required_fields(self, jobs_client):
        """Each job in the list has name, description, schedule."""
        resp = await jobs_client.get("/internal/jobs")
        for job in resp.json()["jobs"]:
            assert "name" in job
            assert "description" in job
            assert "schedule" in job

    @pytest.mark.asyncio
    async def test_list_jobs_known_jobs_present(self, jobs_client):
        """Well-known jobs appear in the listing."""
        resp = await jobs_client.get("/internal/jobs")
        names = {j["name"] for j in resp.json()["jobs"]}
        assert "hourly_digest" in names
        assert "spend_sync" in names
        assert "excerpt_cleanup" in names


# ===========================================================================
# /internal/jobs/run — Run Single Job
# ===========================================================================

class TestRunJobEndpoint:
    """Test POST /internal/jobs/run endpoint."""

    @pytest.mark.asyncio
    async def test_run_unknown_job(self, jobs_client):
        """Running a nonexistent job returns error."""
        resp = await jobs_client.post("/internal/jobs/run?job_name=does_not_exist")
        assert resp.status_code == 200
        body = resp.json()
        assert "error" in body
        assert "Unknown job" in body["error"]

    @pytest.mark.asyncio
    async def test_run_job_returns_status(self, jobs_client):
        """Running a real job returns status and duration."""
        # excerpt_cleanup is safe to run against empty DB
        resp = await jobs_client.post("/internal/jobs/run?job_name=excerpt_cleanup")
        assert resp.status_code == 200
        body = resp.json()
        assert body["job"] == "excerpt_cleanup"
        assert body["status"] in ("completed", "failed")
        assert "duration_seconds" in body


# ===========================================================================
# /internal/jobs/schedule — Run by Schedule
# ===========================================================================

class TestRunScheduleEndpoint:
    """Test POST /internal/jobs/schedule endpoint."""

    @pytest.mark.asyncio
    async def test_run_schedule_returns_results(self, jobs_client):
        """Running a schedule returns results array."""
        resp = await jobs_client.post("/internal/jobs/schedule?schedule=every_5m")
        assert resp.status_code == 200
        body = resp.json()
        assert body["schedule"] == "every_5m"
        assert "results" in body
        assert isinstance(body["results"], list)

    @pytest.mark.asyncio
    async def test_run_empty_schedule(self, jobs_client):
        """Running a schedule with no matching jobs returns empty results."""
        resp = await jobs_client.post("/internal/jobs/schedule?schedule=nonexistent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["results"] == []


# ===========================================================================
# Graceful Error Handling
# ===========================================================================

class TestJobGracefulHandling:
    """Test graceful handling of errors in job execution."""

    @pytest.mark.asyncio
    async def test_job_failure_does_not_crash_endpoint(self, jobs_client):
        """A job that raises an exception returns a structured error, not 500."""
        # Register a job that will fail, then run it via endpoint
        from src.jobs.runner import _JOB_REGISTRY, register_job

        async def crashing_job(db):
            raise RuntimeError("Intentional crash for testing")

        register_job("crash_test", "Crashes on purpose", "daily", crashing_job)

        resp = await jobs_client.post("/internal/jobs/run?job_name=crash_test")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed"
        assert "Intentional crash" in body["error"]

        # Clean up
        _JOB_REGISTRY.pop("crash_test", None)

    @pytest.mark.asyncio
    async def test_schedule_continues_after_failure(self, jobs_client):
        """A failing job in a schedule does not block subsequent jobs."""
        from src.jobs.runner import _JOB_REGISTRY, register_job

        async def fail_job(db):
            raise ValueError("fail")

        async def pass_job(db):
            return {"ok": True}

        register_job("sched_fail", "Fails", "every_5m", fail_job)
        register_job("sched_pass", "Passes", "every_5m", pass_job)

        resp = await jobs_client.post("/internal/jobs/schedule?schedule=every_5m")
        assert resp.status_code == 200
        results = resp.json()["results"]
        statuses = {r["job"]: r["status"] for r in results}
        assert statuses.get("sched_fail") == "failed"
        assert statuses.get("sched_pass") == "completed"

        # Clean up
        _JOB_REGISTRY.pop("sched_fail", None)
        _JOB_REGISTRY.pop("sched_pass", None)
