"""E2E tests for behavioral anomaly correlation endpoints (P3-I4).

Tests cover:
- GET /api/v1/intelligence/anomalies/{child_id}
- POST /api/v1/intelligence/anomalies/scan
- Auth enforcement
- Empty baseline returns safe empty response
- Scan with anomalies returns results and creates alerts
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.device_agent.models import ScreenTimeRecord
from src.groups.models import Group, GroupMember
from src.intelligence.models import BehavioralBaseline
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def e2e_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
async def e2e_session(e2e_engine):
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def setup(e2e_session):
    """Create a parent + group + child member."""
    owner = User(
        id=uuid4(),
        email=f"parent-{uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Test Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(owner)
    await e2e_session.flush()

    group = Group(id=uuid4(), name="E2E Family", type="family", owner_id=owner.id)
    e2e_session.add(group)
    await e2e_session.flush()

    child = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="E2E Child",
        date_of_birth=datetime(2015, 6, 15, tzinfo=timezone.utc),
    )
    e2e_session.add(child)
    await e2e_session.flush()

    return {"owner": owner, "group": group, "child": child}


@pytest.fixture
def make_client(e2e_engine, e2e_session, setup):
    """Factory that creates an authenticated client."""

    async def _build():
        app = create_app()

        async def get_db_override():
            try:
                yield e2e_session
                await e2e_session.commit()
            except Exception:
                await e2e_session.rollback()
                raise

        async def fake_auth():
            return GroupContext(
                user_id=setup["owner"].id,
                group_id=setup["group"].id,
                role="parent",
            )

        app.dependency_overrides[get_db] = get_db_override
        app.dependency_overrides[get_current_user] = fake_auth
        return app, get_db_override, fake_auth

    return _build


@pytest_asyncio.fixture
async def authed_client(e2e_engine, e2e_session, setup):
    """Authenticated test client."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=setup["owner"].id,
            group_id=setup["group"].id,
            role="parent",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client, setup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _add_baseline(session, member_id, metrics: dict, days_ago: int = 0):
    computed = datetime.now(timezone.utc) - timedelta(days=days_ago)
    b = BehavioralBaseline(
        id=uuid4(),
        member_id=member_id,
        window_days=30,
        metrics=metrics,
        computed_at=computed,
        sample_count=10,
    )
    session.add(b)
    await session.flush()
    return b


async def _add_screen_time(session, member, group, minutes: float, days_ago: int = 0):
    d = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date()
    rec = ScreenTimeRecord(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        date=d,
        total_minutes=minutes,
        pickups=0,
    )
    session.add(rec)
    await session.flush()
    return rec


# ---------------------------------------------------------------------------
# GET /api/v1/intelligence/anomalies/{child_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_anomalies_returns_200(authed_client):
    """GET anomalies endpoint returns 200 with correct structure."""
    client, data = authed_client
    child_id = data["child"].id

    resp = await client.get(f"/api/v1/intelligence/anomalies/{child_id}")
    assert resp.status_code == 200

    body = resp.json()
    assert "child_id" in body
    assert "signal_anomalies" in body
    assert "evasion" in body
    assert "cross_signal_anomalies" in body
    assert "total_anomalies" in body


@pytest.mark.asyncio
async def test_get_anomalies_no_baseline_returns_empty(authed_client):
    """GET anomalies with no baseline data returns empty / zero results."""
    client, data = authed_client
    child_id = data["child"].id

    resp = await client.get(f"/api/v1/intelligence/anomalies/{child_id}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total_anomalies"] == 0
    assert body["evasion"] is None
    assert body["cross_signal_anomalies"] == []


