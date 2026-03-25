"""Unit tests for messaging → realtime WebSocket publishing via Redis pub/sub."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.messaging.service import (
    _publish_to_realtime,
    create_conversation,
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
        email=kwargs.pop("email", f"rt-{uuid.uuid4().hex[:8]}@example.com"),
        display_name=kwargs.pop("display_name", "RT Test User"),
        account_type=kwargs.pop("account_type", "family"),
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_conversation(session: AsyncSession, user1: User, user2: User) -> dict:
    """Create a direct conversation between two users."""
    return await create_conversation(
        session,
        created_by=user1.id,
        conv_type="direct",
        member_user_ids=[user1.id, user2.id],
    )


# ---------------------------------------------------------------------------
# Tests: _publish_to_realtime helper
# ---------------------------------------------------------------------------


class TestPublishToRealtime:
    """Unit tests for the _publish_to_realtime helper."""

    @pytest.mark.asyncio
    async def test_publishes_to_messaging_channel(self):
        """publish() is called with the 'messaging' channel."""
        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()
        mock_redis.close = AsyncMock()

        fake_settings = MagicMock()
        fake_settings.redis_url = "redis://localhost:6379"

        with (
            patch("src.config.get_settings", return_value=fake_settings),
            patch(
                "redis.asyncio.from_url",
                return_value=mock_redis,
            ),
        ):
            await _publish_to_realtime(
                "conv-123",
                {"message_id": "msg-1", "content": "hello"},
            )

        mock_redis.publish.assert_awaited_once()
        channel_arg = mock_redis.publish.call_args[0][0]
        assert channel_arg == "messaging"

    @pytest.mark.asyncio
    async def test_publish_data_includes_conversation_id(self):
        """Published payload contains the conversation_id."""
        import json

        mock_redis = AsyncMock()
        mock_redis.publish = AsyncMock()
        mock_redis.close = AsyncMock()

        fake_settings = MagicMock()
        fake_settings.redis_url = "redis://localhost:6379"

        conv_id = str(uuid.uuid4())

        with (
            patch("src.config.get_settings", return_value=fake_settings),
            patch("redis.asyncio.from_url", return_value=mock_redis),
        ):
            await _publish_to_realtime(
                conv_id,
                {"message_id": "msg-42", "content": "test content"},
            )

        payload_json = mock_redis.publish.call_args[0][1]
        payload = json.loads(payload_json)

        assert payload["conversation_id"] == conv_id
        assert payload["content"] == "test content"
        assert payload["type"] == "new_message"

    @pytest.mark.asyncio
    async def test_publish_skipped_when_no_redis_url(self):
        """No Redis call is made when redis_url is empty."""
        mock_redis = AsyncMock()

        fake_settings = MagicMock()
        fake_settings.redis_url = ""

        with (
            patch("src.config.get_settings", return_value=fake_settings),
            patch("redis.asyncio.from_url", return_value=mock_redis) as mock_from_url,
        ):
            await _publish_to_realtime("conv-abc", {"content": "hello"})

        mock_from_url.assert_not_called()
        mock_redis.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_realtime_failure_is_swallowed(self):
        """Exceptions from Redis publish are caught and logged, not raised."""
        fake_settings = MagicMock()
        fake_settings.redis_url = "redis://localhost:6379"

        with (
            patch("src.config.get_settings", return_value=fake_settings),
            patch(
                "redis.asyncio.from_url",
                side_effect=RuntimeError("Redis connection refused"),
            ),
        ):
            # Must not raise
            await _publish_to_realtime("conv-xyz", {"content": "boom"})


# ---------------------------------------------------------------------------
# Tests: send_message() integration with realtime publishing
# ---------------------------------------------------------------------------


class TestSendMessageRealtimePublishing:
    """Verify send_message() calls _publish_to_realtime after saving."""

    @pytest.mark.asyncio
    async def test_send_message_publishes_to_realtime(self, test_session):
        """send_message() triggers _publish_to_realtime with message data."""
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)
        conv_id = conv["id"]

        with patch(
            "src.messaging.service._publish_to_realtime",
            new_callable=AsyncMock,
        ) as mock_publish:
            # Also suppress _publish_message_event (uses real Redis)
            with patch(
                "src.messaging.service._publish_message_event",
                new_callable=AsyncMock,
            ):
                # Suppress moderation submission
                with patch(
                    "src.moderation.submit_for_moderation",
                    new_callable=AsyncMock,
                ):
                    await send_message(
                        test_session,
                        conversation_id=conv_id,
                        sender_id=user1.id,
                        content="Hello real-time world",
                    )

        mock_publish.assert_awaited_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == str(conv_id)
        message_data = call_args[0][1]
        assert message_data["content"] == "Hello real-time world"

    @pytest.mark.asyncio
    async def test_realtime_failure_does_not_block_message_save(self, test_session):
        """Message is persisted even when realtime publishing raises an exception."""
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)
        conv_id = conv["id"]

        # Simulate Redis being unavailable — _publish_to_realtime catches it
        # internally, and send_message also wraps with try/except, so the
        # message save must always complete regardless.
        fake_settings = MagicMock()
        fake_settings.redis_url = "redis://localhost:6379"

        with (
            patch("src.config.get_settings", return_value=fake_settings),
            patch(
                "redis.asyncio.from_url",
                side_effect=ConnectionError("Redis unavailable"),
            ),
        ):
            with patch(
                "src.messaging.service._publish_message_event",
                new_callable=AsyncMock,
            ):
                with patch(
                    "src.moderation.submit_for_moderation",
                    new_callable=AsyncMock,
                ):
                    message = await send_message(
                        test_session,
                        conversation_id=conv_id,
                        sender_id=user1.id,
                        content="Persisted despite realtime failure",
                    )

        assert message is not None
        assert message.content == "Persisted despite realtime failure"

    @pytest.mark.asyncio
    async def test_send_message_publish_includes_sender_id(self, test_session):
        """Published message_data includes sender_id."""
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        with patch(
            "src.messaging.service._publish_to_realtime",
            new_callable=AsyncMock,
        ) as mock_publish:
            with patch(
                "src.messaging.service._publish_message_event",
                new_callable=AsyncMock,
            ):
                with patch(
                    "src.moderation.submit_for_moderation",
                    new_callable=AsyncMock,
                ):
                    await send_message(
                        test_session,
                        conversation_id=conv["id"],
                        sender_id=user1.id,
                        content="Check sender",
                    )

        message_data = mock_publish.call_args[0][1]
        assert message_data["sender_id"] == str(user1.id)

    @pytest.mark.asyncio
    async def test_send_message_publish_includes_message_type(self, test_session):
        """Published message_data includes the message_type field."""
        user1 = await _make_user(test_session)
        user2 = await _make_user(test_session)
        conv = await _make_conversation(test_session, user1, user2)

        with patch(
            "src.messaging.service._publish_to_realtime",
            new_callable=AsyncMock,
        ) as mock_publish:
            with patch(
                "src.messaging.service._publish_message_event",
                new_callable=AsyncMock,
            ):
                with patch(
                    "src.moderation.submit_for_moderation",
                    new_callable=AsyncMock,
                ):
                    await send_message(
                        test_session,
                        conversation_id=conv["id"],
                        sender_id=user1.id,
                        content="A text message",
                        message_type="text",
                    )

        message_data = mock_publish.call_args[0][1]
        assert message_data["message_type"] == "text"
