"""E2E tests for deepfake detection in the risk pipeline."""

import pytest

from src.risk.classifier import classify_by_keywords
from src.risk.taxonomy import DEEPFAKE_CONTENT, RISK_CATEGORIES


def test_deepfake_category_in_taxonomy():
    """DEEPFAKE_CONTENT category exists in taxonomy."""
    assert DEEPFAKE_CONTENT in RISK_CATEGORIES
    meta = RISK_CATEGORIES[DEEPFAKE_CONTENT]
    assert meta["severity"] == "high"
    assert "deepfake" in meta["description"].lower()


def test_deepfake_keywords_trigger_classification():
    """Deepfake-related keywords trigger high-severity classification."""
    test_phrases = [
        "how to create a deepfake",
        "face swap someone's photo",
        "undress ai tool",
        "nudify app download",
        "ai-generated image of a person",
    ]
    for phrase in test_phrases:
        result = classify_by_keywords(phrase)
        assert result is not None, f"Expected match for: {phrase}"
        assert result.severity == "high", f"Expected high severity for: {phrase}"


def test_synthetic_media_keyword():
    """'synthetic media' triggers high classification."""
    result = classify_by_keywords("creating synthetic media content")
    assert result is not None
    assert result.severity == "high"


@pytest.mark.asyncio
async def test_risk_pipeline_with_media_urls():
    """Risk pipeline processes media_urls field (no API key = skips deepfake)."""
    from src.risk.engine import process_event

    result = await process_event({
        "content": "Look at this image",
        "media_urls": ["https://example.com/image.jpg"],
    })
    # Without DEEPFAKE_API_KEY, deepfake layer is skipped
    # Result may be empty or contain only text-based classifications
    assert isinstance(result, list)
