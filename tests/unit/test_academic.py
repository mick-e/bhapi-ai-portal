"""Unit tests for AI Academic Integrity — intent classification and study hours."""

from datetime import datetime, timezone

import pytest

from src.analytics.academic import (
    DOING_PATTERNS,
    LEARNING_PATTERNS,
    STUDY_HOUR_DEFAULTS,
    classify_prompt_intent,
    is_study_hours,
)


# ---------------------------------------------------------------------------
# classify_prompt_intent
# ---------------------------------------------------------------------------


class TestClassifyPromptIntent:
    """Tests for prompt intent classification accuracy."""

    @pytest.mark.asyncio
    async def test_learning_explain(self):
        result = await classify_prompt_intent("Can you explain photosynthesis?")
        assert result == "learning"

    @pytest.mark.asyncio
    async def test_learning_how_does(self):
        result = await classify_prompt_intent("How does gravity work?")
        assert result == "learning"

    @pytest.mark.asyncio
    async def test_learning_what_is(self):
        result = await classify_prompt_intent("What is the Pythagorean theorem?")
        assert result == "learning"

    @pytest.mark.asyncio
    async def test_learning_teach_me(self):
        result = await classify_prompt_intent("Teach me about the French Revolution")
        assert result == "learning"

    @pytest.mark.asyncio
    async def test_learning_help_understand(self):
        result = await classify_prompt_intent("Help me understand fractions")
        assert result == "learning"

    @pytest.mark.asyncio
    async def test_learning_what_are_steps(self):
        result = await classify_prompt_intent("What are the steps in cell division?")
        assert result == "learning"

    @pytest.mark.asyncio
    async def test_learning_can_you_explain(self):
        result = await classify_prompt_intent("Can you explain what osmosis is?")
        assert result == "learning"

    @pytest.mark.asyncio
    async def test_learning_show_me_example(self):
        result = await classify_prompt_intent("Show me an example of alliteration")
        assert result == "learning"

    @pytest.mark.asyncio
    async def test_learning_what_does_mean(self):
        result = await classify_prompt_intent("What does democracy mean?")
        assert result == "learning"

    @pytest.mark.asyncio
    async def test_doing_write_essay(self):
        result = await classify_prompt_intent("Write my essay about climate change")
        assert result == "doing"

    @pytest.mark.asyncio
    async def test_doing_solve_homework(self):
        result = await classify_prompt_intent("Solve my homework problems")
        assert result == "doing"

    @pytest.mark.asyncio
    async def test_doing_do_my_assignment(self):
        result = await classify_prompt_intent("Do my assignment for history class")
        assert result == "doing"

    @pytest.mark.asyncio
    async def test_doing_answer_quiz(self):
        result = await classify_prompt_intent("Answer this quiz for me")
        assert result == "doing"

    @pytest.mark.asyncio
    async def test_doing_complete_worksheet(self):
        result = await classify_prompt_intent("Complete this worksheet")
        assert result == "doing"

    @pytest.mark.asyncio
    async def test_doing_give_me_answer(self):
        result = await classify_prompt_intent("Give me the answer")
        assert result == "doing"

    @pytest.mark.asyncio
    async def test_doing_write_500_word(self):
        result = await classify_prompt_intent("Write a 500 word essay on volcanoes")
        assert result == "doing"

    @pytest.mark.asyncio
    async def test_doing_write_paragraph(self):
        result = await classify_prompt_intent("Write a paragraph about dogs")
        assert result == "doing"

    @pytest.mark.asyncio
    async def test_unclassified_general(self):
        result = await classify_prompt_intent("Tell me a joke")
        assert result == "unclassified"

    @pytest.mark.asyncio
    async def test_unclassified_empty(self):
        result = await classify_prompt_intent("")
        assert result == "unclassified"

    @pytest.mark.asyncio
    async def test_unclassified_whitespace(self):
        result = await classify_prompt_intent("   ")
        assert result == "unclassified"

    @pytest.mark.asyncio
    async def test_doing_before_learning(self):
        """'Doing' patterns take priority over 'learning' patterns."""
        result = await classify_prompt_intent(
            "Explain how to write my essay about volcanoes"
        )
        # "write my essay" should be detected as doing
        assert result == "doing"

    @pytest.mark.asyncio
    async def test_case_insensitive(self):
        result = await classify_prompt_intent("EXPLAIN WHAT IS PHOTOSYNTHESIS")
        assert result == "learning"


