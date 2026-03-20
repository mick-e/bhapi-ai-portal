"""E2E tests for panic button / instant report."""

from uuid import uuid4

import pytest

from src.alerts.panic import (
    PARENT_QUICK_RESPONSES,
    VALID_CATEGORIES,
    create_panic_report,
    list_panic_reports,
    respond_to_panic,
)
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_create_panic_report(test_session):
    """Create a panic report for a member."""
    group, owner_id = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    report = await create_panic_report(
        test_session,
        group_id=group.id,
        member_id=member.id,
        category="scary_content",
        message="I saw something scary",
    )
    assert report.id is not None
    assert report.category == "scary_content"
    assert report.message == "I saw something scary"
    assert report.resolved is False


@pytest.mark.asyncio
async def test_create_panic_report_all_categories(test_session):
    """All valid categories should be accepted."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    for cat in VALID_CATEGORIES:
        report = await create_panic_report(
            test_session,
            group_id=group.id,
            member_id=member.id,
            category=cat,
        )
        assert report.category == cat


@pytest.mark.asyncio
async def test_create_panic_report_invalid_category(test_session):
    """Invalid category should be rejected."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    with pytest.raises(ValidationError):
        await create_panic_report(
            test_session,
            group_id=group.id,
            member_id=member.id,
            category="invalid_category",
        )


@pytest.mark.asyncio
async def test_create_panic_report_with_platform(test_session):
    """Panic report with platform info."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    report = await create_panic_report(
        test_session,
        group_id=group.id,
        member_id=member.id,
        category="bad_ai_response",
        platform="chatgpt",
        session_id="sess_123",
    )
    assert report.platform == "chatgpt"
    assert report.session_id == "sess_123"


@pytest.mark.asyncio
async def test_respond_to_panic(test_session):
    """Parent responds to a panic report."""
    group, owner_id = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    report = await create_panic_report(
        test_session,
        group_id=group.id,
        member_id=member.id,
        category="scary_content",
    )

    updated = await respond_to_panic(
        test_session,
        report_id=report.id,
        user_id=owner_id,
        response=PARENT_QUICK_RESPONSES[0],
    )
    assert updated.resolved is True
    assert updated.parent_response == PARENT_QUICK_RESPONSES[0]
    assert updated.parent_responded_at is not None


@pytest.mark.asyncio
async def test_respond_to_panic_not_found(test_session):
    """Responding to non-existent report raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await respond_to_panic(
            test_session,
            report_id=uuid4(),
            user_id=uuid4(),
            response="test",
        )


@pytest.mark.asyncio
async def test_list_panic_reports(test_session):
    """List panic reports with pagination."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    # Create 3 reports
    for cat in ["scary_content", "weird_request", "other"]:
        await create_panic_report(
            test_session,
            group_id=group.id,
            member_id=member.id,
            category=cat,
        )

    result = await list_panic_reports(test_session, group.id)
    assert result["total"] == 3
    assert len(result["items"]) == 3
    assert result["page"] == 1


@pytest.mark.asyncio
async def test_list_panic_reports_pagination(test_session):
    """Pagination works correctly."""
    group, _ = await make_test_group(test_session, name="Family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(member)
    await test_session.flush()

    for _ in range(5):
        await create_panic_report(
            test_session,
            group_id=group.id,
            member_id=member.id,
            category="other",
        )

    page1 = await list_panic_reports(test_session, group.id, page=1, page_size=2)
    assert len(page1["items"]) == 2
    assert page1["total"] == 5
    assert page1["total_pages"] == 3

    page2 = await list_panic_reports(test_session, group.id, page=2, page_size=2)
    assert len(page2["items"]) == 2


@pytest.mark.asyncio
async def test_parent_quick_responses_exist():
    """Quick responses list should have entries."""
    assert len(PARENT_QUICK_RESPONSES) >= 4
    for r in PARENT_QUICK_RESPONSES:
        assert isinstance(r, str)
        assert len(r) > 0
