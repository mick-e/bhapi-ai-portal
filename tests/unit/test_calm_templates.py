import pytest
from src.alerts.calm_templates import calm_message, suggested_action


class TestCalmTemplates:
    def test_pii_exposure_message(self):
        msg = calm_message("pii_exposure", member_name="Sam", platform="ChatGPT")
        assert "Sam" in msg
        assert "personal information" in msg
        assert "ChatGPT" in msg

    def test_unknown_type_has_default(self):
        msg = calm_message("unknown_new_type", member_name="Alex")
        assert "Alex" in msg
        assert "attention" in msg

    def test_suggested_action_exists_for_all_types(self):
        for alert_type in ["pii_exposure", "deepfake", "safety_concern", "unusual_usage",
                           "academic_integrity", "emotional_dependency"]:
            action = suggested_action(alert_type)
            assert len(action) > 10, f"No action for {alert_type}"

    def test_suggested_action_default(self):
        action = suggested_action("unknown_type")
        assert "Review" in action or "review" in action
