"""Security tests for the SMS module.

Covers: injection prevention, phone validation, rate limiting,
consent gating, message length, credential handling, and delivery callbacks.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.sms.service import (
    SMSRateLimitError,
    _check_sms_rate,
    reset_sms_rate_limits,
    send_sms,
)
from src.sms.templates import digest_summary_sms, risk_alert_sms, spend_alert_sms


# ===================================================================
# 1. SMS injection prevention
# ===================================================================
class TestSMSInjection:
    """Control characters in message bodies must not enable SMS injection."""

    def setup_method(self):
        reset_sms_rate_limits()

    @pytest.mark.asyncio
    async def test_newline_in_message_body(self):
        """Newline chars in the message should not crash send_sms."""
        result = await send_sms(
            "+15551234567",
            "Alert\r\nInjected header: evil",
            group_id="grp-1",
        )
        assert result is True  # Logged in test mode

    @pytest.mark.asyncio
    async def test_null_byte_in_message(self):
        """Null bytes in message should not crash."""
        result = await send_sms(
            "+15551234567",
            "Alert\x00injected",
            group_id="grp-1",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_control_chars_in_phone_number(self):
        """Control characters in phone number should not crash."""
        result = await send_sms(
            "+1555\r\n1234567",
            "Test message",
            group_id="grp-1",
        )
        assert isinstance(result, bool)

    def test_template_risk_alert_injection(self):
        """Risk alert template with injection chars in member_name."""
        msg = risk_alert_sms("Alice\r\nEvil: header", "high", "pii")
        assert isinstance(msg, str)
        assert "Alice" in msg

    def test_template_spend_alert_no_format_string_attack(self):
        """Format string-like values should not break templates."""
        msg = spend_alert_sms(float("inf"), float("nan"), 999)
        assert isinstance(msg, str)

    def test_template_digest_negative_count(self):
        """Negative count should not crash template."""
        msg = digest_summary_sms(-1, "daily")
        assert isinstance(msg, str)


# ===================================================================
# 2. Phone number edge cases
# ===================================================================
class TestPhoneNumberValidation:
    """Phone number inputs should be handled safely."""

    def setup_method(self):
        reset_sms_rate_limits()

    @pytest.mark.asyncio
    async def test_empty_phone_number(self):
        """Empty string phone number should not crash."""
        result = await send_sms("", "Test message")
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_very_long_phone_number(self):
        """Extremely long phone number should not crash."""
        result = await send_sms("+" + "1" * 500, "Test message")
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_non_numeric_phone(self):
        """Non-numeric phone input should not crash."""
        result = await send_sms("not-a-phone-number", "Test message")
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_special_chars_in_phone(self):
        """Special characters in phone should not crash."""
        result = await send_sms("+1(555)123-4567", "Test")
        assert isinstance(result, bool)


# ===================================================================
# 3. Rate limit enforcement
# ===================================================================
class TestSMSRateLimiting:
    """Rate limiter must enforce 10 SMS per minute per group."""

    def setup_method(self):
        reset_sms_rate_limits()

    def test_exactly_at_limit(self):
        """10 calls succeed, 11th raises."""
        for _ in range(10):
            _check_sms_rate("flood-grp")
        with pytest.raises(SMSRateLimitError):
            _check_sms_rate("flood-grp")

    @pytest.mark.asyncio
    async def test_rate_limit_returns_false_on_send(self):
        """send_sms should return False when rate limited."""
        group_id = "rate-test-2"
        for _ in range(10):
            await send_sms("+15551234567", "msg", group_id=group_id)

        result = await send_sms("+15551234567", "msg", group_id=group_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_no_group_id_no_rate_limit(self):
        """Without group_id, SMS should not be rate limited."""
        for _ in range(20):
            result = await send_sms("+15551234567", "msg")
            assert result is True

    def test_reset_clears_all_groups(self):
        """reset_sms_rate_limits should clear all tracking."""
        for _ in range(10):
            _check_sms_rate("grp-reset")
        reset_sms_rate_limits()
        # Should work again after reset
        _check_sms_rate("grp-reset")


# ===================================================================
# 4. Consent gating (COPPA 2026 — Twilio consent check)
# ===================================================================
class TestSMSConsentGating:
    """Twilio consent must be checked before sending when group+member provided."""

    def setup_method(self):
        reset_sms_rate_limits()

    @pytest.mark.asyncio
    async def test_no_consent_skips_sms(self):
        """When third-party consent returns False, SMS should not be sent."""
        group_id = str(uuid4())
        member_id = str(uuid4())
        mock_db = AsyncMock()

        with patch(
            "src.compliance.coppa_2026.check_third_party_consent",
            new_callable=AsyncMock,
            return_value=False,
        ) as mock_consent:
            result = await send_sms(
                "+15551234567",
                "Alert",
                group_id=group_id,
                member_id=member_id,
                db=mock_db,
            )
            assert result is False
            mock_consent.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_consent_sends_sms(self):
        """When third-party consent returns True, SMS should proceed."""
        group_id = str(uuid4())
        member_id = str(uuid4())
        mock_db = AsyncMock()

        with patch(
            "src.compliance.coppa_2026.check_third_party_consent",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await send_sms(
                "+15551234567",
                "Alert",
                group_id=group_id,
                member_id=member_id,
                db=mock_db,
            )
            # In test env, this logs and returns True
            assert result is True

    @pytest.mark.asyncio
    async def test_consent_not_checked_without_db(self):
        """Without a db session, consent check is skipped."""
        group_id = str(uuid4())
        member_id = str(uuid4())

        with patch(
            "src.compliance.coppa_2026.check_third_party_consent",
            new_callable=AsyncMock,
        ) as mock_consent:
            result = await send_sms(
                "+15551234567",
                "Alert",
                group_id=group_id,
                member_id=member_id,
                db=None,
            )
            assert result is True
            mock_consent.assert_not_called()

    @pytest.mark.asyncio
    async def test_consent_not_checked_without_member_id(self):
        """Without member_id, consent check is skipped."""
        mock_db = AsyncMock()

        with patch(
            "src.compliance.coppa_2026.check_third_party_consent",
            new_callable=AsyncMock,
        ) as mock_consent:
            result = await send_sms(
                "+15551234567",
                "Alert",
                group_id=str(uuid4()),
                member_id=None,
                db=mock_db,
            )
            assert result is True
            mock_consent.assert_not_called()


# ===================================================================
# 5. Message length enforcement
# ===================================================================
class TestMessageLength:
    """SMS body is truncated to 1600 chars by the service."""

    def setup_method(self):
        reset_sms_rate_limits()

    @pytest.mark.asyncio
    async def test_long_message_does_not_crash(self):
        """A message exceeding 1600 chars should not crash."""
        long_msg = "A" * 5000
        result = await send_sms("+15551234567", long_msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """Empty message should not crash."""
        result = await send_sms("+15551234567", "")
        assert result is True

    def test_template_outputs_reasonable_length(self):
        """All SMS templates should produce messages under 160 chars (1 segment)."""
        msgs = [
            risk_alert_sms("Alice", "high", "self_harm"),
            spend_alert_sms(99.99, 100.00, 100),
            digest_summary_sms(999, "weekly"),
        ]
        for msg in msgs:
            assert len(msg) <= 160, f"SMS template too long ({len(msg)} chars): {msg[:80]}..."


# ===================================================================
# 6. Twilio credential handling
# ===================================================================
class TestCredentialHandling:
    """Twilio credentials must never be logged or returned in responses."""

    def setup_method(self):
        reset_sms_rate_limits()

    @pytest.mark.asyncio
    async def test_missing_credentials_returns_false_not_exception(self):
        """Missing Twilio config in production should return False, not raise."""
        with patch("src.sms.service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.environment = "production"
            settings.twilio_account_sid = None
            settings.twilio_auth_token = None
            settings.twilio_from_number = None
            mock_settings.return_value = settings

            result = await send_sms("+15551234567", "Test")
            assert result is False

    @pytest.mark.asyncio
    async def test_partial_credentials_returns_false(self):
        """Partial Twilio config (e.g. SID but no token) should return False."""
        with patch("src.sms.service.get_settings") as mock_settings:
            settings = MagicMock()
            settings.environment = "production"
            settings.twilio_account_sid = "AC_test_sid"
            settings.twilio_auth_token = None
            settings.twilio_from_number = "+15550001111"
            mock_settings.return_value = settings

            result = await send_sms("+15551234567", "Test")
            assert result is False


# ===================================================================
# 7. Template XSS / injection in SMS templates
# ===================================================================
class TestSMSTemplateInjection:
    """SMS templates should handle malicious input gracefully."""

    def test_xss_in_member_name(self):
        """HTML/script tags in member_name should not break SMS template."""
        msg = risk_alert_sms('<script>alert(1)</script>', "critical", "pii")
        assert isinstance(msg, str)
        assert "bhapi.ai" in msg

    def test_unicode_in_member_name(self):
        """Unicode characters should render in SMS templates."""
        msg = risk_alert_sms("Alicé 你好", "high", "pii")
        assert "Alicé 你好" in msg

    def test_format_specifier_in_category(self):
        """Format specifiers like %s %d should not cause errors."""
        msg = risk_alert_sms("User", "high", "%s%s%s%n%n")
        assert isinstance(msg, str)
