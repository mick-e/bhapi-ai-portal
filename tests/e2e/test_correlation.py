"""E2E tests for the correlation rules engine.

Full-flow tests: event → rule match → enriched alert, endpoint CRUD,
multiple rule matching, disable/enable, and condition boundaries.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.alerts.models import Alert
from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.intelligence.correlation import (
    create_enriched_alert,
    create_rule,
    evaluate_event,
    get_enriched_alert,
    get_rules,
    update_rule,
)
from src.main import create_app
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Engine / session fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def e2e_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sa_event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
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


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


async def _make_user_group_alert(session, role="parent"):
    """Create minimal User + Group + Alert for FK safety."""
    user = User(
        id=uuid.uuid4(),
        email=f"e2e-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="E2E Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()

    group = Group(id=uuid.uuid4(), name="E2E Family", type="family", owner_id=user.id)
    session.add(group)
    await session.flush()

    alert = Alert(
        id=uuid.uuid4(),
        group_id=group.id,
        severity="high",
        title="E2E Alert",
        body="body",
        channel="portal",
        status="pending",
    )
    session.add(alert)
    await session.flush()

    return user, group, alert


def _simple_condition(metric="session_count", op="gt", multiplier=2.0):
    return {
        "signals": [
            {"source": "ai_session", "metric": metric,
             "operator": op, "threshold_multiplier": multiplier},
        ],
        "logic": "AND",
        "time_window_hours": 48,
    }


async def _mk_rule(session, name=None, condition=None, severity="medium",
                   notification="alert", age_tier=None, enabled=True):
    return await create_rule(session, {
        "name": name or f"rule-{uuid.uuid4().hex[:8]}",
        "description": "E2E test rule",
        "condition": condition or _simple_condition(),
        "action_severity": severity,
        "notification_type": notification,
        "age_tier_filter": age_tier,
        "enabled": enabled,
    })


# ---------------------------------------------------------------------------
# HTTP client fixture (admin role)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def e2e_data(e2e_session):
    user, group, alert = await _make_user_group_alert(e2e_session)
    return {"user": user, "group": group, "alert": alert}


@pytest_asyncio.fixture
async def e2e_client(e2e_engine, e2e_session, e2e_data):
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
            user_id=e2e_data["user"].id,
            group_id=e2e_data["group"].id,
            role="school_admin",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


# ===========================================================================
# Full flow: event → rule match → enriched alert
# ===========================================================================


@pytest.mark.asyncio
async def test_event_matches_rule_creates_enriched_alert(e2e_session):
    """Full flow: event matches a rule; enriched alert created with correct score."""
    rule = await _mk_rule(e2e_session, name="flow-test")
    await e2e_session.flush()

    _, _, alert = await _make_user_group_alert(e2e_session)
    event = {"source": "ai_session", "metrics": {"session_count": 10.0}}

    matches = await evaluate_event(e2e_session, event)
    assert any(m["rule"].name == "flow-test" for m in matches)

    match = next(m for m in matches if m["rule"].name == "flow-test")
    enriched = await create_enriched_alert(
        e2e_session,
        alert_id=alert.id,
        rule_id=rule.id,
        context=f"Rule '{rule.name}' fired",
        signals={"matched_signals": match["signals"]},
        score=match["score"],
        confidence=match["confidence"],
    )
    await e2e_session.flush()

    assert enriched.alert_id == alert.id
    assert enriched.correlation_rule_id == rule.id
    assert enriched.unified_risk_score > 0


@pytest.mark.asyncio
async def test_multiple_rules_match_same_event(e2e_session):
    """Multiple matching rules all return in evaluate_event results."""
    await _mk_rule(e2e_session, name="multi-r1",
                   condition=_simple_condition(multiplier=1.0))
    await _mk_rule(e2e_session, name="multi-r2",
                   condition=_simple_condition(multiplier=1.0))
    await e2e_session.flush()

    event = {"source": "ai_session", "metrics": {"session_count": 5.0}}
    matches = await evaluate_event(e2e_session, event)
    matching_names = [m["rule"].name for m in matches]
    assert "multi-r1" in matching_names
    assert "multi-r2" in matching_names


@pytest.mark.asyncio
async def test_no_match_when_conditions_unmet(e2e_session):
    """evaluate_event returns no matches when all conditions fail."""
    await _mk_rule(e2e_session, name="unmet-rule",
                   condition=_simple_condition(multiplier=1000.0))
    await e2e_session.flush()

    matches = await evaluate_event(e2e_session, {
        "source": "ai_session",
        "metrics": {"session_count": 1.0},
    })
    assert not any(m["rule"].name == "unmet-rule" for m in matches)


@pytest.mark.asyncio
async def test_disable_rule_stops_matching(e2e_session):
    """Disabling a rule stops it from matching future events."""
    rule = await _mk_rule(e2e_session, name="to-disable")
    await e2e_session.flush()

    event = {"source": "ai_session", "metrics": {"session_count": 10.0}}
    matches = await evaluate_event(e2e_session, event)
    assert any(m["rule"].name == "to-disable" for m in matches)

    await update_rule(e2e_session, rule.id, {"enabled": False})
    await e2e_session.flush()

    matches_after = await evaluate_event(e2e_session, event)
    assert not any(m["rule"].name == "to-disable" for m in matches_after)


@pytest.mark.asyncio
async def test_reenable_rule_resumes_matching(e2e_session):
    """Re-enabling a rule allows it to match again."""
    rule = await _mk_rule(e2e_session, name="to-reenable", enabled=False)
    await e2e_session.flush()

    event = {"source": "ai_session", "metrics": {"session_count": 10.0}}
    matches = await evaluate_event(e2e_session, event)
    assert not any(m["rule"].name == "to-reenable" for m in matches)

    await update_rule(e2e_session, rule.id, {"enabled": True})
    await e2e_session.flush()

    matches_after = await evaluate_event(e2e_session, event)
    assert any(m["rule"].name == "to-reenable" for m in matches_after)


@pytest.mark.asyncio
async def test_event_timestamp_outside_window_no_match(e2e_session):
    """An event timestamped outside the rule window does not match."""
    await _mk_rule(e2e_session, name="window-e2e", condition={
        "signals": [{"source": "ai_session", "metric": "session_count",
                     "operator": "gt", "threshold_multiplier": 0.0}],
        "logic": "AND",
        "time_window_hours": 1,
    })
    await e2e_session.flush()

    old_ts = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    matches = await evaluate_event(e2e_session, {
        "source": "ai_session",
        "metrics": {"session_count": 5.0},
        "timestamp": old_ts,
    })
    assert not any(m["rule"].name == "window-e2e" for m in matches)


@pytest.mark.asyncio
async def test_enriched_alert_persists_and_retrieves(e2e_session):
    """Enriched alert created for an event match can be retrieved by alert_id."""
    rule = await _mk_rule(e2e_session, name="persist-rule")
    _, _, alert = await _make_user_group_alert(e2e_session)
    await e2e_session.flush()

    await create_enriched_alert(
        e2e_session,
        alert_id=alert.id,
        rule_id=rule.id,
        context="Test persistence",
        signals={"key": "value"},
        score=60.0,
        confidence="medium",
    )
    await e2e_session.flush()

    found = await get_enriched_alert(e2e_session, alert.id)
    assert found is not None
    assert found.unified_risk_score == 60.0
    assert found.confidence == "medium"


@pytest.mark.asyncio
async def test_age_tier_filter_e2e(e2e_session):
    """Rules with age_tier_filter only match events with matching age_tier."""
    await _mk_rule(e2e_session, name="young-only", age_tier="young",
                   condition=_simple_condition(multiplier=0.0))
    await e2e_session.flush()

    # Preteen event should not match young rule
    matches = await evaluate_event(e2e_session, {
        "source": "ai_session",
        "age_tier": "preteen",
        "metrics": {"session_count": 5.0},
    })
    assert not any(m["rule"].name == "young-only" for m in matches)

    # Young event should match
    matches = await evaluate_event(e2e_session, {
        "source": "ai_session",
        "age_tier": "young",
        "metrics": {"session_count": 5.0},
    })
    assert any(m["rule"].name == "young-only" for m in matches)


@pytest.mark.asyncio
async def test_null_tier_rule_matches_all_tiers(e2e_session):
    """A rule with no age_tier_filter matches all age tiers."""
    await _mk_rule(e2e_session, name="all-ages", age_tier=None,
                   condition=_simple_condition(multiplier=0.0))
    await e2e_session.flush()

    for tier in ("young", "preteen", "teen"):
        matches = await evaluate_event(e2e_session, {
            "source": "ai_session",
            "age_tier": tier,
            "metrics": {"session_count": 5.0},
        })
        assert any(m["rule"].name == "all-ages" for m in matches), f"Expected match for tier {tier}"


# ===========================================================================
# HTTP endpoint: GET /api/v1/intelligence/correlation-rules
# ===========================================================================


@pytest.mark.asyncio
async def test_list_rules_endpoint(e2e_client, e2e_session):
    """GET /intelligence/correlation-rules returns rules for admin user."""
    # Override GroupContext to include is_admin=True
    rule = await _mk_rule(e2e_session, name="list-endpoint-rule")
    await e2e_session.commit()

    resp = await e2e_client.get("/api/v1/intelligence/correlation-rules")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_create_rule_endpoint(e2e_client, e2e_session):
    """POST /intelligence/correlation-rules creates a rule and returns 201."""
    payload = {
        "name": f"http-create-{uuid.uuid4().hex[:6]}",
        "description": "HTTP created rule",
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "session_count",
                 "operator": "gt", "threshold_multiplier": 2.0},
            ],
            "logic": "AND",
            "time_window_hours": 48,
        },
        "action_severity": "high",
        "notification_type": "alert",
    }
    resp = await e2e_client.post("/api/v1/intelligence/correlation-rules", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == payload["name"]
    assert data["action_severity"] == "high"


@pytest.mark.asyncio
async def test_update_rule_endpoint(e2e_client, e2e_session):
    """PUT /intelligence/correlation-rules/{id} updates a rule."""
    rule = await _mk_rule(e2e_session, name=f"upd-http-{uuid.uuid4().hex[:6]}")
    await e2e_session.commit()

    resp = await e2e_client.put(
        f"/api/v1/intelligence/correlation-rules/{rule.id}",
        json={"action_severity": "critical", "enabled": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action_severity"] == "critical"
    assert data["enabled"] is False


@pytest.mark.asyncio
async def test_get_enriched_alert_endpoint_not_found(e2e_client):
    """GET /intelligence/enriched-alerts/{id} returns 404 for unknown alert."""
    resp = await e2e_client.get(f"/api/v1/intelligence/enriched-alerts/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_enriched_alert_endpoint_found(e2e_client, e2e_session, e2e_data):
    """GET /intelligence/enriched-alerts/{id} returns enrichment for known alert."""
    rule = await _mk_rule(e2e_session, name=f"ea-http-{uuid.uuid4().hex[:6]}")
    alert = e2e_data["alert"]
    await create_enriched_alert(
        e2e_session,
        alert_id=alert.id,
        rule_id=rule.id,
        context="E2E enrichment",
        signals={"x": 1},
        score=42.0,
        confidence="medium",
    )
    await e2e_session.commit()

    resp = await e2e_client.get(f"/api/v1/intelligence/enriched-alerts/{alert.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["unified_risk_score"] == 42.0
    assert data["confidence"] == "medium"


@pytest.mark.asyncio
async def test_or_logic_rule_matches_on_single_signal(e2e_session):
    """An OR-logic rule matches when only one of multiple signals is present."""
    await _mk_rule(e2e_session, name="or-logic-e2e", condition={
        "signals": [
            {"source": "ai_session", "metric": "session_count",
             "operator": "gt", "threshold_multiplier": 1.0},
            {"source": "social_activity", "metric": "post_frequency",
             "operator": "gt", "threshold_multiplier": 100.0},  # This one won't match
        ],
        "logic": "OR",
        "time_window_hours": 48,
    })
    await e2e_session.flush()

    # Only session_count is high; post_frequency metric not present
    matches = await evaluate_event(e2e_session, {
        "source": "ai_session",
        "metrics": {"session_count": 5.0},
    })
    assert any(m["rule"].name == "or-logic-e2e" for m in matches)
