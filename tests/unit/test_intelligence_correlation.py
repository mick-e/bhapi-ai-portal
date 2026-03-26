"""Unit tests for intelligence correlation rules engine (src.intelligence.correlation)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.intelligence.correlation import (
    _apply_operator,
    _compute_confidence,
    _validate_condition,
    create_enriched_alert,
    create_rule,
    evaluate_event,
    get_enriched_alert,
    get_rules,
    update_rule,
)
from tests.conftest import make_test_group

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_alert(session, group_id, member_id=None):
    """Create a minimal Alert row to satisfy the FK on EnrichedAlert."""
    from src.alerts.models import Alert

    alert = Alert(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        severity="medium",
        title="Test Alert",
        body="Test body",
        source="ai",
        channel="portal",
        status="pending",
    )
    session.add(alert)
    await session.flush()
    return alert


def _simple_condition(*, operator="gt", threshold=0.5, logic="AND", metric="risk_score"):
    return {
        "logic": logic,
        "signals": [
            {
                "source": "ai",
                "metric": metric,
                "operator": operator,
                "threshold_multiplier": threshold,
            },
        ],
    }


# ===========================================================================
# 1. Rule CRUD — create
# ===========================================================================


@pytest.mark.asyncio
class TestCreateRule:
    async def test_create_rule_defaults(self, test_session):
        rule = await create_rule(
            test_session,
            {
                "name": "Test Rule Defaults",
                "condition": _simple_condition(),
            },
        )
        assert rule.id is not None
        assert rule.name == "Test Rule Defaults"
        assert rule.action_severity == "medium"
        assert rule.notification_type == "alert"
        assert rule.enabled is True
        assert rule.age_tier_filter is None

    async def test_create_rule_all_fields(self, test_session):
        rule = await create_rule(
            test_session,
            {
                "name": "Critical Teen Rule",
                "description": "High risk for teens",
                "condition": _simple_condition(),
                "action_severity": "critical",
                "notification_type": "push",
                "age_tier_filter": "teen",
                "enabled": False,
            },
        )
        assert rule.action_severity == "critical"
        assert rule.notification_type == "push"
        assert rule.age_tier_filter == "teen"
        assert rule.enabled is False
        assert rule.description == "High risk for teens"

    async def test_create_rule_invalid_logic_raises(self, test_session):
        with pytest.raises(ValidationError):
            await create_rule(
                test_session,
                {
                    "name": "Bad Logic Rule",
                    "condition": {"logic": "INVALID"},
                },
            )

    async def test_create_rule_invalid_operator_raises(self, test_session):
        with pytest.raises(ValidationError):
            await create_rule(
                test_session,
                {
                    "name": "Bad Operator Rule",
                    "condition": {
                        "signals": [
                            {"operator": "BETWEEN", "threshold_multiplier": 1.0},
                        ]
                    },
                },
            )

    async def test_create_rule_duplicate_name_raises_conflict(self, test_session):
        await create_rule(
            test_session,
            {
                "name": "DuplicateRuleName",
                "condition": _simple_condition(),
            },
        )
        with pytest.raises(ConflictError):
            await create_rule(
                test_session,
                {
                    "name": "DuplicateRuleName",
                    "condition": _simple_condition(),
                },
            )


# ===========================================================================
# 2. Rule CRUD — list / filter
# ===========================================================================


@pytest.mark.asyncio
class TestGetRules:
    async def test_get_rules_returns_enabled_only_by_default(self, test_session):
        await create_rule(test_session, {"name": "GetEnabled", "condition": _simple_condition(), "enabled": True})
        await create_rule(test_session, {"name": "GetDisabled", "condition": _simple_condition(), "enabled": False})
        rules = await get_rules(test_session)
        names = [r.name for r in rules]
        assert "GetEnabled" in names
        assert "GetDisabled" not in names

    async def test_get_rules_include_disabled(self, test_session):
        await create_rule(test_session, {"name": "IncludeEnabled", "condition": _simple_condition(), "enabled": True})
        await create_rule(test_session, {"name": "IncludeDisabled", "condition": _simple_condition(), "enabled": False})
        rules = await get_rules(test_session, enabled_only=False)
        names = [r.name for r in rules]
        assert "IncludeEnabled" in names
        assert "IncludeDisabled" in names

    async def test_get_rules_filter_by_age_tier_teen(self, test_session):
        await create_rule(
            test_session, {"name": "TierTeen", "condition": _simple_condition(), "age_tier_filter": "teen"}
        )
        await create_rule(
            test_session, {"name": "TierYoung", "condition": _simple_condition(), "age_tier_filter": "young"}
        )
        await create_rule(test_session, {"name": "TierAll", "condition": _simple_condition(), "age_tier_filter": None})

        teen_rules = await get_rules(test_session, age_tier="teen")
        names = [r.name for r in teen_rules]
        assert "TierTeen" in names
        assert "TierAll" in names
        assert "TierYoung" not in names

    async def test_get_rules_null_tier_matches_all_tiers(self, test_session):
        await create_rule(
            test_session, {"name": "UniversalRuleXYZ", "condition": _simple_condition(), "age_tier_filter": None}
        )
        for tier in ("young", "preteen", "teen"):
            rules = await get_rules(test_session, age_tier=tier)
            assert any(r.name == "UniversalRuleXYZ" for r in rules), f"Universal rule missing for tier={tier}"

    async def test_get_rules_empty_db_returns_empty_list(self, test_session):
        rules = await get_rules(test_session)
        assert rules == []


# ===========================================================================
# 3. Rule CRUD — update
# ===========================================================================


@pytest.mark.asyncio
class TestUpdateRule:
    async def test_update_rule_name_and_severity(self, test_session):
        rule = await create_rule(test_session, {"name": "UpdateOldName", "condition": _simple_condition()})
        updated = await update_rule(test_session, rule.id, {"name": "UpdateNewName", "action_severity": "high"})
        assert updated.name == "UpdateNewName"
        assert updated.action_severity == "high"

    async def test_update_rule_condition(self, test_session):
        rule = await create_rule(test_session, {"name": "UpdateCondRule", "condition": _simple_condition()})
        new_condition = _simple_condition(operator="lte", threshold=0.9)
        updated = await update_rule(test_session, rule.id, {"condition": new_condition})
        assert updated.condition == new_condition

    async def test_update_rule_disable(self, test_session):
        rule = await create_rule(test_session, {"name": "DisableMe", "condition": _simple_condition()})
        updated = await update_rule(test_session, rule.id, {"enabled": False})
        assert updated.enabled is False

    async def test_update_rule_age_tier_filter(self, test_session):
        rule = await create_rule(test_session, {"name": "UpdateTier", "condition": _simple_condition()})
        updated = await update_rule(test_session, rule.id, {"age_tier_filter": "preteen"})
        assert updated.age_tier_filter == "preteen"

    async def test_update_rule_not_found_raises(self, test_session):
        with pytest.raises(NotFoundError):
            await update_rule(test_session, uuid4(), {"name": "Ghost"})

    async def test_update_rule_invalid_condition_raises(self, test_session):
        rule = await create_rule(test_session, {"name": "BadUpdCond", "condition": _simple_condition()})
        with pytest.raises(ValidationError):
            await update_rule(test_session, rule.id, {"condition": {"logic": "XOR"}})


# ===========================================================================
# 4. Event Evaluation
# ===========================================================================


@pytest.mark.asyncio
class TestEvaluateEvent:
    async def test_event_matches_rule(self, test_session):
        await create_rule(
            test_session,
            {
                "name": "EvMatchHighRisk",
                "condition": {
                    "logic": "AND",
                    "signals": [
                        {"source": "ai", "metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.7}
                    ],
                },
            },
        )
        event = {"source": "ai", "metrics": {"risk_score": 0.9}}
        matches = await evaluate_event(test_session, event)
        assert len(matches) == 1
        assert matches[0]["confidence"] == "high"

    async def test_event_no_match_below_threshold(self, test_session):
        await create_rule(
            test_session,
            {
                "name": "EvNoMatchHigh",
                "condition": {
                    "logic": "AND",
                    "signals": [
                        {"source": "ai", "metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.9}
                    ],
                },
            },
        )
        event = {"source": "ai", "metrics": {"risk_score": 0.5}}
        matches = await evaluate_event(test_session, event)
        assert matches == []

    async def test_disabled_rule_skipped(self, test_session):
        await create_rule(
            test_session,
            {
                "name": "EvDisabledRule",
                "condition": {
                    "logic": "AND",
                    "signals": [
                        {"source": "ai", "metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.1}
                    ],
                },
                "enabled": False,
            },
        )
        event = {"source": "ai", "metrics": {"risk_score": 0.99}}
        matches = await evaluate_event(test_session, event)
        assert matches == []

    async def test_event_outside_time_window_skipped(self, test_session):
        await create_rule(
            test_session,
            {
                "name": "EvWindowOld",
                "condition": {
                    "logic": "AND",
                    "time_window_hours": 1,
                    "signals": [
                        {"source": "ai", "metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.1}
                    ],
                },
            },
        )
        old_time = datetime.now(timezone.utc) - timedelta(hours=5)
        event = {"source": "ai", "metrics": {"risk_score": 0.9}, "timestamp": old_time.isoformat()}
        matches = await evaluate_event(test_session, event)
        assert matches == []

    async def test_event_inside_time_window_matches(self, test_session):
        await create_rule(
            test_session,
            {
                "name": "EvWindowRecent",
                "condition": {
                    "logic": "AND",
                    "time_window_hours": 48,
                    "signals": [
                        {"source": "ai", "metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.1}
                    ],
                },
            },
        )
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        event = {"source": "ai", "metrics": {"risk_score": 0.9}, "timestamp": recent_time.isoformat()}
        matches = await evaluate_event(test_session, event)
        assert len(matches) == 1

    async def test_multiple_rules_can_match(self, test_session):
        for i in range(3):
            await create_rule(
                test_session,
                {
                    "name": f"EvMultiRule{i}",
                    "condition": {
                        "logic": "AND",
                        "signals": [
                            {"source": "ai", "metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.1}
                        ],
                    },
                },
            )
        event = {"source": "ai", "metrics": {"risk_score": 0.99}}
        matches = await evaluate_event(test_session, event)
        assert len(matches) == 3

    async def test_evaluate_event_no_rules_returns_empty(self, test_session):
        event = {"source": "ai", "metrics": {"risk_score": 0.9}}
        matches = await evaluate_event(test_session, event)
        assert matches == []

    async def test_age_tier_filtering_in_evaluate(self, test_session):
        await create_rule(
            test_session,
            {
                "name": "EvTeenOnly",
                "condition": {"signals": [{"metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.1}]},
                "age_tier_filter": "teen",
            },
        )
        await create_rule(
            test_session,
            {
                "name": "EvYoungOnly",
                "condition": {"signals": [{"metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.1}]},
                "age_tier_filter": "young",
            },
        )
        event = {"age_tier": "teen", "metrics": {"risk_score": 0.9}}
        matches = await evaluate_event(test_session, event)
        matched_names = [m["rule"].name for m in matches]
        assert "EvTeenOnly" in matched_names
        assert "EvYoungOnly" not in matched_names

    async def test_or_logic_partial_match_returns_low_confidence(self, test_session):
        await create_rule(
            test_session,
            {
                "name": "EvORPartial",
                "condition": {
                    "logic": "OR",
                    "signals": [
                        {"metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.9},
                        {"metric": "spend_usd", "operator": "gt", "threshold_multiplier": 100.0},
                    ],
                },
            },
        )
        event = {"metrics": {"risk_score": 0.95}}
        matches = await evaluate_event(test_session, event)
        assert len(matches) == 1
        assert matches[0]["confidence"] == "low"

    async def test_or_logic_no_match_returns_empty(self, test_session):
        await create_rule(
            test_session,
            {
                "name": "EvORNoMatch",
                "condition": {
                    "logic": "OR",
                    "signals": [
                        {"metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.9},
                        {"metric": "spend_usd", "operator": "gt", "threshold_multiplier": 100.0},
                    ],
                },
            },
        )
        event = {"metrics": {"risk_score": 0.1}}
        matches = await evaluate_event(test_session, event)
        assert matches == []

    async def test_null_age_tier_event_matches_all_tier_rules(self, test_session):
        await create_rule(
            test_session,
            {
                "name": "EvNullTierUniversal",
                "condition": {"signals": [{"metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.1}]},
                "age_tier_filter": None,
            },
        )
        event = {"metrics": {"risk_score": 0.9}}  # no age_tier key
        matches = await evaluate_event(test_session, event)
        assert any(m["rule"].name == "EvNullTierUniversal" for m in matches)

    async def test_source_mismatch_does_not_match(self, test_session):
        """A rule with source=social_activity must not match an ai_session event."""
        await create_rule(
            test_session,
            {
                "name": "EvSourceMismatch",
                "condition": {
                    "logic": "AND",
                    "signals": [
                        {
                            "source": "social_activity",
                            "metric": "risk_score",
                            "operator": "gt",
                            "threshold_multiplier": 0.1,
                        },
                    ],
                },
            },
        )
        event = {"source": "ai_session", "metrics": {"risk_score": 0.99}}
        matches = await evaluate_event(test_session, event)
        assert matches == []

    async def test_source_match_does_match(self, test_session):
        """A rule with source=ai_session must match an ai_session event."""
        await create_rule(
            test_session,
            {
                "name": "EvSourceMatch",
                "condition": {
                    "logic": "AND",
                    "signals": [
                        {"source": "ai_session", "metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.1},
                    ],
                },
            },
        )
        event = {"source": "ai_session", "metrics": {"risk_score": 0.99}}
        matches = await evaluate_event(test_session, event)
        assert len(matches) == 1

    async def test_match_result_contains_expected_keys(self, test_session):
        await create_rule(
            test_session,
            {
                "name": "EvResultKeys",
                "condition": {"signals": [{"metric": "risk_score", "operator": "gt", "threshold_multiplier": 0.5}]},
            },
        )
        event = {"metrics": {"risk_score": 0.9}}
        matches = await evaluate_event(test_session, event)
        assert len(matches) == 1
        m = matches[0]
        assert "rule" in m
        assert "signals" in m
        assert "score" in m
        assert "confidence" in m


# ===========================================================================
# 5. Condition Validation (pure function)
# ===========================================================================


class TestValidateCondition:
    def test_valid_condition_passes(self):
        _validate_condition(
            {
                "logic": "AND",
                "signals": [{"operator": "gt", "threshold_multiplier": 1.0}],
            }
        )

    def test_valid_or_logic_passes(self):
        _validate_condition({"logic": "OR", "signals": []})

    def test_not_a_dict_raises(self):
        with pytest.raises(ValidationError):
            _validate_condition("not a dict")

    def test_invalid_logic_raises(self):
        with pytest.raises(ValidationError):
            _validate_condition({"logic": "XOR", "signals": []})

    def test_signals_not_list_raises(self):
        with pytest.raises(ValidationError):
            _validate_condition({"signals": "bad"})

    def test_signal_not_dict_raises(self):
        with pytest.raises(ValidationError):
            _validate_condition({"signals": ["not_a_dict"]})

    def test_invalid_operator_raises(self):
        with pytest.raises(ValidationError):
            _validate_condition({"signals": [{"operator": "BETWEEN", "threshold_multiplier": 1.0}]})

    def test_invalid_threshold_type_raises(self):
        with pytest.raises(ValidationError):
            _validate_condition({"signals": [{"operator": "gt", "threshold_multiplier": "high"}]})

    def test_all_valid_operators_pass(self):
        for op in ("gt", "gte", "lt", "lte", "eq"):
            _validate_condition({"signals": [{"operator": op, "threshold_multiplier": 1.0}]})

    def test_empty_condition_passes(self):
        _validate_condition({})


# ===========================================================================
# 6. Apply Operator (pure function)
# ===========================================================================


class TestApplyOperator:
    def test_gt_true(self):
        assert _apply_operator(5.0, "gt", 3.0) is True

    def test_gt_false(self):
        assert _apply_operator(2.0, "gt", 3.0) is False

    def test_gte_equal_is_true(self):
        assert _apply_operator(3.0, "gte", 3.0) is True

    def test_lt_true(self):
        assert _apply_operator(1.0, "lt", 5.0) is True

    def test_lte_equal_is_true(self):
        assert _apply_operator(5.0, "lte", 5.0) is True

    def test_eq_true(self):
        assert _apply_operator(4.0, "eq", 4.0) is True

    def test_eq_false(self):
        assert _apply_operator(4.0, "eq", 5.0) is False

    def test_unknown_operator_returns_false(self):
        assert _apply_operator(10.0, "between", 5.0) is False

    def test_non_numeric_value_returns_false(self):
        assert _apply_operator("high", "gt", 0.5) is False


# ===========================================================================
# 7. Compute Confidence (pure function)
# ===========================================================================


class TestComputeConfidence:
    def test_and_all_signals_matched_is_high(self):
        matched = [{"x": 1}, {"x": 2}]
        all_signals = [{"x": 1}, {"x": 2}]
        assert _compute_confidence(matched, all_signals, "AND") == "high"

    def test_or_all_signals_matched_is_high(self):
        matched = [{"x": 1}, {"x": 2}]
        all_signals = [{"x": 1}, {"x": 2}]
        assert _compute_confidence(matched, all_signals, "OR") == "high"

    def test_or_partial_match_above_60pct_is_medium(self):
        matched = [{"x": 1}, {"x": 2}]
        all_signals = [{"x": 1}, {"x": 2}, {"x": 3}]  # 66%
        assert _compute_confidence(matched, all_signals, "OR") == "medium"

    def test_or_one_of_many_is_low(self):
        matched = [{"x": 1}]
        all_signals = [{"x": 1}, {"x": 2}, {"x": 3}, {"x": 4}]  # 25%
        assert _compute_confidence(matched, all_signals, "OR") == "low"

    def test_empty_all_signals_is_low(self):
        assert _compute_confidence([], [], "AND") == "low"


# ===========================================================================
# 8. Enriched Alert CRUD
# ===========================================================================


@pytest.mark.asyncio
class TestEnrichedAlert:
    async def test_create_enriched_alert_no_rule(self, test_session):
        group, _ = await make_test_group(test_session)
        alert = await _make_alert(test_session, group.id)

        enriched = await create_enriched_alert(
            test_session,
            alert_id=alert.id,
            rule_id=None,
            context="High risk detected across platforms",
            signals={"risk_score": 0.9},
            score=0.9,
            confidence="high",
        )
        assert enriched.id is not None
        assert enriched.alert_id == alert.id
        assert enriched.confidence == "high"
        assert enriched.unified_risk_score == 0.9
        assert enriched.correlation_context == "High risk detected across platforms"
        assert enriched.correlation_rule_id is None

    async def test_create_enriched_alert_with_rule(self, test_session):
        group, _ = await make_test_group(test_session)
        alert = await _make_alert(test_session, group.id)
        rule = await create_rule(test_session, {"name": "EnrichRuleRef", "condition": _simple_condition()})

        enriched = await create_enriched_alert(
            test_session,
            alert_id=alert.id,
            rule_id=rule.id,
            context="Rule matched",
            signals={"risk_score": 0.8},
            score=0.8,
            confidence="medium",
        )
        assert enriched.correlation_rule_id == rule.id

    async def test_get_enriched_alert_found(self, test_session):
        group, _ = await make_test_group(test_session)
        alert = await _make_alert(test_session, group.id)

        await create_enriched_alert(
            test_session,
            alert_id=alert.id,
            rule_id=None,
            context="Fetched context",
            signals={},
            score=0.5,
            confidence="low",
        )

        result = await get_enriched_alert(test_session, alert.id)
        assert result is not None
        assert result.alert_id == alert.id
        assert result.confidence == "low"

    async def test_get_enriched_alert_not_found_returns_none(self, test_session):
        result = await get_enriched_alert(test_session, uuid4())
        assert result is None