@pytest.mark.asyncio
async def test_get_anomalies_with_spike_detected(authed_client, e2e_session, setup):
    """GET anomalies with AI usage spike returns flagged anomaly."""
    client, data = authed_client
    child = data["child"]
    data["group"]

    # Seed baseline and spike
    for i in range(1, 6):
        await _add_baseline(e2e_session, child.id, {"ai_session_count": 5.0}, days_ago=i)
    await _add_baseline(e2e_session, child.id, {"ai_session_count": 50.0}, days_ago=0)
    await e2e_session.flush()

    resp = await client.get(f"/api/v1/intelligence/anomalies/{child.id}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["total_anomalies"] >= 1
    ai_sigs = [s for s in body["signal_anomalies"] if s["signal_type"] == "ai_usage"]
    assert len(ai_sigs) == 1
    assert ai_sigs[0]["is_anomalous"] is True


@pytest.mark.asyncio
async def test_get_anomalies_evasion_pattern(authed_client, e2e_session, setup):
    """GET anomalies detects evasion when AI drops + screen stable."""
    client, data = authed_client
    child = data["child"]
    group = data["group"]

    # Baseline AI: 20/day; current: 5 (75% drop)
    for i in range(1, 6):
        await _add_baseline(e2e_session, child.id, {"ai_session_count": 20.0}, days_ago=i)
    await _add_baseline(e2e_session, child.id, {"ai_session_count": 5.0}, days_ago=0)

    # Screen time: stable ~120 min
    for i in range(1, 6):
        await _add_screen_time(e2e_session, child, group, minutes=120.0, days_ago=i)
    await _add_screen_time(e2e_session, child, group, minutes=122.0, days_ago=0)
    await e2e_session.flush()

    resp = await client.get(f"/api/v1/intelligence/anomalies/{child.id}")
    assert resp.status_code == 200

    body = resp.json()
    assert body["evasion"] is not None
    assert body["evasion"]["ai_drop_pct"] > 0.5


@pytest.mark.asyncio
async def test_get_anomalies_cross_signal_pattern(authed_client, e2e_session, setup):
    """GET anomalies detects cross-signal pattern (social withdrawal + AI spike)."""
    client, data = authed_client
    child = data["child"]

    # Baseline: social=10, ai=5 for 5 days
    for i in range(1, 6):
        await _add_baseline(
            e2e_session, child.id,
            {"ai_session_count": 5.0, "avg_posts_per_day": 10.0},
            days_ago=i,
        )
    # Spike: AI=40, social=0
    await _add_baseline(
        e2e_session, child.id,
        {"ai_session_count": 40.0, "avg_posts_per_day": 0.0},
        days_ago=0,
    )
    await e2e_session.flush()

    resp = await client.get(f"/api/v1/intelligence/anomalies/{child.id}")
    assert resp.status_code == 200

    body = resp.json()
    cross = body["cross_signal_anomalies"]
    assert len(cross) >= 1
    assert any(a["pattern_type"] == "social_withdrawal_ai_spike" for a in cross)


@pytest.mark.asyncio
async def test_get_anomalies_requires_auth(e2e_engine, setup):
    """GET anomalies without auth returns 401 or 403."""
    app = create_app()
    child_id = setup["child"].id

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        # No Authorization header
    ) as client:
        resp = await client.get(f"/api/v1/intelligence/anomalies/{child_id}")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/v1/intelligence/anomalies/scan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_scan_returns_200(authed_client):
    """POST scan endpoint returns 200 with scan summary."""
    client, data = authed_client
    child_id = data["child"].id

    resp = await client.post(
        "/api/v1/intelligence/anomalies/scan",
        json={"child_id": str(child_id)},
    )
    assert resp.status_code == 200

    body = resp.json()
    assert "child_id" in body
    assert "scanned_at" in body
    assert "total_anomalies" in body
    assert "alerts_created" in body


