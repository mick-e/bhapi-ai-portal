"""Messaging module business logic — conversations, messages, membership."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.age_tier import check_permission, get_permissions
from src.exceptions import ForbiddenError, NotFoundError, ValidationError
from src.messaging.models import Conversation, ConversationMember, Message

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


async def create_conversation(
    db: AsyncSession,
    created_by: UUID,
    conv_type: str = "direct",
    title: str | None = None,
    member_user_ids: list[UUID] | None = None,
    age_tier: str | None = None,
) -> dict:
    """Create a conversation and add members (including creator).

    For "direct" type, enforce max 2 members.
    Check can_message permission via age_tier.
    """
    if conv_type not in ("direct", "group"):
        raise ValidationError("Conversation type must be 'direct' or 'group'")

    # Check messaging permission via age tier
    if age_tier:
        _check_can_message(age_tier)

    member_ids = list(member_user_ids or [])

    # Ensure creator is included
    if created_by not in member_ids:
        member_ids.append(created_by)

    # Direct conversations must have exactly 2 members
    if conv_type == "direct":
        if len(member_ids) != 2:
            raise ValidationError(
                "Direct conversations must have exactly 2 members"
            )
        if title is not None:
            title = None  # Direct conversations don't have titles

    if len(member_ids) < 2:
        raise ValidationError("Conversations require at least 2 members")

    conversation = Conversation(
        id=uuid4(),
        type=conv_type,
        created_by=created_by,
        title=title,
    )
    db.add(conversation)
    await db.flush()

    # Add members
    for uid in member_ids:
        role = "admin" if uid == created_by else "member"
        member = ConversationMember(
            id=uuid4(),
            conversation_id=conversation.id,
            user_id=uid,
            role=role,
        )
        db.add(member)

    await db.flush()
    await db.refresh(conversation)

    logger.info(
        "conversation_created",
        conversation_id=str(conversation.id),
        type=conv_type,
        member_count=len(member_ids),
    )

    return {
        "id": conversation.id,
        "type": conversation.type,
        "title": conversation.title,
        "created_by": conversation.created_by,
        "member_count": len(member_ids),
        "created_at": conversation.created_at,
    }


async def list_conversations(
    db: AsyncSession,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List conversations the user is a member of, ordered by most recent message."""
    # Get conversation IDs the user is a member of
    member_subq = (
        select(ConversationMember.conversation_id)
        .where(ConversationMember.user_id == user_id)
        .subquery()
    )

    # Count total
    count_stmt = select(func.count()).select_from(
        select(Conversation.id)
        .where(Conversation.id.in_(select(member_subq.c.conversation_id)))
        .subquery()
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    # Get conversations ordered by created_at desc (latest message ordering
    # deferred to Phase 2 with real-time support)
    offset = (page - 1) * page_size
    stmt = (
        select(Conversation)
        .where(Conversation.id.in_(select(member_subq.c.conversation_id)))
        .order_by(Conversation.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()

    # Get member counts for each conversation
    items = []
    for conv in conversations:
        count_result = await db.execute(
            select(func.count()).where(
                ConversationMember.conversation_id == conv.id
            )
        )
        member_count = count_result.scalar() or 0
        items.append({
            "id": conv.id,
            "type": conv.type,
            "title": conv.title,
            "created_by": conv.created_by,
            "member_count": member_count,
            "created_at": conv.created_at,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_conversation(
    db: AsyncSession,
    conversation_id: UUID,
    user_id: UUID,
) -> dict:
    """Get conversation detail (verify user is member)."""
    # Verify membership
    await _verify_membership(db, conversation_id, user_id)

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise NotFoundError("Conversation", str(conversation_id))

    # Get member count
    count_result = await db.execute(
        select(func.count()).where(
            ConversationMember.conversation_id == conversation_id
        )
    )
    member_count = count_result.scalar() or 0

    return {
        "id": conversation.id,
        "type": conversation.type,
        "title": conversation.title,
        "created_by": conversation.created_by,
        "member_count": member_count,
        "created_at": conversation.created_at,
    }


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


async def send_message(
    db: AsyncSession,
    conversation_id: UUID,
    sender_id: UUID,
    content: str,
    message_type: str = "text",
    age_tier: str | None = None,
) -> Message:
    """Send a message to a conversation.

    Submits to moderation pipeline. Checks can_message permission.
    Enforces max_message_length from age tier.
    """
    # Check messaging permission
    if age_tier:
        _check_can_message(age_tier)
        _check_message_length(age_tier, content)

    # Verify sender is a member
    await _verify_membership(db, conversation_id, sender_id)

    # Verify conversation exists
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    if not conv_result.scalar_one_or_none():
        raise NotFoundError("Conversation", str(conversation_id))

    message = Message(
        id=uuid4(),
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
        message_type=message_type,
        moderation_status="pending",
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)

    # Submit to moderation pipeline (best-effort, non-blocking)
    try:
        from src.moderation import submit_for_moderation
        await submit_for_moderation(
            db,
            content_type="message",
            content_id=message.id,
            author_age_tier=age_tier,
            content_text=content,
        )
    except Exception:
        logger.warning(
            "moderation_submission_failed",
            message_id=str(message.id),
            exc_info=True,
        )

    logger.info(
        "message_sent",
        message_id=str(message.id),
        conversation_id=str(conversation_id),
        sender_id=str(sender_id),
    )

    return message


async def list_messages(
    db: AsyncSession,
    conversation_id: UUID,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List messages in a conversation (verify membership). Only approved messages shown."""
    await _verify_membership(db, conversation_id, user_id)

    # Count total approved messages
    count_stmt = select(func.count()).where(
        Message.conversation_id == conversation_id,
        Message.moderation_status == "approved",
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    # Get paginated messages
    offset = (page - 1) * page_size
    stmt = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.moderation_status == "approved",
        )
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return {
        "items": [
            {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "sender_id": msg.sender_id,
                "content": msg.content,
                "message_type": msg.message_type,
                "moderation_status": msg.moderation_status,
                "created_at": msg.created_at,
            }
            for msg in messages
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def mark_read(
    db: AsyncSession,
    conversation_id: UUID,
    user_id: UUID,
) -> None:
    """Update last_read_at on ConversationMember."""
    member = await _get_membership(db, conversation_id, user_id)
    if not member:
        raise NotFoundError("Conversation membership")
    member.last_read_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(
        "conversation_marked_read",
        conversation_id=str(conversation_id),
        user_id=str(user_id),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _verify_membership(
    db: AsyncSession, conversation_id: UUID, user_id: UUID,
) -> ConversationMember:
    """Verify user is a member of the conversation. Raises ForbiddenError if not."""
    member = await _get_membership(db, conversation_id, user_id)
    if not member:
        raise ForbiddenError("You are not a member of this conversation")
    return member


async def _get_membership(
    db: AsyncSession, conversation_id: UUID, user_id: UUID,
) -> ConversationMember | None:
    """Get the ConversationMember record for user in conversation."""
    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


def _check_can_message(age_tier: str) -> None:
    """Check if the age tier allows messaging. Raises ForbiddenError if not."""
    from src.age_tier.rules import AgeTier
    try:
        tier = AgeTier(age_tier)
    except ValueError:
        return  # Unknown tier — allow (adults, etc.)

    if not check_permission(tier, "can_message"):
        raise ForbiddenError(
            "Messaging is not available for your age group. "
            "Please ask a parent or guardian for help."
        )


def _check_message_length(age_tier: str, content: str) -> None:
    """Enforce max_message_length per tier if the permission exists."""
    from src.age_tier.rules import AgeTier
    try:
        tier = AgeTier(age_tier)
    except ValueError:
        return

    perms = get_permissions(tier)
    max_len = perms.get("max_message_length", 0)
    if max_len and len(content) > max_len:
        raise ValidationError(
            f"Message exceeds maximum length of {max_len} characters"
        )
