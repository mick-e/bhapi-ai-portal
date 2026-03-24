"""Unit tests + performance tests for the keyword filter engine."""

import threading
import time
import tracemalloc

import pytest

from src.moderation.keyword_filter import (
    FilterAction,
    FilterResult,
    KeywordFilter,
    classify_text,
    get_filter,
)

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


class TestNormalization:
    """Tests for text normalization."""

    def test_case_insensitive(self):
        """Uppercase text is normalized to lowercase."""
        f = KeywordFilter()
        assert f._normalize("HELLO WORLD") == "hello world"

    def test_mixed_case(self):
        """Mixed case is normalized."""
        f = KeywordFilter()
        assert f._normalize("HeLLo WoRLd") == "hello world"

    def test_accent_stripping(self):
        """Accented characters are stripped to ASCII equivalents."""
        f = KeywordFilter()
        assert f._normalize("cafe\u0301") == "cafe"
        assert f._normalize("\u00e9l\u00e8ve") == "eleve"

    def test_whitespace_collapse(self):
        """Multiple spaces and tabs collapse to single space."""
        f = KeywordFilter()
        assert f._normalize("hello   world") == "hello world"
        assert f._normalize("hello\t\tworld") == "hello world"
        assert f._normalize("  hello  ") == "hello"

    def test_newline_handling(self):
        """Newlines are collapsed to spaces."""
        f = KeywordFilter()
        assert f._normalize("hello\nworld") == "hello world"
        assert f._normalize("hello\r\nworld") == "hello world"


# ---------------------------------------------------------------------------
# Critical keywords
# ---------------------------------------------------------------------------


class TestCriticalKeywords:
    """Tests for critical severity keyword detection."""

    def test_single_critical_word(self):
        """Single critical word triggers BLOCK."""
        result = classify_text("I am thinking about suicide")
        assert result.action == FilterAction.BLOCK
        assert result.severity == "critical"
        assert "suicide" in result.matched_keywords

    def test_critical_phrase(self):
        """Multi-word critical phrase detected."""
        result = classify_text("I want to kill myself tonight")
        assert result.action == FilterAction.BLOCK
        assert result.severity == "critical"
        assert "kill myself" in result.matched_keywords

    def test_critical_case_insensitive(self):
        """Critical keywords match regardless of case."""
        result = classify_text("SUICIDE is not the answer")
        assert result.action == FilterAction.BLOCK
        assert result.severity == "critical"

    def test_critical_with_accents(self):
        """Critical keywords match after accent stripping."""
        result = classify_text("su\u00eecide")  # suîcide -> suicide
        assert result.action == FilterAction.BLOCK

    def test_critical_confidence_high(self):
        """Critical matches have high confidence."""
        result = classify_text("csam detected")
        assert result.confidence == 0.95

    def test_critical_blocks_all_age_tiers(self):
        """Critical keywords block regardless of age tier."""
        for tier in ("young", "preteen", "teen", None):
            result = classify_text("suicide", age_tier=tier)
            assert result.action == FilterAction.BLOCK

    def test_want_to_die_phrase(self):
        """'want to die' phrase detected as critical."""
        result = classify_text("i just want to die")
        assert result.action == FilterAction.BLOCK
        assert "want to die" in result.matched_keywords

    def test_self_harm_variants(self):
        """Both 'self-harm' and 'self harm' detected."""
        r1 = classify_text("self-harm is dangerous")
        assert r1.action == FilterAction.BLOCK
        # The hyphenated version normalizes differently but the word
        # "self-harm" won't split to match "self harm" set entry.
        # Check the unhyphenated version too.
        r2 = classify_text("self harm is dangerous")
        assert r2.action == FilterAction.BLOCK


# ---------------------------------------------------------------------------
# High severity keywords
# ---------------------------------------------------------------------------


