"""End-to-end tests for GDPR data deletion workflow."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerts.models import Alert
from src.auth.models import User
from src.capture.models import CaptureEvent
from src.compliance.deletion_worker import process_pending_deletions, _delete_user_data
from src.compliance.models import AuditEntry, DataDeletionRequest
from src.groups.models import Group, GroupMember
from src.risk.models import RiskEvent


@pytest_asyncio.fixture
async def user_with_data(test_session: AsyncSession):
    """Create a user with data across multiple tables for deletion testing."""
    user = User(
        id=uuid.uuid4(),
        email=f"delete-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Delete Me",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Delete Test Group",
        type="family",
        owner_id=user.id,
    )
    test_session.add(group)
    await test_session.flush()

    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=user.id,
        role="parent",
        display_name="Delete Me",
    )
    test_session.add(member)
    await test_session.flush()

    now = datetime.now(timezone.utc)

    # Add capture events
    capture = CaptureEvent(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=member.id,
        platform="chatgpt",
        session_id="delete-session",
        event_type="prompt",
        timestamp=now,
        content="test content",
        source_channel="extension",
    )
    test_session.add(capture)

    # Add risk event
    risk = RiskEvent(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=member.id,
        category="test",
        severity="low",
        confidence=0.5,
    )
    test_session.add(risk)

    # Add alert
    alert = Alert(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=member.id,
        severity="medium",
        title="Test Alert",
        body="Test body",
        channel="portal",
        status="pending",
    )
    test_session.add(alert)
    await test_session.flush()

    return user, group, member


class TestDeleteUserData:
    @pytest.mark.asyncio
    async def test_deletes_capture_events(self, test_session, user_with_data):
        user, group, member = user_with_data
        counts = await _delete_user_data(test_session, user.id)
        assert counts.get("capture_events", 0) >= 1

        result = await test_session.execute(
            select(CaptureEvent).where(CaptureEvent.member_id == member.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_deletes_risk_events(self, test_session, user_with_data):
        user, group, member = user_with_data
        counts = await _delete_user_data(test_session, user.id)
        assert counts.get("risk_events", 0) >= 1

    @pytest.mark.asyncio
    async def test_deletes_alerts(self, test_session, user_with_data):
        user, group, member = user_with_data
        counts = await _delete_user_data(test_session, user.id)
        assert counts.get("alerts", 0) >= 1

    @pytest.mark.asyncio
    async def test_deletes_group_members(self, test_session, user_with_data):
        user, group, member = user_with_data
        counts = await _delete_user_data(test_session, user.id)
        assert counts.get("group_members", 0) >= 1

    @pytest.mark.asyncio
    async def test_soft_deletes_user(self, test_session, user_with_data):
        user, group, member = user_with_data
        counts = await _delete_user_data(test_session, user.id)
        assert counts.get("users", 0) == 1

        # User should be soft-deleted
        await test_session.refresh(user)
        assert user.deleted_at is not None
        assert user.display_name == "Deleted User"
        assert user.password_hash is None
        assert "deleted_" in user.email

    @pytest.mark.asyncio
    async def test_returns_all_counts(self, test_session, user_with_data):
        user, group, member = user_with_data
        counts = await _delete_user_data(test_session, user.id)
        assert isinstance(counts, dict)
        assert "users" in counts

    @pytest.mark.asyncio
    async def test_no_data_user(self, test_session):
        """User with no group memberships — should still soft-delete the user."""
        user = User(
            id=uuid.uuid4(),
            email=f"nodata-{uuid.uuid4().hex[:8]}@example.com",
            password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
            display_name="No Data User",
            account_type="family",
            email_verified=False,
            mfa_enabled=False,
        )
        test_session.add(user)
        await test_session.flush()

        counts = await _delete_user_data(test_session, user.id)
        assert counts.get("users") == 1


class TestProcessPendingDeletions:
    @pytest.mark.asyncio
    async def test_processes_pending_requests(self, test_session, user_with_data):
        user, group, member = user_with_data

        request = DataDeletionRequest(
            id=uuid.uuid4(),
            user_id=user.id,
            request_type="full_deletion",
            status="pending",
        )
        test_session.add(request)
        await test_session.flush()

        completed = await process_pending_deletions(test_session)
        assert completed == 1

        await test_session.refresh(request)
        assert request.status == "completed"
        assert request.completed_at is not None

    @pytest.mark.asyncio
    async def test_creates_audit_trail(self, test_session, user_with_data):
        user, group, member = user_with_data

        request = DataDeletionRequest(
            id=uuid.uuid4(),
            user_id=user.id,
            request_type="full_deletion",
            status="pending",
        )
        test_session.add(request)
        await test_session.flush()

        await process_pending_deletions(test_session)

        result = await test_session.execute(
            select(AuditEntry).where(
                AuditEntry.action == "data_deletion.completed",
                AuditEntry.resource_id == str(user.id),
            )
        )
        audit = result.scalar_one_or_none()
        assert audit is not None
        assert audit.details is not None
        assert "deleted_counts" in audit.details

    @pytest.mark.asyncio
    async def test_ignores_non_deletion_requests(self, test_session, user_with_data):
        user, group, member = user_with_data

        request = DataDeletionRequest(
            id=uuid.uuid4(),
            user_id=user.id,
            request_type="data_export",
            status="pending",
        )
        test_session.add(request)
        await test_session.flush()

        completed = await process_pending_deletions(test_session)
        assert completed == 0

    @pytest.mark.asyncio
    async def test_ignores_completed_requests(self, test_session, user_with_data):
        user, group, member = user_with_data

        request = DataDeletionRequest(
            id=uuid.uuid4(),
            user_id=user.id,
            request_type="full_deletion",
            status="completed",
        )
        test_session.add(request)
        await test_session.flush()

        completed = await process_pending_deletions(test_session)
        assert completed == 0

    @pytest.mark.asyncio
    async def test_no_pending_requests(self, test_session):
        completed = await process_pending_deletions(test_session)
        assert completed == 0
