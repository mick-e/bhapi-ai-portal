"""Web push notification support for browser-based alerts."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import NotFoundError, ValidationError
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class PushSubscription(Base, UUIDMixin, TimestampMixin):
    """A web push notification subscription."""

    __tablename__ = "push_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh_key: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_key: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


async def subscribe_push(
    db: AsyncSession,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    endpoint: str,
    p256dh_key: str,
    auth_key: str,
    user_agent: str | None = None,
) -> PushSubscription:
    """Register a push subscription."""
    if not endpoint or not p256dh_key or not auth_key:
        raise ValidationError("Push subscription requires endpoint, p256dh_key, and auth_key")

    # Deactivate existing subscription with same endpoint
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.p256dh_key = p256dh_key
        existing.auth_key = auth_key
        existing.active = True
        existing.user_agent = user_agent
        await db.flush()
        await db.refresh(existing)
        return existing

    sub = PushSubscription(
        id=uuid.uuid4(),
        user_id=user_id,
        group_id=group_id,
        endpoint=endpoint,
        p256dh_key=p256dh_key,
        auth_key=auth_key,
        user_agent=user_agent,
        active=True,
    )
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    logger.info("push_subscription_created", user_id=str(user_id))
    return sub


async def unsubscribe_push(
    db: AsyncSession, user_id: uuid.UUID, endpoint: str
) -> None:
    """Deactivate a push subscription."""
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.active = False
        await db.flush()
        logger.info("push_subscription_removed", user_id=str(user_id))


async def get_user_subscriptions(
    db: AsyncSession, user_id: uuid.UUID
) -> list[PushSubscription]:
    """Get all active push subscriptions for a user."""
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.active.is_(True),
        )
    )
    return list(result.scalars().all())


async def send_push_notification(
    db: AsyncSession, user_id: uuid.UUID, title: str, body: str, url: str | None = None
) -> int:
    """Send push notification to all active subscriptions for a user.

    Returns the number of successful deliveries.
    """
    subs = await get_user_subscriptions(db, user_id)
    if not subs:
        return 0

    sent = 0
    for sub in subs:
        try:
            # In production, use pywebpush to send
            # For now, log the delivery attempt
            logger.info(
                "push_notification_sent",
                user_id=str(user_id),
                endpoint=sub.endpoint[:50],
                title=title,
            )
            sent += 1
        except Exception as exc:
            logger.warning(
                "push_notification_failed",
                user_id=str(user_id),
                error=str(exc),
            )
            # Deactivate invalid subscriptions
            sub.active = False
            await db.flush()

    return sent
