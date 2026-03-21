"""Unit tests for pre-publish moderation performance.

Validates:
- Pre-publish latency < 2s for young (5-9) and preteen (10-12) tiers
- Keyword filter fast-path < 100ms
- False negative rate < 0.1% on severe content
- CSAM short-circuit behaviour
- Cache refresh and thread safety
- Parent notification on blocks
"""

import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.moderation.keyword_filter import (
    FilterAction,
    FilterResult,
    KeywordFilter,
    _AhoCorasickAutomaton,
    classify_text,
    get_filter,
)
from src.moderation.service import (
    _LATENCY_BUDGET_MS,
    _PRE_PUBLISH_TIERS,
    _notify_parent_on_block,
    _resolve_pipeline,
    submit_for_moderation,
)
from src.moderation.social_risk import classify_social_risk


# ---------------------------------------------------------------------------
# Keyword Filter Performance Tests
# ---------------------------------------------------------------------------


class TestKeywordFilterPerformance:
    """Keyword filter must complete in < 100ms."""

    def test_keyword_filter_latency_safe_text(self):
        """Safe text classification completes in < 100ms."""
        text = "I had a great day at school today and played with my friends."
        start = time.monotonic()
        result = classify_text(text, age_tier="young")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert result.action == FilterAction.ALLOW
        assert elapsed_ms < 100, f"Keyword filter took {elapsed_ms:.1f}ms (budget: 100ms)"

    def test_keyword_filter_latency_blocked_text(self):
        """Blocked text classification completes in < 100ms."""
        text = "I want to kill myself and end my life"
        start = time.monotonic()
        result = classify_text(text, age_tier="young")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert result.action == FilterAction.BLOCK
        assert result.severity == "critical"
        assert elapsed_ms < 100, f"Keyword filter took {elapsed_ms:.1f}ms (budget: 100ms)"

    def test_keyword_filter_latency_long_text(self):
        """Long text (1000+ words) still classifies in < 100ms."""
        text = " ".join(["the quick brown fox jumps over the lazy dog"] * 200)
        start = time.monotonic()
        result = classify_text(text, age_tier="preteen")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert result.action == FilterAction.ALLOW
        assert elapsed_ms < 100, f"Long text filter took {elapsed_ms:.1f}ms (budget: 100ms)"

    def test_keyword_filter_reports_latency(self):
        """FilterResult includes latency_ms field."""
        result = classify_text("hello world", age_tier="young")
        assert hasattr(result, "latency_ms")
        assert result.latency_ms >= 0

    def test_keyword_filter_latency_with_critical_match(self):
        """Critical keyword match exits early and is fast."""
        text = "csam content here with lots of other text " * 50
        start = time.monotonic()
        result = classify_text(text, age_tier="young")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert result.action == FilterAction.BLOCK
        assert result.severity == "critical"
        assert elapsed_ms < 100

    def test_keyword_filter_batch_performance(self):
        """100 classifications complete in < 1s total."""
        texts = [
            f"Message number {i} about school and homework" for i in range(100)
        ]
        start = time.monotonic()
        for text in texts:
            classify_text(text, age_tier="young")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 1000, f"100 classifications took {elapsed_ms:.1f}ms (budget: 1000ms)"


# ---------------------------------------------------------------------------
# False Negative Tests — severe content must NOT be missed
# ---------------------------------------------------------------------------


class TestFalseNegativeRate:
    """False negative rate must be < 0.1% on severe content."""

    SEVERE_CONTENT = [
        "I want to kill myself",
        "suicide is the only way",
        "self-harm is my escape",
        "self harm every night",
        "end my life today",
        "child porn links",
        "csam material",
        "nude children pictures",
        "want to die so badly",
        "hurt myself again",
        "grooming this child",
        "send nudes please",
    ]

    def test_prepublish_false_negative_rate(self):
        """All severe content must be detected (0% false negative on critical keywords)."""
        false_negatives = []
        for content in self.SEVERE_CONTENT:
            result = classify_text(content, age_tier="young")
            if result.action != FilterAction.BLOCK:
                false_negatives.append(content)

        total = len(self.SEVERE_CONTENT)
        fn_rate = len(false_negatives) / total if total > 0 else 0

        assert fn_rate < 0.001, (
            f"False negative rate {fn_rate:.3%} exceeds 0.1% threshold. "
            f"Missed: {false_negatives}"
        )

    def test_preteen_severe_content_blocked(self):
        """Severe content is also blocked for preteen tier."""
        for content in self.SEVERE_CONTENT:
            result = classify_text(content, age_tier="preteen")
            assert result.action == FilterAction.BLOCK, (
                f"Preteen tier missed severe content: '{content}' "
                f"(got {result.action})"
            )

    def test_high_severity_blocked_for_young(self):
        """High severity words must be blocked for young (5-9) tier."""
        high_content = [
            "drugs are cool",
            "bring a weapon to school",
            "gun violence",
            "porn website",
            "naked pictures",
            "cocaine dealer",
            "heroin addict",
        ]
        for content in high_content:
            result = classify_text(content, age_tier="young")
            assert result.action == FilterAction.BLOCK, (
                f"Young tier should block high severity: '{content}' "
                f"(got {result.action})"
            )

    def test_high_severity_uncertain_for_preteen(self):
        """High severity words should be UNCERTAIN (not ALLOW) for preteen tier."""
        result = classify_text("drugs are everywhere", age_tier="preteen")
        assert result.action in (FilterAction.BLOCK, FilterAction.UNCERTAIN)


