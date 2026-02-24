"""End-to-end tests for report generation with real data."""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.billing.models import LLMAccount, SpendRecord
from src.capture.models import CaptureEvent
from src.compliance.models import AuditEntry, ConsentRecord
from src.groups.models import Group, GroupMember
from src.reporting.generators.safety_report import SafetyReportGenerator
from src.reporting.generators.spend_report import SpendReportGenerator
from src.reporting.generators.activity_report import ActivityReportGenerator
from src.reporting.generators.compliance_report import ComplianceReportGenerator
from src.reporting.schemas import ReportRequest
from src.reporting.service import generate_report_bytes
from src.risk.models import RiskEvent


@pytest_asyncio.fixture
async def report_group(test_session: AsyncSession):
    """Create a group with members and sample data for reports."""
    user = User(
        id=uuid.uuid4(),
        email=f"report-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Report Admin",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="Report Test Family",
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
        display_name="Report Admin",
    )
    child = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Test Child",
    )
    test_session.add(member)
    test_session.add(child)
    await test_session.flush()

    now = datetime.now(timezone.utc)

    # Add capture events
    for i in range(3):
        evt = CaptureEvent(
            id=uuid.uuid4(),
            group_id=group.id,
            member_id=child.id,
            platform="chatgpt",
            session_id=f"session-{i}",
            event_type="prompt",
            timestamp=now - timedelta(hours=i),
            content=f"Test prompt {i}",
            source_channel="extension",
        )
        test_session.add(evt)

    # Add risk events
    for sev in ["critical", "high", "medium"]:
        risk = RiskEvent(
            id=uuid.uuid4(),
            group_id=group.id,
            member_id=child.id,
            category="self_harm" if sev == "critical" else "inappropriate_content",
            severity=sev,
            confidence=0.9,
        )
        test_session.add(risk)

    # Add spend records
    account = LLMAccount(
        id=uuid.uuid4(),
        group_id=group.id,
        provider="openai",
        credentials_encrypted="sk-test",
        status="active",
    )
    test_session.add(account)
    await test_session.flush()

    for amt in [10.50, 5.25, 3.00]:
        record = SpendRecord(
            id=uuid.uuid4(),
            group_id=group.id,
            llm_account_id=account.id,
            member_id=child.id,
            period_start=now - timedelta(days=1),
            period_end=now,
            amount=amt,
            currency="USD",
            model="gpt-4o",
        )
        test_session.add(record)

    # Add consent record
    consent = ConsentRecord(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=child.id,
        consent_type="monitoring",
        parent_user_id=user.id,
        given_at=now,
    )
    test_session.add(consent)

    # Add audit entry
    audit = AuditEntry(
        id=uuid.uuid4(),
        group_id=group.id,
        actor_id=user.id,
        action="member.added",
        resource_type="member",
        resource_id=str(child.id),
    )
    test_session.add(audit)

    await test_session.flush()
    return group, user, member, child, account


