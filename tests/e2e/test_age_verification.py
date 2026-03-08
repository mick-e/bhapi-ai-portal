"""E2E tests for Yoti age verification."""

import pytest
from uuid import uuid4

from src.groups.models import GroupMember
from src.integrations.age_verification import start_age_verification, process_age_verification_result
from src.integrations.yoti import create_age_verification_session, get_age_verification_result
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_create_session_dev_mode():
    """Dev mode should return a mock session without calling Yoti."""
    result = await create_age_verification_session("member_123")
    assert "session_id" in result
    assert result["session_id"].startswith("dev_session_")
    assert "url" in result


@pytest.mark.asyncio
async def test_get_result_dev_mode():
    """Dev mode should return a verified result."""
    result = await get_age_verification_result("dev_session_abc")
    assert result["verified"] is True
    assert result["age"] == 12
    assert result["session_id"] == "dev_session_abc"


@pytest.mark.asyncio
async def test_start_age_verification(test_session):
    """Starting age verification should return session info."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    result = await start_age_verification(test_session, group.id, member.id)
    assert "session_id" in result
    assert "url" in result


@pytest.mark.asyncio
async def test_start_age_verification_nonexistent_member(test_session):
    """Starting verification for a nonexistent member should fail."""
    from src.exceptions import NotFoundError

    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    with pytest.raises(NotFoundError):
        await start_age_verification(test_session, group.id, uuid4())


@pytest.mark.asyncio
async def test_process_verification_result(test_session):
    """Processing a dev-mode result should update the member's DOB."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    result = await process_age_verification_result(
        test_session, group.id, member.id, "dev_session_test"
    )
    assert result["verified"] is True
    assert result["age"] == 12

    # Member should now have a DOB set
    from sqlalchemy import select
    refreshed = await test_session.execute(
        select(GroupMember).where(GroupMember.id == member.id)
    )
    m = refreshed.scalar_one()
    assert m.date_of_birth is not None
