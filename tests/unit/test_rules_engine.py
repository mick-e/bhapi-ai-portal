"""Unit tests for deterministic rules engine (src/risk/rules_engine.py).

Covers keyword watchlists per category, age-band scaling, custom keywords,
clean-text scenarios, and multi-category detection.
"""


from src.risk.rules_engine import (
    _effective_threshold,
    _get_age_band,
    evaluate,
)

# ---------------------------------------------------------------------------
# Self-harm detection
# ---------------------------------------------------------------------------

class TestSelfHarmDetection:
    """Tests for SELF_HARM category."""

    def test_suicide_keyword(self):
        results = evaluate("I want to commit suicide")
        categories = [r.category for r in results]
        assert "SELF_HARM" in categories

    def test_self_harm_keyword(self):
        results = evaluate("I have been cutting myself lately")
        categories = [r.category for r in results]
        assert "SELF_HARM" in categories

    def test_want_to_die(self):
        results = evaluate("I want to die and end my life")
        categories = [r.category for r in results]
        assert "SELF_HARM" in categories

    def test_severity_is_critical(self):
        results = evaluate("I want to commit suicide")
        sh = [r for r in results if r.category == "SELF_HARM"]
        assert len(sh) >= 1
        assert sh[0].severity == "critical"


# ---------------------------------------------------------------------------
# Violence detection
# ---------------------------------------------------------------------------

class TestViolenceDetection:
    """Tests for VIOLENCE category."""

    def test_bomb_making(self):
        results = evaluate("how to make a bomb at home")
        categories = [r.category for r in results]
        assert "VIOLENCE" in categories

    def test_school_shooting(self):
        results = evaluate("planning a school shooting")
        categories = [r.category for r in results]
        assert "VIOLENCE" in categories

    def test_violence_severity(self):
        results = evaluate("how to make a weapon")
        violence = [r for r in results if r.category == "VIOLENCE"]
        assert len(violence) >= 1
        assert violence[0].severity == "critical"


# ---------------------------------------------------------------------------
# Academic dishonesty detection
# ---------------------------------------------------------------------------

class TestAcademicDishonesty:
    """Tests for ACADEMIC_DISHONESTY category."""

    def test_write_my_essay(self):
        results = evaluate("Can you write my essay for me about history?")
        categories = [r.category for r in results]
        assert "ACADEMIC_DISHONESTY" in categories

    def test_do_my_homework(self):
        results = evaluate("Please do my homework on algebra")
        categories = [r.category for r in results]
        assert "ACADEMIC_DISHONESTY" in categories

    def test_plagiarize(self):
        results = evaluate("Help me plagiarize this paper")
        categories = [r.category for r in results]
        assert "ACADEMIC_DISHONESTY" in categories

    def test_severity_is_medium(self):
        results = evaluate("write my essay for me")
        ad = [r for r in results if r.category == "ACADEMIC_DISHONESTY"]
        assert len(ad) >= 1
        assert ad[0].severity == "medium"


# ---------------------------------------------------------------------------
# Bullying / harassment detection
# ---------------------------------------------------------------------------

class TestBullyingHarassment:
    """Tests for BULLYING_HARASSMENT category."""

    def test_kill_yourself(self):
        results = evaluate("Why don't you kill yourself")
        categories = [r.category for r in results]
        assert "BULLYING_HARASSMENT" in categories

    def test_kys(self):
        results = evaluate("kys nobody likes you")
        categories = [r.category for r in results]
        assert "BULLYING_HARASSMENT" in categories

    def test_youre_worthless(self):
        results = evaluate("you're worthless and nobody cares")
        categories = [r.category for r in results]
        assert "BULLYING_HARASSMENT" in categories


# ---------------------------------------------------------------------------
# Age-band scaling
# ---------------------------------------------------------------------------

