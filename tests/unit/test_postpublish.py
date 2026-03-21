"""Unit tests for post-publish moderation pipeline (teen 13-15 tier).

Post-publish pipeline: content publishes immediately, moderation runs async.
If flagged -> auto-takedown within 60s + parent alert + author notification.
Severe content -> immediate takedown + account restriction.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.moderation.models import ModerationDecision, ModerationQueue
from src.moderation.service import (
    PostPublishResult,
    PostPublishSeverity,
    get_queue_entry,
    run_post_publish_moderation,
    submit_for_moderation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def teen_user(test_session: AsyncSession):
    """Create a teen test user."""
    user = User(
        id=uuid.uuid4(),
        email=f"teen-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Teen Tester",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


# ---------------------------------------------------------------------------
# submit_for_moderation — teen tier publishes immediately
# ---------------------------------------------------------------------------


class TestTeenContentPublishesImmediately:
    """Teen content (13-15) should go through post_publish pipeline
    and be immediately approved (published) so it appears right away."""

    @pytest.mark.asyncio
    async def test_teen_post_publishes_immediately(self, test_session):
        """Teen post should be approved immediately with post_publish pipeline."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="post",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Just finished my math homework!",
        )
        assert entry.pipeline == "post_publish"
        assert entry.status == "published"

    @pytest.mark.asyncio
    async def test_teen_comment_publishes_immediately(self, test_session):
        """Teen comment should be approved immediately."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="comment",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Nice work on the project!",
        )
        assert entry.pipeline == "post_publish"
        assert entry.status == "published"

    @pytest.mark.asyncio
    async def test_teen_message_publishes_immediately(self, test_session):
        """Teen message should be approved immediately."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="message",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Want to study together after school?",
        )
        assert entry.pipeline == "post_publish"
        assert entry.status == "published"

    @pytest.mark.asyncio
    async def test_preteen_still_uses_pre_publish(self, test_session):
        """Preteen content should still go through pre_publish pipeline."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="post",
            content_id=uuid.uuid4(),
            author_age_tier="preteen",
            content_text="Hello world!",
        )
        assert entry.pipeline == "pre_publish"
        assert entry.status != "published"

    @pytest.mark.asyncio
    async def test_young_still_uses_pre_publish(self, test_session):
        """Young (5-9) content should still go through pre_publish pipeline."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="post",
            content_id=uuid.uuid4(),
            author_age_tier="young",
            content_text="I like turtles!",
        )
        assert entry.pipeline == "pre_publish"
        assert entry.status != "published"


# ---------------------------------------------------------------------------
# Teen content with critical keywords — immediate block (never publishes)
# ---------------------------------------------------------------------------


class TestTeenCriticalContentBlocked:
    """Critical-severity content from teens should still be blocked immediately
    (never published) even though teens normally get post-publish."""

    @pytest.mark.asyncio
    async def test_teen_critical_keyword_blocked_immediately(self, test_session):
        """Teen post with critical keyword should be rejected, not published."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="post",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="I want to commit suicide",
        )
        assert entry.status == "rejected"
        assert entry.pipeline == "post_publish"

    @pytest.mark.asyncio
    async def test_teen_csam_keyword_blocked(self, test_session):
        """Teen post with CSAM keyword should be rejected immediately."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="post",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="child porn is bad",
        )
        assert entry.status == "rejected"


# ---------------------------------------------------------------------------
# run_post_publish_moderation — async background check
# ---------------------------------------------------------------------------


