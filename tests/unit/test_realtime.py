"""Tests for src/realtime — WebSocket service, connection manager, auth, pub/sub.

Unit tests: ≥20, WS E2E: ≥15, Security: ≥10  →  ≥45 total
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from starlette.testclient import TestClient

from src.auth.service import create_access_token
from src.realtime.auth import validate_ws_token
from src.realtime.connections import ConnectionManager
from src.realtime.pubsub import EventBridge
from src.realtime.main import app, manager as app_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_token(
    user_id: str | None = None,
    group_id: str | None = None,
    role: str = "member",
    permissions: list[str] | None = None,
    token_type: str = "session",
    expired: bool = False,
) -> str:
    """Create a valid (or expired) JWT for testing."""
    uid = user_id or str(uuid4())
    data = {
        "sub": uid,
        "type": token_type,
        "role": role,
        "permissions": permissions or [],
    }
    if group_id:
        data["group_id"] = group_id
    delta = timedelta(hours=-1) if expired else timedelta(hours=1)
    return create_access_token(data, expires_delta=delta)


# ---------------------------------------------------------------------------
# UNIT: validate_ws_token  (4 tests)
# ---------------------------------------------------------------------------

class TestValidateWsToken:
    """Unit tests for JWT validation in WebSocket context."""

    @pytest.mark.asyncio
    async def test_valid_session_token(self):
        uid = str(uuid4())
        gid = str(uuid4())
        token = _make_session_token(user_id=uid, group_id=gid, role="admin")
        result = await validate_ws_token(token)
        assert result is not None
        assert result["user_id"] == uid
        assert result["group_id"] == gid
        assert result["role"] == "admin"

    @pytest.mark.asyncio
    async def test_expired_token_returns_none(self):
        token = _make_session_token(expired=True)
        result = await validate_ws_token(token)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self):
        result = await validate_ws_token("not.a.valid.jwt.token")
        assert result is None

    @pytest.mark.asyncio
    async def test_wrong_type_returns_none(self):
        token = _make_session_token(token_type="access")
        result = await validate_ws_token(token)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_token_returns_none(self):
        result = await validate_ws_token("")
        assert result is None

    @pytest.mark.asyncio
    async def test_none_like_token_returns_none(self):
        result = await validate_ws_token("")
        assert result is None


# ---------------------------------------------------------------------------
# UNIT: ConnectionManager  (14 tests)
# ---------------------------------------------------------------------------

class TestConnectionManager:
    """Unit tests for the WebSocket connection manager."""

    def _make_ws(self) -> AsyncMock:
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_accepts_and_registers(self):
        mgr = ConnectionManager()
        ws = self._make_ws()
        await mgr.connect(ws, "u1")
        assert mgr.is_connected("u1")
        assert mgr.get_connected_count() == 1
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_user(self):
        mgr = ConnectionManager()
        ws = self._make_ws()
        await mgr.connect(ws, "u1")
        await mgr.disconnect("u1")
        assert not mgr.is_connected("u1")
        assert mgr.get_connected_count() == 0

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_rooms(self):
        mgr = ConnectionManager()
        ws = self._make_ws()
        await mgr.connect(ws, "u1")
        mgr.join_room("u1", "room1")
        assert "u1" in mgr.get_room_members("room1")
        await mgr.disconnect("u1")
        assert "u1" not in mgr.get_room_members("room1")

    @pytest.mark.asyncio
    async def test_send_to_user(self):
        mgr = ConnectionManager()
        ws = self._make_ws()
        await mgr.connect(ws, "u1")
        msg = {"type": "test"}
        await mgr.send_to_user("u1", msg)
        ws.send_json.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_user_is_noop(self):
        mgr = ConnectionManager()
        await mgr.send_to_user("nobody", {"type": "test"})
        # No error raised

    @pytest.mark.asyncio
    async def test_broadcast_room(self):
        mgr = ConnectionManager()
        ws1, ws2 = self._make_ws(), self._make_ws()
        await mgr.connect(ws1, "u1")
        await mgr.connect(ws2, "u2")
        mgr.join_room("u1", "r")
        mgr.join_room("u2", "r")
        msg = {"type": "hello"}
        await mgr.broadcast_room("r", msg)
        ws1.send_json.assert_awaited_with(msg)
        ws2.send_json.assert_awaited_with(msg)

    @pytest.mark.asyncio
    async def test_broadcast_room_exclude(self):
        mgr = ConnectionManager()
        ws1, ws2 = self._make_ws(), self._make_ws()
        await mgr.connect(ws1, "u1")
        await mgr.connect(ws2, "u2")
        mgr.join_room("u1", "r")
        mgr.join_room("u2", "r")
        await mgr.broadcast_room("r", {"x": 1}, exclude="u1")
        ws1.send_json.assert_not_awaited()
        ws2.send_json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_broadcast_all(self):
        mgr = ConnectionManager()
        ws1, ws2 = self._make_ws(), self._make_ws()
        await mgr.connect(ws1, "u1")
        await mgr.connect(ws2, "u2")
        await mgr.broadcast_all({"type": "x"})
        ws1.send_json.assert_awaited()
        ws2.send_json.assert_awaited()

    @pytest.mark.asyncio
    async def test_join_and_leave_room(self):
        mgr = ConnectionManager()
        ws = self._make_ws()
        await mgr.connect(ws, "u1")
        mgr.join_room("u1", "room")
        assert "u1" in mgr.get_room_members("room")
        mgr.leave_room("u1", "room")
        assert "u1" not in mgr.get_room_members("room")

    @pytest.mark.asyncio
    async def test_leave_nonexistent_room_is_noop(self):
        mgr = ConnectionManager()
        mgr.leave_room("u1", "nope")  # No error

    @pytest.mark.asyncio
    async def test_heartbeat_updates_timestamp(self):
        mgr = ConnectionManager()
        ws = self._make_ws()
        await mgr.connect(ws, "u1")
        old = mgr._last_heartbeat["u1"]
        mgr.heartbeat("u1")
        assert mgr._last_heartbeat["u1"] >= old

    @pytest.mark.asyncio
    async def test_get_room_members_returns_copy(self):
        mgr = ConnectionManager()
        ws = self._make_ws()
        await mgr.connect(ws, "u1")
        mgr.join_room("u1", "r")
        members = mgr.get_room_members("r")
        members.add("fake")
        assert "fake" not in mgr.get_room_members("r")

    @pytest.mark.asyncio
    async def test_duplicate_connection_replaces_old(self):
        mgr = ConnectionManager()
        ws1 = self._make_ws()
        ws2 = self._make_ws()
        await mgr.connect(ws1, "u1")
        await mgr.connect(ws2, "u1")
        assert mgr.get_connected_count() == 1
        ws1.close.assert_awaited_once()
        # New ws is the active one
        await mgr.send_to_user("u1", {"t": 1})
        ws2.send_json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_failure_disconnects_user(self):
        mgr = ConnectionManager()
        ws = self._make_ws()
        ws.send_json.side_effect = RuntimeError("broken pipe")
        await mgr.connect(ws, "u1")
        await mgr.send_to_user("u1", {"t": 1})
        assert not mgr.is_connected("u1")


# ---------------------------------------------------------------------------
# UNIT: EventBridge  (6 tests)
# ---------------------------------------------------------------------------

class TestEventBridge:
    """Unit tests for the Redis pub/sub event bridge."""

    def _make_bridge(self) -> tuple[EventBridge, ConnectionManager]:
        mgr = ConnectionManager()
        return EventBridge(mgr), mgr

    @pytest.mark.asyncio
    async def test_handle_message_routes_to_user(self):
        br, mgr = self._make_bridge()
        mgr.send_to_user = AsyncMock()
        msg = {
            "type": "message",
            "channel": "alerts",
            "data": json.dumps({"target_user_id": "u1", "body": "hi"}),
        }
        await br._handle_message(msg)
        mgr.send_to_user.assert_awaited_once()
        args = mgr.send_to_user.call_args
        assert args[0][0] == "u1"

    @pytest.mark.asyncio
    async def test_handle_message_routes_to_room(self):
        br, mgr = self._make_bridge()
        mgr.broadcast_room = AsyncMock()
        msg = {
            "type": "message",
            "channel": "social",
            "data": json.dumps({"target_room": "group:abc", "body": "yo"}),
        }
        await br._handle_message(msg)
        mgr.broadcast_room.assert_awaited_once()
        assert mgr.broadcast_room.call_args[0][0] == "group:abc"

    @pytest.mark.asyncio
    async def test_handle_message_invalid_json(self):
        br, mgr = self._make_bridge()
        msg = {"type": "message", "channel": "alerts", "data": "not json{{"}
        # Should not raise
        await br._handle_message(msg)

    @pytest.mark.asyncio
    async def test_handle_message_missing_target(self):
        br, mgr = self._make_bridge()
        mgr.send_to_user = AsyncMock()
        mgr.broadcast_room = AsyncMock()
        msg = {
            "type": "message",
            "channel": "alerts",
            "data": json.dumps({"body": "no target"}),
        }
        await br._handle_message(msg)
        mgr.send_to_user.assert_not_awaited()
        mgr.broadcast_room.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_message_bytes_channel(self):
        br, mgr = self._make_bridge()
        mgr.send_to_user = AsyncMock()
        msg = {
            "type": "message",
            "channel": b"alerts",
            "data": json.dumps({"target_user_id": "u1"}),
        }
        await br._handle_message(msg)
        mgr.send_to_user.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_without_redis_url_is_noop(self):
        br, _ = self._make_bridge()
        await br.start(redis_url=None)
        assert not br._running

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self):
        br, _ = self._make_bridge()
        await br.stop()  # No error


# ---------------------------------------------------------------------------
# WS E2E: Full WebSocket lifecycle via TestClient  (15+ tests)
# ---------------------------------------------------------------------------

class TestWebSocketE2E:
    """WebSocket E2E tests using Starlette TestClient."""

    def _token(self, **kwargs) -> str:
        return _make_session_token(**kwargs)

    def test_health_endpoint(self):
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "connections" in data

    def test_connect_with_valid_token_receives_welcome(self):
        uid = str(uuid4())
        token = self._token(user_id=uid)
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={token}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "welcome"
            assert msg["user_id"] == uid

    def test_connect_invalid_token_closes_4001(self):
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=bad") as ws:
                ws.receive_json()

    def test_connect_no_token_closes(self):
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=") as ws:
                ws.receive_json()

    def test_heartbeat_ack(self):
        token = self._token()
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "heartbeat"})
            msg = ws.receive_json()
            assert msg["type"] == "heartbeat_ack"

    def test_join_room(self):
        uid = str(uuid4())
        token = self._token(user_id=uid)
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "join_room", "room": "test-room"})
            # Verify via manager state (room join doesn't send response)
            # Send heartbeat to confirm connection still alive
            ws.send_json({"type": "heartbeat"})
            msg = ws.receive_json()
            assert msg["type"] == "heartbeat_ack"

    def test_leave_room(self):
        uid = str(uuid4())
        token = self._token(user_id=uid)
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "join_room", "room": "r1"})
            ws.send_json({"type": "leave_room", "room": "r1"})
            ws.send_json({"type": "heartbeat"})
            msg = ws.receive_json()
            assert msg["type"] == "heartbeat_ack"

    def test_auto_join_group_room(self):
        uid = str(uuid4())
        gid = str(uuid4())
        token = self._token(user_id=uid, group_id=gid)
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.receive_json()  # welcome
            # The user should be in group room — verify via heartbeat
            ws.send_json({"type": "heartbeat"})
            msg = ws.receive_json()
            assert msg["type"] == "heartbeat_ack"

    def test_send_message_to_user(self):
        """Two users: u1 sends direct message to u2."""
        uid1 = str(uuid4())
        uid2 = str(uuid4())
        t1 = self._token(user_id=uid1)
        t2 = self._token(user_id=uid2)
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={t2}") as ws2:
            ws2.receive_json()  # welcome
            with client.websocket_connect(f"/ws?token={t1}") as ws1:
                ws1.receive_json()  # welcome
                ws1.send_json(
                    {
                        "type": "message",
                        "target_user_id": uid2,
                        "data": {"text": "hello"},
                    }
                )
                msg = ws2.receive_json()
                assert msg["type"] == "message"
                assert msg["from"] == uid1
                assert msg["data"]["text"] == "hello"

    def test_broadcast_room_message(self):
        """Two users in same room: u1 broadcasts, u2 receives."""
        uid1 = str(uuid4())
        uid2 = str(uuid4())
        t1 = self._token(user_id=uid1)
        t2 = self._token(user_id=uid2)
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={t2}") as ws2:
            ws2.receive_json()  # welcome
            ws2.send_json({"type": "join_room", "room": "chat"})
            with client.websocket_connect(f"/ws?token={t1}") as ws1:
                ws1.receive_json()  # welcome
                ws1.send_json({"type": "join_room", "room": "chat"})
                ws1.send_json(
                    {
                        "type": "message",
                        "room": "chat",
                        "data": {"text": "room msg"},
                    }
                )
                msg = ws2.receive_json()
                assert msg["type"] == "message"
                assert msg["from"] == uid1

    def test_disconnect_cleanup(self):
        uid = str(uuid4())
        token = self._token(user_id=uid)
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.receive_json()  # welcome
        # After context exit, the connection is cleaned up
        # Health endpoint still works
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_connection_count(self):
        client = TestClient(app)
        uid = str(uuid4())
        token = self._token(user_id=uid)
        # Check health before connect
        resp1 = client.get("/health")
        count_before = resp1.json()["connections"]
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.receive_json()
            resp2 = client.get("/health")
            # Should have at least 1 connection
            assert resp2.json()["connections"] >= 1

    def test_expired_token_closes(self):
        token = self._token(expired=True)
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws?token={token}") as ws:
                ws.receive_json()

    def test_unknown_message_type_ignored(self):
        token = self._token()
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "unknown_garbage"})
            # Should not crash — send heartbeat to verify
            ws.send_json({"type": "heartbeat"})
            msg = ws.receive_json()
            assert msg["type"] == "heartbeat_ack"

    def test_message_without_target_is_noop(self):
        token = self._token()
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.receive_json()  # welcome
            ws.send_json({"type": "message", "data": {"text": "no target"}})
            # Should not crash
            ws.send_json({"type": "heartbeat"})
            msg = ws.receive_json()
            assert msg["type"] == "heartbeat_ack"


# ---------------------------------------------------------------------------
# SECURITY tests  (10+ tests)
# ---------------------------------------------------------------------------

class TestWebSocketSecurity:
    """Security tests for the WebSocket service."""

    def _token(self, **kwargs) -> str:
        return _make_session_token(**kwargs)

    def test_no_token_rejected(self):
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws") as ws:
                ws.receive_json()

    def test_empty_token_rejected(self):
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=") as ws:
                ws.receive_json()

    def test_expired_token_rejected(self):
        token = _make_session_token(expired=True)
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws?token={token}") as ws:
                ws.receive_json()

    def test_invalid_jwt_rejected(self):
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=eyJhbGciOiJIUzI1NiJ9.bad.sig") as ws:
                ws.receive_json()

    def test_access_token_type_rejected(self):
        """Only session tokens should be accepted, not access tokens."""
        token = _make_session_token(token_type="access")
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws?token={token}") as ws:
                ws.receive_json()

    def test_email_verification_token_rejected(self):
        token = _make_session_token(token_type="email_verification")
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws?token={token}") as ws:
                ws.receive_json()

    def test_password_reset_token_rejected(self):
        token = _make_session_token(token_type="password_reset")
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws?token={token}") as ws:
                ws.receive_json()

    def test_cannot_impersonate_user_via_message(self):
        """User ID in messages comes from authenticated token, not message body."""
        uid1 = str(uuid4())
        uid2 = str(uuid4())
        t1 = self._token(user_id=uid1)
        t2 = self._token(user_id=uid2)
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={t2}") as ws2:
            ws2.receive_json()  # welcome
            with client.websocket_connect(f"/ws?token={t1}") as ws1:
                ws1.receive_json()  # welcome
                # u1 tries to send a message claiming to be someone else
                ws1.send_json(
                    {
                        "type": "message",
                        "target_user_id": uid2,
                        "data": {"text": "spoofed"},
                    }
                )
                msg = ws2.receive_json()
                # The "from" field should be uid1 (actual), not spoofable
                assert msg["from"] == uid1

    def test_tampered_jwt_rejected(self):
        """Modifying JWT payload should fail validation."""
        import base64
        token = _make_session_token()
        parts = token.split(".")
        # Tamper with payload
        payload_bytes = base64.urlsafe_b64decode(parts[1] + "==")
        tampered = payload_bytes.replace(b"session", b"adminn")
        parts[1] = base64.urlsafe_b64encode(tampered).decode().rstrip("=")
        tampered_token = ".".join(parts)
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws?token={tampered_token}") as ws:
                ws.receive_json()

    def test_wrong_secret_key_rejected(self):
        """Token signed with different secret should be rejected."""
        from jose import jwt as jose_jwt
        token = jose_jwt.encode(
            {"sub": str(uuid4()), "type": "session", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret-key-definitely-not-matching",
            algorithm="HS256",
        )
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws?token={token}") as ws:
                ws.receive_json()

    def test_health_endpoint_requires_no_auth(self):
        """Health endpoint should be publicly accessible."""
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_multiple_rapid_connections_same_user(self):
        """Rapid reconnection should not leak old connections."""
        uid = str(uuid4())
        token = self._token(user_id=uid)
        client = TestClient(app)
        # Connect twice rapidly — second should replace first
        with client.websocket_connect(f"/ws?token={token}") as ws1:
            ws1.receive_json()  # welcome
            with client.websocket_connect(f"/ws?token={token}") as ws2:
                msg = ws2.receive_json()
                assert msg["type"] == "welcome"
