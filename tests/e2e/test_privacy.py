"""E2E tests for sibling privacy controls (F11).

Tests visibility enforcement, child self-view scoping, and child dashboard.
"""

from uuid import uuid4

import pytest

from tests.conftest import make_test_group
from src.groups.models import GroupMember
from src.groups.privacy import (
    check_member_visibility,
    disable_child_self_view,
    enable_child_self_view,
    get_child_dashboard,
    get_child_self_view,
    get_member_visibility,
    set_member_visibility,
    ALLOWED_SELF_VIEW_SECTIONS,
)
from src.exceptions import ForbiddenError, ValidationError


@pytest.mark.asyncio
async def test_default_visibility_allows_all(test_session):
    """With no visibility rows, all parents can see."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    result = await check_member_visibility(test_session, group.id, owner_id, child.id)
    assert result is True


@pytest.mark.asyncio
async def test_set_visibility_restricts_access(test_session):
    """Only listed parents can see after setting visibility."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)

    other_parent_id = uuid4()
    from src.auth.models import User
    other_user = User(
        id=other_parent_id, email=f"parent2-{uuid4().hex[:6]}@example.com",
        display_name="Parent 2", account_type="family", email_verified=False, mfa_enabled=False,
    )
    test_session.add(other_user)
    await test_session.flush()

    # Restrict visibility to only owner
    await set_member_visibility(test_session, group.id, child.id, [owner_id])

    assert await check_member_visibility(test_session, group.id, owner_id, child.id) is True
    assert await check_member_visibility(test_session, group.id, other_parent_id, child.id) is False


@pytest.mark.asyncio
async def test_remove_visibility_restrictions(test_session):
    """Passing empty list removes restrictions."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    await set_member_visibility(test_session, group.id, child.id, [owner_id])
    visible_to = await get_member_visibility(test_session, group.id, child.id)
    assert len(visible_to) == 1

    await set_member_visibility(test_session, group.id, child.id, [])
    visible_to = await get_member_visibility(test_session, group.id, child.id)
    assert len(visible_to) == 0

    # Now all parents can see again
    random_user_id = uuid4()
    assert await check_member_visibility(test_session, group.id, random_user_id, child.id) is True


@pytest.mark.asyncio
async def test_enable_child_self_view(test_session):
    """Enable self-view with valid sections."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    self_view = await enable_child_self_view(
        test_session, group.id, child.id, ["safety_score", "rewards"]
    )
    assert self_view.enabled is True
    assert "safety_score" in self_view.sections
    assert "rewards" in self_view.sections


@pytest.mark.asyncio
async def test_enable_self_view_invalid_section(test_session):
    """Invalid section raises ValidationError."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    with pytest.raises(ValidationError, match="Invalid section"):
        await enable_child_self_view(test_session, group.id, child.id, ["secret_data"])


@pytest.mark.asyncio
async def test_disable_child_self_view(test_session):
    """Disable self-view for a child."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    await enable_child_self_view(test_session, group.id, child.id, ["safety_score"])
    await disable_child_self_view(test_session, group.id, child.id)

    self_view = await get_child_self_view(test_session, group.id, child.id)
    assert self_view is not None
    assert self_view.enabled is False


@pytest.mark.asyncio
async def test_child_dashboard_requires_enabled(test_session):
    """Child dashboard raises ForbiddenError if self-view is not enabled."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    with pytest.raises(ForbiddenError, match="Self-view is not enabled"):
        await get_child_dashboard(test_session, group.id, child.id)


@pytest.mark.asyncio
async def test_child_dashboard_with_sections(test_session):
    """Child dashboard returns only allowed sections."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    await enable_child_self_view(
        test_session, group.id, child.id, ["safety_score", "time_usage"]
    )
    dashboard = await get_child_dashboard(test_session, group.id, child.id)

    assert dashboard["member_id"] == str(child.id)
    assert "safety_score" in dashboard
    assert "sessions_today" in dashboard
    # Sections not enabled should NOT be present
    assert "literacy" not in dashboard
    assert "rewards" not in dashboard


@pytest.mark.asyncio
async def test_update_self_view_sections(test_session):
    """Updating self-view replaces sections."""
    group, owner_id = await make_test_group(test_session)
    child = GroupMember(id=uuid4(), group_id=group.id, user_id=None, role="member", display_name="Child")
    test_session.add(child)
    await test_session.flush()

    await enable_child_self_view(test_session, group.id, child.id, ["safety_score"])
    sv1 = await get_child_self_view(test_session, group.id, child.id)
    assert sv1.sections == ["safety_score"]

    await enable_child_self_view(test_session, group.id, child.id, ["literacy", "rewards"])
    sv2 = await get_child_self_view(test_session, group.id, child.id)
    assert "literacy" in sv2.sections
    assert "rewards" in sv2.sections
    assert "safety_score" not in sv2.sections
