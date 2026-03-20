"""Security tests for sibling privacy — cross-member data isolation.

Verifies that visibility controls prevent unauthorized data access.
"""

from uuid import uuid4

import pytest

from src.auth.models import User
from src.exceptions import ForbiddenError
from src.groups.models import GroupMember
from src.groups.privacy import (
    check_member_visibility,
    enable_child_self_view,
    get_child_dashboard,
    set_member_visibility,
)
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_restricted_parent_cannot_see_child(test_session):
    """A parent not in visible_to cannot see a child's data."""
    group, owner_id = await make_test_group(test_session)

    # Create two parents
    parent2_id = uuid4()
    parent2 = User(
        id=parent2_id, email=f"parent-sec-{uuid4().hex[:6]}@example.com",
        display_name="Parent 2", account_type="family", email_verified=False, mfa_enabled=False,
    )
    test_session.add(parent2)

    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child A")
    test_session.add(child)
    await test_session.flush()

    # Restrict to owner only
    await set_member_visibility(test_session, group.id, child.id, [owner_id])

    assert await check_member_visibility(test_session, group.id, owner_id, child.id) is True
    assert await check_member_visibility(test_session, group.id, parent2_id, child.id) is False


@pytest.mark.asyncio
async def test_child_cannot_see_sibling_data(test_session):
    """Child A's dashboard never includes data about Child B."""
    group, owner_id = await make_test_group(test_session)

    child_a = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Alice")
    child_b = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Bob")
    test_session.add(child_a)
    test_session.add(child_b)
    await test_session.flush()

    # Enable self-view for child A
    await enable_child_self_view(test_session, group.id, child_a.id, ["safety_score", "time_usage"])

    dashboard = await get_child_dashboard(test_session, group.id, child_a.id)

    # Dashboard should only contain child A's ID
    assert dashboard["member_id"] == str(child_a.id)
    assert str(child_b.id) not in str(dashboard)


@pytest.mark.asyncio
async def test_disabled_self_view_blocks_dashboard(test_session):
    """A child with disabled self-view cannot access their dashboard."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    # Never enabled
    with pytest.raises(ForbiddenError):
        await get_child_dashboard(test_session, group.id, child.id)


@pytest.mark.asyncio
async def test_self_view_never_exposes_raw_risk_events(test_session):
    """Even with all sections enabled, raw risk events are never in the dashboard."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    # Enable all allowed sections
    await enable_child_self_view(
        test_session, group.id, child.id,
        ["safety_score", "time_usage", "literacy", "rewards"]
    )

    dashboard = await get_child_dashboard(test_session, group.id, child.id)

    # These should never appear in the response
    assert "raw_risk_events" not in str(dashboard)
    assert "parent_alerts" not in str(dashboard)
    assert "sibling_data" not in str(dashboard)


@pytest.mark.asyncio
async def test_multiple_children_isolated(test_session):
    """Visibility set for one child doesn't affect another."""
    group, owner_id = await make_test_group(test_session)

    parent2_id = uuid4()
    parent2 = User(
        id=parent2_id, email=f"p2-iso-{uuid4().hex[:6]}@example.com",
        display_name="Parent 2", account_type="family", email_verified=False, mfa_enabled=False,
    )
    test_session.add(parent2)

    child_a = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Alice")
    child_b = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Bob")
    test_session.add(child_a)
    test_session.add(child_b)
    await test_session.flush()

    # Restrict child A to owner only, leave child B unrestricted
    await set_member_visibility(test_session, group.id, child_a.id, [owner_id])

    # Parent 2 can see child B (unrestricted) but not child A
    assert await check_member_visibility(test_session, group.id, parent2_id, child_a.id) is False
    assert await check_member_visibility(test_session, group.id, parent2_id, child_b.id) is True
