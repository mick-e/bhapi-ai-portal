"""Unit tests for the TypingManager — in-memory typing indicators."""

import time
from datetime import datetime

from src.realtime.typing import TypingManager

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestTypingManagerInit:
    """Test manager initialization."""

    def test_creates_empty_manager(self):
        mgr = TypingManager()
        assert mgr.active_count == 0

    def test_custom_timeout(self):
        mgr = TypingManager(timeout_seconds=10.0)
        assert mgr._timeout == 10.0


# ---------------------------------------------------------------------------
# Start / Stop
# ---------------------------------------------------------------------------


class TestTypingStartStop:
    """Test start_typing and stop_typing."""

    def test_start_typing_sets_state(self):
        mgr = TypingManager()
        mgr.start_typing("user-1", "conv-1")
        assert mgr.is_typing("user-1")

    def test_start_typing_publishes_event(self):
        """Starting typing records the conversation and timestamp."""
        mgr = TypingManager()
        mgr.start_typing("user-1", "conv-1")
        state = mgr._typing["user-1"]
        assert state.conversation_id == "conv-1"
        assert isinstance(state.started_at, datetime)

    def test_stop_typing_clears_state(self):
        mgr = TypingManager()
        mgr.start_typing("user-1", "conv-1")
        mgr.stop_typing("user-1")
        assert not mgr.is_typing("user-1")

    def test_stop_typing_idempotent(self):
        mgr = TypingManager()
        mgr.stop_typing("user-1")  # No error when user isn't typing

    def test_start_typing_overwrites_previous(self):
        mgr = TypingManager()
        mgr.start_typing("user-1", "conv-1")
        mgr.start_typing("user-1", "conv-2")
        assert mgr.is_typing("user-1", "conv-2")
        assert not mgr.is_typing("user-1", "conv-1")


# ---------------------------------------------------------------------------
# Auto-expiry
# ---------------------------------------------------------------------------


class TestTypingAutoExpiry:
    """Test timeout-based expiry of typing indicators."""

    def test_typing_auto_expires_after_timeout(self):
        """Typing indicator auto-expires after the timeout."""
        mgr = TypingManager(timeout_seconds=0.1)
        mgr.start_typing("user-1", "conv-1")
        assert mgr.is_typing("user-1")
        time.sleep(0.15)
        assert not mgr.is_typing("user-1")

    def test_typing_active_before_timeout(self):
        mgr = TypingManager(timeout_seconds=10.0)
        mgr.start_typing("user-1", "conv-1")
        assert mgr.is_typing("user-1")

    def test_refresh_extends_timeout(self):
        """Calling start_typing again refreshes the timer."""
        mgr = TypingManager(timeout_seconds=0.2)
        mgr.start_typing("user-1", "conv-1")
        time.sleep(0.1)
        mgr.start_typing("user-1", "conv-1")  # refresh
        time.sleep(0.1)
        assert mgr.is_typing("user-1")  # Still active — refreshed


# ---------------------------------------------------------------------------
# is_typing
# ---------------------------------------------------------------------------


class TestIsTyping:
    """Test is_typing queries."""

    def test_is_typing_without_conversation_filter(self):
        mgr = TypingManager()
        mgr.start_typing("user-1", "conv-1")
        assert mgr.is_typing("user-1") is True

    def test_is_typing_with_correct_conversation(self):
        mgr = TypingManager()
        mgr.start_typing("user-1", "conv-1")
        assert mgr.is_typing("user-1", "conv-1") is True

    def test_is_typing_with_wrong_conversation(self):
        mgr = TypingManager()
        mgr.start_typing("user-1", "conv-1")
        assert mgr.is_typing("user-1", "conv-99") is False

    def test_is_typing_unknown_user(self):
        mgr = TypingManager()
        assert mgr.is_typing("nobody") is False

    def test_is_typing_cleans_up_expired(self):
        """Expired entries are cleaned up on read."""
        mgr = TypingManager(timeout_seconds=0.05)
        mgr.start_typing("user-1", "conv-1")
        time.sleep(0.1)
        assert not mgr.is_typing("user-1")
        assert mgr.active_count == 0


# ---------------------------------------------------------------------------
# get_typing_users
# ---------------------------------------------------------------------------


class TestGetTypingUsers:
    """Test listing typing users per conversation."""

    def test_no_typing_users(self):
        mgr = TypingManager()
        assert mgr.get_typing_users("conv-1") == []

    def test_single_typing_user(self):
        mgr = TypingManager()
        mgr.start_typing("user-1", "conv-1")
        assert mgr.get_typing_users("conv-1") == ["user-1"]

    def test_multiple_typing_users(self):
        mgr = TypingManager()
        mgr.start_typing("user-1", "conv-1")
        mgr.start_typing("user-2", "conv-1")
        users = mgr.get_typing_users("conv-1")
        assert set(users) == {"user-1", "user-2"}

    def test_filters_by_conversation(self):
        mgr = TypingManager()
        mgr.start_typing("user-1", "conv-1")
        mgr.start_typing("user-2", "conv-2")
        assert mgr.get_typing_users("conv-1") == ["user-1"]
        assert mgr.get_typing_users("conv-2") == ["user-2"]

    def test_expired_users_excluded(self):
        mgr = TypingManager(timeout_seconds=0.05)
        mgr.start_typing("user-1", "conv-1")
        time.sleep(0.1)
        mgr.start_typing("user-2", "conv-1")
        users = mgr.get_typing_users("conv-1")
        assert users == ["user-2"]

    def test_expired_entries_cleaned_up(self):
        mgr = TypingManager(timeout_seconds=0.05)
        mgr.start_typing("user-1", "conv-1")
        time.sleep(0.1)
        mgr.get_typing_users("conv-1")
        assert "user-1" not in mgr._typing


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------


class TestTypingClear:
    """Test clearing all state."""

    def test_clear_removes_all(self):
        mgr = TypingManager()
        mgr.start_typing("user-1", "conv-1")
        mgr.start_typing("user-2", "conv-2")
        mgr.clear()
        assert mgr.active_count == 0
        assert not mgr.is_typing("user-1")
        assert not mgr.is_typing("user-2")


# ---------------------------------------------------------------------------
# Module singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    """Test module-level singleton."""

    def test_typing_manager_singleton_exists(self):
        from src.realtime.typing import typing_manager
        assert isinstance(typing_manager, TypingManager)
