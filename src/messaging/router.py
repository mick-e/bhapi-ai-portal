"""Messaging module FastAPI router — conversations and messages."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.messaging import schemas, service
from src.schemas import GroupContext

logger = structlog.get_logger()

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper — resolve the user's age tier from their social profile
# ---------------------------------------------------------------------------


async def _get_user_age_tier(db: AsyncSession, user_id: UUID) -> str | None:
    """Get the age tier for the authenticated user from their social profile.

    Returns None if the user has no social profile (e.g. adult/parent).
    """
    try:
        from src.social.service import get_profile
        profile = await get_profile(db, user_id)
        return profile.age_tier
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


@router.post("/conversations", response_model=schemas.ConversationResponse, status_code=201)
async def create_conversation(
    data: schemas.ConversationCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation."""
    age_tier = await _get_user_age_tier(db, auth.user_id)
    result = await service.create_conversation(
        db,
        created_by=auth.user_id,
        conv_type=data.type,
        title=data.title,
        member_user_ids=data.member_user_ids,
        age_tier=age_tier,
    )
    await db.commit()
    return result


@router.get("/conversations", response_model=schemas.ConversationListResponse)
async def list_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List my conversations (paginated)."""
    return await service.list_conversations(
        db, auth.user_id, page=page, page_size=page_size,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=schemas.ConversationResponse,
)
async def get_conversation(
    conversation_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation detail."""
    return await service.get_conversation(db, conversation_id, auth.user_id)


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=schemas.MessageResponse,
    status_code=201,
)
async def send_message(
    conversation_id: UUID,
    data: schemas.MessageCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to a conversation."""
    age_tier = await _get_user_age_tier(db, auth.user_id)
    message = await service.send_message(
        db,
        conversation_id=conversation_id,
        sender_id=auth.user_id,
        content=data.content,
        message_type=data.message_type,
        age_tier=age_tier,
    )
    await db.commit()
    return message


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=schemas.MessageListResponse,
)
async def list_messages(
    conversation_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List messages in a conversation (paginated)."""
    return await service.list_messages(
        db, conversation_id, auth.user_id, page=page, page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Read receipts
# ---------------------------------------------------------------------------


@router.patch("/conversations/{conversation_id}/read", status_code=200)
async def mark_read(
    conversation_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a conversation as read."""
    await service.mark_read(db, conversation_id, auth.user_id)
    await db.commit()
    return {"status": "ok"}
