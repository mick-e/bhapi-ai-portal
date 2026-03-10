"""E2E tests for the safety score API endpoints.

Tests GET /risk/score, GET /risk/score/group, and GET /risk/score/history.
"""

from uuid import UUID, uuid4

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

async def _register_and_login(client, email="score@test.com"):
    """Register, return (token, user_id as str)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Score Tester",
        "account_type": "family",
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


async def _create_group_and_member(client, headers):
    """Create group + child member, return (group_id str, member_id str)."""
    grp = await client.post("/api/v1/groups", json={
        "name": "Score Family",
        "type": "family",
    }, headers=headers)
    group_id = grp.json()["id"]

    mem = await client.post(f"/api/v1/groups/{group_id}/members", json={
        "display_name": "Child",
        "role": "member",
    }, headers=headers)
    member_id = mem.json()["id"]
    return group_id, member_id


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def score_client():
    """Test client with committing DB session for score tests."""
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
# GET /risk/score — member score
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_member_score_no_events(score_client):
    """Member with no risk events gets a perfect score."""
    client, session = score_client
    token, user_id = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/score?group_id={gid}&member_id={mid}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 100.0
    assert data["trend"] == "stable"
    assert data["top_categories"] == []
    assert data["member_id"] == mid
    assert data["group_id"] == gid


@pytest.mark.asyncio
async def test_member_score_with_risk_events(score_client):
    """Member with risk events gets a lowered score."""
    client, session = score_client
    token, user_id = await _register_and_login(client, "score1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    # Create critical risk events
    from src.risk.schemas import RiskClassification
    from src.risk.service import create_risk_event

    gid_uuid, mid_uuid = UUID(gid), UUID(mid)
    for _ in range(3):
        await create_risk_event(session, gid_uuid, mid_uuid, RiskClassification(
            category="SELF_HARM", severity="critical", confidence=0.9, reasoning="test"
        ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/risk/score?group_id={gid}&member_id={mid}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] < 100.0
    assert data["risk_count_by_severity"]["critical"] == 3
    assert "SELF_HARM" in data["top_categories"]


@pytest.mark.asyncio
async def test_member_score_requires_member_id(score_client):
    """GET /risk/score without member_id returns 422."""
    client, session = score_client
    token, user_id = await _register_and_login(client, "score2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/score?group_id={gid}", headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_member_score_custom_days(score_client):
    """GET /risk/score with custom days parameter."""
    client, session = score_client
    token, user_id = await _register_and_login(client, "score3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/score?group_id={gid}&member_id={mid}&days=7", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["score"] == 100.0


@pytest.mark.asyncio
async def test_member_score_requires_auth(score_client):
    """GET /risk/score requires authentication."""
    client, _ = score_client
    resp = await client.get(
        f"/api/v1/risk/score?group_id={uuid4()}&member_id={uuid4()}"
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /risk/score/group — group aggregate score
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_group_score_no_events(score_client):
    """Group with no risk events gets a perfect score."""
    client, session = score_client
    token, user_id = await _register_and_login(client, "gscore1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/score/group?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["average_score"] == 100.0
    assert data["member_scores"] == []
    assert data["group_id"] == gid


@pytest.mark.asyncio
async def test_group_score_with_events(score_client):
    """Group score includes members with risk events."""
    client, session = score_client
    token, user_id = await _register_and_login(client, "gscore2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    from src.risk.schemas import RiskClassification
    from src.risk.service import create_risk_event

    await create_risk_event(session, UUID(gid), UUID(mid), RiskClassification(
        category="VIOLENCE", severity="high", confidence=0.8, reasoning="test"
    ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/risk/score/group?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["average_score"] < 100.0
    assert len(data["member_scores"]) == 1
    assert data["member_scores"][0]["member_id"] == mid


@pytest.mark.asyncio
async def test_group_score_requires_auth(score_client):
    """GET /risk/score/group requires authentication."""
    client, _ = score_client
    resp = await client.get(f"/api/v1/risk/score/group?group_id={uuid4()}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /risk/score/history — daily score history
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_score_history_no_events(score_client):
    """Score history with no events returns all 100s."""
    client, session = score_client
    token, user_id = await _register_and_login(client, "hist1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/score/history?group_id={gid}&member_id={mid}&days=7", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["member_id"] == mid
    assert data["group_id"] == gid
    assert data["days"] == 7
    assert len(data["history"]) == 8  # 7 days + today
    for entry in data["history"]:
        assert entry["score"] == 100.0
        assert "date" in entry


@pytest.mark.asyncio
async def test_score_history_with_events(score_client):
    """Score history reflects risk events."""
    client, session = score_client
    token, user_id = await _register_and_login(client, "hist2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    from src.risk.schemas import RiskClassification
    from src.risk.service import create_risk_event

    await create_risk_event(session, UUID(gid), UUID(mid), RiskClassification(
        category="SELF_HARM", severity="critical", confidence=0.9, reasoning="test"
    ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/risk/score/history?group_id={gid}&member_id={mid}&days=7", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    # The most recent entry should be less than 100
    assert data["history"][-1]["score"] < 100.0


@pytest.mark.asyncio
async def test_score_history_requires_member_id(score_client):
    """GET /risk/score/history without member_id returns 422."""
    client, session = score_client
    token, user_id = await _register_and_login(client, "hist3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/score/history?group_id={gid}&days=7", headers=headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_score_history_requires_auth(score_client):
    """GET /risk/score/history requires authentication."""
    client, _ = score_client
    resp = await client.get(
        f"/api/v1/risk/score/history?group_id={uuid4()}&member_id={uuid4()}"
    )
    assert resp.status_code == 401
