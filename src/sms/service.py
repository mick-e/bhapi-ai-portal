"""SMS notification service via Twilio REST API."""

from __future__ import annotations

import time
from collections import defaultdict

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings

logger = structlog.get_logger()

# Rate limiting: 10 SMS per minute per group
_sms_rate_windows: dict[str, list[float]] = defaultdict(list)
_SMS_RATE_LIMIT = 10
_SMS_RATE_WINDOW = 60


class SMSRateLimitError(Exception):
    pass


def _check_sms_rate(group_id: str) -> None:
    now = time.monotonic()
    window = _sms_rate_windows[group_id]
    _sms_rate_windows[group_id] = [t for t in window if now - t < _SMS_RATE_WINDOW]
    if len(_sms_rate_windows[group_id]) >= _SMS_RATE_LIMIT:
        raise SMSRateLimitError(f"Group {group_id} exceeded {_SMS_RATE_LIMIT} SMS per minute")
    _sms_rate_windows[group_id].append(now)


async def send_sms(
    to_phone: str,
    message: str,
    group_id: str | None = None,
    member_id: str | None = None,
    db: "AsyncSession | None" = None,
) -> bool:
    """Send an SMS via Twilio. In dev/test, log only."""
    settings = get_settings()

    if group_id:
        try:
            _check_sms_rate(group_id)
        except SMSRateLimitError:
            logger.warning("sms_rate_limited", group_id=group_id, to=to_phone)
            return False

    # COPPA 2026: Check third-party consent before sending via Twilio
    if group_id and member_id and db:
        from uuid import UUID as _UUID
        from src.compliance.coppa_2026 import check_third_party_consent
        has_consent = await check_third_party_consent(
            db, _UUID(group_id), _UUID(member_id), "twilio_sms"
        )
        if not has_consent:
            logger.info(
                "sms_skipped_no_twilio_consent",
                group_id=group_id,
                member_id=member_id,
            )
            return False

    if settings.environment in ("development", "test"):
        logger.info("sms_logged_dev_mode", to=to_phone, message=message[:100])
        return True

    account_sid = getattr(settings, "twilio_account_sid", None)
    auth_token = getattr(settings, "twilio_auth_token", None)
    from_number = getattr(settings, "twilio_from_number", None)

    if not all([account_sid, auth_token, from_number]):
        logger.error("sms_not_configured", msg="Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER")
        return False

    import httpx

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                auth=(account_sid, auth_token),
                data={
                    "To": to_phone,
                    "From": from_number,
                    "Body": message[:1600],
                },
            )
            if resp.status_code in (200, 201):
                logger.info("sms_sent", to=to_phone, sid=resp.json().get("sid"))
                return True
            logger.error("sms_send_error", status=resp.status_code, body=resp.text[:200])
            return False
    except Exception as exc:
        logger.error("sms_send_exception", error=str(exc))
        return False


def reset_sms_rate_limits() -> None:
    """Reset SMS rate limit windows. Used in tests."""
    _sms_rate_windows.clear()
