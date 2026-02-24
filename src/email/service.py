"""Email delivery service — wraps SendGrid with graceful degradation.

In development/test mode, emails are logged instead of sent.
In production, emails are sent via SendGrid API.

Rate limiting: max 100 emails per minute per group to prevent abuse.
"""

from __future__ import annotations

import time
from collections import defaultdict

import structlog

from src.config import get_settings

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# In-memory rate limiter (per-group, 100/min sliding window)
# ---------------------------------------------------------------------------
_rate_windows: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 100
_RATE_WINDOW_SECONDS = 60


class EmailRateLimitError(Exception):
    """Raised when a group exceeds email send rate."""


def _check_rate_limit(group_id: str) -> None:
    """Check and enforce per-group rate limit."""
    now = time.monotonic()
    window = _rate_windows[group_id]

    # Prune old entries
    _rate_windows[group_id] = [t for t in window if now - t < _RATE_WINDOW_SECONDS]

    if len(_rate_windows[group_id]) >= _RATE_LIMIT:
        raise EmailRateLimitError(
            f"Group {group_id} exceeded {_RATE_LIMIT} emails per minute"
        )

    _rate_windows[group_id].append(now)


# ---------------------------------------------------------------------------
# SendGrid client (lazy-loaded)
# ---------------------------------------------------------------------------
_sg_client = None


def _get_sendgrid_client():
    """Get or create the SendGrid client singleton."""
    global _sg_client
    if _sg_client is not None:
        return _sg_client

    settings = get_settings()
    if not settings.sendgrid_api_key:
        return None

    try:
        from sendgrid import SendGridAPIClient
        _sg_client = SendGridAPIClient(settings.sendgrid_api_key)
        return _sg_client
    except ImportError:
        logger.warning("sendgrid_not_installed", msg="Install sendgrid package for email delivery")
        return None


# ---------------------------------------------------------------------------
# Core send function
# ---------------------------------------------------------------------------
async def send_email(
    *,
    to_email: str,
    subject: str,
    html_content: str,
    plain_content: str | None = None,
    from_email: str | None = None,
    group_id: str | None = None,
) -> bool:
    """Send an email via SendGrid or log in dev/test mode.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        html_content: HTML body content.
        plain_content: Optional plain text fallback.
        from_email: Sender email (defaults to noreply@bhapi.ai).
        group_id: Optional group ID for rate limiting.

    Returns:
        True if email was sent (or logged in dev), False on failure.
    """
    settings = get_settings()
    sender = from_email or "noreply@bhapi.ai"

    # Rate limit check
    if group_id:
        try:
            _check_rate_limit(group_id)
        except EmailRateLimitError:
            logger.warning(
                "email_rate_limited",
                group_id=group_id,
                to=to_email,
                subject=subject,
            )
            return False

    # Dev/test mode: log instead of sending
    if settings.environment in ("development", "test"):
        logger.info(
            "email_logged_dev_mode",
            to=to_email,
            subject=subject,
            from_email=sender,
            html_length=len(html_content),
        )
        return True

    # Production: send via SendGrid
    client = _get_sendgrid_client()
    if client is None:
        logger.error(
            "email_send_failed_no_client",
            to=to_email,
            subject=subject,
            msg="SendGrid not configured — check SENDGRID_API_KEY",
        )
        return False

    try:
        from sendgrid.helpers.mail import Content, Email, Mail, To

        message = Mail(
            from_email=Email(sender, "Bhapi"),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content),
        )
        if plain_content:
            message.add_content(Content("text/plain", plain_content))

        response = client.send(message)

        logger.info(
            "email_sent",
            to=to_email,
            subject=subject,
            status_code=response.status_code,
        )
        return 200 <= response.status_code < 300

    except Exception as exc:
        logger.error(
            "email_send_error",
            to=to_email,
            subject=subject,
            error=str(exc),
        )
        return False


# ---------------------------------------------------------------------------
# Convenience: send to multiple recipients
# ---------------------------------------------------------------------------
async def send_email_to_many(
    *,
    to_emails: list[str],
    subject: str,
    html_content: str,
    plain_content: str | None = None,
    from_email: str | None = None,
    group_id: str | None = None,
) -> dict[str, bool]:
    """Send the same email to multiple recipients.

    Returns a dict mapping email → success bool.
    """
    results: dict[str, bool] = {}
    for email_addr in to_emails:
        results[email_addr] = await send_email(
            to_email=email_addr,
            subject=subject,
            html_content=html_content,
            plain_content=plain_content,
            from_email=from_email,
            group_id=group_id,
        )
    return results


# ---------------------------------------------------------------------------
# Reset rate limiter (for testing)
# ---------------------------------------------------------------------------
def reset_rate_limits() -> None:
    """Reset all rate limit windows. Used in tests."""
    _rate_windows.clear()
