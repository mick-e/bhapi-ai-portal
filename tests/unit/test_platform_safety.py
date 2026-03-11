"""Unit tests for AI Platform Safety Ratings."""

import pytest

from src.billing.platform_safety import (
    PLATFORM_SAFETY_PROFILES,
    get_age_recommendations,
    get_platform_safety_rating,
    get_platform_safety_ratings,
)


def test_all_eight_platforms_defined():
    """There should be exactly 8 platform profiles."""
    assert len(PLATFORM_SAFETY_PROFILES) == 8
    expected_keys = {
        "chatgpt", "claude", "gemini", "copilot",
        "grok", "characterai", "replika", "pi",
    }
    assert set(PLATFORM_SAFETY_PROFILES.keys()) == expected_keys


def test_get_all_ratings():
    """get_platform_safety_ratings should return all 8 platforms."""
    ratings = get_platform_safety_ratings()
    assert len(ratings) == 8
    # Should be sorted by grade
    grades = [r["overall_grade"] for r in ratings]
    assert grades == sorted(grades)


def test_get_single_rating_exists():
    """Known platform should return correct data."""
    rating = get_platform_safety_rating("claude")
    assert rating is not None
    assert rating["key"] == "claude"
    assert rating["name"] == "Claude (Anthropic)"
    assert rating["overall_grade"] == "A"
    assert rating["min_age_recommended"] == 13
    assert isinstance(rating["strengths"], list)
    assert isinstance(rating["concerns"], list)


def test_get_single_rating_not_found():
    """Unknown platform should return None."""
    rating = get_platform_safety_rating("nonexistent")
    assert rating is None


def test_all_profiles_have_required_fields():
    """Every profile should have all required fields."""
    for key, profile in PLATFORM_SAFETY_PROFILES.items():
        assert profile.key == key
        assert profile.name
        assert profile.overall_grade in ("A", "B", "C", "D", "F")
        assert profile.min_age_recommended > 0
        assert isinstance(profile.has_parental_controls, bool)
        assert isinstance(profile.has_content_filters, bool)
        assert profile.data_retention_days > 0
        assert isinstance(profile.coppa_compliant, bool)
        assert isinstance(profile.known_incidents, int)
        assert len(profile.strengths) > 0
        assert len(profile.concerns) > 0
        assert profile.last_updated


def test_age_recommendations_child_8():
    """8-year-old should see most platforms as not recommended."""
    results = get_age_recommendations(8)
    assert len(results) == 8

    not_rec = [r for r in results if r["recommendation"] == "not_recommended"]
    # Platforms with min_age > 11 (8+3) should be not_recommended
    assert len(not_rec) >= 3


def test_age_recommendations_teen_13():
    """13-year-old should have platforms with min_age 13 as recommended."""
    results = get_age_recommendations(13)
    recommended = [r for r in results if r["recommendation"] == "recommended"]

    # ChatGPT, Claude, Gemini, Copilot, Pi all have min_age 13
    recommended_keys = {r["key"] for r in recommended}
    assert "chatgpt" in recommended_keys
    assert "claude" in recommended_keys


def test_age_recommendations_adult_25():
    """25-year-old should see all platforms recommended."""
    results = get_age_recommendations(25)
    recommended = [r for r in results if r["recommendation"] == "recommended"]
    assert len(recommended) == 8


def test_age_recommendations_teen_15():
    """15-year-old should have use_with_caution for CharacterAI."""
    results = get_age_recommendations(15)
    character_ai = next(r for r in results if r["key"] == "characterai")
    # min_age is 16, and 15 is within 3 years, so use_with_caution
    assert character_ai["recommendation"] == "use_with_caution"


def test_age_recommendations_sorting():
    """Results should be sorted: recommended first, then use_with_caution, then not_recommended."""
    results = get_age_recommendations(14)
    order = [r["recommendation"] for r in results]

    recommendation_priority = {
        "recommended": 0,
        "use_with_caution": 1,
        "not_recommended": 2,
    }
    priorities = [recommendation_priority[r] for r in order]
    assert priorities == sorted(priorities)


def test_grok_high_risk():
    """Grok should be marked as high risk with 18+ min age."""
    profile = PLATFORM_SAFETY_PROFILES["grok"]
    assert profile.overall_grade in ("D", "F")
    assert profile.min_age_recommended == 18
    assert profile.has_parental_controls is False
    assert profile.has_content_filters is False


def test_replika_high_risk():
    """Replika should be marked as high risk with 18+ min age."""
    profile = PLATFORM_SAFETY_PROFILES["replika"]
    assert profile.overall_grade in ("D", "F")
    assert profile.min_age_recommended == 18
    assert profile.has_parental_controls is False


def test_rating_dict_serializable():
    """Returned dicts should be JSON-serializable."""
    import json
    ratings = get_platform_safety_ratings()
    serialized = json.dumps(ratings)
    assert len(serialized) > 0

    recommendations = get_age_recommendations(12)
    serialized2 = json.dumps(recommendations)
    assert len(serialized2) > 0
