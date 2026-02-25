"""Alerts service — business logic for notifications and preferences."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert, NotificationPreference
from src.alerts.schemas import AlertCreate, PreferenceConfig
from src.exceptions import NotFoundError

logger = structlog.get_logger()


async def create_alert(db: AsyncSession, data: AlertCreate) -> Alert:
    """Create a new alert notification."""
    alert = Alert(
        id=uuid4(),
        group_id=data.group_id,
        member_id=data.member_id,
        risk_event_id=data.risk_event_id,
        severity=data.severity,
        title=data.title,
        body=data.body,
        channel=data.channel,
        status="pending",
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)

    logger.info(
        "alert_created",
        alert_id=str(alert.id),
        severity=data.severity,
        channel=data.channel,
    )
    return alert


async def list_alerts(
    db: AsyncSession,
    group_id: UUID,
    severity: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Alert]:
    """List alerts for a group with optional filters."""
    query = select(Alert).where(Alert.group_id == group_id)

    if severity:
        query = query.where(Alert.severity == severity)
    if status:
        query = query.where(Alert.status == status)

    query = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_alert(db: AsyncSession, alert_id: UUID) -> Alert:
    """Get a single alert by ID."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise NotFoundError("Alert", str(alert_id))
    return alert


async def acknowledge_alert(
    db: AsyncSession, alert_id: UUID, user_id: UUID
) -> Alert:
    """Acknowledge an alert."""
    alert = await get_alert(db, alert_id)
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = user_id
    await db.flush()
    await db.refresh(alert)

    logger.info("alert_acknowledged", alert_id=str(alert_id), user_id=str(user_id))
    return alert


async def get_preferences(
    db: AsyncSession, group_id: UUID, user_id: UUID
) -> list[NotificationPreference]:
    """Get notification preferences for a user in a group."""
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.group_id == group_id,
            NotificationPreference.user_id == user_id,
        )
    )
    return list(result.scalars().all())


async def update_preferences(
    db: AsyncSession,
    group_id: UUID,
    user_id: UUID,
    preferences: list[PreferenceConfig],
) -> list[NotificationPreference]:
    """Update notification preferences for a user in a group.

    Upserts preferences by category — creates new ones or updates existing.
    """
    existing = await get_preferences(db, group_id, user_id)
    existing_by_category = {p.category: p for p in existing}

    updated: list[NotificationPreference] = []

    for pref_config in preferences:
        if pref_config.category in existing_by_category:
            # Update existing preference
            pref = existing_by_category[pref_config.category]
            pref.channel = pref_config.channel
            pref.digest_mode = pref_config.digest_mode
            pref.enabled = pref_config.enabled
            updated.append(pref)
        else:
            # Create new preference
            pref = NotificationPreference(
                id=uuid4(),
                group_id=group_id,
                user_id=user_id,
                category=pref_config.category,
                channel=pref_config.channel,
                digest_mode=pref_config.digest_mode,
                enabled=pref_config.enabled,
            )
            db.add(pref)
            updated.append(pref)

    await db.flush()
    for p in updated:
        await db.refresh(p)

    logger.info(
        "preferences_updated",
        group_id=str(group_id),
        user_id=str(user_id),
        count=len(updated),
    )
    return updated
