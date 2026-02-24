"""Alert re-notification scheduler.

Runs every 5 minutes. Re-sends email for unacknowledged critical/high alerts:
- Critical: re-notify after 15 minutes
- High: re-notify after 30 minutes
- Max 3 re-notifications per alert

After max re-notifications, clears re_notify_at to stop escalation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.delivery import deliver_alert_email
from src.alerts.models import Alert
from src.constants import RENOTIFY_INTERVALS

logger = structlog.get_logger()

# Maximum number of re-notification attempts per alert
MAX_RENOTIFICATIONS = 3

# Track re-notification count in a simple way using re_notify_at cycles
# We use a metadata approach: count how many times status went through "sent" → re-sent
_renotify_counts: dict[str, int] = {}


async def run_renotification_check(db: AsyncSession) -> int:
    """Check for unacknowledged alerts that need re-notification.

    Returns the number of alerts re-notified.
    """
    now = datetime.now(timezone.utc)
    renotified = 0

    # Find alerts that are due for re-notification
    result = await db.execute(
        select(Alert).where(
            Alert.status.in_(["pending", "sent"]),
            Alert.severity.in_(["critical", "high"]),
            Alert.re_notify_at.isnot(None),
            Alert.re_notify_at <= now,
        ).limit(50)
    )
    alerts = list(result.scalars().all())

    for alert in alerts:
        alert_key = str(alert.id)
        count = _renotify_counts.get(alert_key, 0)

        if count >= MAX_RENOTIFICATIONS:
            # Max re-notifications reached — stop escalating
            alert.re_notify_at = None
            _renotify_counts.pop(alert_key, None)
            logger.info(
                "renotify_max_reached",
                alert_id=alert_key,
                count=count,
            )
            continue

        # Re-send the alert email
        try:
            sent = await deliver_alert_email(db, alert)
            if sent:
                _renotify_counts[alert_key] = count + 1
                renotified += 1

                # Schedule next re-notification
                interval = RENOTIFY_INTERVALS.get(alert.severity, 1800)
                alert.re_notify_at = now + timedelta(seconds=interval)

                logger.info(
                    "alert_renotified",
                    alert_id=alert_key,
                    severity=alert.severity,
                    attempt=count + 1,
                    next_at=alert.re_notify_at.isoformat(),
                )
        except Exception as exc:
            logger.error(
                "renotify_error",
                alert_id=alert_key,
                error=str(exc),
            )

    await db.flush()
    return renotified


async def schedule_renotification(db: AsyncSession, alert: Alert) -> None:
    """Set the initial re-notification time for an alert.

    Called after an alert is first sent. Only applies to critical/high.
    """
    if alert.severity not in ("critical", "high"):
        return

    interval = RENOTIFY_INTERVALS.get(alert.severity, 1800)
    alert.re_notify_at = datetime.now(timezone.utc) + timedelta(seconds=interval)
    await db.flush()

    logger.debug(
        "renotify_scheduled",
        alert_id=str(alert.id),
        severity=alert.severity,
        re_notify_at=alert.re_notify_at.isoformat(),
    )


def clear_renotification(alert_id: str) -> None:
    """Clear re-notification tracking for an acknowledged alert."""
    _renotify_counts.pop(alert_id, None)


def reset_renotify_state() -> None:
    """Reset all re-notification state. Used in tests."""
    _renotify_counts.clear()
