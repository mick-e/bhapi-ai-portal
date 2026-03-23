"""Unit tests for the intelligence correlation rules engine.

Tests rule evaluation, age tier filtering, time window enforcement,
enriched alert creation, rule CRUD, condition JSON validation,
and disabled rule skipping.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.exceptions import NotFoundError, ValidationError
from src.intelligence.correlation import (
    _apply_operator,
    _compute_confidence,
    _evaluate_signals,
    _validate_condition,
    create_enriched_alert,
    create_rule,
    evaluate_event,
    get_enriched_alert,
    get_rules,
    update_rule,
)
from src.intelligence.models import CorrelationRule, EnrichedAlert
from tests.conftest import make_test_group


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_condition(signals=None, logic="AND", window=48):
    return {
        "signals": signals or [],
        "logic": logic,
        "time_window_hours": window,
    }


def _rule_data(name=None, severity="medium", age_tier=None, enabled=True, signals=None):
    return {
        "name": name or f"rule-{uuid4().hex[:8]}",
        "description": "Test rule",
        "condition": _make_condition(
            signals=signals or [
                {"source": "ai_session", "metric": "session_count",
                 "operator": "gt", "threshold_multiplier": 2.0},
            ]
        ),
        "action_severity": severity,
        "notification_type": "alert",
        "age_tier_filter": age_tier,
        "enabled": enabled,
    }


async def _make_alert(session):
    """Create a group + alert for FK-safe enriched alert tests."""
    from src.alerts.models import Alert

    group, _ = await make_test_group(session, name=f"AF-{uuid4().hex[:6]}")
    alert = Alert(
        id=uuid4(),
        group_id=group.id,
        severity="high",
        title="Test Alert",
        body="Test body",
        channel="portal",
        status="pending",
    )
    session.add(alert)
    await session.flush()
    return alert


# ===========================================================================
# Rule CRUD — create
# ===========================================================================


@pytest.mark.asyncio
async def test_create_rule_basic(test_session):
    """create_rule stores a rule with correct fields and a valid UUID."""
    data = _rule_data(name="basic-create")
    rule = await create_rule(test_session, data)
    await test_session.flush()

    assert rule.id is not None
    assert rule.name == "basic-create"
    assert rule.action_severity == "medium"
    assert rule.notification_type == "alert"
    assert rule.enabled is True
    assert rule.age_tier_filter is None


@pytest.mark.asyncio
async def test_create_rule_with_age_tier(test_session):
    """create_rule stores age_tier_filter correctly."""
    rule = await create_rule(test_session, _rule_data(name="teen-rule", age_tier="teen"))
    assert rule.age_tier_filter == "teen"


@pytest.mark.asyncio
async def test_create_rule_critical_severity(test_session):
    """create_rule stores critical severity without error."""
    rule = await create_rule(test_session, _rule_data(name="critical-rule", severity="critical"))
    assert rule.action_severity == "critical"


@pytest.mark.asyncio
async def test_create_rule_condition_stored_as_dict(test_session):
    """create_rule persists condition as a dict."""
    cond = _make_condition(signals=[
        {"source": "ai", "metric": "x", "operator": "gt", "threshold_multiplier": 1.0},
    ])
    data = _rule_data(name="cond-persist")
    data["condition"] = cond
    rule = await create_rule(test_session, data)
    assert isinstance(rule.condition, dict)
    assert "signals" in rule.condition


@pytest.mark.asyncio
async def test_create_rule_invalid_operator_raises(test_session):
    """create_rule rejects a signal with an invalid operator."""
    data = {
        "name": "bad-op",
        "condition": _make_condition(signals=[
            {"source": "ai_session", "metric": "count", "operator": "INVALID",
             "threshold_multiplier": 1.0},
        ]),
        "action_severity": "medium",
        "notification_type": "alert",
    }
    with pytest.raises(ValidationError):
        await create_rule(test_session, data)


@pytest.mark.asyncio
async def test_create_rule_invalid_logic_raises(test_session):
    """create_rule rejects an invalid logic value (only AND/OR allowed)."""
    data = {
        "name": "bad-logic",
        "condition": {"signals": [], "logic": "XOR", "time_window_hours": 48},
        "action_severity": "medium",
        "notification_type": "alert",
    }
    with pytest.raises(ValidationError):
        await create_rule(test_session, data)


@pytest.mark.asyncio
async def test_create_rule_condition_not_dict_raises(test_session):
    """create_rule rejects a non-dict condition."""
    with pytest.raises(ValidationError):
        await create_rule(test_session, {
            "name": "bad-cond",
            "condition": "this is not a dict",
            "action_severity": "medium",
            "notification_type": "alert",
        })


@pytest.mark.asyncio
async def test_create_rule_signals_not_list_raises(test_session):
    """create_rule rejects condition.signals that is not a list."""
    with pytest.raises(ValidationError):
        await create_rule(test_session, {
            "name": "bad-signals",
            "condition": {"signals": "not-a-list", "logic": "AND"},
            "action_severity": "medium",
            "notification_type": "alert",
        })


@pytest.mark.asyncio
async def test_create_rule_non_numeric_threshold_raises(test_session):
    """create_rule rejects non-numeric threshold_multiplier."""
    with pytest.raises(ValidationError):
        await create_rule(test_session, {
            "name": "bad-threshold",
            "condition": {"signals": [{"operator": "gt", "threshold_multiplier": "bad"}], "logic": "AND"},
            "action_severity": "medium",
            "notification_type": "alert",
        })


# ===========================================================================
# Rule CRUD — update
# ===========================================================================


@pytest.mark.asyncio
async def test_update_rule_name_and_severity(test_session):
    """update_rule modifies name and action_severity correctly."""
    rule = await create_rule(test_session, _rule_data(name="before-update"))
    await test_session.flush()

    updated = await update_rule(test_session, rule.id, {
        "name": "after-update",
        "action_severity": "critical",
    })
    assert updated.name == "after-update"
    assert updated.action_severity == "critical"


@pytest.mark.asyncio
async def test_update_rule_disable(test_session):
    """update_rule can disable a rule."""
    rule = await create_rule(test_session, _rule_data(name="disable-me"))
    await test_session.flush()

    updated = await update_rule(test_session, rule.id, {"enabled": False})
    assert updated.enabled is False


@pytest.mark.asyncio
async def test_update_rule_not_found_raises(test_session):
    """update_rule raises NotFoundError for unknown rule_id."""
    with pytest.raises(NotFoundError):
        await update_rule(test_session, uuid4(), {"name": "ghost"})


@pytest.mark.asyncio
async def test_update_rule_invalid_condition_raises(test_session):
    """update_rule validates the new condition."""
    rule = await create_rule(test_session, _rule_data(name="validate-upd"))
    await test_session.flush()
    with pytest.raises(ValidationError):
        await update_rule(test_session, rule.id, {
            "condition": {"signals": [{"operator": "NOPE"}], "logic": "AND"},
        })


# ===========================================================================
# get_rules — listing and filtering
# ===========================================================================


@pytest.mark.asyncio
async def test_get_rules_returns_enabled_only(test_session):
    """get_rules default excludes disabled rules."""
    await create_rule(test_session, _rule_data(name="enabled-gr"))
    await create_rule(test_session, _rule_data(name="disabled-gr", enabled=False))
    await test_session.flush()

    rules = await get_rules(test_session)
    names = [r.name for r in rules]
    assert "enabled-gr" in names
    assert "disabled-gr" not in names


@pytest.mark.asyncio
async def test_get_rules_age_tier_includes_null_tier(test_session):
    """get_rules(age_tier='teen') returns teen-specific AND null-tier rules."""
    await create_rule(test_session, _rule_data(name="teen-only-gr", age_tier="teen"))
    await create_rule(test_session, _rule_data(name="all-tiers-gr", age_tier=None))
    await create_rule(test_session, _rule_data(name="preteen-only-gr", age_tier="preteen"))
    await test_session.flush()

    rules = await get_rules(test_session, age_tier="teen")
    names = [r.name for r in rules]
    assert "teen-only-gr" in names
    assert "all-tiers-gr" in names
    assert "preteen-only-gr" not in names


# ===========================================================================
# Event evaluation
# ===========================================================================


@pytest.mark.asyncio
async def test_evaluate_event_matches_rule(test_session):
    """evaluate_event returns match when event satisfies rule signals."""
    await create_rule(test_session, {
        "name": "ev-match",
        "condition": _make_condition(signals=[
            {"source": "ai_session", "metric": "session_count",
             "operator": "gt", "threshold_multiplier": 2.0},
        ]),
        "action_severity": "medium",
        "notification_type": "alert",
    })
    await test_session.flush()

    matches = await evaluate_event(test_session, {
        "source": "ai_session",
        "metrics": {"session_count": 5.0},
    })
    assert any(m["rule"].name == "ev-match" for m in matches)


@pytest.mark.asyncio
async def test_evaluate_event_no_match_threshold_unmet(test_session):
    """evaluate_event returns no match when threshold not met."""
    await create_rule(test_session, {
        "name": "strict-ev",
        "condition": _make_condition(signals=[
            {"source": "ai_session", "metric": "session_count",
             "operator": "gt", "threshold_multiplier": 100.0},
        ]),
        "action_severity": "medium",
        "notification_type": "alert",
    })
    await test_session.flush()

    matches = await evaluate_event(test_session, {
        "source": "ai_session",
        "metrics": {"session_count": 1.0},
    })
    assert not any(m["rule"].name == "strict-ev" for m in matches)


@pytest.mark.asyncio
async def test_evaluate_event_disabled_rule_skipped(test_session):
    """Disabled rules are not evaluated."""
    await create_rule(test_session, {
        "name": "disabled-ev",
        "condition": _make_condition(signals=[
            {"source": "ai_session", "metric": "session_count",
             "operator": "gt", "threshold_multiplier": 0.0},
        ]),
        "action_severity": "medium",
        "notification_type": "alert",
        "enabled": False,
    })
    await test_session.flush()

    matches = await evaluate_event(test_session, {
        "source": "ai_session",
        "metrics": {"session_count": 100.0},
    })
    assert not any(m["rule"].name == "disabled-ev" for m in matches)


@pytest.mark.asyncio
async def test_evaluate_event_age_tier_filter(test_session):
    """evaluate_event respects age_tier_filter — teen rule not matched for young event."""
    await create_rule(test_session, {
        "name": "teen-ev",
        "condition": _make_condition(signals=[
            {"source": "ai_session", "metric": "session_count",
             "operator": "gt", "threshold_multiplier": 0.0},
        ]),
        "action_severity": "medium",
        "notification_type": "alert",
        "age_tier_filter": "teen",
    })
    await test_session.flush()

    # Young event should not match teen-specific rule
    young_matches = await evaluate_event(test_session, {
        "source": "ai_session",
        "age_tier": "young",
        "metrics": {"session_count": 5.0},
    })
    assert not any(m["rule"].name == "teen-ev" for m in young_matches)

    # Teen event should match
    teen_matches = await evaluate_event(test_session, {
        "source": "ai_session",
        "age_tier": "teen",
        "metrics": {"session_count": 5.0},
    })
    assert any(m["rule"].name == "teen-ev" for m in teen_matches)


@pytest.mark.asyncio
async def test_evaluate_event_time_window_enforced(test_session):
    """evaluate_event skips events older than the rule time window."""
    await create_rule(test_session, {
        "name": "window-ev",
        "condition": {
            "signals": [
                {"source": "ai_session", "metric": "session_count",
                 "operator": "gt", "threshold_multiplier": 0.0},
            ],
            "logic": "AND",
            "time_window_hours": 2,
        },
        "action_severity": "medium",
        "notification_type": "alert",
    })
    await test_session.flush()

    old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    matches = await evaluate_event(test_session, {
        "source": "ai_session",
        "metrics": {"session_count": 5.0},
        "timestamp": old_timestamp,
    })
    assert not any(m["rule"].name == "window-ev" for m in matches)


# ===========================================================================
# Operator and helper tests (pure unit)
# ===========================================================================


def test_apply_operator_gt_true():
    assert _apply_operator(5.0, "gt", 2.0) is True


def test_apply_operator_gt_false():
    assert _apply_operator(1.0, "gt", 2.0) is False


def test_apply_operator_lt_true():
    assert _apply_operator(1.0, "lt", 2.0) is True


def test_apply_operator_gte_equal():
    assert _apply_operator(2.0, "gte", 2.0) is True


def test_apply_operator_lte_equal():
    assert _apply_operator(2.0, "lte", 2.0) is True


def test_apply_operator_eq_match():
    assert _apply_operator(3.0, "eq", 3.0) is True


def test_apply_operator_eq_no_match():
    assert _apply_operator(3.0, "eq", 4.0) is False


def test_apply_operator_non_numeric():
    assert _apply_operator("text", "gt", 1.0) is False


def test_compute_confidence_all_match_high():
    matched = [{"x": 1}, {"x": 2}]
    sigs = [{"x": 1}, {"x": 2}]
    assert _compute_confidence(matched, sigs, "AND") == "high"


def test_compute_confidence_partial_medium():
    matched = [{"x": 1}, {"x": 2}]
    sigs = [{"x": 1}, {"x": 2}, {"x": 3}]
    assert _compute_confidence(matched, sigs, "OR") == "medium"


def test_compute_confidence_one_of_many_low():
    matched = [{"x": 1}]
    sigs = [{"x": 1}, {"x": 2}, {"x": 3}, {"x": 4}]
    assert _compute_confidence(matched, sigs, "OR") == "low"


def test_evaluate_signals_and_all_match():
    signals = [
        {"source": "s", "metric": "a", "operator": "gt", "threshold_multiplier": 1.0},
        {"source": "s", "metric": "b", "operator": "lt", "threshold_multiplier": 5.0},
    ]
    matched, score = _evaluate_signals({"metrics": {"a": 3.0, "b": 2.0}}, signals, "AND")
    assert len(matched) == 2
    assert score > 0


def test_evaluate_signals_and_partial_no_match():
    signals = [
        {"source": "s", "metric": "a", "operator": "gt", "threshold_multiplier": 10.0},
        {"source": "s", "metric": "b", "operator": "lt", "threshold_multiplier": 5.0},
    ]
    matched, score = _evaluate_signals({"metrics": {"a": 1.0, "b": 2.0}}, signals, "AND")
    assert matched == []
    assert score == 0.0


def test_evaluate_signals_or_one_match():
    signals = [
        {"source": "s", "metric": "a", "operator": "gt", "threshold_multiplier": 100.0},
        {"source": "s", "metric": "b", "operator": "lt", "threshold_multiplier": 5.0},
    ]
    matched, score = _evaluate_signals({"metrics": {"a": 1.0, "b": 2.0}}, signals, "OR")
    assert len(matched) == 1


def test_validate_condition_valid_passes():
    _validate_condition({
        "signals": [{"source": "ai", "metric": "x", "operator": "gt", "threshold_multiplier": 1.0}],
        "logic": "AND",
        "time_window_hours": 48,
    })  # should not raise


def test_validate_condition_invalid_threshold_raises():
    with pytest.raises(ValidationError):
        _validate_condition({
            "signals": [{"operator": "gt", "threshold_multiplier": "bad"}],
            "logic": "AND",
        })


def test_validate_condition_invalid_operator_raises():
    with pytest.raises(ValidationError):
        _validate_condition({
            "signals": [{"operator": "BOOM", "threshold_multiplier": 1.0}],
            "logic": "AND",
        })


# ===========================================================================
# Enriched Alerts
# ===========================================================================


@pytest.mark.asyncio
async def test_create_enriched_alert_basic(test_session):
    """create_enriched_alert stores with all fields populated."""
    alert = await _make_alert(test_session)
    rule = await create_rule(test_session, _rule_data(name="enrich-basic"))
    await test_session.flush()

    enriched = await create_enriched_alert(
        test_session,
        alert_id=alert.id,
        rule_id=rule.id,
        context="Two signals correlated",
        signals={"signal_count": 2, "sources": ["ai_session"]},
        score=75.0,
        confidence="high",
    )
    assert enriched.id is not None
    assert enriched.alert_id == alert.id
    assert enriched.correlation_rule_id == rule.id
    assert enriched.unified_risk_score == 75.0
    assert enriched.confidence == "high"
    assert "Two signals" in enriched.correlation_context


@pytest.mark.asyncio
async def test_create_enriched_alert_without_rule(test_session):
    """create_enriched_alert works when no correlation rule exists."""
    alert = await _make_alert(test_session)
    await test_session.flush()

    enriched = await create_enriched_alert(
        test_session,
        alert_id=alert.id,
        rule_id=None,
        context="Manual",
        signals={},
        score=50.0,
        confidence="medium",
    )
    assert enriched.correlation_rule_id is None


@pytest.mark.asyncio
async def test_get_enriched_alert_found(test_session):
    """get_enriched_alert retrieves record by alert_id."""
    alert = await _make_alert(test_session)
    await create_enriched_alert(
        test_session,
        alert_id=alert.id,
        rule_id=None,
        context="ctx",
        signals={},
        score=30.0,
        confidence="low",
    )
    await test_session.flush()

    found = await get_enriched_alert(test_session, alert.id)
    assert found is not None
    assert found.alert_id == alert.id


@pytest.mark.asyncio
async def test_get_enriched_alert_not_found(test_session):
    """get_enriched_alert returns None for unknown alert_id."""
    result = await get_enriched_alert(test_session, uuid4())
    assert result is None
