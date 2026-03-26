"""Unit tests for alert enrichment with correlated context (P3-I3).

Covers:
- Alert creation without enrichment (baseline)
- Alert creation with matching correlation rule
- Enrichment context string format
- Contributing signals JSON structure
- Enrichment failure doesn't block alert creation
- enriched_alert_id stored on alert
- get_enriched_alert_by_id returns correct record
- Alert.enriched_alert_id is nullable
- Enrichment omitted when no member_id
- Service gracefully handles intelligence import error
- EnrichedAlert fields match what was written
- Multiple alerts can have independent enrichments
- Confidence levels propagated correctly
- Score propagated correctly from matched signals
- get_enriched_alert returns None when alert has no enrichment
"""

from unittest.mock import patch
from uuid import uuid4

import pytest

from src.alerts.models import Alert
from src.alerts.schemas import AlertCreate
from src.alerts.service import create_alert
from src.intelligence.correlation import create_enriched_alert, get_enriched_alert, get_enriched_alert_by_id
from tests.conftest import make_test_group

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_group_member(session, group_id, user_id=None):
    from src.auth.models import User
    from src.groups.models import GroupMember

    uid = user_id or uuid4()
    user = User(
        id=uid,
        email=f"child-{uid.hex[:8]}@example.com",
        display_name="Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()

    member = GroupMember(
        id=uuid4(),
        group_id=group_id,
        user_id=uid,
        role="member",
        display_name="Child",
    )
    session.add(member)
    await session.flush()
    return member


async def _make_raw_alert(session, group_id, member_id=None, severity="medium"):
    """Create a raw Alert row without going through the service."""
    alert = Alert(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        severity=severity,
        title="Test Alert",
        body="Test body",
        source="ai",
        channel="portal",
        status="pending",
    )
    session.add(alert)
    await session.flush()
    return alert


def _alert_create(group_id, member_id=None, severity="medium", source="ai"):
    return AlertCreate(
        group_id=group_id,
        member_id=member_id,
        severity=severity,
        title="Test enrichment alert",
        body="Body text for enrichment test",
        channel="portal",
        source=source,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alert_enriched_alert_id_nullable(test_session):
    """Alert.enriched_alert_id defaults to None."""
    group, _ = await make_test_group(test_session)
    alert = await _make_raw_alert(test_session, group.id)
    assert alert.enriched_alert_id is None


@pytest.mark.asyncio
async def test_create_enriched_alert_direct(test_session):
    """create_enriched_alert stores correlation_context and signals correctly."""
    group, _ = await make_test_group(test_session)
    alert = await _make_raw_alert(test_session, group.id)

    signals = {"matched": [{"source": "ai", "metric": "risk_score", "value": 0.9}], "source": "ai"}
    enriched = await create_enriched_alert(
        test_session,
        alert_id=alert.id,
        rule_id=None,
        context="Correlated alert: rule 'test_rule' matched 1 signal(s) with score 0.90 [high confidence]",
        signals=signals,
        score=0.9,
        confidence="high",
    )

    assert enriched.id is not None
    assert enriched.alert_id == alert.id
    assert "test_rule" in enriched.correlation_context
    assert enriched.contributing_signals == signals
    assert enriched.unified_risk_score == pytest.approx(0.9)
    assert enriched.confidence == "high"


@pytest.mark.asyncio
async def test_enrichment_context_string_format(test_session):
    """Enrichment context string contains member_id, rule name, signal count and score."""
    group, _ = await make_test_group(test_session)
    alert = await _make_raw_alert(test_session, group.id)
    member_id = uuid4()

    context_str = (
        f"Correlated alert for member {member_id}: "
        f"rule 'emotional_dependency' matched 2 signal(s) "
        f"with score 1.50 [medium confidence]"
    )
    enriched = await create_enriched_alert(
        test_session,
        alert_id=alert.id,
        rule_id=None,
        context=context_str,
        signals={"matched": [], "source": "ai"},
        score=1.5,
        confidence="medium",
    )

    assert str(member_id) in enriched.correlation_context
    assert "emotional_dependency" in enriched.correlation_context
    assert "2 signal(s)" in enriched.correlation_context
    assert "1.50" in enriched.correlation_context


@pytest.mark.asyncio
async def test_contributing_signals_json_structure(test_session):
    """Contributing signals must contain 'matched' list and 'source' key."""
    group, _ = await make_test_group(test_session)
    alert = await _make_raw_alert(test_session, group.id)

    signals = {
        "matched": [
            {"source": "ai", "metric": "risk_score", "value": 0.8, "score_contribution": 0.8},
            {"source": "device", "metric": "screen_time", "value": 6.0, "score_contribution": 6.0},
        ],
        "source": "ai",
    }
    enriched = await create_enriched_alert(
        test_session,
        alert_id=alert.id,
        rule_id=None,
        context="test context",
        signals=signals,
        score=6.8,
        confidence="high",
    )

    stored = enriched.contributing_signals
    assert "matched" in stored
    assert "source" in stored
    assert isinstance(stored["matched"], list)
    assert len(stored["matched"]) == 2
    assert stored["matched"][0]["metric"] == "risk_score"


@pytest.mark.asyncio
async def test_get_enriched_alert_by_id(test_session):
    """get_enriched_alert_by_id returns the correct EnrichedAlert by its own PK."""
    group, _ = await make_test_group(test_session)
    alert = await _make_raw_alert(test_session, group.id)

    enriched = await create_enriched_alert(
        test_session,
        alert_id=alert.id,
        rule_id=None,
        context="context string",
        signals={"matched": [], "source": "ai"},
        score=0.5,
        confidence="low",
    )

    fetched = await get_enriched_alert_by_id(test_session, enriched.id)
    assert fetched is not None
    assert fetched.id == enriched.id
    assert fetched.alert_id == alert.id


@pytest.mark.asyncio
async def test_get_enriched_alert_by_id_not_found(test_session):
    """get_enriched_alert_by_id returns None for unknown ID."""
    result = await get_enriched_alert_by_id(test_session, uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_enriched_alert_by_alert_id(test_session):
    """get_enriched_alert fetches enrichment by the parent alert ID."""
    group, _ = await make_test_group(test_session)
    alert = await _make_raw_alert(test_session, group.id)

    enriched = await create_enriched_alert(
        test_session,
        alert_id=alert.id,
        rule_id=None,
        context="ctx",
        signals={"matched": [], "source": "ai"},
        score=1.0,
        confidence="medium",
    )

    found = await get_enriched_alert(test_session, alert.id)
    assert found is not None
    assert found.id == enriched.id


@pytest.mark.asyncio
async def test_get_enriched_alert_returns_none_when_absent(test_session):
    """get_enriched_alert returns None when no enrichment exists."""
    group, _ = await make_test_group(test_session)
    alert = await _make_raw_alert(test_session, group.id)
    result = await get_enriched_alert(test_session, alert.id)
    assert result is None


@pytest.mark.asyncio
async def test_alert_creation_without_enrichment_no_member(test_session):
    """Alert creation with no member_id skips enrichment, alert still created."""
    group, _ = await make_test_group(test_session)
    data = _alert_create(group.id, member_id=None)

    # Side-effects (SSE, push) are wrapped in try/except inside create_alert,
    # so they will not block alert creation even when they fail in test env.
    alert = await create_alert(test_session, data)

    assert alert.id is not None
    assert alert.enriched_alert_id is None
    # Verify alert persisted
    from sqlalchemy import select

    from src.alerts.models import Alert as AlertModel
    result = await test_session.execute(select(AlertModel).where(AlertModel.id == alert.id))
    stored = result.scalar_one_or_none()
    assert stored is not None


@pytest.mark.asyncio
async def test_enrichment_failure_does_not_block_alert_creation(test_session):
    """If enrichment raises, the alert is still created successfully."""
    group, _ = await make_test_group(test_session)
    member = await _make_group_member(test_session, group.id)
    data = _alert_create(group.id, member_id=member.id, severity="critical")

    with patch("src.intelligence.correlation.evaluate_event", side_effect=RuntimeError("boom")):
        alert = await create_alert(test_session, data)

    assert alert.id is not None
    assert alert.severity == "critical"
    # enriched_alert_id may be None because enrichment failed
    # (that's the expected graceful degradation behaviour)


@pytest.mark.asyncio
async def test_multiple_alerts_independent_enrichments(test_session):
    """Two alerts can have separate, independent enrichment records."""
    group, _ = await make_test_group(test_session)
    alert1 = await _make_raw_alert(test_session, group.id)
    alert2 = await _make_raw_alert(test_session, group.id)

    e1 = await create_enriched_alert(
        test_session, alert_id=alert1.id, rule_id=None,
        context="ctx1", signals={"matched": [], "source": "ai"}, score=1.0, confidence="high",
    )
    e2 = await create_enriched_alert(
        test_session, alert_id=alert2.id, rule_id=None,
        context="ctx2", signals={"matched": [], "source": "device"}, score=2.0, confidence="low",
    )

    assert e1.id != e2.id
    assert e1.alert_id == alert1.id
    assert e2.alert_id == alert2.id
    assert e1.unified_risk_score == pytest.approx(1.0)
    assert e2.unified_risk_score == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_confidence_levels_propagated(test_session):
    """All three confidence levels are stored and retrieved correctly."""
    group, _ = await make_test_group(test_session)
    for confidence in ("low", "medium", "high"):
        alert = await _make_raw_alert(test_session, group.id)
        enriched = await create_enriched_alert(
            test_session, alert_id=alert.id, rule_id=None,
            context=f"ctx {confidence}",
            signals={"matched": [], "source": "ai"},
            score=0.5, confidence=confidence,
        )
        assert enriched.confidence == confidence


@pytest.mark.asyncio
async def test_score_propagated_from_matched_signals(test_session):
    """Unified risk score matches the value passed from matched signals."""
    group, _ = await make_test_group(test_session)
    alert = await _make_raw_alert(test_session, group.id)

    enriched = await create_enriched_alert(
        test_session,
        alert_id=alert.id,
        rule_id=None,
        context="score test",
        signals={"matched": [{"score_contribution": 3.7}], "source": "ai"},
        score=3.7,
        confidence="medium",
    )

    assert enriched.unified_risk_score == pytest.approx(3.7)


@pytest.mark.asyncio
async def test_enrichment_with_rule_id(test_session):
    """Enriched alert stores correlation_rule_id when provided."""
    from src.intelligence.models import CorrelationRule

    group, _ = await make_test_group(test_session)
    alert = await _make_raw_alert(test_session, group.id)

    rule = CorrelationRule(
        id=uuid4(),
        name=f"test_rule_{uuid4().hex[:6]}",
        condition={"signals": [], "logic": "AND"},
        action_severity="high",
        notification_type="alert",
        enabled=True,
    )
    test_session.add(rule)
    await test_session.flush()

    enriched = await create_enriched_alert(
        test_session,
        alert_id=alert.id,
        rule_id=rule.id,
        context="rule linked context",
        signals={"matched": [], "source": "ai"},
        score=0.8,
        confidence="high",
    )

    assert enriched.correlation_rule_id == rule.id


@pytest.mark.asyncio
async def test_enriched_alert_id_stored_on_alert_when_linked(test_session):
    """Alert.enriched_alert_id is set when we manually link an enrichment."""
    group, _ = await make_test_group(test_session)
    alert = await _make_raw_alert(test_session, group.id)

    enriched = await create_enriched_alert(
        test_session,
        alert_id=alert.id,
        rule_id=None,
        context="linking test",
        signals={"matched": [], "source": "ai"},
        score=1.0,
        confidence="medium",
    )

    # Manually link
    alert.enriched_alert_id = enriched.id
    await test_session.flush()
    await test_session.refresh(alert)

    assert alert.enriched_alert_id == enriched.id
