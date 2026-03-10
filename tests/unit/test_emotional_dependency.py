"""Unit tests for emotional dependency pattern detection."""

import pytest

from src.risk.classifier import classify_by_keywords
from src.risk.taxonomy import (
    EMOTIONAL_DEPENDENCY,
    DEEPFAKE_CONTENT,
    RISK_CATEGORIES,
    MEDIUM_CATEGORIES,
    HIGH_CATEGORIES,
)


def test_emotional_dependency_in_taxonomy():
    """EMOTIONAL_DEPENDENCY is defined in the risk taxonomy."""
    assert EMOTIONAL_DEPENDENCY in RISK_CATEGORIES
    assert RISK_CATEGORIES[EMOTIONAL_DEPENDENCY]["severity"] == "medium"


def test_emotional_dependency_in_medium_categories():
    """EMOTIONAL_DEPENDENCY is in the MEDIUM_CATEGORIES set."""
    assert EMOTIONAL_DEPENDENCY in MEDIUM_CATEGORIES


def test_deepfake_content_in_taxonomy():
    """DEEPFAKE_CONTENT is defined in the risk taxonomy."""
    assert DEEPFAKE_CONTENT in RISK_CATEGORIES
    assert RISK_CATEGORIES[DEEPFAKE_CONTENT]["severity"] == "high"


def test_deepfake_content_in_high_categories():
    """DEEPFAKE_CONTENT is in the HIGH_CATEGORIES set."""
    assert DEEPFAKE_CONTENT in HIGH_CATEGORIES


def test_i_love_you_triggers_classification():
    """'I love you' triggers medium classification."""
    result = classify_by_keywords("I love you so much, you're the best AI")
    assert result is not None
    assert result.severity == "medium"


def test_dont_leave_me_triggers_classification():
    """'Don't leave me' triggers medium classification."""
    result = classify_by_keywords("Please don't leave me, I need you")
    assert result is not None
    assert result.severity == "medium"


def test_wish_you_were_real_triggers_classification():
    """'I wish you were real' triggers medium classification."""
    result = classify_by_keywords("I wish you were real so we could meet")
    assert result is not None
    assert result.severity == "medium"


def test_deepfake_keyword_triggers_high():
    """'deepfake' keyword triggers high classification."""
    result = classify_by_keywords("How to make a deepfake video")
    assert result is not None
    assert result.severity == "high"


def test_face_swap_keyword_triggers_high():
    """'face swap' keyword triggers high classification."""
    result = classify_by_keywords("I want to face swap my teacher")
    assert result is not None
    assert result.severity == "high"


def test_nudify_keyword_triggers_high():
    """'nudify' keyword triggers high classification."""
    result = classify_by_keywords("How to nudify someone's photo")
    assert result is not None
    assert result.severity == "high"


def test_normal_text_no_match():
    """Normal text does not trigger emotional dependency or deepfake."""
    result = classify_by_keywords("What is the weather today?")
    assert result is None