class TestAgeBandScaling:
    """Tests for age-band threshold scaling."""

    def test_age_band_under_8(self):
        assert _get_age_band(5) == "under_8"
        assert _get_age_band(7) == "under_8"

    def test_age_band_8_to_10(self):
        assert _get_age_band(8) == "8_to_10"
        assert _get_age_band(10) == "8_to_10"

    def test_age_band_11_to_13(self):
        assert _get_age_band(11) == "11_to_13"
        assert _get_age_band(13) == "11_to_13"

    def test_age_band_14_to_16(self):
        assert _get_age_band(14) == "14_to_16"
        assert _get_age_band(16) == "14_to_16"

    def test_age_band_17_plus(self):
        assert _get_age_band(17) == "17_plus"
        assert _get_age_band(25) == "17_plus"

    def test_age_none_conservative_default(self):
        """None age defaults to 11_to_13 (conservative)."""
        assert _get_age_band(None) == "11_to_13"

    def test_younger_gets_lower_threshold(self):
        """Younger age bands produce lower thresholds (more sensitive)."""
        threshold_5yr = _effective_threshold(50, 5)
        threshold_17yr = _effective_threshold(50, 17)
        assert threshold_5yr < threshold_17yr

    def test_effective_threshold_range(self):
        """Threshold is always 0.0 to 1.0."""
        for sensitivity in [0, 25, 50, 75, 100]:
            for age in [5, 10, 13, 16, 18, None]:
                t = _effective_threshold(sensitivity, age)
                assert 0.0 <= t <= 1.0


# ---------------------------------------------------------------------------
# Custom keywords from config
# ---------------------------------------------------------------------------

class TestCustomKeywords:
    """Tests for custom keyword injection via config."""

    def test_custom_keyword_triggers_category(self):
        config = {
            "VIOLENCE": {
                "enabled": True,
                "sensitivity": 80,
                "custom_keywords": {
                    "keywords": ["super dangerous phrase"]
                },
            }
        }
        results = evaluate("this text contains super dangerous phrase", config=config)
        categories = [r.category for r in results]
        assert "VIOLENCE" in categories

    def test_disabled_category_not_flagged(self):
        config = {
            "SELF_HARM": {
                "enabled": False,
                "sensitivity": 50,
            }
        }
        results = evaluate("I want to commit suicide", config=config)
        categories = [r.category for r in results]
        assert "SELF_HARM" not in categories


# ---------------------------------------------------------------------------
# Clean text
# ---------------------------------------------------------------------------

class TestCleanText:
    """Tests that clean text returns no risk."""

    def test_normal_conversation(self):
        results = evaluate("Today we learned about photosynthesis in class")
        assert len(results) == 0

    def test_homework_question(self):
        results = evaluate("Can you explain how gravity works?")
        assert len(results) == 0

    def test_friendly_text(self):
        results = evaluate("I love playing with my friends at the park")
        assert len(results) == 0

    def test_empty_text(self):
        results = evaluate("")
        assert len(results) == 0

    def test_whitespace_only(self):
        results = evaluate("   \n\t  ")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Multiple categories in same text
# ---------------------------------------------------------------------------

class TestMultipleCategories:
    """Tests for detecting multiple categories in same text."""

    def test_self_harm_and_bullying(self):
        text = "kill yourself you're worthless, I want to die"
        results = evaluate(text)
        categories = {r.category for r in results}
        assert "SELF_HARM" in categories
        assert "BULLYING_HARASSMENT" in categories

    def test_results_sorted_by_severity(self):
        """Results should be sorted by severity: critical > high > medium > low."""
        text = "write my essay for me, I want to commit suicide"
        results = evaluate(text)
        if len(results) >= 2:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            for i in range(len(results) - 1):
                assert severity_order.get(results[i].severity, 4) <= severity_order.get(results[i + 1].severity, 4)

    def test_confidence_is_between_0_and_1(self):
        results = evaluate("how to make a bomb, write my essay")
        for r in results:
            assert 0.0 <= r.confidence <= 1.0

    def test_reasoning_includes_keyword(self):
        results = evaluate("I want to commit suicide")
        sh = [r for r in results if r.category == "SELF_HARM"]
        assert len(sh) >= 1
        assert "Keyword match" in sh[0].reasoning
