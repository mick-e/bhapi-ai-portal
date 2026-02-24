"""Unit tests for the email service."""

import pytest

from src.email.service import (
    EmailRateLimitError,
    _check_rate_limit,
    reset_rate_limits,
    send_email,
)
from src.email import templates


class TestEmailService:
    """Tests for the core send_email function."""

    def setup_method(self):
        reset_rate_limits()

    @pytest.mark.asyncio
    async def test_send_email_dev_mode_logs(self):
        """In dev/test mode, emails are logged, not sent."""
        result = await send_email(
            to_email="test@example.com",
            subject="Test Subject",
            html_content="<p>Hello</p>",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_email_with_plain_content(self):
        result = await send_email(
            to_email="test@example.com",
            subject="Test",
            html_content="<p>Hello</p>",
            plain_content="Hello",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_email_with_group_id(self):
        result = await send_email(
            to_email="test@example.com",
            subject="Test",
            html_content="<p>Hello</p>",
            group_id="test-group-123",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_email_to_many(self):
        from src.email.service import send_email_to_many
        results = await send_email_to_many(
            to_emails=["a@example.com", "b@example.com", "c@example.com"],
            subject="Test",
            html_content="<p>Hello</p>",
        )
        assert len(results) == 3
        assert all(v is True for v in results.values())


class TestRateLimit:
    """Tests for the email rate limiter."""

    def setup_method(self):
        reset_rate_limits()

    def test_under_limit_passes(self):
        for _ in range(10):
            _check_rate_limit("group-1")

    def test_at_limit_raises(self):
        for _ in range(100):
            _check_rate_limit("group-1")
        with pytest.raises(EmailRateLimitError):
            _check_rate_limit("group-1")

    def test_different_groups_independent(self):
        for _ in range(100):
            _check_rate_limit("group-a")
        # Different group should still work
        _check_rate_limit("group-b")

    @pytest.mark.asyncio
    async def test_rate_limited_email_returns_false(self):
        group_id = "rate-test-group"
        for _ in range(100):
            _check_rate_limit(group_id)

        result = await send_email(
            to_email="test@example.com",
            subject="Test",
            html_content="<p>Hello</p>",
            group_id=group_id,
        )
        assert result is False

    def test_reset_clears_limits(self):
        for _ in range(100):
            _check_rate_limit("group-1")
        reset_rate_limits()
        # Should work again
        _check_rate_limit("group-1")


class TestEmailTemplates:
    """Tests for email template functions."""

    def test_risk_alert_template(self):
        subject, html, plain = templates.risk_alert(
            member_name="Alice",
            severity="critical",
            category="SELF_HARM",
            category_description="Self-harm ideation",
            platform="ChatGPT",
            confidence=0.92,
            reasoning="Keyword match detected",
            group_name="Test Family",
            alert_url="https://bhapi.ai/alerts/123",
        )
        assert "CRITICAL" in subject
        assert "Alice" in subject
        assert "Alice" in html
        assert "ChatGPT" in html
        assert "92%" in html
        assert "bhapi.ai/alerts/123" in html
        assert "Alice" in plain
        assert "92%" in plain

    def test_email_verification_template(self):
        subject, html, plain = templates.email_verification(
            display_name="Bob",
            verification_url="https://bhapi.ai/verify?token=abc",
        )
        assert "Verify" in subject
        assert "Bob" in html
        assert "verify?token=abc" in html
        assert "24 hours" in html
        assert "Bob" in plain

    def test_password_reset_template(self):
        subject, html, plain = templates.password_reset(
            display_name="Carol",
            reset_url="https://bhapi.ai/reset?token=xyz",
        )
        assert "Reset" in subject
        assert "Carol" in html
        assert "reset?token=xyz" in html
        assert "1 hour" in html
        assert "Carol" in plain

    def test_group_invitation_template(self):
        subject, html, plain = templates.group_invitation(
            inviter_name="Dave",
            group_name="Smith Family",
            role="parent",
            invitation_url="https://bhapi.ai/invite?token=123",
        )
        assert "Smith Family" in subject
        assert "Dave" in html
        assert "parent" in html
        assert "invite?token=123" in html
        assert "7 days" in html

    def test_alert_digest_template(self):
        subject, html, plain = templates.alert_digest(
            group_name="Test Family",
            period="daily",
            total_alerts=5,
            by_severity={"critical": 1, "high": 2, "medium": 2},
            alert_summaries=[
                {"severity": "critical", "title": "Self-harm detected", "member_name": "Alice"},
                {"severity": "high", "title": "PII shared", "member_name": "Bob"},
            ],
            dashboard_url="https://bhapi.ai/dashboard",
        )
        assert "5 alerts" in subject
        assert "daily" in subject
        assert "Self-harm detected" in html
        assert "Alice" in html
        assert "bhapi.ai/dashboard" in html

    def test_report_ready_template(self):
        subject, html, plain = templates.report_ready(
            report_type="Safety",
            group_name="Test Family",
            period="January 2026",
            download_url="https://bhapi.ai/reports/456/download",
        )
        assert "Safety" in subject
        assert "Test Family" in subject
        assert "January 2026" in html
        assert "reports/456/download" in html

    def test_all_templates_have_html_structure(self):
        """All templates should produce valid HTML with the layout wrapper."""
        templates_to_test = [
            templates.risk_alert(
                member_name="X", severity="high", category="PII", category_description="PII",
                platform="Gemini", confidence=0.5, reasoning="test", group_name="G", alert_url="http://x",
            ),
            templates.email_verification(display_name="X", verification_url="http://x"),
            templates.password_reset(display_name="X", reset_url="http://x"),
            templates.group_invitation(
                inviter_name="X", group_name="G", role="member", invitation_url="http://x",
            ),
            templates.alert_digest(
                group_name="G", period="hourly", total_alerts=0, by_severity={},
                alert_summaries=[], dashboard_url="http://x",
            ),
            templates.report_ready(
                report_type="Safety", group_name="G", period="Jan", download_url="http://x",
            ),
        ]
        for subject, html, plain in templates_to_test:
            assert subject  # Not empty
            assert "<!DOCTYPE html>" in html
            assert "Bhapi" in html
            assert plain  # Not empty