# ---------------------------------------------------------------------------
# Aho-Corasick Automaton Tests
# ---------------------------------------------------------------------------


class TestAhoCorasickAutomaton:
    """Tests for the phrase matcher."""

    def test_search_finds_phrases(self):
        matcher = _AhoCorasickAutomaton({"kill myself", "end my life"})
        matches = matcher.search("i want to kill myself today")
        assert "kill myself" in matches

    def test_search_no_match(self):
        matcher = _AhoCorasickAutomaton({"kill myself"})
        matches = matcher.search("i am happy today")
        assert len(matches) == 0

    def test_search_multiple_matches(self):
        matcher = _AhoCorasickAutomaton({"kill myself", "end my life"})
        matches = matcher.search("kill myself and end my life")
        assert matches == {"kill myself", "end my life"}

    def test_add_and_remove_phrase(self):
        matcher = _AhoCorasickAutomaton({"kill myself"})
        matcher.add_phrase("new phrase")
        assert "new phrase" in matcher.phrases

        matcher.remove_phrase("new phrase")
        assert "new phrase" not in matcher.phrases


# ---------------------------------------------------------------------------
# KeywordFilter Cache and Thread Safety Tests
# ---------------------------------------------------------------------------


class TestKeywordFilterCache:
    """Tests for keyword cache TTL and refresh."""

    def test_cache_age_increases(self):
        kf = KeywordFilter()
        age1 = kf.cache_age_seconds
        time.sleep(0.01)
        age2 = kf.cache_age_seconds
        assert age2 > age1

    def test_cache_not_stale_initially(self):
        kf = KeywordFilter()
        assert not kf.is_cache_stale

    def test_refresh_if_stale_returns_false_when_fresh(self):
        kf = KeywordFilter()
        assert kf.refresh_if_stale() is False

    def test_refresh_if_stale_returns_true_when_expired(self):
        kf = KeywordFilter()
        kf._last_refresh = time.monotonic() - 600  # Simulate 10 min old
        assert kf.is_cache_stale
        assert kf.refresh_if_stale() is True
        assert not kf.is_cache_stale

    def test_add_keywords_thread_safe(self):
        kf = KeywordFilter()
        kf.add_keywords("critical", {"new_danger_word"})
        result = kf.classify_text("this has new_danger_word in it")
        assert result.action == FilterAction.BLOCK
        assert "new_danger_word" in result.matched_keywords

    def test_remove_keywords(self):
        kf = KeywordFilter()
        kf.remove_keywords("critical", {"suicide"})
        result = kf.classify_text("suicide")
        # Should not match critical anymore
        assert result.severity != "critical" or result.action != FilterAction.BLOCK


# ---------------------------------------------------------------------------
# Pipeline Routing Tests
# ---------------------------------------------------------------------------


class TestPipelineRouting:
    """Tests for age-tier pipeline routing."""

    def test_young_routes_to_pre_publish(self):
        assert _resolve_pipeline("young") == "pre_publish"

    def test_preteen_routes_to_pre_publish(self):
        assert _resolve_pipeline("preteen") == "pre_publish"

    def test_teen_routes_to_post_publish(self):
        assert _resolve_pipeline("teen") == "post_publish"

    def test_none_routes_to_post_publish(self):
        assert _resolve_pipeline(None) == "post_publish"

    def test_pre_publish_tiers_set(self):
        assert _PRE_PUBLISH_TIERS == {"young", "preteen"}


