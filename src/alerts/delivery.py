"""Alert email delivery — sends email notifications for risk alerts.

Delivery rules by severity:
- critical/high → immediate email to all group admins
- medium → per user preference (immediate/hourly/daily)
- low → daily digest only (never immediate)

Updates Alert.status to "sent" after successful delivery.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert, NotificationPreference
from src.auth.models import User
from src.groups.models import Group, GroupMember
from src.risk.taxonomy import RISK_CATEGORIES

logger = structlog.get_logger()


async def deliver_alert_email(
    db: AsyncSession,
    alert: Alert,
) -> bool:
    """Deliver an alert via email to the appropriate recipients.

    Returns True if at least one email was sent (or logged in dev).
    """
    from src.email import templates
    from src.email.service import send_email

    # Load the group
    group_result = await db.execute(select(Group).where(Group.id == alert.group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        logger.warning("delivery_skip_no_group", alert_id=str(alert.id))
        return False

    # Determine if this alert should be sent immediately
    if not _should_send_immediate(alert):
        logger.debug(
            "delivery_deferred_to_digest",
            alert_id=str(alert.id),
            severity=alert.severity,
        )
        return False

    # COPPA 2026: Check third-party consent before sending via SendGrid
    if alert.member_id:
        from src.compliance.coppa_2026 import check_third_party_consent, check_push_notification_consent
        has_sendgrid_consent = await check_third_party_consent(
            db, alert.group_id, alert.member_id, "sendgrid"
        )
        if not has_sendgrid_consent:
            logger.info(
                "delivery_skipped_no_sendgrid_consent",
                alert_id=str(alert.id),
                group_id=str(alert.group_id),
                member_id=str(alert.member_id),
            )
            return False

        # Map severity to notification type
        notification_type = "risk_alerts"
        if alert.severity == "low":
            notification_type = "activity_summaries"

        has_push_consent = await check_push_notification_consent(
            db, alert.group_id, alert.member_id, notification_type
        )
        if not has_push_consent:
            logger.info(
                "delivery_skipped_no_push_consent",
                alert_id=str(alert.id),
                notification_type=notification_type,
            )
            return False

    # Get recipient emails (group admins)
    recipients = await _get_admin_emails(db, alert.group_id, alert.severity)
    if not recipients:
        logger.info("delivery_no_recipients", alert_id=str(alert.id))
        return False

    # Get member name
    member_name = "Unknown member"
    if alert.member_id:
        member_result = await db.execute(
            select(GroupMember.display_name).where(GroupMember.id == alert.member_id)
        )
        member_name = member_result.scalar_one_or_none() or "Unknown member"

    # Build email from template
    category_meta = RISK_CATEGORIES.get(
        _extract_category(alert.title), {}
    )
    category_description = category_meta.get("description", alert.title)

    subject, html, plain = templates.risk_alert(
        member_name=member_name,
        severity=alert.severity,
        category=_extract_category(alert.title),
        category_description=category_description,
        platform=_extract_platform(alert.body),
        confidence=_extract_confidence(alert.body),
        reasoning=alert.body,
        group_name=group.name,
        alert_url=f"https://bhapi.ai/alerts/{alert.id}",
    )

    # Send to all recipients
    sent_any = False
    for email_addr in recipients:
        success = await send_email(
            to_email=email_addr,
            subject=subject,
            html_content=html,
            plain_content=plain,
            group_id=str(alert.group_id),
        )
        if success:
            sent_any = True

    # Update alert status
    if sent_any:
        alert.status = "sent"
        alert.channel = "email"
        await db.flush()
        logger.info(
            "alert_email_delivered",
            alert_id=str(alert.id),
            recipient_count=len(recipients),
        )

    return sent_any


async def deliver_risk_alert(
    db: AsyncSession,
    alert: Alert,
) -> bool:
    """Convenience wrapper: deliver an alert email immediately if severity warrants it.

    Called from the risk pipeline after creating an alert.
    """
    if alert.severity in ("critical", "high"):
        return await deliver_alert_email(db, alert)

    # Medium alerts: check user preferences
    if alert.severity == "medium":
        immediate_recipients = await _get_immediate_preference_users(
            db, alert.group_id, "risk_alert"
        )
        if immediate_recipients:
            return await deliver_alert_email(db, alert)

    # Low severity or no immediate preference — defer to digest
    return False


def _should_send_immediate(alert: Alert) -> bool:
    """Determine if an alert should be sent immediately."""
    return alert.severity in ("critical", "high", "medium")


async def _get_admin_emails(
    db: AsyncSession,
    group_id: UUID,
    severity: str,
) -> list[str]:
    """Get email addresses of group admins who should receive alerts.

    For critical/high: all admins.
    For medium: admins with immediate preference for risk_alert.
    """
    # Get admin members (parent, school_admin, club_admin)
    members_result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.role.in_(["parent", "school_admin", "club_admin"]),
        )
    )
    admin_members = list(members_result.scalars().all())

    if not admin_members:
        return []

    # Get the user emails for these members
    user_ids = [m.user_id for m in admin_members if m.user_id is not None]
    if not user_ids:
        return []

    users_result = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users = {u.id: u for u in users_result.scalars().all()}

    # For medium severity, filter by preference
    if severity == "medium":
        immediate_users = await _get_immediate_preference_users(
            db, group_id, "risk_alert"
        )
        user_ids = [uid for uid in user_ids if uid in immediate_users]

    return [users[uid].email for uid in user_ids if uid in users]


async def _get_immediate_preference_users(
    db: AsyncSession,
    group_id: UUID,
    category: str,
) -> set[UUID]:
    """Get user IDs who have immediate notification preference for a category."""
    result = await db.execute(
        select(NotificationPreference.user_id).where(
            NotificationPreference.group_id == group_id,
            NotificationPreference.category == category,
            NotificationPreference.channel == "email",
            NotificationPreference.digest_mode == "immediate",
            NotificationPreference.enabled.is_(True),
        )
    )
    return set(result.scalars().all())


def _extract_category(title: str) -> str:
    """Extract the risk category name from an alert title."""
    # Title format: "CRITICAL risk: Content indicating self-harm..."
    # Try to match against known categories
    for cat_name in RISK_CATEGORIES:
        desc = RISK_CATEGORIES[cat_name].get("description", "")
        if desc and desc in title:
            return cat_name
    return "UNKNOWN"


def _extract_platform(body: str) -> str:
    """Extract platform name from alert body."""
    for platform in ("chatgpt", "gemini", "copilot", "claude", "grok"):
        if platform in body.lower():
            return platform
    return "unknown"


def _extract_confidence(body: str) -> float:
    """Extract confidence value from alert body."""
    import re
    match = re.search(r"(\d+)% confidence", body)
    if match:
        return int(match.group(1)) / 100.0
    return 0.0
