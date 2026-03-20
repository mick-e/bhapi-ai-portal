"""E2E tests for member cap enforcement (Phase 1A)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.constants import MAX_FAMILY_MEMBERS
from src.exceptions import ValidationError
from src.groups.models import GroupMember
from src.groups.schemas import MemberAdd
from src.groups.service import accept_invitation, add_member
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_family_rejects_sixth_member(test_session):
    """Family group should reject adding a 6th member (cap=5)."""
    group, owner_id = await make_test_group(test_session, name="Test Family", group_type="family")

    # Add 5 members (including owner)
    for i in range(MAX_FAMILY_MEMBERS):
        member = GroupMember(
            id=uuid4(), group_id=group.id,
            user_id=None if i > 0 else owner_id,
            role="parent" if i == 0 else "member",
            display_name=f"Member {i}",
        )
        test_session.add(member)
    await test_session.flush()

    # 6th member should be rejected
    with pytest.raises(ValidationError, match=f"Maximum {MAX_FAMILY_MEMBERS}"):
        await add_member(
            test_session, group.id, owner_id,
            MemberAdd(
                user_id=None, role="member",
                display_name="Extra Member",
            ),
        )


@pytest.mark.asyncio
async def test_school_allows_more_than_five(test_session):
    """School group should allow more than 5 members."""
    group, owner_id = await make_test_group(test_session, name="Test School", group_type="school")

    # Add owner as admin
    owner_member = GroupMember(
        id=uuid4(), group_id=group.id,
        user_id=owner_id, role="school_admin",
        display_name="Admin",
    )
    test_session.add(owner_member)

    # Add 5 more members (6 total including admin)
    for i in range(5):
        member = GroupMember(
            id=uuid4(), group_id=group.id,
            user_id=None, role="member",
            display_name=f"Student {i}",
        )
        test_session.add(member)
    await test_session.flush()

    # 7th member should succeed for school
    result = await add_member(
        test_session, group.id, owner_id,
        MemberAdd(
            user_id=None, role="member",
            display_name="Student 6",
        ),
    )
    assert result is not None
    assert result.display_name == "Student 6"


@pytest.mark.asyncio
async def test_family_invitation_cap_check(test_session):
    """Accepting an invitation should also check family cap."""
    group, owner_id = await make_test_group(test_session, name="Full Family", group_type="family")

    # Fill to cap
    for i in range(MAX_FAMILY_MEMBERS):
        member = GroupMember(
            id=uuid4(), group_id=group.id,
            user_id=None if i > 0 else owner_id,
            role="parent" if i == 0 else "member",
            display_name=f"Member {i}",
        )
        test_session.add(member)
    await test_session.flush()

    # Create invitation
    import secrets
    from datetime import timedelta

    from src.groups.models import Invitation

    invitation = Invitation(
        id=uuid4(), group_id=group.id,
        invited_by=owner_id,
        email="new@example.com", role="member",
        token=secrets.token_urlsafe(32),
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    test_session.add(invitation)
    await test_session.flush()

    # Accept should fail due to cap
    with pytest.raises(ValidationError, match=f"Maximum {MAX_FAMILY_MEMBERS}"):
        await accept_invitation(test_session, invitation.token, uuid4())


@pytest.mark.asyncio
async def test_club_allows_many_members(test_session):
    """Club group should allow up to MAX_GROUP_MEMBERS."""
    group, owner_id = await make_test_group(test_session, name="Test Club", group_type="club")

    owner_member = GroupMember(
        id=uuid4(), group_id=group.id,
        user_id=owner_id, role="club_admin",
        display_name="Admin",
    )
    test_session.add(owner_member)

    # Add 10 members (well under MAX_GROUP_MEMBERS=500)
    for i in range(10):
        member = GroupMember(
            id=uuid4(), group_id=group.id,
            user_id=None, role="member",
            display_name=f"Member {i}",
        )
        test_session.add(member)
    await test_session.flush()

    # Adding 12th should succeed
    result = await add_member(
        test_session, group.id, owner_id,
        MemberAdd(
            user_id=None, role="member",
            display_name="Member 11",
        ),
    )
    assert result is not None