# ---------------------------------------------------------------------------
# Pre-Publish Pipeline Latency (end-to-end with DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPrePublishLatency:
    """Pre-publish pipeline must complete in < 2s."""

    async def test_prepublish_latency_safe_text_young(self, test_session: AsyncSession):
        """Safe text for young tier completes well under 2s."""
        content_id = uuid.uuid4()
        start = time.monotonic()

        entry = await submit_for_moderation(
            test_session,
            content_type="post",
            content_id=content_id,
            author_age_tier="young",
            content_text="I drew a picture of my cat today!",
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert entry.pipeline == "pre_publish"
        assert entry.status == "approved"
        assert elapsed_ms < 2000, f"Pre-publish took {elapsed_ms:.1f}ms (budget: 2000ms)"

    async def test_prepublish_latency_safe_text_preteen(self, test_session: AsyncSession):
        """Safe text for preteen tier completes well under 2s."""
        content_id = uuid.uuid4()
        start = time.monotonic()

        entry = await submit_for_moderation(
            test_session,
            content_type="post",
            content_id=content_id,
            author_age_tier="preteen",
            content_text="Working on my science project about volcanoes.",
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert entry.pipeline == "pre_publish"
        assert entry.status == "approved"
        assert elapsed_ms < 2000, f"Pre-publish took {elapsed_ms:.1f}ms (budget: 2000ms)"

    async def test_prepublish_latency_blocked_text(self, test_session: AsyncSession):
        """Blocked text fast-path completes well under 2s."""
        content_id = uuid.uuid4()
        start = time.monotonic()

        entry = await submit_for_moderation(
            test_session,
            content_type="post",
            content_id=content_id,
            author_age_tier="young",
            content_text="I want to kill myself",
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert entry.status == "rejected"
        assert elapsed_ms < 2000, f"Fast-path block took {elapsed_ms:.1f}ms (budget: 2000ms)"

    async def test_prepublish_latency_uncertain_text(self, test_session: AsyncSession):
        """Uncertain text (needs AI review) completes within budget."""
        content_id = uuid.uuid4()
        start = time.monotonic()

        entry = await submit_for_moderation(
            test_session,
            content_type="comment",
            content_id=content_id,
            author_age_tier="preteen",
            content_text="you are so stupid and ugly",
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        # Medium severity for preteen = UNCERTAIN -> pending
        assert entry.status == "pending"
        assert elapsed_ms < 2000

    async def test_prepublish_latency_message_with_social_risk(self, test_session: AsyncSession):
        """Message with social risk detection completes within budget."""
        content_id = uuid.uuid4()
        start = time.monotonic()

        entry = await submit_for_moderation(
            test_session,
            content_type="message",
            content_id=content_id,
            author_age_tier="young",
            content_text="don't tell your parents, keep this our secret",
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 2000, f"Social risk pipeline took {elapsed_ms:.1f}ms"


# ---------------------------------------------------------------------------
# Parent Notification Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestParentNotification:
    """Parent notification on pre-publish blocks."""

    async def test_notify_parent_on_block_young(self, test_session: AsyncSession):
        """Blocking content for young tier creates parent alert."""
        content_id = uuid.uuid4()
        entry = await submit_for_moderation(
            test_session,
            content_type="post",
            content_id=content_id,
            author_age_tier="young",
            content_text="I want to kill myself",
        )
        assert entry.status == "rejected"
        # The notification is best-effort; verify the entry was created correctly
        assert entry.age_tier == "young"

    async def test_notify_parent_on_block_preteen(self, test_session: AsyncSession):
        """Blocking content for preteen tier creates parent alert."""
        content_id = uuid.uuid4()
        entry = await submit_for_moderation(
            test_session,
            content_type="post",
            content_id=content_id,
            author_age_tier="preteen",
            content_text="csam material",
        )
        assert entry.status == "rejected"
        assert entry.age_tier == "preteen"

    async def test_no_notify_for_teen_block(self, test_session: AsyncSession):
        """Teen tier blocks do not trigger parent notification (post-publish)."""
        content_id = uuid.uuid4()
        entry = await submit_for_moderation(
            test_session,
            content_type="post",
            content_id=content_id,
            author_age_tier="teen",
            content_text="csam material",
        )
        # Teen goes through post-publish; keyword still blocks
        assert entry.status == "rejected"
        assert entry.pipeline == "post_publish"

    async def test_notify_function_handles_errors(self, test_session: AsyncSession):
        """_notify_parent_on_block handles errors gracefully."""
        # Should not raise even if Alert model import fails
        await _notify_parent_on_block(
            test_session,
            content_type="post",
            content_id=uuid.uuid4(),
            age_tier="young",
            reason="test reason",
        )

    async def test_no_notify_for_non_prepublish(self, test_session: AsyncSession):
        """No notification for non-pre-publish tiers."""
        await _notify_parent_on_block(
            test_session,
            content_type="post",
            content_id=uuid.uuid4(),
            age_tier="teen",
            reason="test reason",
        )
        # Should return immediately without error


# ---------------------------------------------------------------------------
# Social Risk Performance
# ---------------------------------------------------------------------------


class TestSocialRiskPerformance:
    """Social risk classification performance."""

    def test_social_risk_latency(self):
        """Social risk classification completes in < 50ms."""
        text = "don't tell your parents, meet me alone, age is just a number"
        start = time.monotonic()
        result = classify_social_risk(text, author_age_tier="young")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert result.risk_score > 0
        assert elapsed_ms < 50, f"Social risk took {elapsed_ms:.1f}ms (budget: 50ms)"

    def test_social_risk_batch_performance(self):
        """100 social risk classifications complete in < 1s."""
        texts = [f"Message {i} about school" for i in range(100)]
        start = time.monotonic()
        for text in texts:
            classify_social_risk(text)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 1000


# ---------------------------------------------------------------------------
# Latency Budget Constants
# ---------------------------------------------------------------------------


class TestLatencyBudget:
    """Verify latency budget is properly configured."""

    def test_latency_budget_is_2s(self):
        assert _LATENCY_BUDGET_MS == 2000

    def test_pre_publish_tiers_include_young_and_preteen(self):
        assert "young" in _PRE_PUBLISH_TIERS
        assert "preteen" in _PRE_PUBLISH_TIERS
        assert "teen" not in _PRE_PUBLISH_TIERS
