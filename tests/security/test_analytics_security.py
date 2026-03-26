"""Security tests for the analytics module.

Covers:
- Unauthenticated access (401) on all analytics endpoints
- Cross-group data isolation (analytics returns only own group's data)
- Cannot access other group's usage patterns or trends
- Date range / parameter validation
- Cannot inject SQL through analytics query parameters
- Member-level analytics only accessible within own group
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.capture.models import CaptureEvent
from src.database import Base, get_db
from src.dependencies import require_active_trial_or_subscription
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sec_engine():
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

    yield engine
    await engine.dispose()


@pytest.fixture
async def sec_session(sec_engine):
    async_session_maker = sessionmaker(
        sec_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def sec_data(sec_session):
    """Create two groups with capture events for isolation tests."""
    owner_a = User(
        id=uuid.uuid4(),
        email=f"analytics-a-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Analytics Owner A",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    owner_b = User(
        id=uuid.uuid4(),
        email=f"analytics-b-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Analytics Owner B",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add_all([owner_a, owner_b])
    await sec_session.flush()

    group_a = Group(
        id=uuid.uuid4(), name="Analytics Family A", type="family", owner_id=owner_a.id,
    )
    group_b = Group(
        id=uuid.uuid4(), name="Analytics Family B", type="family", owner_id=owner_b.id,
    )
    sec_session.add_all([group_a, group_b])
    await sec_session.flush()

    member_a = GroupMember(
        id=uuid.uuid4(), group_id=group_a.id, user_id=owner_a.id,
        role="parent", display_name="Member A",
    )
    member_b = GroupMember(
        id=uuid.uuid4(), group_id=group_b.id, user_id=owner_b.id,
        role="parent", display_name="Member B",
    )
    sec_session.add_all([member_a, member_b])
    await sec_session.flush()

    # Create capture events for group A
    now = datetime.now(timezone.utc)
    for i in range(5):
        ev = CaptureEvent(
            id=uuid.uuid4(),
            group_id=group_a.id,
            member_id=member_a.id,
            platform="chatgpt",
            session_id=f"sess-a-{i}",
            event_type="prompt",
            timestamp=now - timedelta(days=i),
            source_channel="extension",
        )
        sec_session.add(ev)

    # Create capture events for group B
    for i in range(3):
        ev = CaptureEvent(
            id=uuid.uuid4(),
            group_id=group_b.id,
            member_id=member_b.id,
            platform="gemini",
            session_id=f"sess-b-{i}",
            event_type="prompt",
            timestamp=now - timedelta(days=i),
            source_channel="extension",
        )
        sec_session.add(ev)

    await sec_session.flush()

    return {
        "owner_a": owner_a,
        "owner_b": owner_b,
        "group_a": group_a,
        "group_b": group_b,
        "member_a": member_a,
        "member_b": member_b,
    }


def _make_client(sec_engine, sec_session, user_id, group_id=None, role="parent"):
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(user_id=user_id, group_id=group_id, role=role)

    async def fake_trial(auth=None, db=None):
        return GroupContext(user_id=user_id, group_id=group_id, role=role)

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth
    app.dependency_overrides[require_active_trial_or_subscription] = fake_trial

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


def _make_unauthed_client(sec_engine, sec_session):
    """Client without auth override — relies on real auth middleware."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


