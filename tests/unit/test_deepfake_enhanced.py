"""Unit tests for enhanced deepfake keyword patterns and voice cloning detection."""

import pytest

from src.risk.classifier import classify_by_keywords
from src.risk.deepfake_detector import (
    VoiceCloningRisk,
    detect_voice_cloning_risk,
)


# ---------------------------------------------------------------------------
# New deepfake/nudify keyword patterns in classifier
# ---------------------------------------------------------------------------


class TestNewDeepfakePatterns:
    """Verify new deepfake patterns in classifier detect correctly."""

    def test_remove_clothes(self):
        result = classify_by_keywords("remove her clothes from this photo")
        assert result is not None
        assert result.severity == "high"
        assert "DEEPFAKE_CONTENT" in result.categories
        assert result.confidence >= 0.90

    def test_make_nude_photo(self):
        result = classify_by_keywords("make a nude photo of this person")
        assert result is not None
        assert result.severity == "high"
        assert result.confidence >= 0.90

    def test_clone_voice(self):
        result = classify_by_keywords("clone my voice for this project")
        assert result is not None
        assert result.severity == "high"
        assert result.confidence >= 0.90

    def test_voice_sample_for_cloning(self):
        result = classify_by_keywords("I have a voice sample for cloning")
        assert result is not None
        assert result.severity == "high"

    def test_voice_recording_for_ai(self):
        result = classify_by_keywords("voice recording for ai purposes")
        assert result is not None
        assert result.severity == "high"

    def test_face_on_body(self):
        result = classify_by_keywords("put her face on a body")
        assert result is not None
        assert result.severity == "high"

    def test_face_onto_video(self):
        result = classify_by_keywords("put face onto a video")
        assert result is not None
        assert result.severity == "high"

    def test_undress_ai_app(self):
        result = classify_by_keywords("use the undress ai app")
        assert result is not None
        assert result.severity == "high"

    def test_put_my_face_on(self):
        result = classify_by_keywords("put my face on a celebrity")
        assert result is not None
        assert result.severity == "high"

    def test_ai_nude(self):
        result = classify_by_keywords("ai nude generator online")
        assert result is not None
        assert result.severity == "high"

    def test_fake_nude_photo(self):
        result = classify_by_keywords("create a fake nude photo")
        assert result is not None
        assert result.severity == "high"

    def test_fake_naked_video(self):
        result = classify_by_keywords("fake naked video of someone")
        assert result is not None
        assert result.severity == "high"

    def test_safe_content_not_matched(self):
        """Normal content should not trigger deepfake patterns."""
        result = classify_by_keywords("How do I clone a Git repository?")
        assert result is None

    def test_safe_voice_reference(self):
        """'Voice' in normal context should not trigger."""
        result = classify_by_keywords("What is the passive voice in writing?")
        assert result is None


# ---------------------------------------------------------------------------
# Voice cloning detection
# ---------------------------------------------------------------------------


class TestVoiceCloningDetection:
    """Tests for detect_voice_cloning_risk function."""

    def test_clone_voice_detected(self):
        result = detect_voice_cloning_risk("I want to clone my voice using AI")
        assert result.is_risk is True
        assert result.confidence >= 0.90
        assert len(result.matched_patterns) >= 1
        assert result.recommendation != ""

    def test_voice_cloning_keyword(self):
        result = detect_voice_cloning_risk("How does voice cloning work?")
        assert result.is_risk is True
        assert result.confidence >= 0.90

    def test_deepfake_voice(self):
        result = detect_voice_cloning_risk("Create a deepfake voice message")
        assert result.is_risk is True

    def test_ai_voice_generator(self):
        result = detect_voice_cloning_risk("Best ai voice generator to copy someone")
        assert result.is_risk is True

    def test_replicate_voice(self):
        result = detect_voice_cloning_risk("How to replicate my voice")
        assert result.is_risk is True

    def test_safe_text_no_risk(self):
        result = detect_voice_cloning_risk("I like listening to music")
        assert result.is_risk is False
        assert result.confidence == 0.0
        assert result.matched_patterns == []

    def test_empty_text(self):
        result = detect_voice_cloning_risk("")
        assert result.is_risk is False
        assert result.confidence == 0.0

    def test_whitespace_only(self):
        result = detect_voice_cloning_risk("   ")
        assert result.is_risk is False

    def test_multiple_matches_increase_confidence(self):
        result = detect_voice_cloning_risk(
            "I want to use voice cloning to clone my voice with an AI voice generator"
        )
        assert result.is_risk is True
        assert result.confidence >= 0.90
        assert len(result.matched_patterns) >= 2

    def test_result_dataclass(self):
        result = VoiceCloningRisk(
            is_risk=True,
            confidence=0.95,
            matched_patterns=["clone my voice"],
            recommendation="Be careful",
        )
        assert result.is_risk is True
        assert result.confidence == 0.95