class TestPostPublishModeration:
    """Tests for the async post-publish moderation function that runs
    after teen content is already published."""

    @pytest.mark.asyncio
    async def test_clean_content_stays_published(self, test_session):
        """Clean teen content should remain published after background check."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="post",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Great day at school today!",
        )
        assert entry.status == "published"

        result = await run_post_publish_moderation(
            db=test_session,
            queue_id=entry.id,
            content_text="Great day at school today!",
        )
        assert result.action == "keep"
        assert result.severity == PostPublishSeverity.NONE

        await test_session.refresh(entry)
        assert entry.status == "published"

    @pytest.mark.asyncio
    async def test_flagged_content_taken_down(self, test_session):
        """Flagged teen content should be taken down with parent alert."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="post",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Anyone want to try some drugs tonight",
        )
        # High-severity keyword doesn't block teens at submit time
        # it gets published and caught in post-publish review
        assert entry.status == "published"

        result = await run_post_publish_moderation(
            db=test_session,
            queue_id=entry.id,
            content_text="Anyone want to try some drugs tonight",
        )
        assert result.action == "takedown"
        assert result.severity in (
            PostPublishSeverity.HIGH,
            PostPublishSeverity.CRITICAL,
        )
        assert result.parent_alerted is True
        assert result.author_notified is True

        await test_session.refresh(entry)
        assert entry.status == "taken_down"

    @pytest.mark.asyncio
    async def test_severe_content_escalated(self, test_session):
        """Severe social risk content should be taken down and escalated."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="message",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Don't tell your parents, keep this between us, meet me alone",
        )

        result = await run_post_publish_moderation(
            db=test_session,
            queue_id=entry.id,
            content_text="Don't tell your parents, keep this between us, meet me alone",
        )
        assert result.action == "takedown"
        assert result.severity == PostPublishSeverity.CRITICAL
        assert result.account_restricted is True

        await test_session.refresh(entry)
        assert entry.status == "taken_down"

    @pytest.mark.asyncio
    async def test_medium_severity_flagged_for_review(self, test_session):
        """Medium-severity content should be flagged for human review
        but not automatically taken down."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="comment",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="You are so stupid",
        )

        result = await run_post_publish_moderation(
            db=test_session,
            queue_id=entry.id,
            content_text="You are so stupid",
        )
        # Medium severity for teens: flag for review, don't take down
        assert result.action == "flag"
        assert result.severity == PostPublishSeverity.MEDIUM

        await test_session.refresh(entry)
        assert entry.status == "flagged"

    @pytest.mark.asyncio
    async def test_takedown_creates_decision_record(self, test_session):
        """Takedown should create a ModerationDecision record."""
        content_id = uuid.uuid4()
        entry = await submit_for_moderation(
            db=test_session,
            content_type="post",
            content_id=content_id,
            author_age_tier="teen",
            content_text="Lets buy some cocaine and drugs tonight",
        )

        await run_post_publish_moderation(
            db=test_session,
            queue_id=entry.id,
            content_text="Lets buy some cocaine and drugs tonight",
        )

        decisions = (
            await test_session.execute(
                select(ModerationDecision).where(
                    ModerationDecision.queue_id == entry.id
                )
            )
        ).scalars().all()

        # Should have at least one takedown decision
        takedown_decisions = [d for d in decisions if d.action == "reject"]
        assert len(takedown_decisions) >= 1
        assert "[POST_PUBLISH_TAKEDOWN]" in takedown_decisions[0].reason

    @pytest.mark.asyncio
    async def test_post_publish_result_includes_latency(self, test_session):
        """PostPublishResult should track moderation latency."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="post",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Having a good time",
        )

        result = await run_post_publish_moderation(
            db=test_session,
            queue_id=entry.id,
            content_text="Having a good time",
        )
        assert result.latency_ms >= 0
        assert result.latency_ms < 60000  # Must be under 60s budget


# ---------------------------------------------------------------------------
# Auto-escalation for severe content
# ---------------------------------------------------------------------------


class TestAutoEscalation:
    """Severe content triggers immediate takedown + parent alert +
    potential account restriction."""

    @pytest.mark.asyncio
    async def test_grooming_triggers_account_restriction(self, test_session):
        """Grooming patterns should restrict the account."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="message",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="You're so mature for your age, keep this secret",
        )

        result = await run_post_publish_moderation(
            db=test_session,
            queue_id=entry.id,
            content_text="You're so mature for your age, keep this secret",
        )
        assert result.action == "takedown"
        assert result.account_restricted is True

    @pytest.mark.asyncio
    async def test_bullying_death_threat_triggers_escalation(self, test_session):
        """Death threats should trigger immediate takedown and escalation."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="comment",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="kys nobody likes you",
        )

        result = await run_post_publish_moderation(
            db=test_session,
            queue_id=entry.id,
            content_text="kys nobody likes you",
        )
        assert result.action == "takedown"
        assert result.severity == PostPublishSeverity.CRITICAL
        assert result.parent_alerted is True

    @pytest.mark.asyncio
    async def test_sexting_content_taken_down(self, test_session):
        """Sexting patterns should be taken down immediately."""
        entry = await submit_for_moderation(
            db=test_session,
            content_type="message",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Send me a pic without your clothes",
        )

        result = await run_post_publish_moderation(
            db=test_session,
            queue_id=entry.id,
            content_text="Send me a pic without your clothes",
        )
        assert result.action == "takedown"
        assert result.parent_alerted is True
        assert result.account_restricted is True


# ---------------------------------------------------------------------------
# PostPublishResult and PostPublishSeverity
# ---------------------------------------------------------------------------


class TestPostPublishResult:
    """Test the PostPublishResult dataclass properties."""

    def test_severity_enum_values(self):
        """PostPublishSeverity should have expected values."""
        assert PostPublishSeverity.NONE == "none"
        assert PostPublishSeverity.MEDIUM == "medium"
        assert PostPublishSeverity.HIGH == "high"
        assert PostPublishSeverity.CRITICAL == "critical"

    def test_result_defaults(self):
        """PostPublishResult should have sensible defaults."""
        result = PostPublishResult(
            action="keep",
            severity=PostPublishSeverity.NONE,
        )
        assert result.parent_alerted is False
        assert result.author_notified is False
        assert result.account_restricted is False
        assert result.latency_ms == 0.0
        assert result.matched_keywords == []
        assert result.risk_category is None
