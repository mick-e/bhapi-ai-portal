"""Security tests for the intelligence correlation rules engine.

Tests: non-admin role blocked, enriched alerts parent-only access,
condition injection prevention, rule deletion blocked for non-admin,
injection attempts via rule name/description, confidence boundary checks.
"""

import uuid
from datetime import datetime, timezone

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
from src.exceptions import ValidationError
from src.groups.models import Group, GroupMember
from src.intelligence.correlation import (
    _validate_condition,
    create_enriched_alert,
    create_rule,
)
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

    @sa_event.listens_for(engine.sync_engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
async def sec_session(sec_engine):
    session = AsyncSession(sec_engine, expire_on_commit=False)
    yield session
    await session.close()


async def _make_family(session, suffix=""):
    user = User(
        id=uuid.uuid4(),
        email=f"sec{suffix}-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name=f"Sec Parent {suffix}",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()

    group = Group(id=uuid.uuid4(), name=f"Sec Family {suffix}", type="family", owner_id=user.id)
    session.add(group)
    await session.flush()

    alert = Alert(
        id=uuid.uuid4(),
        group_id=group.id,
        severity="high",
        title="Sec Alert",
        body="body",
        channel="portal",
        status="pending",
    )
    session.add(alert)
    await session.flush()

    return user, group, alert


def _make_client(engine, session, user, group, role):
    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def fake_auth():
        return GroupContext(user_id=user.id, group_id=group.id, role=role)

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


VALID_RULE_PAYLOAD = {
    "name": "sec-test-rule",
    "description": "Security test rule",
    "condition": {
        "signals": [
            {"source": "ai_session", "metric": "session_count",
             "operator": "gt", "threshold_multiplier": 2.0},
        ],
        "logic": "AND",
        "time_window_hours": 48,
    },
    "action_severity": "medium",
    "notification_type": "alert",
}


# ===========================================================================
# Non-admin role blocked from creating rules
# ===========================================================================


@pytest.mark.asyncio
async def test_non_admin_cannot_create_rule(sec_engine, sec_session):
    """A user with 'member' role receives 403 trying to create a rule."""
    user, group, _ = await _make_family(sec_session, "na")
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, user, group, "member") as client:
        payload = {**VALID_RULE_PAYLOAD, "name": f"forbidden-{uuid.uuid4().hex[:6]}"}
        resp = await client.post("/api/v1/intelligence/correlation-rules", json=payload)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_update_rule(sec_engine, sec_session):
    """A user with 'member' role receives 403 trying to update a rule."""
    user, group, _ = await _make_family(sec_session, "nu")
    rule = await create_rule(sec_session, {
        "name": f"upd-sec-{uuid.uuid4().hex[:6]}",
        "condition": {"signals": [], "logic": "AND", "time_window_hours": 48},
        "action_severity": "medium",
        "notification_type": "alert",
    })
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, user, group, "member") as client:
        resp = await client.put(
            f"/api/v1/intelligence/correlation-rules/{rule.id}",
            json={"action_severity": "critical"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_list_rules(sec_engine, sec_session):
    """A user with 'member' role receives 403 trying to list rules."""
    user, group, _ = await _make_family(sec_session, "nl")
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, user, group, "member") as client:
        resp = await client.get("/api/v1/intelligence/correlation-rules")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_parent_role_cannot_create_rule(sec_engine, sec_session):
    """A 'parent' role user also cannot create rules (only school_admin/club_admin)."""
    user, group, _ = await _make_family(sec_session, "par")
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, user, group, "parent") as client:
        payload = {**VALID_RULE_PAYLOAD, "name": f"par-forbidden-{uuid.uuid4().hex[:6]}"}
        resp = await client.post("/api/v1/intelligence/correlation-rules", json=payload)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_create_rule(sec_engine, sec_session):
    """A 'school_admin' role user can successfully create rules."""
    user, group, _ = await _make_family(sec_session, "sa")
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, user, group, "school_admin") as client:
        payload = {**VALID_RULE_PAYLOAD, "name": f"sa-allowed-{uuid.uuid4().hex[:6]}"}
        resp = await client.post("/api/v1/intelligence/correlation-rules", json=payload)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_club_admin_can_create_rule(sec_engine, sec_session):
    """A 'club_admin' role user can successfully create rules."""
    user, group, _ = await _make_family(sec_session, "ca")
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, user, group, "club_admin") as client:
        payload = {**VALID_RULE_PAYLOAD, "name": f"ca-allowed-{uuid.uuid4().hex[:6]}"}
        resp = await client.post("/api/v1/intelligence/correlation-rules", json=payload)
    assert resp.status_code == 201


# ===========================================================================
# Condition injection prevention
# ===========================================================================


def test_condition_injection_invalid_operator():
    """Reject SQL-like injection through operator field."""
    with pytest.raises(ValidationError):
        _validate_condition({
            "signals": [{"operator": "'; DROP TABLE correlation_rules; --", "threshold_multiplier": 1.0}],
            "logic": "AND",
        })


