"""Family Safety Weekly Report E2E tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app


async def _register_and_login(client, email="test@example.com", account_type="family"):
    """Helper: register and return token."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Test User",
        "account_type": account_type,
    })
    return reg.json()["access_token"]


@pytest.fixture
async def report_client():
    """Report test client with committing DB session."""
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
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await session.close()
    await engine.dispose()


# --- Weekly Report Generation ---


@pytest.mark.asyncio
async def test_get_weekly_family_report(report_client):
    """Get weekly family report data."""
    token = await _register_and_login(report_client, "weekly@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create group
    group_resp = await report_client.post("/api/v1/groups", json={
        "name": "Report Family",
        "type": "family",
    }, headers=headers)
    assert group_resp.status_code == 201

    response = await report_client.get(
        "/api/v1/reports/weekly-family", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "family_safety_score" in data
    assert "members" in data
    assert "highlights" in data
    assert "action_items" in data
    assert "group_name" in data


@pytest.mark.asyncio
async def test_weekly_report_includes_members(report_client):
    """Weekly report includes per-member breakdown."""
    token = await _register_and_login(report_client, "members@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Get the auto-created group from registration
    groups_resp = await report_client.get("/api/v1/groups", headers=headers)
    group_id = groups_resp.json()[0]["id"]

    # Add a child member to the auto-created group
    await report_client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"display_name": "Child", "role": "member"},
        headers=headers,
    )

    response = await report_client.get(
        "/api/v1/reports/weekly-family", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["member_count"] == 2  # Owner + child
    assert len(data["members"]) == 2

    # Each member has expected fields
    for member in data["members"]:
        assert "display_name" in member
        assert "safety_score" in member
        assert "risk_count" in member
        assert "events_this_week" in member
        assert "week_change" in member


@pytest.mark.asyncio
async def test_weekly_report_safety_score_range(report_client):
    """Safety score is in valid range."""
    token = await _register_and_login(report_client, "score@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await report_client.post("/api/v1/groups", json={
        "name": "Score Family",
        "type": "family",
    }, headers=headers)

    response = await report_client.get(
        "/api/v1/reports/weekly-family", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["family_safety_score"] <= 100


@pytest.mark.asyncio
async def test_send_weekly_report_endpoint(report_client):
    """Trigger on-demand send of weekly report."""
    token = await _register_and_login(report_client, "send@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await report_client.post("/api/v1/groups", json={
        "name": "Send Family",
        "type": "family",
    }, headers=headers)

    response = await report_client.post(
        "/api/v1/reports/weekly-family/send", headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "sent" in data


@pytest.mark.asyncio
async def test_weekly_report_requires_auth(report_client):
    """Get weekly report without auth returns 401."""
    response = await report_client.get("/api/v1/reports/weekly-family")
    assert response.status_code == 401
