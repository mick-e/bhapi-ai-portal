"""Unit tests for SMS service."""

import pytest

from src.sms.service import send_sms, reset_sms_rate_limits
from src.sms.templates import risk_alert_sms, spend_alert_sms, digest_summary_sms


@pytest.mark.asyncio
async def test_sms_dev_mode_logs():
    """SMS in dev/test mode should return True (logged)."""
    reset_sms_rate_limits()
    result = await send_sms("+15551234567", "Test message", group_id="test-group")
    assert result is True


@pytest.mark.asyncio
async def test_sms_rate_limit():
    """SMS should be rate limited per group."""
    reset_sms_rate_limits()
    group_id = "rate-test"

    # Send 10 (the limit)
    for _ in range(10):
        result = await send_sms("+15551234567", "msg", group_id=group_id)
        assert result is True

    # 11th should fail
    result = await send_sms("+15551234567", "msg", group_id=group_id)
    assert result is False


def test_risk_alert_template():
    msg = risk_alert_sms("Alice", "high", "self_harm")
    assert "HIGH" in msg
    assert "Alice" in msg
    assert "bhapi.ai" in msg


def test_spend_alert_template():
    msg = spend_alert_sms(45.00, 50.00, 90)
    assert "45.00" in msg
    assert "50.00" in msg
    assert "90%" in msg


def test_digest_summary_template():
    msg = digest_summary_sms(5, "daily")
    assert "5 alerts" in msg
    assert "daily" in msg
