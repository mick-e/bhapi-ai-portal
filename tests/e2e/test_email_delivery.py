"""End-to-end tests for alert email delivery and auth email flows."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert, NotificationPreference
from src.alerts.delivery import deliver_alert_email, deliver_risk_alert
from src.alerts.scheduler import (
    run_renotification_check,
    schedule_renotification,
    reset_renotify_state,
)
from src.alerts.digest import run_hourly_digest, run_daily_digest
from src.auth.models import User
from src.auth.service import (
    confirm_email,
    create_email_verification_token,
    register_user,
    request_password_reset,
    reset_password,
    send_verification_email,
)
from src.auth.schemas import RegisterRequest
from src.groups.models import Group, GroupMember


@pytest_asyncio.fixture
async def test_user(test_session: AsyncSession):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Test Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest_asyncio.fixture
async def test_group_with_admin(test_session: AsyncSession, test_user: User):
    """Create a group with a parent admin member."""
    group = Group(
        id=uuid.uuid4(),
        name="Test Family",
        type="family",
        owner_id=test_user.id,
    )
    test_session.add(group)
    await test_session.flush()

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=test_user.id,
        role="parent",
        display_name="Test Parent",
        date_of_birth=datetime(2014, 5, 15, tzinfo=timezone.utc),
    )
    test_session.add(member)
    await test_session.flush()

    return group, member, test_user


def _make_alert(group_id, member_id=None, severity="critical", status="pending"):
    return Alert(
        id=uuid.uuid4(),
        group_id=group_id,
        member_id=member_id,
        severity=severity,
        title=f"Test {severity} alert",
        body=f"Detected test content on chatgpt with 90% confidence. Test reasoning.",
        channel="portal",
        status=status,
    )


class TestAlertEmailDelivery:
    """Test alert email delivery to group admins."""

    @pytest.mark.asyncio
    async def test_critical_alert_sends_email(self, test_session, test_group_with_admin):
        group, member, user = test_group_with_admin
        alert = _make_alert(group.id, member.id, severity="critical")
        test_session.add(alert)
        await test_session.flush()

        result = await deliver_alert_email(test_session, alert)
        assert result is True
        assert alert.status == "sent"

    @pytest.mark.asyncio
    async def test_high_alert_sends_email(self, test_session, test_group_with_admin):
        group, member, user = test_group_with_admin
        alert = _make_alert(group.id, member.id, severity="high")
        test_session.add(alert)
        await test_session.flush()

        result = await deliver_alert_email(test_session, alert)
        assert result is True

    @pytest.mark.asyncio
    async def test_deliver_risk_alert_critical_sends(self, test_session, test_group_with_admin):
        group, member, user = test_group_with_admin
        alert = _make_alert(group.id, member.id, severity="critical")
        test_session.add(alert)
        await test_session.flush()

        result = await deliver_risk_alert(test_session, alert)
        assert result is True

    @pytest.mark.asyncio
    async def test_deliver_risk_alert_low_defers(self, test_session, test_group_with_admin):
        group, member, user = test_group_with_admin
        alert = _make_alert(group.id, member.id, severity="low")
        test_session.add(alert)
        await test_session.flush()

        result = await deliver_risk_alert(test_session, alert)
        assert result is False

    @pytest.mark.asyncio
    async def test_no_recipients_returns_false(self, test_session, test_group_with_admin):
        """Alert for a group where admin member has no user_id should return False."""
        group, member, user = test_group_with_admin

        # Create a second group with a member that has no user_id (so no email)
        group2 = Group(
            id=uuid.uuid4(),
            name="No-Admin Group",
            type="family",
            owner_id=user.id,
        )
        test_session.add(group2)
        await test_session.flush()

        member2 = GroupMember(
            id=uuid.uuid4(),
            group_id=group2.id,
            user_id=None,  # No linked user
            role="member",  # Not an admin role
            display_name="Child Member",
        )
        test_session.add(member2)
        await test_session.flush()

        alert = _make_alert(group2.id, member2.id, severity="critical")
        test_session.add(alert)
        await test_session.flush()

        result = await deliver_alert_email(test_session, alert)
        assert result is False


class TestRenotificationScheduler:
    """Test re-notification scheduling and execution."""

    def setup_method(self):
        reset_renotify_state()

    @pytest.mark.asyncio
    async def test_schedule_sets_renotify_at(self, test_session, test_group_with_admin):
        group, member, user = test_group_with_admin
        alert = _make_alert(group.id, member.id, severity="critical")
        test_session.add(alert)
        await test_session.flush()

        await schedule_renotification(test_session, alert)
        assert alert.re_notify_at is not None
        assert alert.re_notify_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_schedule_ignores_low_severity(self, test_session, test_group_with_admin):
        group, member, user = test_group_with_admin
        alert = _make_alert(group.id, member.id, severity="low")
        test_session.add(alert)
        await test_session.flush()

        await schedule_renotification(test_session, alert)
        assert alert.re_notify_at is None

    @pytest.mark.asyncio
    async def test_renotification_check_sends_due_alerts(self, test_session, test_group_with_admin):
        group, member, user = test_group_with_admin
        alert = _make_alert(group.id, member.id, severity="critical")
        alert.re_notify_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        test_session.add(alert)
        await test_session.flush()

        count = await run_renotification_check(test_session)
        assert count >= 1

    @pytest.mark.asyncio
    async def test_acknowledged_not_renotified(self, test_session, test_group_with_admin):
        group, member, user = test_group_with_admin
        alert = _make_alert(group.id, member.id, severity="critical", status="acknowledged")
        alert.re_notify_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        test_session.add(alert)
        await test_session.flush()

        count = await run_renotification_check(test_session)
        assert count == 0


class TestDigestBatching:
    """Test hourly and daily digest batching."""

    @pytest.mark.asyncio
    async def test_hourly_digest_no_prefs_sends_nothing(self, test_session):
        count = await run_hourly_digest(test_session)
        assert count == 0

    @pytest.mark.asyncio
    async def test_daily_digest_no_prefs_sends_nothing(self, test_session):
        count = await run_daily_digest(test_session)
        assert count == 0

    @pytest.mark.asyncio
    async def test_hourly_digest_with_prefs_and_alerts(self, test_session, test_group_with_admin):
        group, member, user = test_group_with_admin

        # Create preference for hourly digest
        pref = NotificationPreference(
            id=uuid.uuid4(),
            group_id=group.id,
            user_id=user.id,
            category="risk_alert",
            channel="email",
            digest_mode="hourly",
            enabled=True,
        )
        test_session.add(pref)

        # Create an alert within the hour
        alert = _make_alert(group.id, member.id, severity="medium")
        test_session.add(alert)
        await test_session.flush()

        count = await run_hourly_digest(test_session)
        assert count >= 1


class TestAuthEmailFlows:
    """Test email verification and password reset flows."""

    @pytest.mark.asyncio
    async def test_send_verification_email(self, test_session, test_user):
        result = await send_verification_email(test_user)
        assert result is True

    @pytest.mark.asyncio
    async def test_confirm_email_sets_verified(self, test_session, test_user):
        assert test_user.email_verified is False
        token = create_email_verification_token(test_user.id)

        user = await confirm_email(test_session, token)
        assert user.email_verified is True

    @pytest.mark.asyncio
    async def test_confirm_email_idempotent(self, test_session, test_user):
        token = create_email_verification_token(test_user.id)
        await confirm_email(test_session, token)
        # Second confirmation is a no-op
        user = await confirm_email(test_session, token)
        assert user.email_verified is True

    @pytest.mark.asyncio
    async def test_password_reset_request_no_enumeration(self, test_session):
        """Reset request always returns True even for non-existent emails."""
        result = await request_password_reset(test_session, "nobody@example.com")
        assert result is True

    @pytest.mark.asyncio
    async def test_password_reset_flow(self, test_session):
        """Full password reset: register → request reset → reset password."""
        from src.auth.service import authenticate_user, create_password_reset_token

        # Register a user
        user = await register_user(
            test_session,
            RegisterRequest(
                email=f"reset-{uuid.uuid4().hex[:8]}@example.com",
                password="OldPass123",
                display_name="Reset User",
                account_type="family",
            ),
        )

        # Create reset token and reset password
        token = create_password_reset_token(user.id)
        await reset_password(test_session, token, "NewPass456")

        # Verify new password works
        authed = await authenticate_user(test_session, user.email, "NewPass456")
        assert authed.id == user.id
