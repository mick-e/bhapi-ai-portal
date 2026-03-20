"""Unit tests for COPPA Dashboard checklist logic."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.compliance.coppa_dashboard import (
    COPPAChecklistItem,
    COPPAComplianceReport,
    assess_coppa_compliance,
)
from src.compliance.models import ConsentRecord
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_report_dataclass_fields():
    """COPPAComplianceReport should have all required fields."""
    report = COPPAComplianceReport(
        group_id="test",
        group_name="Test Group",
        score=85.0,
        status="compliant",
        checklist=[],
        assessed_at="2026-01-01T00:00:00",
    )
    assert report.score == 85.0
    assert report.status == "compliant"
    assert report.last_review is None


@pytest.mark.asyncio
async def test_checklist_item_dataclass():
    """COPPAChecklistItem should hold all fields."""
    item = COPPAChecklistItem(
        id="test_item",
        label="Test",
        description="A test item",
        status="complete",
        evidence="Some evidence",
        action_url="/test",
        regulation_ref="16 CFR 312.5",
    )
    assert item.id == "test_item"
    assert item.status == "complete"


@pytest.mark.asyncio
async def test_score_all_complete_no_minors(test_session):
    """Group with no minors should have high compliance score."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    # Mark annual review
    settings = dict(group.settings or {})
    settings["coppa_last_review"] = datetime.now(timezone.utc).isoformat()
    group.settings = settings
    await test_session.flush()

    report = await assess_coppa_compliance(test_session, group.id)
    # With no minors, consent items are N/A; platform defaults complete; review complete
    assert report.score >= 80
    assert report.status in ("compliant", "partial")


@pytest.mark.asyncio
async def test_score_with_unconsented_minor(test_session):
    """Group with unconsented minor should have lower score."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    minor = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
        date_of_birth=datetime(2019, 3, 10, tzinfo=timezone.utc),
    )
    test_session.add(minor)
    await test_session.flush()

    report = await assess_coppa_compliance(test_session, group.id)
    # Two items should be incomplete (consent + FTC method)
    incomplete = [i for i in report.checklist if i.status == "incomplete"]
    assert len(incomplete) >= 2


@pytest.mark.asyncio
async def test_score_with_partial_consent(test_session):
    """Group with consent but no FTC verification should show warning."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    minor = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
        date_of_birth=datetime(2019, 3, 10, tzinfo=timezone.utc),
    )
    test_session.add(minor)
    await test_session.flush()

    # Add consent without FTC verification
    consent = ConsentRecord(
        id=uuid4(),
        group_id=group.id,
        member_id=minor.id,
        consent_type="coppa",
        parent_user_id=owner_id,
        evidence=json.dumps({"method": "email", "verification_status": "unverified"}),
    )
    test_session.add(consent)
    await test_session.flush()

    report = await assess_coppa_compliance(test_session, group.id)
    ftc_item = next(i for i in report.checklist if i.id == "ftc_approved_method")
    assert ftc_item.status in ("incomplete", "warning")


@pytest.mark.asyncio
async def test_pii_detection_disabled(test_session):
    """PII detection disabled should mark item incomplete."""
    group, owner_id = await make_test_group(
        test_session, name="Family", group_type="family",
        settings={"pii_detection": False},
    )

    report = await assess_coppa_compliance(test_session, group.id)
    pii_item = next(i for i in report.checklist if i.id == "pii_detection_enabled")
    assert pii_item.status == "incomplete"


@pytest.mark.asyncio
async def test_pii_detection_enabled(test_session):
    """PII detection enabled should mark item complete."""
    group, owner_id = await make_test_group(
        test_session, name="Family", group_type="family",
        settings={"pii_detection": True},
    )

    report = await assess_coppa_compliance(test_session, group.id)
    pii_item = next(i for i in report.checklist if i.id == "pii_detection_enabled")
    assert pii_item.status == "complete"


@pytest.mark.asyncio
async def test_annual_review_overdue(test_session):
    """Annual review older than 365 days should be incomplete."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    old_date = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    settings = dict(group.settings or {})
    settings["coppa_last_review"] = old_date
    group.settings = settings
    await test_session.flush()

    report = await assess_coppa_compliance(test_session, group.id)
    review_item = next(i for i in report.checklist if i.id == "annual_review")
    assert review_item.status == "incomplete"


@pytest.mark.asyncio
async def test_annual_review_current(test_session):
    """Recent annual review should be complete."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    recent_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    settings = dict(group.settings or {})
    settings["coppa_last_review"] = recent_date
    group.settings = settings
    await test_session.flush()

    report = await assess_coppa_compliance(test_session, group.id)
    review_item = next(i for i in report.checklist if i.id == "annual_review")
    assert review_item.status == "complete"


@pytest.mark.asyncio
async def test_compliance_status_mapping(test_session):
    """Score should map to correct status."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    # With defaults, should get a status
    report = await assess_coppa_compliance(test_session, group.id)
    assert report.status in ("compliant", "partial", "non_compliant")

    # Score >= 90 = compliant, >= 50 = partial, < 50 = non_compliant
    if report.score >= 90:
        assert report.status == "compliant"
    elif report.score >= 50:
        assert report.status == "partial"
    else:
        assert report.status == "non_compliant"


@pytest.mark.asyncio
async def test_twelve_checklist_items(test_session):
    """Assessment should always return exactly 12 items."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    report = await assess_coppa_compliance(test_session, group.id)
    assert len(report.checklist) == 12


@pytest.mark.asyncio
async def test_multiple_minors_some_consented(test_session):
    """With multiple minors, partial consent should show correct counts."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    minor1 = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child 1",
        date_of_birth=datetime(2018, 1, 1, tzinfo=timezone.utc),
    )
    minor2 = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child 2",
        date_of_birth=datetime(2019, 6, 15, tzinfo=timezone.utc),
    )
    test_session.add_all([minor1, minor2])
    await test_session.flush()

    # Only consent for minor1
    consent = ConsentRecord(
        id=uuid4(),
        group_id=group.id,
        member_id=minor1.id,
        consent_type="coppa_verifiable",
        parent_user_id=owner_id,
        evidence=json.dumps({"method": "signed_form", "verification_status": "verified"}),
    )
    test_session.add(consent)
    await test_session.flush()

    report = await assess_coppa_compliance(test_session, group.id)
    consent_item = next(i for i in report.checklist if i.id == "consent_all_members")
    assert consent_item.status == "incomplete"
    assert "1" in consent_item.evidence  # 1 missing
