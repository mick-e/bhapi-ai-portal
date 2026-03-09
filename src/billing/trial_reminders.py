"""Daily job: send trial expiry reminder emails.

Sends reminders at 3 days, 1 day, and 0 days remaining.
Tracks sent reminders in group.settings["trial_reminders_sent"] to avoid duplicates.
"""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.billing.models import Subscription
from src.billing.trial import FREE_TRIAL_DAYS, get_trial_status
from src.email import templates
from src.email.service import send_email
from src.groups.models import Group

logger = structlog.get_logger()

SUBSCRIBE_URL = "https://bhapi.ai/settings?tab=billing"
CONTACT_EMAIL = "contactus@bhapi.io"
REMINDER_DAYS = {3, 1, 0}


async def send_trial_reminders(db: AsyncSession) -> dict:
    """Send trial expiry reminder emails to groups without paid subscriptions."""
    # Groups with active paid subscriptions — exclude these
    paid_sub = select(Subscription.group_id).where(
        Subscription.status.in_(["active", "trialing"]),
        Subscription.plan_type != "free",
    )
    paid_group_ids = {row[0] for row in (await db.execute(paid_sub)).all()}

    # All groups
    groups_result = await db.execute(select(Group))
    groups = list(groups_result.scalars().all())

    sent_count = 0
    skipped = 0

    for group in groups:
        if group.id in paid_group_ids:
            continue

        trial = await get_trial_status(db, group.id)
        if not trial.is_trial:
            continue

        days = trial.days_remaining
        if days not in REMINDER_DAYS:
            continue

        # Check if already sent for this day
        settings = dict(group.settings or {})
        sent_list = settings.get("trial_reminders_sent", [])
        reminder_key = f"day_{days}"
        if reminder_key in sent_list:
            skipped += 1
            continue

        # Find group owner
        if not group.owner_id:
            continue
        owner_result = await db.execute(
            select(User).where(User.id == group.owner_id)
        )
        owner = owner_result.scalar_one_or_none()
        if not owner or not owner.email:
            continue

        # Build and send email
        if days == 0:
            subject, html, plain = templates.trial_expired(
                display_name=owner.display_name,
                group_name=group.name,
                contact_email=CONTACT_EMAIL,
                subscribe_url=SUBSCRIBE_URL,
            )
        elif days == 1:
            subject, html, plain = templates.trial_expiring_tomorrow(
                display_name=owner.display_name,
                group_name=group.name,
                subscribe_url=SUBSCRIBE_URL,
            )
        else:
            subject, html, plain = templates.trial_reminder(
                display_name=owner.display_name,
                group_name=group.name,
                days_remaining=days,
                subscribe_url=SUBSCRIBE_URL,
            )

        try:
            await send_email(
                to_email=owner.email,
                subject=subject,
                html_content=html,
                plain_content=plain,
            )
        except Exception:
            logger.warning(
                "trial_reminder_email_failed",
                group_id=str(group.id),
                days_remaining=days,
            )
            continue

        # Mark as sent
        sent_list.append(reminder_key)
        settings["trial_reminders_sent"] = sent_list
        group.settings = settings
        sent_count += 1

        logger.info(
            "trial_reminder_sent",
            group_id=str(group.id),
            owner_email=owner.email,
            days_remaining=days,
        )

    await db.flush()

    return {
        "reminders_sent": sent_count,
        "skipped_already_sent": skipped,
        "groups_checked": len(groups),
    }
