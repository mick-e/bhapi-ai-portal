"""Unit tests for the moderation module."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.groups.models import Group
from src.moderation.models import ContentReport, ModerationDecision, ModerationQueue
from src.moderation.service import (
    create_content_report,
    get_dashboard_stats,
    get_queue_entry,
    list_queue,
    list_reports,
    process_queue_entry,
    submit_for_moderation,
    takedown_content,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_user(test_session: AsyncSession):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email=f"mod-test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Mod Tester",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest_asyncio.fixture
async def second_user(test_session: AsyncSession):
    """Create a second test user."""
    user = User(
        id=uuid.uuid4(),
        email=f"mod-test2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Mod Tester 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


# ---------------------------------------------------------------------------
# Queue CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_for_moderation_creates_entry(test_session: AsyncSession):
    """Submitting content creates a queue entry."""
    content_id = uuid.uuid4()
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=content_id
    )
    assert entry.id is not None
    assert entry.content_type == "post"
    assert entry.content_id == content_id
    assert entry.status == "pending"


@pytest.mark.asyncio
async def test_submit_with_content_text(test_session: AsyncSession):
    """Submitting with content_text populates risk_scores."""
    entry = await submit_for_moderation(
        test_session,
        content_type="comment",
        content_id=uuid.uuid4(),
        content_text="Hello world",
    )
    assert entry.risk_scores is not None
    assert "keyword_filter" in entry.risk_scores


@pytest.mark.asyncio
async def test_get_queue_entry_found(test_session: AsyncSession):
    """Get an existing queue entry."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )
    fetched = await get_queue_entry(test_session, entry.id)
    assert fetched.id == entry.id


@pytest.mark.asyncio
async def test_get_queue_entry_not_found(test_session: AsyncSession):
    """Get a non-existent queue entry raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await get_queue_entry(test_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_list_queue_all(test_session: AsyncSession):
    """List all queue entries."""
    for _ in range(3):
        await submit_for_moderation(
            test_session, content_type="post", content_id=uuid.uuid4()
        )
    result = await list_queue(test_session)
    assert result["total"] == 3
    assert len(result["items"]) == 3


@pytest.mark.asyncio
async def test_list_queue_filter_by_status(test_session: AsyncSession):
    """List queue entries filtered by status."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )
    await process_queue_entry(test_session, entry.id, action="approve")

    await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )

    pending = await list_queue(test_session, status="pending")
    assert pending["total"] == 1

    approved = await list_queue(test_session, status="approved")
    assert approved["total"] == 1


@pytest.mark.asyncio
async def test_list_queue_filter_by_pipeline(test_session: AsyncSession):
    """List queue entries filtered by pipeline."""
    await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4(), author_age_tier="young"
    )
    await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4(), author_age_tier="teen"
    )

    pre = await list_queue(test_session, pipeline="pre_publish")
    assert pre["total"] == 1

    post = await list_queue(test_session, pipeline="post_publish")
    assert post["total"] == 1


@pytest.mark.asyncio
async def test_list_queue_pagination(test_session: AsyncSession):
    """List queue supports pagination."""
    for _ in range(5):
        await submit_for_moderation(
            test_session, content_type="post", content_id=uuid.uuid4()
        )
    result = await list_queue(test_session, page=1, page_size=2)
    assert result["total"] == 5
    assert len(result["items"]) == 2
    assert result["page"] == 1


# ---------------------------------------------------------------------------
# Pipeline routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_young_routes_to_pre_publish(test_session: AsyncSession):
    """Young age tier routes to pre_publish pipeline."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4(), author_age_tier="young"
    )
    assert entry.pipeline == "pre_publish"


@pytest.mark.asyncio
async def test_preteen_routes_to_pre_publish(test_session: AsyncSession):
    """Preteen age tier routes to pre_publish pipeline."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4(), author_age_tier="preteen"
    )
    assert entry.pipeline == "pre_publish"


