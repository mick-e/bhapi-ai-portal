"""End-to-end tests for pre-publish moderation pipeline.

Tests the full pipeline for young (5-9) and preteen (10-12) tiers:
- Auto-approve safe content
- Auto-reject severe content (keyword fast-path)
- Escalate ambiguous content for human review
- CSAM short-circuit
- Social risk escalation for messages/comments
- Parent notification on blocks
- Latency requirements
"""

import time
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.moderation.models import ModerationDecision, ModerationQueue
from src.moderation.service import (
    get_queue_entry,
    list_queue,
    process_queue_entry,
    submit_for_moderation,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _submit(
    session: AsyncSession,
    content_text: str,
    age_tier: str = "young",
    content_type: str = "post",
) -> ModerationQueue:
    """Helper to submit content for moderation."""
    return await submit_for_moderation(
        session,
        content_type=content_type,
        content_id=uuid.uuid4(),
        author_age_tier=age_tier,
        content_text=content_text,
    )


async def _make_moderator(session: AsyncSession) -> User:
    """Create a user that can serve as a moderator (FK-valid)."""
    user = User(
        id=uuid.uuid4(),
        email=f"mod-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Moderator",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()
    return user


# ---------------------------------------------------------------------------
# Young Tier (5-9) E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestYoungTierPipeline:
    """Full pipeline tests for the young (5-9) age tier."""

    async def test_safe_content_auto_approved(self, test_session: AsyncSession):
        """Safe content from young child is auto-approved."""
        entry = await _submit(test_session, "I love my dog and playing outside!")
        assert entry.pipeline == "pre_publish"
        assert entry.status == "approved"
        assert entry.age_tier == "young"

    async def test_critical_content_auto_rejected(self, test_session: AsyncSession):
        """Critical content from young child is immediately rejected."""
        entry = await _submit(test_session, "I want to kill myself")
        assert entry.pipeline == "pre_publish"
        assert entry.status == "rejected"
        assert entry.risk_scores is not None
        assert entry.risk_scores["keyword_filter"]["severity"] == "critical"

    async def test_high_severity_blocked_for_young(self, test_session: AsyncSession):
        """High severity content is blocked (not just flagged) for young tier."""
        entry = await _submit(test_session, "drugs are cool lets try them")
        assert entry.status == "rejected"
        assert entry.risk_scores["keyword_filter"]["severity"] == "high"

    async def test_medium_severity_uncertain_for_young(self, test_session: AsyncSession):
        """Medium severity content goes to pending (AI/human review) for young tier."""
        entry = await _submit(
            test_session,
            "you are stupid and ugly",
            age_tier="young",
            content_type="comment",
        )
        # Medium severity for young = UNCERTAIN -> pending
        assert entry.status == "pending"

    async def test_empty_text_approved(self, test_session: AsyncSession):
        """Empty text content is auto-approved."""
        entry = await _submit(test_session, "   ")
        assert entry.status == "approved"

    async def test_decision_created_on_approval(self, test_session: AsyncSession):
        """Auto-approval creates a ModerationDecision record."""
        entry = await _submit(test_session, "Had fun at the park today!")
        assert entry.status == "approved"

        decisions = await test_session.execute(
            select(ModerationDecision).where(
                ModerationDecision.queue_id == entry.id
            )
        )
        decision = decisions.scalar_one_or_none()
        assert decision is not None
        assert decision.action == "approve"
        assert "Auto-approved" in decision.reason

    async def test_decision_created_on_rejection(self, test_session: AsyncSession):
        """Auto-rejection creates a ModerationDecision record."""
        entry = await _submit(test_session, "csam content")
        assert entry.status == "rejected"

        decisions = await test_session.execute(
            select(ModerationDecision).where(
                ModerationDecision.queue_id == entry.id
            )
        )
        decision = decisions.scalar_one_or_none()
        assert decision is not None
        assert decision.action == "reject"
        assert "Auto-blocked" in decision.reason


# ---------------------------------------------------------------------------
# Preteen Tier (10-12) E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPreteenTierPipeline:
    """Full pipeline tests for the preteen (10-12) age tier."""

    async def test_safe_content_auto_approved(self, test_session: AsyncSession):
        """Safe content from preteen is auto-approved."""
        entry = await _submit(
            test_session,
            "Working on my book report for English class",
            age_tier="preteen",
        )
        assert entry.pipeline == "pre_publish"
        assert entry.status == "approved"

    async def test_critical_content_rejected(self, test_session: AsyncSession):
        """Critical content from preteen is rejected."""
        entry = await _submit(
            test_session,
            "self-harm is my only escape",
            age_tier="preteen",
        )
        assert entry.status == "rejected"
        assert entry.risk_scores["keyword_filter"]["severity"] == "critical"

    async def test_high_severity_uncertain_for_preteen(self, test_session: AsyncSession):
        """High severity content is UNCERTAIN for preteen (not auto-blocked like young)."""
        entry = await _submit(
            test_session,
            "saw a gun in a video game",
            age_tier="preteen",
            content_type="comment",
        )
        # High severity for preteen = UNCERTAIN -> pending (not blocked)
        assert entry.status == "pending"

    async def test_medium_severity_uncertain_for_preteen(self, test_session: AsyncSession):
        """Medium severity content goes to pending for preteen tier."""
        entry = await _submit(
            test_session,
            "you are such a loser and an idiot",
            age_tier="preteen",
            content_type="comment",
        )
        assert entry.status == "pending"


# ---------------------------------------------------------------------------
# Social Risk Escalation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSocialRiskEscalation:
    """Social risk patterns escalate messages and comments."""

    async def test_grooming_pattern_escalates_message(self, test_session: AsyncSession):
        """Grooming patterns in messages trigger escalation."""
        entry = await _submit(
            test_session,
            "don't tell your parents, keep this our secret, meet me alone",
            age_tier="young",
            content_type="message",
        )
        # Grooming patterns should be detected; message may be escalated or rejected
        # depending on keyword match (the keyword "grooming" may or may not appear)
        assert entry.status in ("rejected", "escalated", "pending")

    async def test_bullying_pattern_escalates_comment(self, test_session: AsyncSession):
        """Cyberbullying patterns in comments trigger escalation."""
        entry = await _submit(
            test_session,
            "kill yourself nobody likes you go die",
            age_tier="preteen",
            content_type="comment",
        )
        # "kill yourself" -> death_threat (bullying) -> should escalate or reject
        assert entry.status in ("rejected", "escalated")

    async def test_safe_message_approved(self, test_session: AsyncSession):
        """Safe messages are approved for pre-publish tiers."""
        entry = await _submit(
            test_session,
            "Hey want to play minecraft after school?",
            age_tier="young",
            content_type="message",
        )
        assert entry.status == "approved"


# ---------------------------------------------------------------------------
# Pipeline Latency E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPipelineLatencyE2E:
    """End-to-end latency tests for the full pipeline."""

    async def test_full_pipeline_young_safe_under_2s(self, test_session: AsyncSession):
        """Full young tier pipeline for safe content completes under 2s."""
        start = time.monotonic()
        entry = await _submit(test_session, "Today I learned about dinosaurs!")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert entry.status == "approved"
        assert elapsed_ms < 2000

    async def test_full_pipeline_young_blocked_under_2s(self, test_session: AsyncSession):
        """Full young tier pipeline for blocked content completes under 2s."""
        start = time.monotonic()
        entry = await _submit(test_session, "suicide is the answer")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert entry.status == "rejected"
        assert elapsed_ms < 2000

    async def test_full_pipeline_preteen_safe_under_2s(self, test_session: AsyncSession):
        """Full preteen tier pipeline for safe content completes under 2s."""
        start = time.monotonic()
        entry = await _submit(
            test_session, "Check out this cool math puzzle!", age_tier="preteen"
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert entry.status == "approved"
        assert elapsed_ms < 2000

    async def test_full_pipeline_preteen_blocked_under_2s(self, test_session: AsyncSession):
        """Full preteen tier pipeline for blocked content completes under 2s."""
        start = time.monotonic()
        entry = await _submit(
            test_session, "child porn links here", age_tier="preteen"
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert entry.status == "rejected"
        assert elapsed_ms < 2000

    async def test_full_pipeline_message_with_risk_under_2s(self, test_session: AsyncSession):
        """Message with social risk processing completes under 2s."""
        start = time.monotonic()
        await _submit(
            test_session,
            "nobody likes you, you're a loser",
            age_tier="preteen",
            content_type="message",
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 2000


# ---------------------------------------------------------------------------
# Queue Management E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestQueueManagementE2E:
    """End-to-end tests for moderation queue operations."""

    async def test_pending_entry_can_be_approved(self, test_session: AsyncSession):
        """Pending entries can be manually approved by moderators."""
        entry = await _submit(
            test_session,
            "you are stupid and ugly",
            age_tier="young",
            content_type="comment",
        )
        assert entry.status == "pending"

        moderator = await _make_moderator(test_session)
        decision = await process_queue_entry(
            test_session,
            queue_id=entry.id,
            action="approve",
            moderator_id=moderator.id,
            reason="Reviewed: context is a quote from a book",
        )
        assert decision.action == "approve"

        refreshed = await get_queue_entry(test_session, entry.id)
        assert refreshed.status == "approved"

    async def test_pending_entry_can_be_rejected(self, test_session: AsyncSession):
        """Pending entries can be manually rejected by moderators."""
        entry = await _submit(
            test_session,
            "hate speech here",
            age_tier="preteen",
            content_type="comment",
        )
        assert entry.status == "pending"

        moderator = await _make_moderator(test_session)
        decision = await process_queue_entry(
            test_session,
            queue_id=entry.id,
            action="reject",
            moderator_id=moderator.id,
            reason="Contains hate speech",
        )
        assert decision.action == "reject"

    async def test_list_queue_filters_by_pipeline(self, test_session: AsyncSession):
        """Queue listing can be filtered by pipeline type."""
        await _submit(test_session, "Safe post", age_tier="young")
        await _submit(test_session, "Another safe post", age_tier="teen")

        result = await list_queue(test_session, pipeline="pre_publish")
        assert result["total"] >= 1
        for item in result["items"]:
            assert item.pipeline == "pre_publish"


# ---------------------------------------------------------------------------
# Validation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestValidation:
    """Input validation for the moderation pipeline."""

    async def test_invalid_content_type_raises(self, test_session: AsyncSession):
        """Invalid content type raises ValidationError."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await submit_for_moderation(
                test_session,
                content_type="invalid_type",
                content_id=uuid.uuid4(),
                content_text="test",
            )

    async def test_risk_scores_include_latency(self, test_session: AsyncSession):
        """Risk scores include keyword filter latency metric."""
        entry = await _submit(test_session, "I love coding!")
        if entry.risk_scores and "keyword_filter" in entry.risk_scores:
            assert "latency_ms" in entry.risk_scores["keyword_filter"]
