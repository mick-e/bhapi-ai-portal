"""Unit tests for Expo push notification service (P2-S8).

Tests: token registration, send, unregister, validation, upsert, service integration.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from src.alerts.push import ExpoPushService


@pytest_asyncio.fixture
async def push_service():
    """Create an ExpoPushService instance."""
    return ExpoPushService(push_url="https://exp.host/--/api/v2/push/send")


VALID_TOKEN = "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"
VALID_TOKEN_2 = "ExponentPushToken[yyyyyyyyyyyyyyyyyyyyyy]"


# ---------------------------------------------------------------------------
# Token Registration
# ---------------------------------------------------------------------------


class TestRegisterPushToken:
    """Test registering Expo push tokens."""

    @pytest.mark.asyncio
    async def test_register_push_token(self, test_session, push_service):
        """Register a new Expo push token for a user."""
        user_id = uuid4()
        pt = await push_service.register_token(
            test_session, user_id, VALID_TOKEN, "ios"
        )
        assert pt.user_id == user_id
        assert pt.token == VALID_TOKEN
        assert pt.device_type == "ios"
        assert pt.id is not None

    @pytest.mark.asyncio
    async def test_register_android_token(self, test_session, push_service):
        """Register an Android push token."""
        user_id = uuid4()
        pt = await push_service.register_token(
            test_session, user_id, VALID_TOKEN, "android"
        )
        assert pt.device_type == "android"

    @pytest.mark.asyncio
    async def test_register_token_upsert(self, test_session, push_service):
        """Re-registering same token updates the existing record."""
        user_id = uuid4()
        pt1 = await push_service.register_token(
            test_session, user_id, VALID_TOKEN, "ios"
        )
        pt2 = await push_service.register_token(
            test_session, user_id, VALID_TOKEN, "android"
        )
        assert pt1.id == pt2.id
        assert pt2.device_type == "android"

    @pytest.mark.asyncio
    async def test_register_token_different_user_upsert(self, test_session, push_service):
        """Token transferred to different user on re-register."""
        user1 = uuid4()
        user2 = uuid4()
        await push_service.register_token(test_session, user1, VALID_TOKEN, "ios")
        pt = await push_service.register_token(test_session, user2, VALID_TOKEN, "ios")
        assert pt.user_id == user2

    @pytest.mark.asyncio
    async def test_register_invalid_device_type(self, test_session, push_service):
        """Invalid device_type raises ValidationError."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await push_service.register_token(
                test_session, uuid4(), VALID_TOKEN, "windows"
            )

    @pytest.mark.asyncio
    async def test_register_invalid_token_format(self, test_session, push_service):
        """Non-Expo token format raises ValidationError."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await push_service.register_token(
                test_session, uuid4(), "not-an-expo-token", "ios"
            )

    @pytest.mark.asyncio
    async def test_register_empty_token(self, test_session, push_service):
        """Empty token raises ValidationError."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await push_service.register_token(
                test_session, uuid4(), "", "ios"
            )


# ---------------------------------------------------------------------------
# Token Unregistration
# ---------------------------------------------------------------------------


class TestUnregisterPushToken:
    """Test removing Expo push tokens."""

    @pytest.mark.asyncio
    async def test_unregister_token(self, test_session, push_service):
        """Unregister removes the token."""
        user_id = uuid4()
        await push_service.register_token(
            test_session, user_id, VALID_TOKEN, "ios"
        )
        removed = await push_service.unregister_token(
            test_session, user_id, VALID_TOKEN
        )
        assert removed is True

        # Verify token is gone
        tokens = await push_service.get_user_tokens(test_session, user_id)
        assert len(tokens) == 0

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_token(self, test_session, push_service):
        """Unregistering a non-existent token returns False."""
        removed = await push_service.unregister_token(
            test_session, uuid4(), VALID_TOKEN
        )
        assert removed is False

    @pytest.mark.asyncio
    async def test_unregister_wrong_user(self, test_session, push_service):
        """Cannot unregister another user's token."""
        user1 = uuid4()
        user2 = uuid4()
        await push_service.register_token(test_session, user1, VALID_TOKEN, "ios")
        removed = await push_service.unregister_token(test_session, user2, VALID_TOKEN)
        assert removed is False


# ---------------------------------------------------------------------------
# Get User Tokens
# ---------------------------------------------------------------------------


class TestGetUserTokens:
    """Test listing tokens for a user."""

    @pytest.mark.asyncio
    async def test_get_user_tokens_empty(self, test_session, push_service):
        """User with no tokens returns empty list."""
        tokens = await push_service.get_user_tokens(test_session, uuid4())
        assert tokens == []

    @pytest.mark.asyncio
    async def test_get_user_tokens_multiple(self, test_session, push_service):
        """User with multiple tokens returns all of them."""
        user_id = uuid4()
        await push_service.register_token(
            test_session, user_id, VALID_TOKEN, "ios"
        )
        await push_service.register_token(
            test_session, user_id, VALID_TOKEN_2, "android"
        )
        tokens = await push_service.get_user_tokens(test_session, user_id)
        assert len(tokens) == 2
        device_types = {t.device_type for t in tokens}
        assert device_types == {"ios", "android"}


# ---------------------------------------------------------------------------
# Send Notification
# ---------------------------------------------------------------------------


class TestSendNotification:
    """Test sending push notifications via Expo API."""

    @pytest.mark.asyncio
    async def test_send_push_notification(self, test_session, push_service):
        """Send push notification via mocked Expo API."""
        user_id = uuid4()
        await push_service.register_token(
            test_session, user_id, VALID_TOKEN, "ios"
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None

        with patch("src.alerts.push.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await push_service.send_notification(
                test_session, user_id, "Test Title", "Test body", {"key": "val"}
            )

            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload[0]["to"] == VALID_TOKEN
            assert payload[0]["title"] == "Test Title"
            assert payload[0]["body"] == "Test body"
            assert payload[0]["data"] == {"key": "val"}

    @pytest.mark.asyncio
    async def test_send_no_tokens(self, test_session, push_service):
        """Send returns False when user has no tokens."""
        result = await push_service.send_notification(
            test_session, uuid4(), "Title", "Body"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_notification_api_failure(self, test_session, push_service):
        """Send returns False on Expo API failure."""
        user_id = uuid4()
        await push_service.register_token(
            test_session, user_id, VALID_TOKEN, "ios"
        )

        with patch("src.alerts.push.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await push_service.send_notification(
                test_session, user_id, "Title", "Body"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_send_multiple_devices(self, test_session, push_service):
        """Send to multiple devices in a single Expo API call."""
        user_id = uuid4()
        await push_service.register_token(
            test_session, user_id, VALID_TOKEN, "ios"
        )
        await push_service.register_token(
            test_session, user_id, VALID_TOKEN_2, "android"
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None

        with patch("src.alerts.push.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await push_service.send_notification(
                test_session, user_id, "Title", "Body"
            )
            assert result is True
            payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
            assert len(payload) == 2

    @pytest.mark.asyncio
    async def test_send_without_data(self, test_session, push_service):
        """Send notification without optional data field."""
        user_id = uuid4()
        await push_service.register_token(
            test_session, user_id, VALID_TOKEN, "ios"
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None

        with patch("src.alerts.push.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await push_service.send_notification(
                test_session, user_id, "Title", "Body"
            )
            assert result is True
            payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
            assert "data" not in payload[0]