class TestHighKeywords:
    """Tests for high severity keyword detection."""

    def test_high_word_preteen(self):
        """High keyword for preteen returns UNCERTAIN."""
        result = classify_text("I found some porn online", age_tier="preteen")
        assert result.action == FilterAction.UNCERTAIN
        assert result.severity == "high"

    def test_high_word_teen(self):
        """High keyword for teen returns UNCERTAIN."""
        result = classify_text("someone is sexting me", age_tier="teen")
        assert result.action == FilterAction.UNCERTAIN
        assert result.severity == "high"

    def test_high_word_young_blocks(self):
        """High keyword for young tier auto-blocks."""
        result = classify_text("I saw a gun", age_tier="young")
        assert result.action == FilterAction.BLOCK
        assert result.severity == "high"
        assert result.confidence == 0.85

    def test_high_word_no_age_tier(self):
        """High keyword without age tier returns UNCERTAIN."""
        result = classify_text("drugs are bad")
        assert result.action == FilterAction.UNCERTAIN
        assert result.severity == "high"

    def test_high_phrase_detected(self):
        """Multi-word high phrase ('knife attack') detected."""
        result = classify_text("there was a knife attack today")
        assert result.action == FilterAction.UNCERTAIN
        assert "knife attack" in result.matched_keywords

    def test_high_confidence(self):
        """High severity matches have appropriate confidence."""
        result = classify_text("weapon found", age_tier="teen")
        assert result.confidence == 0.7


# ---------------------------------------------------------------------------
# Medium severity keywords
# ---------------------------------------------------------------------------


class TestMediumKeywords:
    """Tests for medium severity keyword detection."""

    def test_medium_young_uncertain(self):
        """Medium keyword for young child triggers UNCERTAIN."""
        result = classify_text("you are so stupid", age_tier="young")
        assert result.action == FilterAction.UNCERTAIN
        assert result.severity == "medium"

    def test_medium_preteen_uncertain(self):
        """Medium keyword for preteen triggers UNCERTAIN."""
        result = classify_text("what a loser", age_tier="preteen")
        assert result.action == FilterAction.UNCERTAIN
        assert result.severity == "medium"

    def test_medium_teen_allows(self):
        """Medium keyword for teen is ALLOW (informational)."""
        result = classify_text("that was dumb", age_tier="teen")
        assert result.action == FilterAction.ALLOW
        assert result.severity == "medium"
        assert result.confidence == 0.6

    def test_medium_no_age_tier_allows(self):
        """Medium keyword without age tier is ALLOW."""
        result = classify_text("i hate mondays")
        assert result.action == FilterAction.ALLOW
        assert result.severity == "medium"

    def test_medium_phrase_detected(self):
        """Multi-word medium phrase detected."""
        result = classify_text("can you give me the homework answers", age_tier="young")
        assert result.action == FilterAction.UNCERTAIN
        assert "homework answers" in result.matched_keywords

    def test_medium_test_answers(self):
        """'test answers' phrase detected."""
        result = classify_text("share your test answers", age_tier="preteen")
        assert result.action == FilterAction.UNCERTAIN
        assert "test answers" in result.matched_keywords


# ---------------------------------------------------------------------------
# No matches / edge cases
# ---------------------------------------------------------------------------


class TestNoMatchesAndEdgeCases:
    """Tests for clean text and edge cases."""

    def test_clean_text_allows(self):
        """Clean text returns ALLOW with no matches."""
        result = classify_text("I had a great day at school today")
        assert result.action == FilterAction.ALLOW
        assert result.matched_keywords == []
        assert result.severity is None
        assert result.confidence == 0.9

    def test_empty_string(self):
        """Empty string returns ALLOW."""
        result = classify_text("")
        assert result.action == FilterAction.ALLOW
        assert result.matched_keywords == []

    def test_whitespace_only(self):
        """Whitespace-only string returns ALLOW."""
        result = classify_text("   \t\n  ")
        assert result.action == FilterAction.ALLOW

    def test_single_character(self):
        """Single character text returns ALLOW."""
        result = classify_text("a")
        assert result.action == FilterAction.ALLOW

    def test_very_long_clean_text(self):
        """Long clean text returns ALLOW."""
        text = "This is a perfectly normal sentence. " * 100
        result = classify_text(text)
        assert result.action == FilterAction.ALLOW

    def test_numbers_only(self):
        """Numeric text returns ALLOW."""
        result = classify_text("12345 67890")
        assert result.action == FilterAction.ALLOW

    def test_special_characters(self):
        """Special characters don't cause errors."""
        result = classify_text("!@#$%^&*()_+-=[]{}|;':\",./<>?")
        assert result.action == FilterAction.ALLOW


