"""End-to-end tests for content reporting (P2-S9).

Tests the full lifecycle: report creation, reason taxonomy, deduplication,
self-report prevention, status workflow, moderator review.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.moderation.service import (
    REPORT_REASON_LABELS,
    ReportReason,
    create_content_report,
    get_report,
    list_reports,
    update_report_status,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def reporter(test_session: AsyncSession):
    """Create a reporter user."""
    user = User(
        id=uuid.uuid4(),
        email=f"reporter-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Reporter User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest_asyncio.fixture
async def target_user(test_session: AsyncSession):
    """Create a target user (the one being reported)."""
    user = User(
        id=uuid.uuid4(),
        email=f"target-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Target User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest_asyncio.fixture
async def second_reporter(test_session: AsyncSession):
    """Create a second reporter user for multi-reporter scenarios."""
    user = User(
        id=uuid.uuid4(),
        email=f"reporter2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Second Reporter",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


# ---------------------------------------------------------------------------
# Report creation — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_post_with_reason(test_session: AsyncSession, reporter):
    """Report a post with a valid reason from taxonomy."""
    post_id = uuid.uuid4()
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="post",
        target_id=post_id,
        reason="bullying",
        description="This post contains mean comments about someone.",
    )
    assert report.id is not None
    assert report.reporter_id == reporter.id
    assert report.target_type == "post"
    assert report.target_id == post_id
    assert report.reason == "bullying"
    assert report.description == "This post contains mean comments about someone."
    assert report.status == "pending"


@pytest.mark.asyncio
async def test_report_user(test_session: AsyncSession, reporter, target_user):
    """Report a user (not self)."""
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="user",
        target_id=target_user.id,
        reason="impersonation",
    )
    assert report.target_type == "user"
    assert report.target_id == target_user.id
    assert report.reason == "impersonation"
    assert report.status == "pending"


@pytest.mark.asyncio
async def test_report_message(test_session: AsyncSession, reporter):
    """Report a message."""
    msg_id = uuid.uuid4()
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="message",
        target_id=msg_id,
        reason="adult_content",
    )
    assert report.target_type == "message"
    assert report.reason == "adult_content"


@pytest.mark.asyncio
async def test_report_comment(test_session: AsyncSession, reporter):
    """Report a comment."""
    comment_id = uuid.uuid4()
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="comment",
        target_id=comment_id,
        reason="spam",
    )
    assert report.target_type == "comment"
    assert report.reason == "spam"


@pytest.mark.asyncio
async def test_report_without_description(test_session: AsyncSession, reporter):
    """Report with no description (description is optional)."""
    post_id = uuid.uuid4()
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="post",
        target_id=post_id,
        reason="inappropriate",
    )
    assert report.description is None


# ---------------------------------------------------------------------------
# Report reason taxonomy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_reason_taxonomy_all_values():
    """All report reasons are defined and have labels."""
    assert len(ReportReason) == 7
    expected = {
        "inappropriate", "bullying", "spam", "impersonation",
        "self_harm", "adult_content", "other",
    }
    actual = {r.value for r in ReportReason}
    assert actual == expected


@pytest.mark.asyncio
async def test_report_reason_labels_complete():
    """Every reason has an age-appropriate label."""
    for reason in ReportReason:
        assert reason in REPORT_REASON_LABELS
        assert isinstance(REPORT_REASON_LABELS[reason], str)
        assert len(REPORT_REASON_LABELS[reason]) > 0


@pytest.mark.asyncio
async def test_invalid_reason_rejected(test_session: AsyncSession, reporter):
    """Reasons not in the taxonomy are rejected."""
    with pytest.raises(ValidationError, match="Invalid reason"):
        await create_content_report(
            test_session,
            reporter_id=reporter.id,
            target_type="post",
            target_id=uuid.uuid4(),
            reason="not_a_real_reason",
        )


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_report_same_reporter_409(test_session: AsyncSession, reporter):
    """Same reporter + same target = ConflictError (409)."""
    post_id = uuid.uuid4()
    await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="post",
        target_id=post_id,
        reason="spam",
    )
    with pytest.raises(ConflictError, match="already reported"):
        await create_content_report(
            test_session,
            reporter_id=reporter.id,
            target_type="post",
            target_id=post_id,
            reason="bullying",  # Different reason, same target — still blocked
        )


@pytest.mark.asyncio
async def test_different_reporters_same_target_allowed(
    test_session: AsyncSession, reporter, second_reporter
):
    """Different reporters CAN report the same target."""
    post_id = uuid.uuid4()
    r1 = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="post",
        target_id=post_id,
        reason="spam",
    )
    r2 = await create_content_report(
        test_session,
        reporter_id=second_reporter.id,
        target_type="post",
        target_id=post_id,
        reason="bullying",
    )
    assert r1.id != r2.id
    assert r1.target_id == r2.target_id


# ---------------------------------------------------------------------------
# Self-report prevention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_self_report_prevented(test_session: AsyncSession, reporter):
    """Users cannot report themselves (target_type=user, target_id=self)."""
    with pytest.raises(ValidationError, match="cannot report yourself"):
        await create_content_report(
            test_session,
            reporter_id=reporter.id,
            target_type="user",
            target_id=reporter.id,
            reason="other",
        )


# ---------------------------------------------------------------------------
# Invalid target type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_target_type_rejected(test_session: AsyncSession, reporter):
    """Invalid target types are rejected."""
    with pytest.raises(ValidationError, match="Invalid target_type"):
        await create_content_report(
            test_session,
            reporter_id=reporter.id,
            target_type="story",
            target_id=uuid.uuid4(),
            reason="spam",
        )


# ---------------------------------------------------------------------------
# Status workflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_workflow_pending_to_under_review(
    test_session: AsyncSession, reporter
):
    """Moderator moves report from pending to under_review."""
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="post",
        target_id=uuid.uuid4(),
        reason="bullying",
    )
    assert report.status == "pending"

    updated = await update_report_status(
        test_session, report.id, "under_review", moderator_id=uuid.uuid4()
    )
    assert updated.status == "under_review"


@pytest.mark.asyncio
async def test_status_workflow_under_review_to_action_taken(
    test_session: AsyncSession, reporter
):
    """Moderator takes action on a report."""
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="message",
        target_id=uuid.uuid4(),
        reason="self_harm",
    )
    await update_report_status(test_session, report.id, "under_review")
    updated = await update_report_status(test_session, report.id, "action_taken")
    assert updated.status == "action_taken"


@pytest.mark.asyncio
async def test_status_workflow_dismiss(test_session: AsyncSession, reporter):
    """Moderator dismisses a report from pending."""
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="post",
        target_id=uuid.uuid4(),
        reason="other",
        description="Not actually a problem.",
    )
    updated = await update_report_status(test_session, report.id, "dismissed")
    assert updated.status == "dismissed"


@pytest.mark.asyncio
async def test_invalid_status_transition_rejected(
    test_session: AsyncSession, reporter
):
    """Cannot skip from pending straight to action_taken."""
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="post",
        target_id=uuid.uuid4(),
        reason="spam",
    )
    with pytest.raises(ValidationError, match="Cannot transition"):
        await update_report_status(test_session, report.id, "action_taken")


@pytest.mark.asyncio
async def test_terminal_status_cannot_change(test_session: AsyncSession, reporter):
    """Dismissed reports cannot be re-opened."""
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="post",
        target_id=uuid.uuid4(),
        reason="inappropriate",
    )
    await update_report_status(test_session, report.id, "dismissed")
    with pytest.raises(ValidationError, match="Cannot transition"):
        await update_report_status(test_session, report.id, "under_review")


# ---------------------------------------------------------------------------
# Get report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_report_by_id(test_session: AsyncSession, reporter):
    """Retrieve a report by its ID."""
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="post",
        target_id=uuid.uuid4(),
        reason="bullying",
    )
    fetched = await get_report(test_session, report.id)
    assert fetched.id == report.id
    assert fetched.reason == "bullying"


@pytest.mark.asyncio
async def test_get_nonexistent_report(test_session: AsyncSession):
    """Getting a non-existent report raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await get_report(test_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# List reports with filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_reports_with_status_filter(
    test_session: AsyncSession, reporter
):
    """List reports filtered by status."""
    # Create two reports
    r1 = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="post",
        target_id=uuid.uuid4(),
        reason="spam",
    )
    r2 = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="message",
        target_id=uuid.uuid4(),
        reason="bullying",
    )
    # Dismiss one
    await update_report_status(test_session, r1.id, "dismissed")

    # Filter for pending only
    result = await list_reports(
        test_session, reporter_id=reporter.id, status="pending"
    )
    assert result["total"] == 1
    assert result["items"][0].id == r2.id

    # Filter for dismissed
    result_dismissed = await list_reports(
        test_session, reporter_id=reporter.id, status="dismissed"
    )
    assert result_dismissed["total"] == 1
    assert result_dismissed["items"][0].id == r1.id


