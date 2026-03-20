"""E2E tests for automated blocking rules engine."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.billing.models import LLMAccount, SpendRecord
from src.blocking.models import BlockRule
from src.blocking.schemas import AutoBlockRuleCreate, AutoBlockRuleUpdate
from src.blocking.service import (
    create_auto_block_rule,
    delete_auto_block_rule,
    evaluate_auto_block_rules,
    list_auto_block_rules,
    update_auto_block_rule,
)
from src.groups.models import GroupMember
from src.risk.models import RiskEvent
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_create_auto_block_rule(test_session):
    """Create an auto block rule and verify response fields."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    rule = await create_auto_block_rule(
        test_session,
        AutoBlockRuleCreate(
            group_id=group.id,
            trigger_type="risk_event_count",
            threshold=3,
            time_window_minutes=60,
            platforms=["chatgpt"],
        ),
        user_id=owner_id,
    )

    assert rule.id is not None
    assert rule.trigger_type == "risk_event_count"
    assert rule.threshold == 3
    assert rule.time_window_minutes == 60
    assert rule.active is True
    assert rule.created_by == owner_id
    assert rule.last_triggered_at is None


@pytest.mark.asyncio
async def test_list_auto_block_rules(test_session):
    """Create two rules for a group and verify list returns both."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    await create_auto_block_rule(
        test_session,
        AutoBlockRuleCreate(
            group_id=group.id,
            trigger_type="risk_event_count",
            threshold=5,
            time_window_minutes=30,
        ),
        user_id=owner_id,
    )
    await create_auto_block_rule(
        test_session,
        AutoBlockRuleCreate(
            group_id=group.id,
            trigger_type="spend_threshold",
            threshold=100,
        ),
        user_id=owner_id,
    )

    rules = await list_auto_block_rules(test_session, group.id)
    assert len(rules) == 2


@pytest.mark.asyncio
async def test_update_auto_block_rule(test_session):
    """Update threshold on an auto block rule."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    rule = await create_auto_block_rule(
        test_session,
        AutoBlockRuleCreate(
            group_id=group.id,
            trigger_type="risk_event_count",
            threshold=3,
            time_window_minutes=60,
        ),
        user_id=owner_id,
    )

    updated = await update_auto_block_rule(
        test_session,
        rule.id,
        AutoBlockRuleUpdate(threshold=10),
        user_id=owner_id,
    )

    assert updated.threshold == 10
    assert updated.trigger_type == "risk_event_count"


@pytest.mark.asyncio
async def test_delete_auto_block_rule(test_session):
    """Delete an auto block rule and verify list is empty."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    rule = await create_auto_block_rule(
        test_session,
        AutoBlockRuleCreate(
            group_id=group.id,
            trigger_type="spend_threshold",
            threshold=50,
        ),
        user_id=owner_id,
    )

    await delete_auto_block_rule(test_session, rule.id, user_id=owner_id)
    rules = await list_auto_block_rules(test_session, group.id)
    assert len(rules) == 0


@pytest.mark.asyncio
async def test_risk_event_count_trigger(test_session):
    """Auto block fires when risk event count exceeds threshold."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Create auto rule: trigger after 2 risk events in 60 minutes
    await create_auto_block_rule(
        test_session,
        AutoBlockRuleCreate(
            group_id=group.id,
            trigger_type="risk_event_count",
            threshold=2,
            time_window_minutes=60,
            member_id=member.id,
        ),
        user_id=owner_id,
    )

    # Insert 2 risk events
    datetime.now(timezone.utc)
    for i in range(2):
        event = RiskEvent(
            id=uuid4(),
            group_id=group.id,
            member_id=member.id,
            category="unsafe_content",
            severity="high",
            confidence=0.95,
        )
        test_session.add(event)
    await test_session.flush()

    # Evaluate — should trigger
    result = await evaluate_auto_block_rules(test_session)
    assert result["triggered"] == 1

    # Verify a BlockRule was created
    from sqlalchemy import select
    block_result = await test_session.execute(
        select(BlockRule).where(
            BlockRule.group_id == group.id,
            BlockRule.member_id == member.id,
            BlockRule.active.is_(True),
        )
    )
    blocks = list(block_result.scalars().all())
    assert len(blocks) == 1
    assert "risk_event_count" in blocks[0].reason


@pytest.mark.asyncio
async def test_spend_threshold_trigger(test_session):
    """Auto block fires when spend exceeds threshold."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Create an LLM account (required FK for SpendRecord)
    llm_account = LLMAccount(
        id=uuid4(),
        group_id=group.id,
        provider="openai",
        status="active",
    )
    test_session.add(llm_account)
    await test_session.flush()

    # Create auto rule: trigger when spend >= 100
    await create_auto_block_rule(
        test_session,
        AutoBlockRuleCreate(
            group_id=group.id,
            trigger_type="spend_threshold",
            threshold=100,
            time_window_minutes=60 * 24 * 30,
            member_id=member.id,
        ),
        user_id=owner_id,
    )

    # Insert a spend record exceeding the threshold
    now = datetime.now(timezone.utc)
    spend = SpendRecord(
        id=uuid4(),
        group_id=group.id,
        llm_account_id=llm_account.id,
        member_id=member.id,
        period_start=now - timedelta(hours=1),
        period_end=now,
        amount=150.0,
        currency="USD",
    )
    test_session.add(spend)
    await test_session.flush()

    # Evaluate — should trigger
    result = await evaluate_auto_block_rules(test_session)
    assert result["triggered"] == 1

    # Verify a BlockRule was created
    from sqlalchemy import select
    block_result = await test_session.execute(
        select(BlockRule).where(
            BlockRule.group_id == group.id,
            BlockRule.active.is_(True),
        )
    )
    blocks = list(block_result.scalars().all())
    assert len(blocks) == 1
    assert "spend" in blocks[0].reason.lower()
