"""Tests for push notification relay and presence system."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.realtime.notifications import EXPO_PUSH_URL, PushNotificationRelay, PushResult
from src.realtime.presence import PresenceInfo, PresenceTracker

# ── Unit tests: PushNotificationRelay ─────────────────────────────


class TestPushNotificationRelay:
    """Unit tests for PushNotificationRelay."""

    def test_register_token(self):
        relay = PushNotificationRelay()
        relay.register_token("user1", "ExponentPushToken[abc123]")
        assert relay.get_token("user1") == "ExponentPushToken[abc123]"

    def test_register_token_overwrites_previous(self):
        relay = PushNotificationRelay()
        relay.register_token("user1", "token_old")
        relay.register_token("user1", "token_new")
        assert relay.get_token("user1") == "token_new"

    def test_unregister_token(self):
        relay = PushNotificationRelay()
        relay.register_token("user1", "token1")
        relay.unregister_token("user1")
        assert relay.get_token("user1") is None

    def test_unregister_token_nonexistent(self):
        relay = PushNotificationRelay()
        relay.unregister_token("nonexistent")  # should not raise

    def test_get_token_not_registered(self):
        relay = PushNotificationRelay()
        assert relay.get_token("unknown") is None

    def test_multiple_users(self):
        relay = PushNotificationRelay()
        relay.register_token("user1", "token1")
        relay.register_token("user2", "token2")
        assert relay.get_token("user1") == "token1"
        assert relay.get_token("user2") == "token2"

    @pytest.mark.asyncio
    async def test_send_push_no_token(self):
        relay = PushNotificationRelay()
        result = await relay.send_push("unknown", "Title", "Body")
        assert result.success is False
        assert result.error == "No push token registered"

    @pytest.mark.asyncio
    async def test_send_push_success(self):
        relay = PushNotificationRelay()
        relay.register_token("user1", "ExponentPushToken[abc]")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"id": "ticket-123"}}

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await relay.send_push("user1", "Alert", "New alert!")
            assert result.success is True
            assert result.ticket_id == "ticket-123"

            # Verify correct payload
            call_args = mock_client.post.call_args
            assert call_args[0][0] == EXPO_PUSH_URL
            payload = call_args[1]["json"]
            assert payload["to"] == "ExponentPushToken[abc]"
            assert payload["title"] == "Alert"
            assert payload["body"] == "New alert!"
            assert payload["sound"] == "default"

    @pytest.mark.asyncio
    async def test_send_push_with_data(self):
        relay = PushNotificationRelay()
        relay.register_token("user1", "token1")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"id": "t-456"}}

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await relay.send_push(
                "user1", "Title", "Body", data={"alert_id": "a1"}
            )
            assert result.success is True
            payload = mock_client.post.call_args[1]["json"]
            assert payload["data"] == {"alert_id": "a1"}

    @pytest.mark.asyncio
    async def test_send_push_http_error(self):
        relay = PushNotificationRelay()
        relay.register_token("user1", "token1")

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await relay.send_push("user1", "Title", "Body")
            assert result.success is False
            assert "Connection refused" in result.error

    @pytest.mark.asyncio
    async def test_send_push_batch_all_registered(self):
        relay = PushNotificationRelay()
        relay.register_token("u1", "t1")
        relay.register_token("u2", "t2")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"id": "ticket"}}

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await relay.send_push_batch(
                ["u1", "u2"], "Title", "Body"
            )
            assert len(results) == 2
            assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_send_push_batch_partial_tokens(self):
        relay = PushNotificationRelay()
        relay.register_token("u1", "t1")
        # u2 not registered

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"id": "ticket"}}

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await relay.send_push_batch(
                ["u1", "u2"], "Title", "Body"
            )
            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False

    @pytest.mark.asyncio
    async def test_send_push_batch_empty_list(self):
        relay = PushNotificationRelay()
        results = await relay.send_push_batch([], "Title", "Body")
        assert results == []

    @pytest.mark.asyncio
    async def test_send_push_default_data_is_empty_dict(self):
        relay = PushNotificationRelay()
        relay.register_token("u1", "t1")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"id": "t"}}

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await relay.send_push("u1", "T", "B")
            payload = mock_client.post.call_args[1]["json"]
            assert payload["data"] == {}

    @pytest.mark.asyncio
    async def test_send_push_no_ticket_in_response(self):
        relay = PushNotificationRelay()
        relay.register_token("u1", "t1")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {}}

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await relay.send_push("u1", "T", "B")
            assert result.success is True
            assert result.ticket_id is None


# ── Unit tests: PresenceTracker ───────────────────────────────────


class TestPresenceTracker:
    """Unit tests for PresenceTracker."""

    def test_initial_state(self):
        t = PresenceTracker()
        assert t.get_online_count() == 0
        assert t.get_online_users() == []

    def test_set_online(self):
        t = PresenceTracker()
        t.set_online("user1")
        assert t.get_presence("user1").is_online is True

    def test_set_offline(self):
        t = PresenceTracker()
        t.set_online("user1")
        t.set_offline("user1")
        assert t.get_presence("user1").is_online is False

    def test_set_offline_without_online(self):
        t = PresenceTracker()
        t.set_offline("user1")  # should not raise
        assert t.get_presence("user1").is_online is False
        assert t.get_presence("user1").last_seen is not None

    def test_last_seen_set_on_online(self):
        t = PresenceTracker()
        before = datetime.now(timezone.utc)
        t.set_online("user1")
        info = t.get_presence("user1")
        assert info.last_seen is not None
        assert info.last_seen >= before

    def test_last_seen_updated_on_offline(self):
        t = PresenceTracker()
        t.set_online("user1")
        first_seen = t.get_presence("user1").last_seen
        t.set_offline("user1")
        second_seen = t.get_presence("user1").last_seen
        assert second_seen >= first_seen

    def test_get_presence_unknown_user(self):
        t = PresenceTracker()
        info = t.get_presence("unknown")
        assert info.user_id == "unknown"
        assert info.is_online is False
        assert info.last_seen is None

    def test_get_online_users_all(self):
        t = PresenceTracker()
        t.set_online("u1")
        t.set_online("u2")
        t.set_online("u3")
        online = t.get_online_users()
        assert set(online) == {"u1", "u2", "u3"}

    def test_get_online_users_filtered(self):
        t = PresenceTracker()
        t.set_online("u1")
        t.set_online("u2")
        t.set_online("u3")
        online = t.get_online_users(["u1", "u3", "u4"])
        assert set(online) == {"u1", "u3"}

    def test_get_online_count(self):
        t = PresenceTracker()
        t.set_online("u1")
        t.set_online("u2")
        assert t.get_online_count() == 2
        t.set_offline("u1")
        assert t.get_online_count() == 1

    def test_set_online_idempotent(self):
        t = PresenceTracker()
        t.set_online("u1")
        t.set_online("u1")
        assert t.get_online_count() == 1

    def test_presence_info_fields(self):
        info = PresenceInfo(
            user_id="u1",
            is_online=True,
            last_seen=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert info.user_id == "u1"
        assert info.is_online is True
        assert info.last_seen.year == 2026


# ── Integration / E2E tests ──────────────────────────────────────


class TestPushNotificationRelayIntegration:
    """Integration tests for the push relay with presence."""

    @pytest.mark.asyncio
    async def test_register_send_unregister_flow(self):
        relay = PushNotificationRelay()
        relay.register_token("user1", "ExponentPushToken[xyz]")
        assert relay.get_token("user1") is not None

        # Send with mock
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"id": "t1"}}

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await relay.send_push("user1", "Test", "Hello")
            assert result.success is True

        relay.unregister_token("user1")
        result = await relay.send_push("user1", "Test", "Hello again")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_batch_send_with_presence_check(self):
        """Integration: batch push to online users only."""
        presence = PresenceTracker()
        relay = PushNotificationRelay()

        presence.set_online("u1")
        presence.set_online("u2")
        presence.set_offline("u3")

        relay.register_token("u1", "t1")
        relay.register_token("u2", "t2")
        relay.register_token("u3", "t3")

        # Only send to online users
        online = presence.get_online_users(["u1", "u2", "u3"])
        assert set(online) == {"u1", "u2"}

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"id": "t"}}

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            results = await relay.send_push_batch(online, "Alert", "Risk")
            assert len(results) == 2
            assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_offline_user_gets_push_when_token_exists(self):
        """Even offline users receive push if token is registered."""
        presence = PresenceTracker()
        relay = PushNotificationRelay()

        relay.register_token("u1", "t1")
        presence.set_offline("u1")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"id": "t"}}

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await relay.send_push("u1", "Title", "Body")
            assert result.success is True

    def test_presence_lifecycle(self):
        """Full lifecycle: online -> offline -> online."""
        t = PresenceTracker()
        t.set_online("u1")
        assert t.get_presence("u1").is_online is True
        t.set_offline("u1")
        assert t.get_presence("u1").is_online is False
        seen_after_offline = t.get_presence("u1").last_seen
        t.set_online("u1")
        assert t.get_presence("u1").is_online is True
        assert t.get_presence("u1").last_seen >= seen_after_offline

    def test_multiple_users_presence_isolation(self):
        """Each user's presence is independent."""
        t = PresenceTracker()
        t.set_online("u1")
        t.set_online("u2")
        t.set_offline("u1")
        assert t.get_presence("u1").is_online is False
        assert t.get_presence("u2").is_online is True

    @pytest.mark.asyncio
    async def test_relay_token_replacement_sends_to_new(self):
        """When token is replaced, sends to the new token."""
        relay = PushNotificationRelay()
        relay.register_token("u1", "old_token")
        relay.register_token("u1", "new_token")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"id": "t"}}

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            await relay.send_push("u1", "T", "B")
            payload = mock_client.post.call_args[1]["json"]
            assert payload["to"] == "new_token"

    def test_get_online_users_empty_filter(self):
        """Filtering with empty list returns empty."""
        t = PresenceTracker()
        t.set_online("u1")
        assert t.get_online_users([]) == []

    def test_presence_count_after_multiple_operations(self):
        """Count stays correct after many operations."""
        t = PresenceTracker()
        for i in range(10):
            t.set_online(f"user_{i}")
        assert t.get_online_count() == 10
        for i in range(5):
            t.set_offline(f"user_{i}")
        assert t.get_online_count() == 5

    @pytest.mark.asyncio
    async def test_push_result_dataclass(self):
        """PushResult dataclass has correct defaults."""
        r = PushResult(success=True)
        assert r.ticket_id is None
        assert r.error is None

        r2 = PushResult(success=False, error="fail")
        assert r2.error == "fail"

    @pytest.mark.asyncio
    async def test_batch_send_preserves_order(self):
        """Results are in same order as input user_ids."""
        relay = PushNotificationRelay()
        relay.register_token("u1", "t1")
        # u2 not registered
        relay.register_token("u3", "t3")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"id": "t"}}

        with patch("src.realtime.notifications.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            results = await relay.send_push_batch(
                ["u1", "u2", "u3"], "T", "B"
            )
            assert results[0].success is True   # u1 registered
            assert results[1].success is False   # u2 not registered
            assert results[2].success is True    # u3 registered
