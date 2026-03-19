"""E2E tests for emotional dependency score endpoints.

Tests endpoint auth, response schema, and history pagination.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.capture.models import CaptureEvent
from src.database import Base, get_db
from src.main import create_app
from src.risk.models import RiskEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client, email="dep@example.com"):
    """Register, return (token, user_id as str)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Dep Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


async def _create_group_and_member(client, headers):
    """Create group + child member, return (group_id str, member_id str)."""
    grp = await client.post("/api/v1/groups", json={
        "name": "Dep Family",
        "type": "family",
    }, headers=headers)
    group_id = grp.json()["id"]

    mem = await client.post(f"/api/v1/groups/{group_id}/members", json={
        "display_name": "Child",
        "role": "member",
    }, headers=headers)
    member_id = mem.json()["id"]
    return group_id, member_id


def _make_capture_event(group_id, member_id, platform="characterai", timestamp=None):
    """Create a CaptureEvent instance for DB insertion."""
    return CaptureEvent(
        id=uuid.uuid4(),
        group_id=uuid.UUID(group_id) if isinstance(group_id, str) else group_id,
        member_id=uuid.UUID(member_id) if isinstance(member_id, str) else member_id,
        platform=platform,
        session_id=f"sess-{uuid.uuid4().hex[:8]}",
        event_type="prompt",
        timestamp=timestamp or datetime.now(timezone.utc),
        content="Hello",
        risk_processed=False,
        source_channel="extension",
    )


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def dep_client():
    """Test client with committing DB session for dependency tests."""
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
        yield client, session

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Dependency score endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dependency_score_no_auth(dep_client):
    """GET /risk/dependency-score without auth returns 401."""
    client, _ = dep_client
    resp = await client.get(
        f"/api/v1/risk/dependency-score?member_id={uuid.uuid4()}"
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dependency_score_empty(dep_client):
    """GET /risk/dependency-score with no data returns zero score."""
    client, session = dep_client
    token, user_id = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/dependency-score?group_id={gid}&member_id={mid}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 0
    assert data["trend"] == "stable"
    assert data["risk_factors"] == []
    assert data["platform_breakdown"] == {}
    assert "recommendation" in data


@pytest.mark.asyncio
async def test_dependency_score_response_schema(dep_client):
    """Verify response includes all expected fields."""
    client, session = dep_client
    token, user_id = await _register_and_login(client, "schema@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    # Create some companion events
    now = datetime.now(timezone.utc)
    for i in range(5):
        session.add(_make_capture_event(gid, mid, timestamp=now - timedelta(hours=i)))
    await session.commit()

    resp = await client.get(
        f"/api/v1/risk/dependency-score?group_id={gid}&member_id={mid}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Verify all schema fields present
    assert "score" in data
    assert "session_duration_score" in data
    assert "frequency_score" in data
    assert "attachment_language_score" in data
    assert "time_pattern_score" in data
    assert "trend" in data
    assert "risk_factors" in data
    assert "platform_breakdown" in data
    assert "recommendation" in data

    # Score bounds
    assert 0 <= data["score"] <= 100
    assert 0 <= data["session_duration_score"] <= 25
    assert 0 <= data["frequency_score"] <= 25
    assert 0 <= data["attachment_language_score"] <= 25
    assert 0 <= data["time_pattern_score"] <= 25
    assert data["trend"] in ("improving", "stable", "worsening")


@pytest.mark.asyncio
async def test_dependency_score_with_companion_data(dep_client):
    """Score increases with companion platform usage."""
    client, session = dep_client
    token, user_id = await _register_and_login(client, "companion@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    now = datetime.now(timezone.utc)
    for i in range(20):
        session.add(_make_capture_event(
            gid, mid,
            platform="replika",
            timestamp=now - timedelta(hours=i),
        ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/risk/dependency-score?group_id={gid}&member_id={mid}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] > 0
    assert "replika" in data["platform_breakdown"]


@pytest.mark.asyncio
async def test_dependency_score_custom_days(dep_client):
    """Custom days parameter works."""
    client, session = dep_client
    token, user_id = await _register_and_login(client, "days@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/dependency-score?group_id={gid}&member_id={mid}&days=7",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["score"] == 0


@pytest.mark.asyncio
async def test_dependency_score_validation_missing_member(dep_client):
    """GET /risk/dependency-score without member_id returns 422."""
    client, _ = dep_client
    token, user_id = await _register_and_login(client, "nomember@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(
        "/api/v1/risk/dependency-score",
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Dependency history endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dependency_history_no_auth(dep_client):
    """GET /risk/dependency-score/history without auth returns 401."""
    client, _ = dep_client
    resp = await client.get(
        f"/api/v1/risk/dependency-score/history?member_id={uuid.uuid4()}"
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dependency_history_response_schema(dep_client):
    """Verify history response includes expected fields."""
    client, session = dep_client
    token, user_id = await _register_and_login(client, "history@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/dependency-score/history?group_id={gid}&member_id={mid}&days=14",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "member_id" in data
    assert "group_id" in data
    assert "days" in data
    assert "history" in data
    assert isinstance(data["history"], list)

    if len(data["history"]) > 0:
        entry = data["history"][0]
        assert "week_start" in entry
        assert "week_end" in entry
        assert "score" in entry


@pytest.mark.asyncio
async def test_dependency_history_custom_days(dep_client):
    """History with custom days parameter works."""
    client, session = dep_client
    token, user_id = await _register_and_login(client, "histdays@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/dependency-score/history?group_id={gid}&member_id={mid}&days=28",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["days"] == 28


@pytest.mark.asyncio
async def test_dependency_history_validation_missing_member(dep_client):
    """GET /risk/dependency-score/history without member_id returns 422."""
    client, _ = dep_client
    token, user_id = await _register_and_login(client, "nomem2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(
        "/api/v1/risk/dependency-score/history",
        headers=headers,
    )
    assert resp.status_code == 422
