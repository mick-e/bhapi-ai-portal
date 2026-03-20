"""Unit tests for privacy notice acceptance at registration."""

from src.auth.schemas import RegisterRequest


class TestPrivacyNoticeSchema:
    """Tests for privacy_notice_accepted field on RegisterRequest."""

    def test_defaults_to_false(self):
        """Privacy notice defaults to False."""
        req = RegisterRequest(
            email="test@example.com",
            password="TestPass123",
            display_name="Test User",
            account_type="family",
        )
        assert req.privacy_notice_accepted is False

    def test_accepts_true(self):
        """Privacy notice can be set to True."""
        req = RegisterRequest(
            email="test@example.com",
            password="TestPass123",
            display_name="Test User",
            account_type="family",
            privacy_notice_accepted=True,
        )
        assert req.privacy_notice_accepted is True

    def test_field_is_bool(self):
        """Field type is boolean."""
        req = RegisterRequest(
            email="test@example.com",
            password="TestPass123",
            display_name="Test User",
            account_type="family",
            privacy_notice_accepted=True,
        )
        assert isinstance(req.privacy_notice_accepted, bool)