# ---------------------------------------------------------------------------
# Tests — Unauthenticated Access (401)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthed_trends(sec_engine, sec_session):
    """Unauthenticated request to trends returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get("/api/v1/analytics/trends")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_usage_patterns(sec_engine, sec_session):
    """Unauthenticated request to usage patterns returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get("/api/v1/analytics/usage-patterns")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_member_baselines(sec_engine, sec_session):
    """Unauthenticated request to member baselines returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get("/api/v1/analytics/member-baselines")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_peer_comparison(sec_engine, sec_session):
    """Unauthenticated request to peer comparison returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get("/api/v1/analytics/peer-comparison")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_anomalies(sec_engine, sec_session):
    """Unauthenticated request to anomalies returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get("/api/v1/analytics/anomalies")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_academic_report(sec_engine, sec_session):
    """Unauthenticated request to academic report returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get(
            "/api/v1/analytics/academic",
            params={"member_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthed_academic_intent(sec_engine, sec_session):
    """Unauthenticated request to intent classification returns 401."""
    async with _make_unauthed_client(sec_engine, sec_session) as client:
        resp = await client.get(
            "/api/v1/analytics/academic/intent",
            params={"text": "help me with homework"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests — Cross-Group Data Isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trends_returns_only_own_group_data(sec_engine, sec_session, sec_data):
    """Trends endpoint returns data scoped to the user's group only."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get("/api/v1/analytics/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == str(sec_data["group_a"].id)


@pytest.mark.asyncio
async def test_trends_does_not_leak_other_group(sec_engine, sec_session, sec_data):
    """User A's trends should not contain group B's group_id."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get("/api/v1/analytics/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert str(sec_data["group_b"].id) not in str(data)


@pytest.mark.asyncio
async def test_usage_patterns_cross_group_isolation(sec_engine, sec_session, sec_data):
    """Usage patterns only includes events from the user's group."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get("/api/v1/analytics/usage-patterns")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == str(sec_data["group_a"].id)
        # Group A only uses chatgpt, group B uses gemini
        if data["by_platform"]:
            assert "gemini" not in data["by_platform"]


@pytest.mark.asyncio
async def test_member_baselines_cross_group_isolation(sec_engine, sec_session, sec_data):
    """Member baselines only includes members from own group."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get("/api/v1/analytics/member-baselines")
        assert resp.status_code == 200
        data = resp.json()
        member_ids = [m["member_id"] for m in data]
        assert str(sec_data["member_a"].id) in member_ids
        assert str(sec_data["member_b"].id) not in member_ids


@pytest.mark.asyncio
async def test_peer_comparison_cross_group_isolation(sec_engine, sec_session, sec_data):
    """Peer comparison only includes members from own group."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get("/api/v1/analytics/peer-comparison")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == str(sec_data["group_a"].id)
        member_ids = [m["member_id"] for m in data["members"]]
        assert str(sec_data["member_b"].id) not in member_ids


@pytest.mark.asyncio
async def test_anomalies_cross_group_isolation(sec_engine, sec_session, sec_data):
    """Anomaly detection scoped to own group only."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get("/api/v1/analytics/anomalies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == str(sec_data["group_a"].id)


# ---------------------------------------------------------------------------
# Tests — Parameter Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trends_days_too_low_rejected(sec_engine, sec_session, sec_data):
    """Days parameter below minimum (7) is rejected."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get("/api/v1/analytics/trends", params={"days": 1})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_trends_days_too_high_rejected(sec_engine, sec_session, sec_data):
    """Days parameter above maximum (90) is rejected."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get("/api/v1/analytics/trends", params={"days": 365})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_usage_patterns_days_validation(sec_engine, sec_session, sec_data):
    """Usage patterns days parameter validates range."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get("/api/v1/analytics/usage-patterns", params={"days": 0})
        assert resp.status_code == 422

        resp = await client.get("/api/v1/analytics/usage-patterns", params={"days": 200})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_anomalies_threshold_sd_validation(sec_engine, sec_session, sec_data):
    """Anomaly threshold_sd parameter validates range (1.0 - 5.0)."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get("/api/v1/analytics/anomalies", params={"threshold_sd": 0.1})
        assert resp.status_code == 422

        resp = await client.get("/api/v1/analytics/anomalies", params={"threshold_sd": 10.0})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_academic_start_date_after_end_date_rejected(sec_engine, sec_session, sec_data):
    """Academic report with start_date after end_date is rejected."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get(
            "/api/v1/analytics/academic",
            params={
                "member_id": str(sec_data["member_a"].id),
                "start_date": "2026-03-20",
                "end_date": "2026-03-10",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_academic_intent_empty_text_rejected(sec_engine, sec_session, sec_data):
    """Intent classification with empty text is rejected."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get(
            "/api/v1/analytics/academic/intent",
            params={"text": ""},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests — SQL Injection Attempts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sql_injection_in_days_param(sec_engine, sec_session, sec_data):
    """SQL injection attempt in days parameter is rejected (type validation)."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get(
            "/api/v1/analytics/trends",
            params={"days": "30; DROP TABLE capture_events;--"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_in_group_id_param(sec_engine, sec_session, sec_data):
    """SQL injection attempt in group_id parameter is rejected (UUID validation)."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get(
            "/api/v1/analytics/trends",
            params={"group_id": "'; DROP TABLE groups;--"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_in_threshold_sd(sec_engine, sec_session, sec_data):
    """SQL injection attempt in threshold_sd is rejected (float validation)."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get(
            "/api/v1/analytics/anomalies",
            params={"threshold_sd": "2.0 OR 1=1"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_in_member_id(sec_engine, sec_session, sec_data):
    """SQL injection attempt in member_id is rejected (UUID validation)."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get(
            "/api/v1/analytics/academic",
            params={
                "member_id": "'; SELECT * FROM users;--",
                "start_date": "2026-03-01",
                "end_date": "2026-03-20",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sql_injection_in_intent_text(sec_engine, sec_session, sec_data):
    """SQL injection in intent text — should not crash, just classify normally."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get(
            "/api/v1/analytics/academic/intent",
            params={"text": "'; DROP TABLE users;--"},
        )
        # The text is just classified, not used in SQL — should return 200
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests — Member-Level Analytics Within Own Group
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_academic_report_for_own_group_member(sec_engine, sec_session, sec_data):
    """Academic report for a member in the user's own group succeeds."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_a"].id, sec_data["group_a"].id,
    ) as client:
        resp = await client.get(
            "/api/v1/analytics/academic",
            params={
                "member_id": str(sec_data["member_a"].id),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["member_id"] == str(sec_data["member_a"].id)


@pytest.mark.asyncio
async def test_member_baselines_does_not_include_other_group_members(
    sec_engine, sec_session, sec_data,
):
    """Member baselines for group A must not include group B members."""
    async with _make_client(
        sec_engine, sec_session, sec_data["owner_b"].id, sec_data["group_b"].id,
    ) as client:
        resp = await client.get("/api/v1/analytics/member-baselines")
        assert resp.status_code == 200
        data = resp.json()
        member_ids = [m["member_id"] for m in data]
        # Should include member_b, not member_a
        assert str(sec_data["member_b"].id) in member_ids
        assert str(sec_data["member_a"].id) not in member_ids
