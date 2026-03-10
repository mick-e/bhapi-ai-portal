"""Alert digest batching — collects and sends batched alert notifications.

Digest modes:
- hourly: Collects alerts from the past hour, sends to users with hourly preference
- daily: Collects alerts from the past 24 hours, sends to users with daily preference
- weekly: Collects alerts from the past 7 days, sends to users with weekly preference

Each user receives a single digest email per window, grouped by severity then category.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert, NotificationPreference
from src.auth.models import User
from src.groups.models import Group, GroupMember

logger = structlog.get_logger()


async def run_hourly_digest(db: AsyncSession) -> int:
    """Collect and send hourly digest emails.

    Returns the number of digest emails sent.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=1)
    return await _run_digest(db, window_start, now, "hourly")


async def run_daily_digest(db: AsyncSession) -> int:
    """Collect and send daily digest emails.

    Returns the number of digest emails sent.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)
    return await _run_digest(db, window_start, now, "daily")


async def run_weekly_digest(db: AsyncSession) -> int:
    """Collect and send weekly digest emails.

    Returns the number of digest emails sent.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)
    return await _run_digest(db, window_start, now, "weekly")


async def _run_digest(
    db: AsyncSession,
    window_start: datetime,
    window_end: datetime,
    digest_mode: str,
) -> int:
    """Core digest logic: collect alerts, group by user, send digest emails."""
    from src.email import templates
    from src.email.service import send_email

    # Find users who want this digest mode for risk_alert category
    prefs_result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.category == "risk_alert",
            NotificationPreference.channel == "email",
            NotificationPreference.digest_mode == digest_mode,
            NotificationPreference.enabled.is_(True),
        )
    )
    preferences = list(prefs_result.scalars().all())

    if not preferences:
        return 0

    # Group preferences by group_id
    group_user_map: dict[UUID, list[UUID]] = {}
    for pref in preferences:
        group_user_map.setdefault(pref.group_id, []).append(pref.user_id)

    sent_count = 0

    for group_id, user_ids in group_user_map.items():
        # Get alerts for this group in the time window
        alerts_result = await db.execute(
            select(Alert).where(
                Alert.group_id == group_id,
                Alert.created_at >= window_start,
                Alert.created_at <= window_end,
                Alert.status.in_(["pending", "sent"]),
            ).order_by(Alert.created_at.desc())
        )
        alerts = list(alerts_result.scalars().all())

        if not alerts:
            continue

        # Load group info
        group_result = await db.execute(select(Group).where(Group.id == group_id))
        group = group_result.scalar_one_or_none()
        if not group:
            continue

        # Load member names for display
        members_result = await db.execute(
            select(GroupMember).where(GroupMember.group_id == group_id)
        )
        members = {m.id: m.display_name for m in members_result.scalars().all()}

        # Build digest data
        by_severity: dict[str, int] = {}
        alert_summaries: list[dict] = []
        for alert in alerts:
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
            alert_summaries.append({
                "severity": alert.severity,
                "title": alert.title,
                "member_name": members.get(alert.member_id, "Unknown") if alert.member_id else "",
            })

        period = "hourly" if digest_mode == "hourly" else "daily"

        subject, html, plain = templates.alert_digest(
            group_name=group.name,
            period=period,
            total_alerts=len(alerts),
            by_severity=by_severity,
            alert_summaries=alert_summaries,
            dashboard_url=f"https://bhapi.ai/dashboard?group={group_id}",
        )

        # Send to each user
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = list(users_result.scalars().all())

        for user in users:
            success = await send_email(
                to_email=user.email,
                subject=subject,
                html_content=html,
                plain_content=plain,
                group_id=str(group_id),
            )
            if success:
                sent_count += 1

        # Mark alerts as sent (for digest tracking)
        for alert in alerts:
            if alert.status == "pending":
                alert.status = "sent"

    await db.flush()

    logger.info(
        "digest_completed",
        mode=digest_mode,
        emails_sent=sent_count,
    )

    return sent_count