@pytest.mark.asyncio
async def test_post_scan_no_data_returns_zero(authed_client):
    """POST scan on child with no data returns 0 anomalies."""
    client, data = authed_client
    child_id = data["child"].id

    resp = await client.post(
        "/api/v1/intelligence/anomalies/scan",
        json={"child_id": str(child_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_anomalies"] == 0
    assert body["alerts_created"] == 0


@pytest.mark.asyncio
async def test_post_scan_with_anomaly_creates_alert(authed_client, e2e_session, setup):
    """POST scan with AI spike creates alert and returns counts."""
    client, data = authed_client
    child = data["child"]

    # Seed AI spike
    for i in range(1, 6):
        await _add_baseline(e2e_session, child.id, {"ai_session_count": 5.0}, days_ago=i)
    await _add_baseline(e2e_session, child.id, {"ai_session_count": 50.0}, days_ago=0)
    await e2e_session.flush()

    resp = await client.post(
        "/api/v1/intelligence/anomalies/scan",
        json={"child_id": str(child.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_anomalies"] >= 1
    assert body["alerts_created"] >= 1


@pytest.mark.asyncio
async def test_post_scan_requires_auth(e2e_engine, setup):
    """POST scan without auth returns 401 or 403."""
    app = create_app()
    child_id = setup["child"].id

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v1/intelligence/anomalies/scan",
            json={"child_id": str(child_id)},
        )
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_post_scan_invalid_uuid_returns_422(authed_client):
    """POST scan with invalid UUID returns 422 validation error."""
    client, _ = authed_client

    resp = await client.post(
        "/api/v1/intelligence/anomalies/scan",
        json={"child_id": "not-a-uuid"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_scan_unknown_child_returns_empty(authed_client):
    """POST scan with unknown child_id returns empty scan (not crash)."""
    client, _ = authed_client

    resp = await client.post(
        "/api/v1/intelligence/anomalies/scan",
        json={"child_id": str(uuid4())},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_anomalies"] == 0


@pytest.mark.asyncio
async def test_post_scan_evasion_creates_high_severity_alert(authed_client, e2e_session, setup):
    """Evasion detection scan creates a high-severity alert."""
    from sqlalchemy import select

    from src.alerts.models import Alert

    client, data = authed_client
    child = data["child"]
    group = data["group"]

    # Baseline AI: 20/day; current: 5 (75% drop)
    for i in range(1, 6):
        await _add_baseline(e2e_session, child.id, {"ai_session_count": 20.0}, days_ago=i)
    await _add_baseline(e2e_session, child.id, {"ai_session_count": 5.0}, days_ago=0)
    # Screen stable
    for i in range(1, 6):
        await _add_screen_time(e2e_session, child, group, minutes=120.0, days_ago=i)
    await _add_screen_time(e2e_session, child, group, minutes=118.0, days_ago=0)
    await e2e_session.flush()

    resp = await client.post(
        "/api/v1/intelligence/anomalies/scan",
        json={"child_id": str(child.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["evasion"] is not None
    assert body["alerts_created"] >= 1

    # Verify high-severity alert was created
    result = await e2e_session.execute(
        select(Alert).where(Alert.member_id == child.id, Alert.severity == "high")
    )
    high_alerts = result.scalars().all()
    assert len(high_alerts) >= 1


@pytest.mark.asyncio
async def test_get_anomalies_child_id_in_response_matches(authed_client):
    """GET anomalies response child_id matches request path parameter."""
    client, data = authed_client
    child_id = data["child"].id

    resp = await client.get(f"/api/v1/intelligence/anomalies/{child_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["child_id"] == str(child_id)


@pytest.mark.asyncio
async def test_post_scan_child_id_in_response_matches(authed_client):
    """POST scan response child_id matches request body."""
    client, data = authed_client
    child_id = data["child"].id

    resp = await client.post(
        "/api/v1/intelligence/anomalies/scan",
        json={"child_id": str(child_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["child_id"] == str(child_id)


@pytest.mark.asyncio
async def test_get_anomalies_signal_list_has_location_placeholder(authed_client, e2e_session, setup):
    """GET anomalies signal_anomalies always includes location placeholder (not anomalous)."""
    client, data = authed_client
    child = data["child"]

    # Add at least one baseline to get signal results
    await _add_baseline(e2e_session, child.id, {"ai_session_count": 5.0}, days_ago=1)
    await _add_baseline(e2e_session, child.id, {"ai_session_count": 5.0}, days_ago=0)
    await e2e_session.flush()

    resp = await client.get(f"/api/v1/intelligence/anomalies/{child.id}")
    assert resp.status_code == 200
    body = resp.json()

    location_sigs = [s for s in body["signal_anomalies"] if s["signal_type"] == "location_movement"]
    assert len(location_sigs) == 1
    assert location_sigs[0]["is_anomalous"] is False
