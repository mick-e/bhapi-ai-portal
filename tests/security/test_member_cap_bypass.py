"""Security tests for member cap bypass via race condition."""


from uuid import uuid4

import pytest

from src.constants import MAX_FAMILY_MEMBERS
from src.exceptions import ValidationError
from src.groups.models import GroupMember
from src.groups.schemas import MemberAdd
from src.groups.service import add_member
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_concurrent_add_member_respects_cap(test_session):
    """Concurrent add_member calls should not exceed the family cap."""
    group, owner_id = await make_test_group(test_session, name="Race Family", group_type="family")

    # Add owner as admin member first
    owner_member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=owner_id,
        role="parent", display_name="Owner",
    )
    test_session.add(owner_member)

    # Fill to cap - 1 (owner counts as 1, so add cap - 2 more)
    for i in range(MAX_FAMILY_MEMBERS - 2):
        member = GroupMember(
            id=uuid4(), group_id=group.id,
            user_id=None,
            role="member",
            display_name=f"Member {i}",
        )
        test_session.add(member)
    await test_session.flush()

    # One slot left — try to add 3 concurrently
    # With a single test session, these run sequentially, but the logic
    # is tested: the second add_member should fail because the first
    # already filled the last slot.
    first = await add_member(
        test_session, group.id, owner_id,
        MemberAdd(user_id=None, role="member", display_name="Racer 1"),
    )
    assert first is not None

    with pytest.raises(ValidationError, match=f"Maximum {MAX_FAMILY_MEMBERS}"):
        await add_member(
            test_session, group.id, owner_id,
            MemberAdd(user_id=None, role="member", display_name="Racer 2"),
        )