# ---------------------------------------------------------------------------
# Age tier sensitivity
# ---------------------------------------------------------------------------


class TestAgeTierSensitivity:
    """Tests for age-tier-specific sensitivity adjustments."""

    def test_young_most_restrictive(self):
        """Young tier is the most restrictive."""
        result = classify_text("I saw a gun", age_tier="young")
        assert result.action == FilterAction.BLOCK

    def test_preteen_medium_sensitivity(self):
        """Preteen triggers UNCERTAIN for medium keywords."""
        result = classify_text("you are ugly", age_tier="preteen")
        assert result.action == FilterAction.UNCERTAIN

    def test_teen_least_restrictive(self):
        """Teen allows medium severity keywords."""
        result = classify_text("that was stupid", age_tier="teen")
        assert result.action == FilterAction.ALLOW

    def test_none_age_tier_defaults(self):
        """None age tier uses default (less restrictive) behavior."""
        result = classify_text("stupid idea")
        assert result.action == FilterAction.ALLOW
        assert result.severity == "medium"


# ---------------------------------------------------------------------------
# Singleton and module-level function
# ---------------------------------------------------------------------------


class TestSingleton:
    """Tests for the module-level singleton."""

    def test_classify_text_function_works(self):
        """Module-level classify_text works correctly."""
        result = classify_text("normal text here")
        assert result.action == FilterAction.ALLOW

    def test_get_filter_returns_instance(self):
        """get_filter returns a KeywordFilter instance."""
        f = get_filter()
        assert isinstance(f, KeywordFilter)

    def test_singleton_consistent(self):
        """Multiple calls to get_filter return the same instance."""
        f1 = get_filter()
        f2 = get_filter()
        assert f1 is f2


# ---------------------------------------------------------------------------
# Custom keywords
# ---------------------------------------------------------------------------


class TestCustomKeywords:
    """Tests for adding/removing custom keywords."""

    def test_add_custom_critical_word(self):
        """Adding custom critical keyword triggers BLOCK."""
        f = KeywordFilter()
        f.add_keywords("critical", {"customdanger"})
        result = f.classify_text("customdanger detected")
        assert result.action == FilterAction.BLOCK

    def test_add_custom_phrase(self):
        """Adding custom multi-word phrase works."""
        f = KeywordFilter()
        f.add_keywords("high", {"very bad thing"})
        result = f.classify_text("this is a very bad thing to do")
        assert result.action == FilterAction.UNCERTAIN
        assert "very bad thing" in result.matched_keywords

    def test_remove_keyword(self):
        """Removing a keyword prevents matching."""
        f = KeywordFilter()
        f.remove_keywords("medium", {"stupid"})
        result = f.classify_text("that is stupid")
        # Should not match "stupid" anymore (but may match other medium words)
        assert "stupid" not in result.matched_keywords

    def test_add_invalid_severity_raises(self):
        """Adding keyword with invalid severity raises ValueError."""
        f = KeywordFilter()
        with pytest.raises(ValueError, match="Invalid severity"):
            f.add_keywords("extreme", {"badword"})

    def test_remove_invalid_severity_raises(self):
        """Removing keyword with invalid severity raises ValueError."""
        f = KeywordFilter()
        with pytest.raises(ValueError, match="Invalid severity"):
            f.remove_keywords("extreme", {"badword"})


# ---------------------------------------------------------------------------
# FilterResult dataclass
# ---------------------------------------------------------------------------


