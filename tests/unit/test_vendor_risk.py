"""Unit tests for vendor risk scoring."""

import pytest

from src.billing.vendor_risk import (
    calculate_vendor_risk,
    get_all_vendor_risks,
)


def test_openai_score_is_high():
    """OpenAI should score well given full compliance."""
    score = calculate_vendor_risk("openai")
    assert score is not None
    assert score.overall_score >= 80
    assert score.grade in ("A", "B")
    assert score.provider == "openai"
    assert score.name == "OpenAI"


def test_anthropic_score_is_high():
    """Anthropic should score well (0 incidents)."""
    score = calculate_vendor_risk("anthropic")
    assert score is not None
    assert score.overall_score >= 85
    assert score.grade in ("A", "B")


def test_xai_score_is_low():
    """xAI/Grok should score low (missing compliance, no child safety)."""
    score = calculate_vendor_risk("xai")
    assert score is not None
    assert score.overall_score < 60
    assert score.grade in ("D", "F")


def test_unknown_provider_returns_none():
    """Unknown provider returns None."""
    result = calculate_vendor_risk("unknown_provider")
    assert result is None


def test_grade_assignment():
    """Verify grade thresholds."""
    from src.billing.vendor_risk import _grade
    assert _grade(95) == "A"
    assert _grade(80) == "B"
    assert _grade(65) == "C"
    assert _grade(45) == "D"
    assert _grade(30) == "F"


def test_recommendations_for_noncompliant_vendor():
    """xAI should have multiple recommendations."""
    score = calculate_vendor_risk("xai")
    assert score is not None
    assert len(score.recommendations) >= 3


def test_recommendations_for_compliant_vendor():
    """Fully compliant vendor gets positive recommendation."""
    score = calculate_vendor_risk("anthropic")
    assert score is not None
    assert any("meets all" in r.lower() for r in score.recommendations)


def test_get_all_vendor_risks_returns_all():
    """get_all_vendor_risks returns all 5 vendors sorted by score."""
    risks = get_all_vendor_risks()
    assert len(risks) == 5
    # Should be sorted descending by score
    scores = [r.overall_score for r in risks]
    assert scores == sorted(scores, reverse=True)


def test_category_scores_present():
    """Each vendor score has all 5 category scores."""
    score = calculate_vendor_risk("google")
    assert score is not None
    assert "privacy" in score.category_scores
    assert "compliance" in score.category_scores
    assert "security" in score.category_scores
    assert "child_safety" in score.category_scores
    assert "transparency" in score.category_scores
    for v in score.category_scores.values():
        assert 0 <= v <= 100
