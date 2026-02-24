"""Budget threshold alerting — checks spend against thresholds after each sync.

After a spend sync, checks each group's current spend against their budget
thresholds. Fires alerts at configured percentages (default: 50%, 80%, 100%).
Each alert fires only once per level per billing period.

Severity mapping:
- Soft threshold → medium severity alert
- Hard threshold → high severity alert
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert
from src.alerts.schemas import AlertCreate
from src.alerts.service import create_alert
from src.billing.models import BudgetThreshold, SpendRecord

logger = structlog.get_logger()

# Track which (threshold_id, percentage_level) alerts have been fired
# In production this would be persisted in the database
_fired_alerts: set[tuple[str, int]] = set()


async def check_thresholds(db: AsyncSession, group_id: UUID) -> int:
    """Check a group's spend against all their budget thresholds.

    Returns the number of new alerts created.
    """
    # Get thresholds for this group
    result = await db.execute(
        select(BudgetThreshold).where(BudgetThreshold.group_id == group_id)
    )
    thresholds = list(result.scalars().all())

    if not thresholds:
        return 0

    # Get current month's total spend
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    spend_result = await db.execute(
        select(func.coalesce(func.sum(SpendRecord.amount), 0.0)).where(
            SpendRecord.group_id == group_id,
            SpendRecord.period_start >= month_start,
        )
    )
    total_spend = float(spend_result.scalar() or 0.0)

    alerts_created = 0

    for threshold in thresholds:
        notify_levels = threshold.notify_at or [50, 80, 100]
        for level in sorted(notify_levels):
            trigger_amount = threshold.amount * (level / 100.0)

            if total_spend >= trigger_amount:
                # Check if we already fired this alert
                alert_key = (str(threshold.id), level)
                if alert_key in _fired_alerts:
                    continue

                # Determine severity based on threshold type
                if level >= 100:
                    severity = "high" if threshold.type == "hard" else "medium"
                else:
                    severity = "medium" if threshold.type == "soft" else "medium"

                title = f"Budget alert: {level}% of ${threshold.amount:.2f} reached"
                body = (
                    f"Your group has spent ${total_spend:.2f} of your "
                    f"${threshold.amount:.2f} {threshold.type} budget "
                    f"({level}% threshold). "
                )
                if level >= 100:
                    body += "Budget exceeded."
                elif level >= 80:
                    body += "Approaching budget limit."
                else:
                    body += "Spend is increasing."

                await create_alert(
                    db=db,
                    data=AlertCreate(
                        group_id=group_id,
                        member_id=threshold.member_id,
                        severity=severity,
                        title=title[:500],
                        body=body[:2000],
                        channel="portal",
                    ),
                )
                _fired_alerts.add(alert_key)
                alerts_created += 1

                logger.info(
                    "budget_threshold_alert",
                    group_id=str(group_id),
                    threshold_id=str(threshold.id),
                    level=level,
                    spend=total_spend,
                    budget=threshold.amount,
                )

    return alerts_created


async def check_all_group_thresholds(db: AsyncSession) -> int:
    """Check thresholds for all groups that have them.

    Called after spend sync completes. Returns total alerts created.
    """
    result = await db.execute(
        select(func.distinct(BudgetThreshold.group_id))
    )
    group_ids = list(result.scalars().all())

    total_alerts = 0
    for group_id in group_ids:
        try:
            count = await check_thresholds(db, group_id)
            total_alerts += count
        except Exception as exc:
            logger.error(
                "threshold_check_error",
                group_id=str(group_id),
                error=str(exc),
            )

    logger.info("threshold_check_completed", groups=len(group_ids), alerts=total_alerts)
    return total_alerts


def reset_fired_alerts() -> None:
    """Reset fired alerts tracking. Called at the start of each billing period or in tests."""
    _fired_alerts.clear()
