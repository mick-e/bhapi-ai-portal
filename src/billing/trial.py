"""Trial status computation.

Uses Group.created_at as trial start. Supports manual extensions via
group.settings["trial_extended_until"] — no migration needed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import Subscription
from src.billing.schemas import TrialStatusResponse
from src.groups.models import Group

FREE_TRIAL_DAYS = 14


async def get_trial_status(db: AsyncSession, group_id: UUID) -> TrialStatusResponse:
    """Compute trial/subscription status for a group."""
    # Check for active paid subscription
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.group_id == group_id,
            Subscription.status.in_(["active", "trialing"]),
            Subscription.plan_type != "free",
        )
    )
    subscription = sub_result.scalar_one_or_none()

    if subscription:
        return TrialStatusResponse(
            is_active=True,
            is_trial=False,
            is_locked=False,
            days_remaining=0,
            trial_end=None,
            plan=subscription.plan_type,
        )

    # No paid subscription — compute trial status from Group.created_at
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        from src.exceptions import NotFoundError
        raise NotFoundError("Group", str(group_id))

    now = datetime.now(timezone.utc)
    created_at = group.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    trial_end = created_at + timedelta(days=FREE_TRIAL_DAYS)

    # Check for manual extension
    settings = group.settings or {}
    extended_until_str = settings.get("trial_extended_until")
    if extended_until_str:
        try:
            extended_until = datetime.fromisoformat(extended_until_str)
            if extended_until.tzinfo is None:
                extended_until = extended_until.replace(tzinfo=timezone.utc)
            trial_end = max(trial_end, extended_until)
        except (ValueError, TypeError):
            pass

    days_remaining = max(0, (trial_end - now).days)
    is_locked = days_remaining <= 0

    return TrialStatusResponse(
        is_active=not is_locked,
        is_trial=True,
        is_locked=is_locked,
        days_remaining=days_remaining,
        trial_end=trial_end,
        plan="free",
    )