# ---------------------------------------------------------------------------
# Full lifecycle: report -> queue -> review -> status update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_report_lifecycle(test_session: AsyncSession, reporter):
    """Full lifecycle: create report -> under_review -> action_taken."""
    post_id = uuid.uuid4()

    # Step 1: User reports a post
    report = await create_content_report(
        test_session,
        reporter_id=reporter.id,
        target_type="post",
        target_id=post_id,
        reason="bullying",
        description="This post is targeting another student.",
    )
    assert report.status == "pending"

    # Step 2: Moderator picks up the report
    moderator_id = uuid.uuid4()
    report = await update_report_status(
        test_session, report.id, "under_review", moderator_id=moderator_id
    )
    assert report.status == "under_review"

    # Step 3: Moderator takes action
    report = await update_report_status(
        test_session, report.id, "action_taken", moderator_id=moderator_id
    )
    assert report.status == "action_taken"

    # Step 4: Verify final state
    final = await get_report(test_session, report.id)
    assert final.status == "action_taken"
    assert final.reason == "bullying"
    assert final.description == "This post is targeting another student."


@pytest.mark.asyncio
async def test_all_report_reasons_can_be_used(test_session: AsyncSession, reporter):
    """Every reason in the taxonomy can be used to create a report."""
    for reason in ReportReason:
        report = await create_content_report(
            test_session,
            reporter_id=reporter.id,
            target_type="post",
            target_id=uuid.uuid4(),
            reason=reason.value,
        )
        assert report.reason == reason.value
        assert report.status == "pending"
