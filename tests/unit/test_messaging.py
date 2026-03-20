"""Unit tests for the messaging module — conversations, messages, membership."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.exceptions import ForbiddenError, NotFoundError, ValidationError
from src.messaging.models import ConversationMember
from src.messaging.service import (
    create_conversation,
    get_conversation,
    list_conversations,
    list_messages,
    mark_read,
    send_message,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(session: AsyncSession, **kwargs) -> User:
    """Create a test user."""
    uid = kwargs.pop("id", None) or uuid.uuid4()
    user = User(
        id=uid,
        email=kwargs.pop("email", f"test-{uuid.uuid4().hex[:8]}@example.com"),
        display_name=kwargs.pop("display_name", "Test User"),
        account_type=kwargs.pop("account_type", "family"),
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_conversation(
    session: AsyncSession, user1: User, user2: User,
    conv_type: str = "direct", title: str | None = None,
) -> dict:
    """Create a test conversation between two users."""
    return await create_conversation(
        session,
        created_by=user1.id,
        conv_type=conv_type,
        title=title,
        member_user_ids=[user1.id, user2.id],
    )


# ---------------------------------------------------------------------------
# Conversation tests
# ---------------------------------------------------------------------------


class TestCreateConversation:
    """Test create_conversation service function."""

    @pytest.mark.asyncio
    async def test_create_direct_conversation(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)

        result = await create_conversation(
            test_session,
            created_by=user1.id,
            conv_type="direct",
            member_user_ids=[user1.id, user2.id],
        )

        assert result["type"] == "direct"
        assert result["member_count"] == 2
        assert result["created_by"] == user1.id

    @pytest.mark.asyncio
    async def test_create_group_conversation(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        user3 = await _make_user(test_session)

        result = await create_conversation(
            test_session,
            created_by=user1.id,
            conv_type="group",
            title="Test Group",
            member_user_ids=[user1.id, user2.id, user3.id],
        )

        assert result["type"] == "group"
        assert result["title"] == "Test Group"
        assert result["member_count"] == 3

    @pytest.mark.asyncio
    async def test_create_direct_too_many_members(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        user3 = await _make_user(test_session)

        with pytest.raises(ValidationError, match="exactly 2 members"):
            await create_conversation(
                test_session,
                created_by=user1.id,
                conv_type="direct",
                member_user_ids=[user1.id, user2.id, user3.id],
            )

    @pytest.mark.asyncio
    async def test_create_conversation_invalid_type(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)

        with pytest.raises(ValidationError, match="must be 'direct' or 'group'"):
            await create_conversation(
                test_session,
                created_by=user1.id,
                conv_type="invalid",
                member_user_ids=[user1.id, user2.id],
            )

    @pytest.mark.asyncio
    async def test_creator_auto_added_to_members(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)

        # Only pass user2 — creator should be auto-added
        result = await create_conversation(
            test_session,
            created_by=user1.id,
            conv_type="direct",
            member_user_ids=[user2.id],
        )
        assert result["member_count"] == 2

    @pytest.mark.asyncio
    async def test_young_tier_cannot_message(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)

        with pytest.raises(ForbiddenError, match="not available"):
            await create_conversation(
                test_session,
                created_by=user1.id,
                conv_type="direct",
                member_user_ids=[user1.id, user2.id],
                age_tier="young",
            )

    @pytest.mark.asyncio
    async def test_preteen_can_message(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)

        result = await create_conversation(
            test_session,
            created_by=user1.id,
            conv_type="direct",
            member_user_ids=[user1.id, user2.id],
            age_tier="preteen",
        )
        assert result["type"] == "direct"

    @pytest.mark.asyncio
    async def test_teen_can_message(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)

        result = await create_conversation(
            test_session,
            created_by=user1.id,
            conv_type="direct",
            member_user_ids=[user1.id, user2.id],
            age_tier="teen",
        )
        assert result["type"] == "direct"

    @pytest.mark.asyncio
    async def test_direct_conversation_title_ignored(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)

        result = await create_conversation(
            test_session,
            created_by=user1.id,
            conv_type="direct",
            title="Should be ignored",
            member_user_ids=[user1.id, user2.id],
        )
        assert result["title"] is None


class TestListConversations:
    """Test list_conversations service function."""

    @pytest.mark.asyncio
    async def test_list_empty(self, test_session):
        user = await _make_user(test_session)
        result = await list_conversations(test_session, user.id)
        assert result["total"] == 0
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_list_with_conversations(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        await _make_conversation(test_session, user1, user2)

        result = await list_conversations(test_session, user1.id)
        assert result["total"] == 1
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_pagination(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)

        for _ in range(3):
            await create_conversation(
                test_session,
                created_by=user1.id,
                conv_type="group",
                member_user_ids=[user1.id, user2.id],
            )

        result = await list_conversations(
            test_session, user1.id, page=1, page_size=2,
        )
        assert result["total"] == 3
        assert len(result["items"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == 2


class TestGetConversation:
    """Test get_conversation service function."""

    @pytest.mark.asyncio
    async def test_get_conversation(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        result = await get_conversation(
            test_session, conv["id"], user1.id,
        )
        assert result["id"] == conv["id"]
        assert result["member_count"] == 2

    @pytest.mark.asyncio
    async def test_get_conversation_non_member(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        user3 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        with pytest.raises(ForbiddenError, match="not a member"):
            await get_conversation(test_session, conv["id"], user3.id)


# ---------------------------------------------------------------------------
# Message tests
# ---------------------------------------------------------------------------


class TestSendMessage:
    """Test send_message service function."""

    @pytest.mark.asyncio
    async def test_send_message(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        message = await send_message(
            test_session,
            conversation_id=conv["id"],
            sender_id=user1.id,
            content="Hello!",
        )
        assert message.content == "Hello!"
        assert message.sender_id == user1.id
        assert message.moderation_status == "pending"

    @pytest.mark.asyncio
    async def test_send_message_non_member(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        user3 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        with pytest.raises(ForbiddenError, match="not a member"):
            await send_message(
                test_session,
                conversation_id=conv["id"],
                sender_id=user3.id,
                content="Intruder!",
            )

    @pytest.mark.asyncio
    async def test_send_message_young_tier_blocked(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        with pytest.raises(ForbiddenError, match="not available"):
            await send_message(
                test_session,
                conversation_id=conv["id"],
                sender_id=user1.id,
                content="Hi",
                age_tier="young",
            )

    @pytest.mark.asyncio
    async def test_send_message_exceeds_max_length(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        # Preteen max_message_length is 300
        long_content = "x" * 301
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            await send_message(
                test_session,
                conversation_id=conv["id"],
                sender_id=user1.id,
                content=long_content,
                age_tier="preteen",
            )

    @pytest.mark.asyncio
    async def test_send_message_within_max_length(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        content = "x" * 300
        message = await send_message(
            test_session,
            conversation_id=conv["id"],
            sender_id=user1.id,
            content=content,
            age_tier="preteen",
        )
        assert message.content == content


class TestListMessages:
    """Test list_messages service function."""

    @pytest.mark.asyncio
    async def test_list_messages_empty(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        result = await list_messages(
            test_session, conv["id"], user1.id,
        )
        assert result["total"] == 0
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_list_messages_only_approved(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        # Send a message (will be "pending")
        await send_message(
            test_session, conv["id"], user1.id, "Pending msg",
        )

        result = await list_messages(
            test_session, conv["id"], user1.id,
        )
        # Pending messages are not shown
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_messages_non_member(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        user3 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        with pytest.raises(ForbiddenError, match="not a member"):
            await list_messages(
                test_session, conv["id"], user3.id,
            )


class TestMarkRead:
    """Test mark_read service function."""

    @pytest.mark.asyncio
    async def test_mark_read(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        await mark_read(test_session, conv["id"], user1.id)
        # Verify the membership was updated
        from sqlalchemy import select
        result = await test_session.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id == conv["id"],
                ConversationMember.user_id == user1.id,
            )
        )
        member = result.scalar_one()
        assert member.last_read_at is not None

    @pytest.mark.asyncio
    async def test_mark_read_non_member(self, test_session):
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        user3 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        with pytest.raises(NotFoundError):
            await mark_read(test_session, conv["id"], user3.id)
