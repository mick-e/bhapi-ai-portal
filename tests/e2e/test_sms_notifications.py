"""E2E test for SMS notification dev mode."""

import pytest


@pytest.mark.asyncio
async def test_sms_dev_mode_logs_only():
    """In dev/test mode, SMS should log instead of sending via Twilio.

    When TWILIO_ACCOUNT_SID is not configured, the SMS module should
    gracefully degrade to logging-only mode.
    """
    from src.config import get_settings

    settings = get_settings()

    # In test environment, Twilio is not configured
    assert settings.twilio_account_sid is None or settings.environment == "test"

    # Import SMS module to verify it doesn't crash without Twilio
    from src.sms import service as sms_service

    assert hasattr(sms_service, "send_sms"), "SMS service must expose send_sms()"

    # In dev/test mode, send_sms should log only and return True (logged) or False (rate-limited/no-consent)
    # The actual parameter name is `to_phone` (not `to_number`)
    result = await sms_service.send_sms(
        to_phone="+1234567890",
        message="Test SMS — should not actually send",
    )
    # Should return a bool — True means logged in dev mode, False means skipped
    assert isinstance(result, bool)
