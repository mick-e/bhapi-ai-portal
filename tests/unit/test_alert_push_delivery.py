"""Unit tests for push notification delivery on alert creation (P2-S8).

Tests that create_alert sends a push notification to the group owner,
that push failures never block alert creation, and that missing owners
are handled gracefully.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import src.alerts.models  # noqa: F401 — ensure alerts table is created
import src.alerts.push  # noqa: F401 — ensure push_tokens table is created
from src.alerts.schemas import AlertCreate
from src.alerts.service import create_alert
from src.auth.models import User
from src.groups.models import Group

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(session: AsyncSession) -> User:
    """Create and flush a minimal User row."""
    user = User(
        id=uuid4(),
        email=f"owner-{uuid4().hex[:8]}@example.com",
        display_name="Test Owner",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_group(session: AsyncSession, owner_id) -> Group:
    """Create and flush a Group owned by the given user."""
    group = Group(
        id=uuid4(),
        name="Test Family",
        type="family",
        owner_id=owner_id,
    )
    session.add(group)
    await session.flush()
    return group


def _alert_data(group_id, **kwargs) -> AlertCreate:
    """Return a valid AlertCreate instance for the given group."""
    return AlertCreate(
        group_id=group_id,
        severity=kwargs.get("severity", "high"),
        title=kwargs.get("title", "Test Alert Title"),
        body=kwargs.get("body", "Test alert body content."),
        source=kwargs.get("source", "ai"),
        channel=kwargs.get("channel", "portal"),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAlertPushDelivery:
    """Push notification delivery behaviour on alert creation."""

    @pytest.mark.asyncio
    async def test_alert_creation_sends_push_to_owner(self, test_session: AsyncSession):
        """create_alert sends a push notification to the group owner."""
        owner = await _make_user(test_session)
        group = await _make_group(test_session, owner.id)
        data = _alert_data(group.id, title="Child used harmful AI prompt")

        mock_send = AsyncMock(return_value=True)

        # expo_push_service is imported inside create_alert via
        # `from src.alerts.push import expo_push_service`.
        # Patching the singleton on the source module is the correct target.
        with patch("src.alerts.push.expo_push_service") as mock_push:
            mock_push.send_notification = mock_send
            with patch("src.alerts.push.expo_push_service.send_notification", mock_send):
                with patch("src.alerts.sse.sse_manager", new=AsyncMock()):
                    alert = await create_alert(test_session, data)

        assert alert.id is not None
        assert alert.group_id == group.id

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["user_id"] == owner.id
        assert call_kwargs["title"] == f"Bhapi Alert: {data.title}"
        assert call_kwargs["body"] == data.body[:200]
        assert call_kwargs["data"]["alert_id"] == str(alert.id)
        assert call_kwargs["data"]["severity"] == data.severity

    @pytest.mark.asyncio
    async def test_push_failure_does_not_prevent_alert_creation(
        self, test_session: AsyncSession
    ):
        """If push delivery raises an exception, the alert is still created."""
        owner = await _make_user(test_session)
        group = await _make_group(test_session, owner.id)
        data = _alert_data(group.id, severity="critical", title="Panic button pressed")

        mock_send = AsyncMock(side_effect=Exception("Expo API timeout"))

        with patch("src.alerts.push.expo_push_service.send_notification", mock_send):
            with patch("src.alerts.sse.sse_manager", new=AsyncMock()):
                alert = await create_alert(test_session, data)

        # Alert must be created despite push failure
        assert alert.id is not None
        assert alert.severity == "critical"
        assert alert.title == data.title

    @pytest.mark.asyncio
    async def test_alert_created_when_group_obj_is_none(
        self, test_session: AsyncSession
    ):
        """Alert creation succeeds when the Group query returns None in the push block.

        This can happen if the group was soft-deleted between alert creation and
        the push lookup. The push block must guard against a None group_obj silently.

        We simulate this by patching expo_push_service.send_notification and verifying
        it is NOT called when group_obj is None (patched via the Group model query).
        """
        owner = await _make_user(test_session)
        group = await _make_group(test_session, owner.id)
        data = _alert_data(group.id, title="No group push test")

        mock_send = AsyncMock(return_value=True)

        # Intercept the Group select inside create_alert's push block.
        # We count DB calls: the push block does a SELECT on groups after the alert
        # is flushed. We return a sync result wrapper with scalar_one_or_none=None
        # for that specific query.
        original_execute = test_session.execute
        groups_query_count = 0

        class _NullResult:
            """Minimal result stand-in whose scalar_one_or_none() returns None."""
            def scalar_one_or_none(self):
                return None

            def scalars(self):
                return self

            def all(self):
                return []

            def scalar(self):
                return None

        async def patched_execute(stmt, *args, **kwargs):
            nonlocal groups_query_count
            compiled = str(stmt).lower()
            if "from groups" in compiled:
                groups_query_count += 1
                return _NullResult()
            return await original_execute(stmt, *args, **kwargs)

        with patch.object(test_session, "execute", side_effect=patched_execute):
            with patch("src.alerts.push.expo_push_service.send_notification", mock_send):
                with patch("src.alerts.sse.sse_manager", new=AsyncMock()):
                    alert = await create_alert(test_session, data)

        assert alert.id is not None
        # send_notification must NOT have been called (group_obj was None)
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_notification_body_truncated_to_200_chars(
        self, test_session: AsyncSession
    ):
        """Body passed to push service is capped at 200 characters."""
        owner = await _make_user(test_session)
        group = await _make_group(test_session, owner.id)
        long_body = "B" * 500  # 500-char body — must be truncated to 200
        data = _alert_data(group.id, body=long_body)

        mock_send = AsyncMock(return_value=True)

        with patch("src.alerts.push.expo_push_service.send_notification", mock_send):
            with patch("src.alerts.sse.sse_manager", new=AsyncMock()):
                alert = await create_alert(test_session, data)

        assert alert.id is not None
        call_kwargs = mock_send.call_args.kwargs
        assert len(call_kwargs["body"]) == 200
        assert call_kwargs["body"] == long_body[:200]
