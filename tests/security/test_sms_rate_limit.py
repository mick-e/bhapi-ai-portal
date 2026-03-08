"""Security tests for SMS flood prevention."""

import pytest

from src.sms.service import SMSRateLimitError, _check_sms_rate, reset_sms_rate_limits


def test_sms_rate_limit_enforced():
    """SMS should be rate limited to 10 per minute per group."""
    reset_sms_rate_limits()
    group_id = "test-group-sms"

    # First 10 should succeed
    for _ in range(10):
        _check_sms_rate(group_id)

    # 11th should be rejected
    with pytest.raises(SMSRateLimitError):
        _check_sms_rate(group_id)


def test_sms_rate_limit_per_group():
    """Rate limit should be per-group, not global."""
    reset_sms_rate_limits()

    # Fill group A
    for _ in range(10):
        _check_sms_rate("group-a")

    # Group B should still work
    _check_sms_rate("group-b")  # Should not raise