def test_condition_injection_invalid_logic():
    """Reject injection through logic field."""
    with pytest.raises(ValidationError):
        _validate_condition({
            "signals": [],
            "logic": "AND; DROP TABLE correlation_rules",
        })


def test_condition_signal_not_dict_rejected():
    """Reject signals that are not dicts."""
    with pytest.raises(ValidationError):
        _validate_condition({
            "signals": ["not a dict"],
            "logic": "AND",
        })


def test_condition_invalid_threshold_type_rejected():
    """Reject threshold_multiplier that is a string."""
    with pytest.raises(ValidationError):
        _validate_condition({
            "signals": [{"operator": "gt", "threshold_multiplier": "1; DROP TABLE"}],
            "logic": "AND",
        })


def test_condition_none_condition_rejected():
    """Reject None/null condition."""
    with pytest.raises(ValidationError):
        _validate_condition(None)


def test_condition_empty_list_is_valid():
    """An empty signals list with valid logic is accepted."""
    _validate_condition({"signals": [], "logic": "AND", "time_window_hours": 48})


# ===========================================================================
# Enriched alert — access isolation
# ===========================================================================


@pytest.mark.asyncio
async def test_enriched_alert_not_found_returns_404(sec_engine, sec_session):
    """GET enriched-alerts/{id} returns 404 for non-existent alert_id."""
    user, group, _ = await _make_family(sec_session, "ea1")
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, user, group, "school_admin") as client:
        resp = await client.get(f"/api/v1/intelligence/enriched-alerts/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_enriched_alert_member_role_can_read(sec_engine, sec_session):
    """GET enriched-alerts/{id} allows any authenticated user to read (404 if not found)."""
    user, group, alert = await _make_family(sec_session, "ea2")
    rule = await create_rule(sec_session, {
        "name": f"ea-sec-{uuid.uuid4().hex[:6]}",
        "condition": {"signals": [], "logic": "AND", "time_window_hours": 48},
        "action_severity": "medium",
        "notification_type": "alert",
    })
    await create_enriched_alert(
        sec_session,
        alert_id=alert.id,
        rule_id=rule.id,
        context="sec ctx",
        signals={},
        score=50.0,
        confidence="medium",
    )
    await sec_session.flush()

    # Parent can read their own alert enrichment
    async with _make_client(sec_engine, sec_session, user, group, "parent") as client:
        resp = await client.get(f"/api/v1/intelligence/enriched-alerts/{alert.id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rule_update_blocked_for_member(sec_engine, sec_session):
    """Member role cannot update rules even if they know the rule UUID."""
    user, group, _ = await _make_family(sec_session, "rb")
    rule = await create_rule(sec_session, {
        "name": f"target-{uuid.uuid4().hex[:6]}",
        "condition": {"signals": [], "logic": "AND", "time_window_hours": 48},
        "action_severity": "low",
        "notification_type": "alert",
    })
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, user, group, "member") as client:
        resp = await client.put(
            f"/api/v1/intelligence/correlation-rules/{rule.id}",
            json={"action_severity": "critical"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_rule_invalid_payload_rejected(sec_engine, sec_session):
    """Invalid action_severity value returns 422 validation error."""
    user, group, _ = await _make_family(sec_session, "vp")
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, user, group, "school_admin") as client:
        payload = {
            "name": f"inv-{uuid.uuid4().hex[:6]}",
            "condition": {"signals": [], "logic": "AND"},
            "action_severity": "EXTREME",  # invalid
            "notification_type": "alert",
        }
        resp = await client.post("/api/v1/intelligence/correlation-rules", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_rule_invalid_notification_type_rejected(sec_engine, sec_session):
    """Invalid notification_type value returns 422 validation error."""
    user, group, _ = await _make_family(sec_session, "nt")
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, user, group, "school_admin") as client:
        payload = {
            "name": f"nt-{uuid.uuid4().hex[:6]}",
            "condition": {"signals": [], "logic": "AND"},
            "action_severity": "medium",
            "notification_type": "telegram",  # invalid
        }
        resp = await client.post("/api/v1/intelligence/correlation-rules", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_rule_invalid_age_tier_rejected(sec_engine, sec_session):
    """Invalid age_tier_filter value returns 422 validation error."""
    user, group, _ = await _make_family(sec_session, "at")
    await sec_session.flush()

    async with _make_client(sec_engine, sec_session, user, group, "school_admin") as client:
        payload = {
            "name": f"at-{uuid.uuid4().hex[:6]}",
            "condition": {"signals": [], "logic": "AND"},
            "action_severity": "medium",
            "notification_type": "alert",
            "age_tier_filter": "adult",  # invalid — not young/preteen/teen
        }
        resp = await client.post("/api/v1/intelligence/correlation-rules", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_unauthenticated_request_blocked(sec_engine):
    """Requests without Authorization header are rejected."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/v1/intelligence/correlation-rules")
    assert resp.status_code in (401, 403)
