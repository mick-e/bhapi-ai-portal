"""E2E tests for the reporting module.

Covers report generation (CSV, PDF, JSON), listing reports,
schedule creation (daily, weekly, monthly), and schedule listing.
"""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client, email="reports@test.com"):
    """Register, return token."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Reports Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    return reg.json()["access_token"]


async def _create_group(client, headers):
    """Create a group, return group_id."""
    grp = await client.post("/api/v1/groups", json={
        "name": "Reports Family",
        "type": "family",
    }, headers=headers)
    return grp.json()["id"]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def report_client():
    """Test client with committing DB session for reporting tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Report generation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_report_pdf(report_client):
    """POST /reports/generate creates a PDF report (201)."""
    token = await _register_and_login(report_client)
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    resp = await report_client.post(
        "/api/v1/reports/generate",
        json={
            "group_id": gid,
            "report_type": "activity",
            "format": "pdf",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "activity"
    assert data["format"] == "pdf"
    assert data["status"] == "ready"
    assert data["download_url"] is not None


@pytest.mark.asyncio
async def test_generate_report_csv(report_client):
    """Generate a CSV report."""
    token = await _register_and_login(report_client, "csv@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    resp = await report_client.post(
        "/api/v1/reports/generate",
        json={"group_id": gid, "report_type": "risk", "format": "csv"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["format"] == "csv"
    assert resp.json()["type"] == "safety"  # "risk" maps to "safety" for frontend


@pytest.mark.asyncio
async def test_generate_report_json(report_client):
    """Generate a JSON report."""
    token = await _register_and_login(report_client, "json@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    resp = await report_client.post(
        "/api/v1/reports/generate",
        json={"group_id": gid, "report_type": "spend", "format": "json"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["format"] == "json"
    assert resp.json()["type"] == "spend"


@pytest.mark.asyncio
async def test_generate_compliance_report(report_client):
    """Generate a compliance report."""
    token = await _register_and_login(report_client, "compliance@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    resp = await report_client.post(
        "/api/v1/reports/generate",
        json={"group_id": gid, "report_type": "compliance", "format": "pdf"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["type"] == "compliance"


@pytest.mark.asyncio
async def test_generate_report_has_generated_at(report_client):
    """Generated report has a generated_at timestamp."""
    token = await _register_and_login(report_client, "expiry@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    resp = await report_client.post(
        "/api/v1/reports/generate",
        json={"group_id": gid, "report_type": "activity", "format": "pdf"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["generated_at"] is not None


@pytest.mark.asyncio
async def test_generate_report_invalid_type(report_client):
    """Invalid report type returns 422."""
    token = await _register_and_login(report_client, "invalid@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    resp = await report_client.post(
        "/api/v1/reports/generate",
        json={"group_id": gid, "report_type": "nonexistent", "format": "pdf"},
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# List reports
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_reports_empty(report_client):
    """GET /reports returns empty paginated result for new group."""
    token = await _register_and_login(report_client, "list0@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    resp = await report_client.get(
        f"/api/v1/reports?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_reports_after_generation(report_client):
    """List reports includes generated reports."""
    token = await _register_and_login(report_client, "list1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    await report_client.post(
        "/api/v1/reports/generate",
        json={"group_id": gid, "report_type": "activity", "format": "pdf"},
        headers=headers,
    )
    await report_client.post(
        "/api/v1/reports/generate",
        json={"group_id": gid, "report_type": "risk", "format": "csv"},
        headers=headers,
    )

    resp = await report_client.get(
        f"/api/v1/reports?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 2


# ---------------------------------------------------------------------------
# Schedule tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_weekly_schedule(report_client):
    """POST /reports/schedule creates a weekly schedule (201)."""
    token = await _register_and_login(report_client, "sched1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    resp = await report_client.post(
        "/api/v1/reports/schedule",
        json={
            "group_id": gid,
            "report_type": "activity",
            "schedule": "weekly",
            "recipients": ["parent@example.com"],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["schedule"] == "weekly"
    assert data["type"] == "activity"


@pytest.mark.asyncio
async def test_create_monthly_schedule(report_client):
    """Create monthly schedule."""
    token = await _register_and_login(report_client, "sched2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    resp = await report_client.post(
        "/api/v1/reports/schedule",
        json={
            "group_id": gid,
            "report_type": "spend",
            "schedule": "monthly",
            "recipients": ["admin@school.edu"],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["schedule"] == "monthly"


@pytest.mark.asyncio
async def test_create_daily_schedule(report_client):
    """Create daily schedule."""
    token = await _register_and_login(report_client, "sched3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    resp = await report_client.post(
        "/api/v1/reports/schedule",
        json={
            "group_id": gid,
            "report_type": "risk",
            "schedule": "daily",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["schedule"] == "daily"


@pytest.mark.asyncio
async def test_list_schedules(report_client):
    """GET /reports/schedules lists all schedules for group."""
    token = await _register_and_login(report_client, "sched4@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    await report_client.post(
        "/api/v1/reports/schedule",
        json={"group_id": gid, "report_type": "activity", "schedule": "weekly"},
        headers=headers,
    )
    await report_client.post(
        "/api/v1/reports/schedule",
        json={"group_id": gid, "report_type": "risk", "schedule": "daily"},
        headers=headers,
    )

    resp = await report_client.get(
        f"/api/v1/reports/schedules?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    schedules = resp.json()
    assert len(schedules) == 2


@pytest.mark.asyncio
async def test_list_schedules_empty(report_client):
    """Empty schedule list for new group."""
    token = await _register_and_login(report_client, "sched5@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid = await _create_group(report_client, headers)

    resp = await report_client.get(
        f"/api/v1/reports/schedules?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_reporting_requires_auth(report_client):
    """Reporting endpoints require auth."""
    resp = await report_client.get(
        f"/api/v1/reports?group_id={uuid4()}"
    )
    assert resp.status_code == 401
