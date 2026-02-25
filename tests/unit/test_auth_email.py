"""Unit tests for auth email flows (verification + password reset)."""

import pytest

from src.auth.service import (
    _check_reset_rate_limit,
    _reset_rate_tracker,
    create_email_verification_token,
    create_password_reset_token,
    verify_email_token,
    verify_reset_token,
)
from src.exceptions import UnauthorizedError


class TestEmailVerificationToken:
    def test_create_and_verify_roundtrip(self):
        import uuid
        user_id = uuid.uuid4()
        token = create_email_verification_token(user_id)
        result = verify_email_token(token)
        assert result == user_id

    def test_invalid_token_raises(self):
        with pytest.raises(UnauthorizedError):
            verify_email_token("garbage-token")

    def test_wrong_type_raises(self):
        """A password reset token should not work for email verification."""
        import uuid
        token = create_password_reset_token(uuid.uuid4())
        with pytest.raises(UnauthorizedError, match="Invalid verification token"):
            verify_email_token(token)


class TestPasswordResetToken:
    def test_create_and_verify_roundtrip(self):
        import uuid
        user_id = uuid.uuid4()
        token = create_password_reset_token(user_id)
        result = verify_reset_token(token)
        assert result == user_id

    def test_invalid_token_raises(self):
        with pytest.raises(UnauthorizedError):
            verify_reset_token("garbage-token")

    def test_wrong_type_raises(self):
        """An email verification token should not work for password reset."""
        import uuid
        token = create_email_verification_token(uuid.uuid4())
        with pytest.raises(UnauthorizedError, match="Invalid reset token"):
            verify_reset_token(token)


class TestResetRateLimit:
    def setup_method(self):
        _reset_rate_tracker.clear()

    def test_under_limit_returns_true(self):
        assert _check_reset_rate_limit("user@example.com") is True

    def test_at_limit_returns_false(self):
        email = "limited@example.com"
        for _ in range(5):
            _check_reset_rate_limit(email)
        assert _check_reset_rate_limit(email) is False

    def test_different_emails_independent(self):
        for _ in range(5):
            _check_reset_rate_limit("a@example.com")
        assert _check_reset_rate_limit("b@example.com") is True

    def test_clear_resets(self):
        email = "test@example.com"
        for _ in range(5):
            _check_reset_rate_limit(email)
        _reset_rate_tracker.clear()
        assert _check_reset_rate_limit(email) is True