@pytest.mark.asyncio
async def test_teen_routes_to_post_publish(test_session: AsyncSession):
    """Teen age tier routes to post_publish pipeline."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4(), author_age_tier="teen"
    )
    assert entry.pipeline == "post_publish"


@pytest.mark.asyncio
async def test_no_age_tier_routes_to_post_publish(test_session: AsyncSession):
    """No age tier defaults to post_publish pipeline."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )
    assert entry.pipeline == "post_publish"


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_entry(test_session: AsyncSession, test_user):
    """Approving an entry updates status and creates decision."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )
    decision = await process_queue_entry(
        test_session, entry.id, action="approve", moderator_id=test_user.id
    )
    assert decision.action == "approve"
    assert decision.moderator_id == test_user.id

    updated = await get_queue_entry(test_session, entry.id)
    assert updated.status == "approved"


@pytest.mark.asyncio
async def test_reject_entry(test_session: AsyncSession, test_user):
    """Rejecting an entry updates status."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )
    decision = await process_queue_entry(
        test_session, entry.id, action="reject", moderator_id=test_user.id, reason="Spam"
    )
    assert decision.action == "reject"
    assert decision.reason == "Spam"

    updated = await get_queue_entry(test_session, entry.id)
    assert updated.status == "rejected"


@pytest.mark.asyncio
async def test_escalate_entry(test_session: AsyncSession, test_user):
    """Escalating an entry updates status."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )
    decision = await process_queue_entry(
        test_session, entry.id, action="escalate", moderator_id=test_user.id
    )
    assert decision.action == "escalate"

    updated = await get_queue_entry(test_session, entry.id)
    assert updated.status == "escalated"


@pytest.mark.asyncio
async def test_process_already_approved_raises_conflict(test_session: AsyncSession):
    """Processing an already-approved entry raises ConflictError."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )
    await process_queue_entry(test_session, entry.id, action="approve")
    with pytest.raises(ConflictError):
        await process_queue_entry(test_session, entry.id, action="reject")


