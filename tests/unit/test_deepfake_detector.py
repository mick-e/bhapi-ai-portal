"""Unit tests for deepfake detection module."""

import os
from unittest.mock import patch

import pytest

from src.risk.deepfake_detector import (
    DeepfakeResult,
    HiveDetector,
    SensityDetector,
    analyze_media,
    get_detector,
)


def test_get_detector_default_is_hive():
    """Default detector is Hive."""
    with patch.dict(os.environ, {}, clear=True):
        detector = get_detector()
        assert isinstance(detector, HiveDetector)


def test_get_detector_sensity():
    """DEEPFAKE_PROVIDER=sensity returns SensityDetector."""
    with patch.dict(os.environ, {"DEEPFAKE_PROVIDER": "sensity"}):
        detector = get_detector()
        assert isinstance(detector, SensityDetector)


@pytest.mark.asyncio
async def test_hive_detector_no_api_key():
    """Hive detector without API key returns safe result."""
    with patch.dict(os.environ, {}, clear=True):
        detector = HiveDetector()
        result = await detector.detect("https://example.com/image.jpg")
        assert result.is_deepfake is False
        assert result.confidence == 0.0
        assert result.provider == "hive"
        assert "No API key" in result.details.get("error", "")


@pytest.mark.asyncio
async def test_sensity_detector_no_api_key():
    """Sensity detector without API key returns safe result."""
    with patch.dict(os.environ, {}, clear=True):
        detector = SensityDetector()
        result = await detector.detect("https://example.com/image.jpg")
        assert result.is_deepfake is False
        assert result.confidence == 0.0
        assert result.provider == "sensity"


@pytest.mark.asyncio
async def test_analyze_media_no_api_key():
    """analyze_media without API key returns safe result."""
    with patch.dict(os.environ, {}, clear=True):
        result = await analyze_media("https://example.com/image.jpg")
        assert result.is_deepfake is False
        assert result.confidence == 0.0


def test_deepfake_result_dataclass():
    """DeepfakeResult stores values correctly."""
    result = DeepfakeResult(
        is_deepfake=True,
        confidence=0.95,
        provider="hive",
        details={"class": "deepfake"},
    )
    assert result.is_deepfake is True
    assert result.confidence == 0.95
    assert result.provider == "hive"
