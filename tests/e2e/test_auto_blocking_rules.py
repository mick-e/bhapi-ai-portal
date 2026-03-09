"""E2E tests for the automated blocking rules engine."""

from uuid import uuid4

import pytest

from src.blocking.models import AutoBlockRule
from src.blocking.schemas import AutoBlockRuleCreate, AutoBlockRuleRequest, AutoBlockRuleUpdate
from src.blocking.service import (
    create_auto_block_rule,
    delete_auto_block_rule,
    evaluate_group_auto_block_rules,
    list_active_auto_block_rules,
    list_auto_block_rules,
    update_auto_block_rule,
)
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_create_auto_block_rule(test_session):
    """Create a risk_event_count rule and verify all fields."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    rule = await create_auto_block_rule(
        test_session,
        AutoBlockRuleRequest(
            group_id=group.id,
            name="High risk alert",
            trigger_type="risk_event_count",
            trigger_config={"threshold": 3, "window_hours": 24},
            action="block_all",
            enabled=True,
        ),
        user_id=owner_id,
    )

    assert rule.id is not None
    assert rule.name == "High risk alert"
    assert rule.trigger_type == "risk_event_count"
    assert rule.trigger_config == {"threshold": 3, "window_hours": 24}
    assert rule.action == "block_all"
    assert rule.enabled is True
    assert rule.last_triggered_at is None
    assert rule.created_at is not None


@pytest.mark.asyncio
async def test_list_auto_block_rules(test_session):
    """Create 2 rules and verify list returns both."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    await create_auto_block_rule(
        test_session,
        AutoBlockRuleRequest(
            group_id=group.id,
            name="Risk count rule",
            trigger_type="risk_event_count",
            trigger_config={"threshold": 5, "window_hours": 12},
        ),
        user_id=owner_id,
    )
    await create_auto_block_rule(
        test_session,
        AutoBlockRuleRequest(
            group_id=group.id,
            name="Spend limit rule",
            trigger_type="spend_threshold",
            trigger_config={"threshold_usd": 100.0},
        ),
        user_id=owner_id,
    )

    rules = await list_auto_block_rules(test_session, group.id)
    assert len(rules) == 2
    names = {r.name for r in rules}
    assert "Risk count rule" in names
    assert "Spend limit rule" in names


@pytest.mark.asyncio
async def test_update_auto_block_rule(test_session):
    """Create a rule, update its name, and verify."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    rule = await create_auto_block_rule(
        test_session,
        AutoBlockRuleRequest(
            group_id=group.id,
            name="Original name",
            trigger_type="risk_event_count",
            trigger_config={"threshold": 3, "window_hours": 24},
        ),
        user_id=owner_id,
    )

    updated = await update_auto_block_rule(
        test_session,
        rule.id,
        AutoBlockRuleUpdate(name="Updated name"),
        user_id=owner_id,
    )

    assert updated.name == "Updated name"
    assert updated.trigger_type == "risk_event_count"


@pytest.mark.asyncio
async def test_delete_auto_block_rule(test_session):
    """Create a rule, delete it, and verify it is gone."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    rule = await create_auto_block_rule(
        test_session,
        AutoBlockRuleRequest(
            group_id=group.id,
            name="Temporary rule",
            trigger_type="spend_threshold",
            trigger_config={"threshold_usd": 50.0},
        ),
        user_id=owner_id,
    )

    await delete_auto_block_rule(test_session, rule.id, user_id=owner_id)
    rules = await list_auto_block_rules(test_session, group.id)
    assert len(rules) == 0


@pytest.mark.asyncio
async def test_create_spend_threshold_rule(test_session):
    """Create a spend_threshold rule with trigger_config."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    rule = await create_auto_block_rule(
        test_session,
        AutoBlockRuleRequest(
            group_id=group.id,
            name="Monthly spend cap",
            trigger_type="spend_threshold",
            trigger_config={"threshold_usd": 200.0},
            action="block_all",
        ),
        user_id=owner_id,
    )

    assert rule.trigger_type == "spend_threshold"
    assert rule.trigger_config == {"threshold_usd": 200.0}
    assert rule.action == "block_all"
    assert rule.name == "Monthly spend cap"


@pytest.mark.asyncio
async def test_create_time_of_day_rule(test_session):
    """Create a time_of_day rule with start/end hours in trigger_config."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    rule = await create_auto_block_rule(
        test_session,
        AutoBlockRuleRequest(
            group_id=group.id,
            name="Bedtime blocker",
            trigger_type="time_of_day",
            trigger_config={"start_hour": 22, "end_hour": 6},
            action="block_all",
        ),
        user_id=owner_id,
    )

    assert rule.trigger_type == "time_of_day"
    assert rule.trigger_config == {"start_hour": 22, "end_hour": 6}
    assert rule.name == "Bedtime blocker"


@pytest.mark.asyncio
async def test_evaluate_rules_no_trigger(test_session):
    """Evaluate with no matching data — nothing should trigger."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    await create_auto_block_rule(
        test_session,
        AutoBlockRuleRequest(
            group_id=group.id,
            name="High threshold",
            trigger_type="risk_event_count",
            trigger_config={"threshold": 100, "window_hours": 24},
        ),
        user_id=owner_id,
    )

    triggered = await evaluate_group_auto_block_rules(test_session, group.id)
    assert triggered == []


@pytest.mark.asyncio
async def test_disabled_rule_not_listed(test_session):
    """A rule with enabled=False should not appear in the active rules list."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    await create_auto_block_rule(
        test_session,
        AutoBlockRuleRequest(
            group_id=group.id,
            name="Disabled rule",
            trigger_type="risk_event_count",
            trigger_config={"threshold": 5, "window_hours": 24},
            enabled=False,
        ),
        user_id=owner_id,
    )

    # Active list should not include the disabled rule
    active_rules = await list_active_auto_block_rules(test_session, group.id)
    assert len(active_rules) == 0

    # Full list should still include it
    all_rules = await list_auto_block_rules(test_session, group.id)
    assert len(all_rules) == 1
    assert all_rules[0].enabled is False