@pytest.mark.asyncio
async def test_process_invalid_action_raises_validation(test_session: AsyncSession):
    """Invalid action raises ValidationError."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )
    with pytest.raises(ValidationError):
        await process_queue_entry(test_session, entry.id, action="delete")


# ---------------------------------------------------------------------------
# Takedown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_takedown_creates_decision(test_session: AsyncSession, test_user):
    """Takedown creates a reject decision."""
    content_id = uuid.uuid4()
    decision = await takedown_content(
        test_session,
        content_type="post",
        content_id=content_id,
        reason="Harmful content",
        moderator_id=test_user.id,
    )
    assert decision.action == "reject"
    assert "[TAKEDOWN]" in decision.reason


@pytest.mark.asyncio
async def test_takedown_existing_entry(test_session: AsyncSession, test_user):
    """Takedown on existing queue entry reuses it."""
    content_id = uuid.uuid4()
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=content_id
    )
    decision = await takedown_content(
        test_session,
        content_type="post",
        content_id=content_id,
        reason="Harmful content",
        moderator_id=test_user.id,
    )
    assert decision.queue_id == entry.id

    updated = await get_queue_entry(test_session, entry.id)
    assert updated.status == "rejected"


@pytest.mark.asyncio
async def test_takedown_new_entry(test_session: AsyncSession, test_user):
    """Takedown without existing entry creates one."""
    content_id = uuid.uuid4()
    decision = await takedown_content(
        test_session,
        content_type="media",
        content_id=content_id,
        reason="CSAM detected",
        moderator_id=test_user.id,
    )
    assert decision.queue_id is not None
    entry = await get_queue_entry(test_session, decision.queue_id)
    assert entry.pipeline == "takedown"
    assert entry.status == "rejected"


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_empty(test_session: AsyncSession):
    """Dashboard with no data returns zeros."""
    stats = await get_dashboard_stats(test_session)
    assert stats["pending_count"] == 0
    assert stats["total_processed_today"] == 0
    assert stats["avg_processing_time_ms"] == 0.0


@pytest.mark.asyncio
async def test_dashboard_counts_pending(test_session: AsyncSession):
    """Dashboard counts pending entries."""
    await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )
    await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )
    stats = await get_dashboard_stats(test_session)
    assert stats["pending_count"] == 2


@pytest.mark.asyncio
async def test_dashboard_severity_breakdown(test_session: AsyncSession):
    """Dashboard provides status breakdown."""
    entry = await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )
    await process_queue_entry(test_session, entry.id, action="approve")
    await submit_for_moderation(
        test_session, content_type="post", content_id=uuid.uuid4()
    )

    stats = await get_dashboard_stats(test_session)
    assert "pending" in stats["severity_breakdown"]
    assert "approved" in stats["severity_breakdown"]


# ---------------------------------------------------------------------------
# Content reports
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_report(test_session: AsyncSession, test_user):
    """Create a content report."""
    report = await create_content_report(
        test_session,
        reporter_id=test_user.id,
        target_type="post",
        target_id=uuid.uuid4(),
        reason="Inappropriate content",
    )
    assert report.id is not None
    assert report.reporter_id == test_user.id
    assert report.status == "pending"


@pytest.mark.asyncio
async def test_create_report_duplicate_raises_conflict(test_session: AsyncSession, test_user):
    """Duplicate report by same user on same target raises ConflictError."""
    target_id = uuid.uuid4()
    await create_content_report(
        test_session,
        reporter_id=test_user.id,
        target_type="post",
        target_id=target_id,
        reason="Spam",
    )
    with pytest.raises(ConflictError):
        await create_content_report(
            test_session,
            reporter_id=test_user.id,
            target_type="post",
            target_id=target_id,
            reason="Spam again",
        )


@pytest.mark.asyncio
async def test_different_users_can_report_same_target(
    test_session: AsyncSession, test_user, second_user
):
    """Different users can report the same target."""
    target_id = uuid.uuid4()
    r1 = await create_content_report(
        test_session,
        reporter_id=test_user.id,
        target_type="post",
        target_id=target_id,
        reason="Spam",
    )
    r2 = await create_content_report(
        test_session,
        reporter_id=second_user.id,
        target_type="post",
        target_id=target_id,
        reason="Hateful",
    )
    assert r1.id != r2.id


@pytest.mark.asyncio
async def test_list_reports_all(test_session: AsyncSession, test_user):
    """List all reports."""
    for i in range(3):
        await create_content_report(
            test_session,
            reporter_id=test_user.id,
            target_type="comment",
            target_id=uuid.uuid4(),
            reason=f"Reason {i}",
        )
    result = await list_reports(test_session)
    assert result["total"] == 3


@pytest.mark.asyncio
async def test_list_reports_by_reporter(test_session: AsyncSession, test_user, second_user):
    """List reports filtered by reporter."""
    await create_content_report(
        test_session,
        reporter_id=test_user.id,
        target_type="post",
        target_id=uuid.uuid4(),
        reason="Spam",
    )
    await create_content_report(
        test_session,
        reporter_id=second_user.id,
        target_type="post",
        target_id=uuid.uuid4(),
        reason="Hateful",
    )

    result = await list_reports(test_session, reporter_id=test_user.id)
    assert result["total"] == 1
    assert result["items"][0].reporter_id == test_user.id


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_invalid_content_type(test_session: AsyncSession):
    """Invalid content_type raises ValidationError."""
    with pytest.raises(ValidationError, match="Invalid content_type"):
        await submit_for_moderation(
            test_session, content_type="tweet", content_id=uuid.uuid4()
        )


@pytest.mark.asyncio
async def test_report_invalid_target_type(test_session: AsyncSession, test_user):
    """Invalid target_type raises ValidationError."""
    with pytest.raises(ValidationError, match="Invalid target_type"):
        await create_content_report(
            test_session,
            reporter_id=test_user.id,
            target_type="profile",
            target_id=uuid.uuid4(),
            reason="Bad",
        )


@pytest.mark.asyncio
async def test_takedown_invalid_content_type(test_session: AsyncSession, test_user):
    """Invalid content_type on takedown raises ValidationError."""
    with pytest.raises(ValidationError, match="Invalid content_type"):
        await takedown_content(
            test_session,
            content_type="tweet",
            content_id=uuid.uuid4(),
            reason="Bad",
            moderator_id=test_user.id,
        )


@pytest.mark.asyncio
async def test_submit_all_content_types(test_session: AsyncSession):
    """All valid content types are accepted."""
    for ct in ("post", "comment", "message", "media"):
        entry = await submit_for_moderation(
            test_session, content_type=ct, content_id=uuid.uuid4()
        )
        assert entry.content_type == ct


@pytest.mark.asyncio
async def test_process_nonexistent_entry(test_session: AsyncSession):
    """Processing non-existent entry raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await process_queue_entry(test_session, uuid.uuid4(), action="approve")


@pytest.mark.asyncio
async def test_submit_stores_age_tier(test_session: AsyncSession):
    """Age tier is stored on the queue entry."""
    entry = await submit_for_moderation(
        test_session,
        content_type="post",
        content_id=uuid.uuid4(),
        author_age_tier="preteen",
    )
    assert entry.age_tier == "preteen"