# ---------------------------------------------------------------------------
# is_study_hours
# ---------------------------------------------------------------------------


class TestIsStudyHours:
    """Tests for study hour checking logic."""

    @pytest.mark.asyncio
    async def test_weekday_within_hours(self):
        # Wednesday at 16:00 — within default 15:00-21:00
        ts = datetime(2026, 3, 11, 16, 0, tzinfo=timezone.utc)  # Wednesday
        assert await is_study_hours(ts) is True

    @pytest.mark.asyncio
    async def test_weekday_before_hours(self):
        # Wednesday at 10:00 — before 15:00
        ts = datetime(2026, 3, 11, 10, 0, tzinfo=timezone.utc)
        assert await is_study_hours(ts) is False

    @pytest.mark.asyncio
    async def test_weekday_after_hours(self):
        # Wednesday at 22:00 — after 21:00
        ts = datetime(2026, 3, 11, 22, 0, tzinfo=timezone.utc)
        assert await is_study_hours(ts) is False

    @pytest.mark.asyncio
    async def test_weekend_within_hours(self):
        # Saturday at 10:00 — within default 09:00-21:00
        ts = datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc)  # Saturday
        assert await is_study_hours(ts) is True

    @pytest.mark.asyncio
    async def test_weekend_before_hours(self):
        # Saturday at 07:00 — before 09:00
        ts = datetime(2026, 3, 14, 7, 0, tzinfo=timezone.utc)
        assert await is_study_hours(ts) is False

    @pytest.mark.asyncio
    async def test_boundary_start(self):
        # Exactly at weekday start
        ts = datetime(2026, 3, 11, 15, 0, tzinfo=timezone.utc)
        assert await is_study_hours(ts) is True

    @pytest.mark.asyncio
    async def test_boundary_end(self):
        # Exactly at weekday end
        ts = datetime(2026, 3, 11, 21, 0, tzinfo=timezone.utc)
        assert await is_study_hours(ts) is True

    @pytest.mark.asyncio
    async def test_custom_config(self):
        custom = {
            "weekday": {"start": "08:00", "end": "22:00"},
            "weekend": {"start": "10:00", "end": "18:00"},
        }
        # Wednesday 08:30 — within custom weekday hours
        ts = datetime(2026, 3, 11, 8, 30, tzinfo=timezone.utc)
        assert await is_study_hours(ts, custom) is True

        # Saturday 19:00 — after custom weekend end
        ts = datetime(2026, 3, 14, 19, 0, tzinfo=timezone.utc)
        assert await is_study_hours(ts, custom) is False

    @pytest.mark.asyncio
    async def test_sunday_is_weekend(self):
        # Sunday at 12:00
        ts = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)  # Sunday
        assert await is_study_hours(ts) is True


# ---------------------------------------------------------------------------
# Pattern completeness
# ---------------------------------------------------------------------------


class TestPatternCompleteness:
    """Verify pattern lists are non-empty and well-formed."""

    def test_learning_patterns_exist(self):
        assert len(LEARNING_PATTERNS) >= 5

    def test_doing_patterns_exist(self):
        assert len(DOING_PATTERNS) >= 6

    def test_study_hour_defaults_have_weekday_and_weekend(self):
        assert "weekday" in STUDY_HOUR_DEFAULTS
        assert "weekend" in STUDY_HOUR_DEFAULTS
        assert "start" in STUDY_HOUR_DEFAULTS["weekday"]
        assert "end" in STUDY_HOUR_DEFAULTS["weekday"]
