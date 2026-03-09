"""Unit tests for risk classification engine."""

import pytest

from src.risk.classifier import (
    ClassificationResult,
    classify_by_keywords,
    classify_content,
)


def test_classify_critical_content():
    result = classify_by_keywords("how to kill myself")
    assert result is not None
    assert result.severity == "critical"
    assert result.source == "keyword"
    assert result.confidence > 0.8


def test_classify_high_content():
    result = classify_by_keywords("how to hack into someone's account")
    assert result is not None
    assert result.severity == "high"


def test_classify_medium_content():
    result = classify_by_keywords("write my homework for me please")
    assert result is not None
    assert result.severity == "medium"
    assert "academic_integrity" in result.categories


def test_classify_safe_content():
    result = classify_by_keywords("What is the weather today?")
    assert result is None


def test_classify_case_insensitive():
    result = classify_by_keywords("How to HACK INTO passwords")
    assert result is not None
    assert result.severity == "high"


@pytest.mark.asyncio
async def test_classify_content_default_mode():
    """Default keyword_only mode."""
    result = await classify_content("how to kill myself")
    assert result.severity == "critical"
    assert result.source == "keyword"


@pytest.mark.asyncio
async def test_classify_content_safe():
    result = await classify_content("Tell me about photosynthesis")
    assert result.severity == "low"
    assert result.source == "keyword"


def test_classification_result_dataclass():
    result = ClassificationResult(
        severity="high",
        categories=["safety"],
        confidence=0.9,
        source="keyword",
    )
    assert result.severity == "high"
    assert result.details is None
