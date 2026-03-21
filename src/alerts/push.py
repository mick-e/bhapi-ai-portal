"""Expo push notification service for mobile apps.

Sends push notifications via Expo's Push API to registered iOS/Android devices.
Manages push token registration (upsert/remove) per user.
"""

import uuid
from datetime import datetime, timezone

import httpx
import structlog
from sqlalchemy import String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import TimestampMixin, UUIDMixin

logger = structlog.get_logger()

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class PushToken(Base, UUIDMixin, TimestampMixin):
    """An Expo push token registered for a user's mobile device."""

    __tablename__ = "push_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    device_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # ios | android


class ExpoPushService:
    """Service for sending push notifications via Expo Push API."""

    def __init__(self, push_url: str = EXPO_PUSH_URL):
        self.push_url = push_url

    async def register_token(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        token: str,
        device_type: str,
    ) -> PushToken:
        """Register or update an Expo push token for a user.

        Upserts by token — if the token already exists, updates user_id and device_type.
        """
        if device_type not in ("ios", "android"):
            from src.exceptions import ValidationError
            raise ValidationError("device_type must be 'ios' or 'android'")

        if not token or not token.startswith("ExponentPushToken["):
            from src.exceptions import ValidationError
            raise ValidationError("Invalid Expo push token format")

        # Check if token already exists
        result = await db.execute(
            select(PushToken).where(PushToken.token == token)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.user_id = user_id
            existing.device_type = device_type
            existing.updated_at = datetime.now(timezone.utc)
            await db.flush()
            await db.refresh(existing)
            logger.info(
                "push_token_updated",
                user_id=str(user_id),
                device_type=device_type,
            )
            return existing

        push_token = PushToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token=token,
            device_type=device_type,
        )
        db.add(push_token)
        await db.flush()
        await db.refresh(push_token)
        logger.info(
            "push_token_registered",
            user_id=str(user_id),
            device_type=device_type,
        )
        return push_token

    async def unregister_token(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        token: str,
    ) -> bool:
        """Remove a push token for a user. Returns True if token was found and removed."""
        result = await db.execute(
            select(PushToken).where(
                PushToken.user_id == user_id,
                PushToken.token == token,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            await db.delete(existing)
            await db.flush()
            logger.info(
                "push_token_unregistered",
                user_id=str(user_id),
            )
            return True
        return False

    async def get_user_tokens(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[PushToken]:
        """Get all push tokens for a user."""
        result = await db.execute(
            select(PushToken).where(PushToken.user_id == user_id)
        )
        return list(result.scalars().all())

    async def send_notification(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """Send a push notification to all of a user's registered devices.

        Returns True if at least one notification was sent successfully.
        """
        tokens = await self.get_user_tokens(db, user_id)
        if not tokens:
            logger.debug(
                "push_no_tokens",
                user_id=str(user_id),
            )
            return False

        messages = [
            {
                "to": t.token,
                "title": title,
                "body": body,
                "sound": "default",
                **({"data": data} if data else {}),
            }
            for t in tokens
        ]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.push_url,
                    json=messages,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()

            logger.info(
                "push_notification_sent",
                user_id=str(user_id),
                device_count=len(tokens),
                title=title,
            )
            return True

        except Exception as exc:
            logger.warning(
                "push_notification_failed",
                user_id=str(user_id),
                error=str(exc),
            )
            return False


# Module-level singleton
expo_push_service = ExpoPushService()