class TestSafetyReportGeneration:
    @pytest.mark.asyncio
    async def test_fetch_risk_events(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = SafetyReportGenerator(test_session, group.id)
        data = await gen.fetch_data()
        assert len(data) == 3
        assert any(r["severity"] == "critical" for r in data)
        assert all(r["member_name"] == "Test Child" for r in data)

    @pytest.mark.asyncio
    async def test_generate_csv(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = SafetyReportGenerator(test_session, group.id)
        csv_bytes = await gen.generate_csv()
        text = csv_bytes.decode("utf-8")
        assert "Date,Member,Category,Severity,Confidence,Acknowledged" in text
        assert "Test Child" in text
        assert "critical" in text

    @pytest.mark.asyncio
    async def test_generate_pdf(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = SafetyReportGenerator(test_session, group.id)
        pdf_bytes = await gen.generate_pdf()
        assert len(pdf_bytes) > 100
        assert pdf_bytes[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_generate_json(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = SafetyReportGenerator(test_session, group.id)
        json_bytes = await gen.generate(fmt="json")
        data = json.loads(json_bytes)
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_empty_report(self, test_session):
        gen = SafetyReportGenerator(test_session, uuid.uuid4())
        data = await gen.fetch_data()
        assert data == []

    @pytest.mark.asyncio
    async def test_empty_pdf_still_valid(self, test_session):
        gen = SafetyReportGenerator(test_session, uuid.uuid4())
        pdf_bytes = await gen.generate_pdf()
        assert pdf_bytes[:4] == b"%PDF"


class TestSpendReportGeneration:
    @pytest.mark.asyncio
    async def test_fetch_spend_records(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = SpendReportGenerator(test_session, group.id)
        data = await gen.fetch_data()
        assert len(data) == 3
        assert all(r["provider"] == "openai" for r in data)

    @pytest.mark.asyncio
    async def test_generate_csv(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = SpendReportGenerator(test_session, group.id)
        csv_bytes = await gen.generate_csv()
        text = csv_bytes.decode("utf-8")
        assert "Provider" in text
        assert "$10.50" in text

    @pytest.mark.asyncio
    async def test_generate_pdf(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = SpendReportGenerator(test_session, group.id)
        pdf_bytes = await gen.generate_pdf()
        assert pdf_bytes[:4] == b"%PDF"


class TestActivityReportGeneration:
    @pytest.mark.asyncio
    async def test_fetch_capture_events(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = ActivityReportGenerator(test_session, group.id)
        data = await gen.fetch_data()
        assert len(data) == 3
        assert all(r["platform"] == "chatgpt" for r in data)

    @pytest.mark.asyncio
    async def test_generate_csv(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = ActivityReportGenerator(test_session, group.id)
        csv_bytes = await gen.generate_csv()
        text = csv_bytes.decode("utf-8")
        assert "Platform" in text
        assert "chatgpt" in text

    @pytest.mark.asyncio
    async def test_generate_pdf(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = ActivityReportGenerator(test_session, group.id)
        pdf_bytes = await gen.generate_pdf()
        assert pdf_bytes[:4] == b"%PDF"


class TestComplianceReportGeneration:
    @pytest.mark.asyncio
    async def test_fetch_consent_and_audit(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = ComplianceReportGenerator(test_session, group.id)
        data = await gen.fetch_data()
        # 1 consent + 1 audit = 2 rows
        assert len(data) >= 2
        types = {r["type"] for r in data}
        assert "Consent" in types
        assert "Audit" in types

    @pytest.mark.asyncio
    async def test_generate_csv(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = ComplianceReportGenerator(test_session, group.id)
        csv_bytes = await gen.generate_csv()
        text = csv_bytes.decode("utf-8")
        assert "Record Type" in text

    @pytest.mark.asyncio
    async def test_generate_pdf(self, test_session, report_group):
        group, user, member, child, account = report_group
        gen = ComplianceReportGenerator(test_session, group.id)
        pdf_bytes = await gen.generate_pdf()
        assert pdf_bytes[:4] == b"%PDF"


class TestReportServiceIntegration:
    @pytest.mark.asyncio
    async def test_generate_report_bytes_pdf(self, test_session, report_group):
        group, user, member, child, account = report_group
        content, filename = await generate_report_bytes(
            test_session,
            ReportRequest(group_id=group.id, report_type="risk", format="pdf"),
        )
        assert content[:4] == b"%PDF"
        assert filename.endswith(".pdf")

    @pytest.mark.asyncio
    async def test_generate_report_bytes_csv(self, test_session, report_group):
        group, user, member, child, account = report_group
        content, filename = await generate_report_bytes(
            test_session,
            ReportRequest(group_id=group.id, report_type="spend", format="csv"),
        )
        assert b"Provider" in content
        assert filename.endswith(".csv")

    @pytest.mark.asyncio
    async def test_generate_report_bytes_json(self, test_session, report_group):
        group, user, member, child, account = report_group
        content, filename = await generate_report_bytes(
            test_session,
            ReportRequest(group_id=group.id, report_type="activity", format="json"),
        )
        data = json.loads(content)
        assert isinstance(data, list)
        assert filename.endswith(".json")
