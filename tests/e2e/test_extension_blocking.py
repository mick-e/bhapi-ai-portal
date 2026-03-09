"""E2E tests for extension blocking enforcement (active-rules endpoint)."""

import pytest
from uuid import uuid4

from src.blocking.models import BlockRule
from src.blocking.service import list_active_rules
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_active_rules_endpoint_returns_rules(test_session):
    """Create a block rule, then list_active_rules should return it."""
    group, owner_id = await make_test_group(
        test_session, name="Family", group_type="family"
    )
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    rule = BlockRule(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        platforms=["chatgpt", "claude.ai"],
        reason="Bedtime hours",
        active=True,
        created_by=owner_id,
    )
    test_session.add(rule)
    await test_session.flush()

    rules = await list_active_rules(test_session, group.id)
    assert len(rules) == 1
    assert rules[0].id == rule.id
    assert rules[0].platforms == ["chatgpt", "claude.ai"]
    assert rules[0].reason == "Bedtime hours"
    assert rules[0].active is True


@pytest.mark.asyncio
async def test_active_rules_empty(test_session):
    """Groups with no block rules should return an empty list."""
    group, _ = await make_test_group(
        test_session, name="Empty Family", group_type="family"
    )

    rules = await list_active_rules(test_session, group.id)
    assert rules == []


@pytest.mark.asyncio
async def test_active_rules_excludes_inactive(test_session):
    """Inactive rules should not appear in active rules list."""
    group, owner_id = await make_test_group(
        test_session, name="Family", group_type="family"
    )
    member = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Active rule
    active_rule = BlockRule(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        platforms=["chatgpt"],
        reason="Active block",
        active=True,
        created_by=owner_id,
    )
    # Inactive rule
    inactive_rule = BlockRule(
        id=uuid4(),
        group_id=group.id,
        member_id=member.id,
        platforms=["gemini"],
        reason="Revoked block",
        active=False,
        created_by=owner_id,
    )
    test_session.add(active_rule)
    test_session.add(inactive_rule)
    await test_session.flush()

    rules = await list_active_rules(test_session, group.id)
    assert len(rules) == 1
    assert rules[0].id == active_rule.id


@pytest.mark.asyncio
async def test_active_rules_multiple_members(test_session):
    """Active rules should include rules for all members in the group."""
    group, owner_id = await make_test_group(
        test_session, name="Family", group_type="family"
    )
    child1 = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child 1",
    )
    child2 = GroupMember(
        id=uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child 2",
    )
    test_session.add(child1)
    test_session.add(child2)
    await test_session.flush()

    rule1 = BlockRule(
        id=uuid4(),
        group_id=group.id,
        member_id=child1.id,
        platforms=["chatgpt"],
        active=True,
        created_by=owner_id,
    )
    rule2 = BlockRule(
        id=uuid4(),
        group_id=group.id,
        member_id=child2.id,
        platforms=["grok.com"],
        active=True,
        created_by=owner_id,
    )
    test_session.add(rule1)
    test_session.add(rule2)
    await test_session.flush()

    rules = await list_active_rules(test_session, group.id)
    assert len(rules) == 2
    rule_ids = {r.id for r in rules}
    assert rule1.id in rule_ids
    assert rule2.id in rule_ids
