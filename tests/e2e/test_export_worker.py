"""End-to-end tests for GDPR data export workflow."""

import json
import uuid
import zipfile
import io
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.capture.models import CaptureEvent
from src.compliance.export_worker import (
    export_user_data_bytes,
    process_pending_exports,
    _collect_user_data,
)
from src.compliance.models import AuditEntry, DataDeletionRequest
from src.groups.models import Group, GroupMember
from src.risk.models import RiskEvent


@pytest_asyncio.fixture
async def export_user(test_session: AsyncSession):
    """Create a user with data for export testing."""
    user = User(
        id=uuid.uuid4(),
        email=f"export-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Export User",
        account_type="family",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Export Test Group",
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
        display_name="Export User",
    )
    test_session.add(member)
    await test_session.flush()

    now = datetime.now(timezone.utc)
    capture = CaptureEvent(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=member.id,
        platform="chatgpt",
        session_id="export-session",
        event_type="prompt",
        timestamp=now,
        content="test export content",
        source_channel="extension",
    )
    test_session.add(capture)

    risk = RiskEvent(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=member.id,
        category="test",
        severity="low",
        confidence=0.5,
    )
    test_session.add(risk)
    await test_session.flush()

    return user, group, member


class TestCollectUserData:
    @pytest.mark.asyncio
    async def test_collects_profile(self, test_session, export_user):
        user, group, member = export_user
        data = await _collect_user_data(test_session, user.id)
        assert "profile" in data
        assert data["profile"]["email"] == user.email
        assert data["profile"]["display_name"] == "Export User"

    @pytest.mark.asyncio
    async def test_collects_memberships(self, test_session, export_user):
        user, group, member = export_user
        data = await _collect_user_data(test_session, user.id)
        assert len(data["memberships"]) >= 1
        assert data["memberships"][0]["role"] == "parent"

    @pytest.mark.asyncio
    async def test_collects_groups_owned(self, test_session, export_user):
        user, group, member = export_user
        data = await _collect_user_data(test_session, user.id)
        assert len(data["groups_owned"]) >= 1
        assert data["groups_owned"][0]["name"] == "Export Test Group"

    @pytest.mark.asyncio
    async def test_collects_capture_events(self, test_session, export_user):
        user, group, member = export_user
        data = await _collect_user_data(test_session, user.id)
        assert len(data["capture_events"]) >= 1
        assert data["capture_events"][0]["platform"] == "chatgpt"

    @pytest.mark.asyncio
    async def test_collects_risk_events(self, test_session, export_user):
        user, group, member = export_user
        data = await _collect_user_data(test_session, user.id)
        assert len(data["risk_events"]) >= 1

    @pytest.mark.asyncio
    async def test_includes_metadata(self, test_session, export_user):
        user, group, member = export_user
        data = await _collect_user_data(test_session, user.id)
        assert "export_metadata" in data
        assert data["export_metadata"]["user_id"] == str(user.id)
        assert data["export_metadata"]["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_user_with_no_data(self, test_session):
        user = User(
            id=uuid.uuid4(),
            email=f"empty-{uuid.uuid4().hex[:8]}@example.com",
            password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
            display_name="Empty User",
            account_type="family",
            email_verified=False,
            mfa_enabled=False,
        )
        test_session.add(user)
        await test_session.flush()

        data = await _collect_user_data(test_session, user.id)
        assert data["profile"]["email"] == user.email
        assert data["memberships"] == []
        assert data["capture_events"] == []


class TestExportUserDataBytes:
    @pytest.mark.asyncio
    async def test_returns_valid_zip(self, test_session, export_user):
        user, group, member = export_user
        zip_bytes = await export_user_data_bytes(test_session, user.id)
        assert len(zip_bytes) > 0

        # Verify it's a valid ZIP
        buf = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(buf, "r") as zf:
            names = zf.namelist()
            assert "profile.json" in names
            assert "memberships.json" in names
            assert "capture_events.json" in names
            assert "risk_events.json" in names
            assert "export_metadata.json" in names

    @pytest.mark.asyncio
    async def test_zip_contains_valid_json(self, test_session, export_user):
        user, group, member = export_user
        zip_bytes = await export_user_data_bytes(test_session, user.id)

        buf = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(buf, "r") as zf:
            profile_data = json.loads(zf.read("profile.json"))
            assert profile_data["email"] == user.email

            events = json.loads(zf.read("capture_events.json"))
            assert isinstance(events, list)
            assert len(events) >= 1


class TestProcessPendingExports:
    @pytest.mark.asyncio
    async def test_processes_pending_export(self, test_session, export_user):
        user, group, member = export_user

        request = DataDeletionRequest(
            id=uuid.uuid4(),
            user_id=user.id,
            request_type="data_export",
            status="pending",
        )
        test_session.add(request)
        await test_session.flush()

        completed = await process_pending_exports(test_session)
        assert completed == 1

        await test_session.refresh(request)
        assert request.status == "completed"
        assert request.completed_at is not None

    @pytest.mark.asyncio
    async def test_creates_audit_trail(self, test_session, export_user):
        user, group, member = export_user

        request = DataDeletionRequest(
            id=uuid.uuid4(),
            user_id=user.id,
            request_type="data_export",
            status="pending",
        )
        test_session.add(request)
        await test_session.flush()

        await process_pending_exports(test_session)

        result = await test_session.execute(
            select(AuditEntry).where(
                AuditEntry.action == "data_export.completed",
                AuditEntry.resource_id == str(user.id),
            )
        )
        audit = result.scalar_one_or_none()
        assert audit is not None

    @pytest.mark.asyncio
    async def test_ignores_deletion_requests(self, test_session, export_user):
        user, group, member = export_user

        request = DataDeletionRequest(
            id=uuid.uuid4(),
            user_id=user.id,
            request_type="full_deletion",
            status="pending",
        )
        test_session.add(request)
        await test_session.flush()

        completed = await process_pending_exports(test_session)
        assert completed == 0

    @pytest.mark.asyncio
    async def test_no_pending_exports(self, test_session):
        completed = await process_pending_exports(test_session)
        assert completed == 0