class TestFilterResult:
    """Tests for the FilterResult dataclass."""

    def test_default_values(self):
        """FilterResult defaults are sensible."""
        r = FilterResult(action=FilterAction.ALLOW)
        assert r.matched_keywords == []
        assert r.severity is None
        assert r.confidence == 0.0

    def test_all_fields(self):
        """FilterResult stores all fields."""
        r = FilterResult(
            action=FilterAction.BLOCK,
            matched_keywords=["bad"],
            severity="critical",
            confidence=0.95,
        )
        assert r.action == FilterAction.BLOCK
        assert r.matched_keywords == ["bad"]
        assert r.severity == "critical"
        assert r.confidence == 0.95


# ---------------------------------------------------------------------------
# FilterAction enum
# ---------------------------------------------------------------------------


class TestFilterAction:
    """Tests for the FilterAction enum."""

    def test_str_values(self):
        """FilterAction values are strings."""
        assert FilterAction.BLOCK == "block"
        assert FilterAction.ALLOW == "allow"
        assert FilterAction.UNCERTAIN == "uncertain"

    def test_str_enum(self):
        """FilterAction is a StrEnum."""
        assert isinstance(FilterAction.BLOCK, str)


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    """Performance tests ensuring <100ms classification."""

    def test_1000_texts_under_100ms(self):
        """Classifying 1000 different texts completes in <100ms."""
        texts = [f"This is test message number {i} with content" for i in range(1000)]
        start = time.perf_counter()
        for text in texts:
            classify_text(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, f"1000 classifications took {elapsed_ms:.1f}ms"

    def test_large_text_under_50ms(self):
        """A 10KB text classifies in <50ms (relaxed for CI under load)."""
        text = "a " * 5000  # ~10KB
        # Warm up to avoid cold-start penalty
        classify_text("warm up")
        start = time.perf_counter()
        classify_text(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50, f"10KB text took {elapsed_ms:.1f}ms"

    def test_repeated_no_degradation(self):
        """10000 repeated classifications don't degrade performance."""
        text = "some normal text with no keywords at all"
        # Warm up
        classify_text(text)
        start = time.perf_counter()
        for _ in range(10000):
            classify_text(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        per_call = elapsed_ms / 10000
        assert per_call < 0.1, f"Per-call avg: {per_call:.4f}ms"

    def test_concurrent_classification(self):
        """Concurrent classification in multiple threads works correctly."""
        results = []
        errors = []

        def classify_in_thread(text, expected_action):
            try:
                result = classify_text(text)
                results.append((result.action, expected_action))
            except Exception as e:
                errors.append(e)

        threads = []
        cases = [
            ("normal text", FilterAction.ALLOW),
            ("suicide note", FilterAction.BLOCK),
            ("someone has drugs", FilterAction.UNCERTAIN),
            ("clean message", FilterAction.ALLOW),
            ("child porn", FilterAction.BLOCK),
        ]
        for text, expected in cases * 10:  # 50 threads
            t = threading.Thread(target=classify_in_thread, args=(text, expected))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Thread errors: {errors}"
        assert len(results) == 50
        for actual, expected in results:
            assert actual == expected

    def test_memory_stable(self):
        """Memory doesn't grow significantly with repeated use."""
        tracemalloc.start()
        # Baseline
        for _ in range(1000):
            classify_text("baseline text")
        _, baseline_peak = tracemalloc.get_traced_memory()

        tracemalloc.reset_peak()
        for _ in range(10000):
            classify_text("more text to classify with various words")
        _, after_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory should not grow more than 1MB
        growth = after_peak - baseline_peak
        assert growth < 1_000_000, f"Memory grew by {growth} bytes"

    def test_keyword_match_text_under_1ms(self):
        """Text with a keyword match classifies in <1ms."""
        text = "someone mentioned suicide today"
        start = time.perf_counter()
        result = classify_text(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert result.action == FilterAction.BLOCK
        assert elapsed_ms < 1, f"Keyword match took {elapsed_ms:.4f}ms"
