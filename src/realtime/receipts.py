"""Read receipt manager — tracks per-user read cursors for conversations."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.messaging import ConversationMember, Message

logger = structlog.get_logger()


class ReadReceiptManager:
    """Manages read receipts using the ConversationMember.last_read_at field.

    Read receipts are persisted in the database via the existing
    ConversationMember model (last_read_at column).
    """

    async def mark_read(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        read_at: datetime | None = None,
    ) -> datetime:
        """Mark a conversation as read up to a given timestamp.

        Returns the timestamp used for the read receipt.
        """
        ts = read_at or datetime.now(timezone.utc)

        result = await db.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            logger.warning(
                "read_receipt_no_membership",
                conversation_id=str(conversation_id),
                user_id=str(user_id),
            )
            return ts

        member.last_read_at = ts
        await db.flush()

        logger.info(
            "read_receipt_updated",
            conversation_id=str(conversation_id),
            user_id=str(user_id),
            read_at=ts.isoformat(),
        )
        return ts

    async def get_unread_count(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
    ) -> int:
        """Get the number of unread messages in a conversation for a user.

        Counts approved messages created after the user's last_read_at.
        If the user has never read the conversation, all approved messages
        are unread.
        """
        # Get the user's last_read_at
        member_result = await db.execute(
            select(ConversationMember.last_read_at).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
            )
        )
        row = member_result.first()
        if not row:
            return 0

        last_read_at = row[0]

        # Count approved messages after last_read_at
        stmt = select(func.count()).where(
            Message.conversation_id == conversation_id,
            Message.moderation_status == "approved",
            Message.sender_id != user_id,  # Don't count own messages
        )
        if last_read_at:
            stmt = stmt.where(Message.created_at > last_read_at)

        result = await db.execute(stmt)
        return result.scalar() or 0

    async def get_last_read(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
    ) -> datetime | None:
        """Get the last read timestamp for a user in a conversation."""
        result = await db.execute(
            select(ConversationMember.last_read_at).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
            )
        )
        row = result.first()
        return row[0] if row else None

    async def get_read_status(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        member_user_ids: list[UUID],
    ) -> dict[str, datetime | None]:
        """Get read status for multiple members of a conversation.

        Returns a dict mapping user_id (str) -> last_read_at.
        """
        result = await db.execute(
            select(
                ConversationMember.user_id,
                ConversationMember.last_read_at,
            ).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id.in_(member_user_ids),
            )
        )
        rows = result.all()
        return {str(r[0]): r[1] for r in rows}


# Module-level singleton
receipt_manager = ReadReceiptManager()
