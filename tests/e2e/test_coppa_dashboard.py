"""E2E tests for COPPA 2026 Compliance Dashboard."""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.compliance.coppa_dashboard import (
    assess_coppa_compliance,
    export_coppa_evidence,
    mark_annual_review,
)
from src.compliance.models import ConsentRecord
from src.exceptions import NotFoundError
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_assess_coppa_compliance_no_minors(test_session):
    """Assessment with no minors should have high score."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    member = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Adult User",
    )
    test_session.add(member)
    await test_session.flush()

    report = await assess_coppa_compliance(test_session, group.id)
    assert report.score > 0
    assert report.group_name == "Family"
    assert report.group_id == str(group.id)
    assert len(report.checklist) == 12


@pytest.mark.asyncio
async def test_assess_coppa_compliance_with_consented_minor(test_session):
    """Minor with verified consent should improve score."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    minor = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
        date_of_birth=datetime(2018, 6, 15, tzinfo=timezone.utc),
    )
    test_session.add(minor)
    await test_session.flush()

    # Add verified consent
    consent = ConsentRecord(
        id=uuid4(),
        group_id=group.id,
        member_id=minor.id,
        consent_type="coppa_verifiable",
        parent_user_id=owner_id,
        evidence=json.dumps({
            "method": "signed_form",
            "verification_status": "verified",
        }),
    )
    test_session.add(consent)
    await test_session.flush()

    report = await assess_coppa_compliance(test_session, group.id)
    # Consent items should be complete
    consent_item = next(i for i in report.checklist if i.id == "consent_all_members")
    assert consent_item.status == "complete"

    ftc_item = next(i for i in report.checklist if i.id == "ftc_approved_method")
    assert ftc_item.status == "complete"


@pytest.mark.asyncio
async def test_assess_coppa_compliance_missing_consent(test_session):
    """Minor without consent should lower score."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    minor = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
        date_of_birth=datetime(2018, 6, 15, tzinfo=timezone.utc),
    )
    test_session.add(minor)
    await test_session.flush()

    report = await assess_coppa_compliance(test_session, group.id)
    consent_item = next(i for i in report.checklist if i.id == "consent_all_members")
    assert consent_item.status == "incomplete"


@pytest.mark.asyncio
async def test_assess_coppa_compliance_group_not_found(test_session):
    """Non-existent group should raise NotFoundError."""
    with pytest.raises(NotFoundError):
        await assess_coppa_compliance(test_session, uuid4())


@pytest.mark.asyncio
async def test_export_coppa_evidence_pdf(test_session):
    """Export should generate valid PDF bytes."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    pdf_bytes = await export_coppa_evidence(test_session, group.id)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    # PDF magic bytes
    assert pdf_bytes[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_mark_annual_review(test_session):
    """Marking annual review should update group settings."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    result = await mark_annual_review(test_session, group.id)
    assert result["status"] == "complete"
    assert result["group_id"] == str(group.id)
    assert "reviewed_at" in result

    # Verify it affects compliance score
    report = await assess_coppa_compliance(test_session, group.id)
    review_item = next(i for i in report.checklist if i.id == "annual_review")
    assert review_item.status == "complete"


@pytest.mark.asyncio
async def test_mark_annual_review_not_found(test_session):
    """Non-existent group should raise NotFoundError."""
    with pytest.raises(NotFoundError):
        await mark_annual_review(test_session, uuid4())


@pytest.mark.asyncio
async def test_coppa_checklist_endpoint_requires_auth(client):
    """COPPA checklist endpoint should require authentication."""
    resp = await client.get(f"/api/v1/compliance/coppa/checklist?group_id={uuid4()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_coppa_export_endpoint_requires_auth(client):
    """COPPA export endpoint should require authentication."""
    resp = await client.get(f"/api/v1/compliance/coppa/export?group_id={uuid4()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_coppa_review_endpoint_requires_auth(client):
    """COPPA review endpoint should require authentication."""
    resp = await client.post(f"/api/v1/compliance/coppa/review?group_id={uuid4()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_biometric_handling_not_applicable(test_session):
    """Biometric handling should be not_applicable since we don't collect it."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    report = await assess_coppa_compliance(test_session, group.id)
    bio_item = next(i for i in report.checklist if i.id == "biometric_handling")
    assert bio_item.status == "not_applicable"


@pytest.mark.asyncio
async def test_platform_defaults_are_complete(test_session):
    """Platform-provided capabilities should always be complete."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    report = await assess_coppa_compliance(test_session, group.id)

    always_complete_ids = {
        "content_encryption",
        "data_retention_policy",
        "deletion_requests_72h",
        "privacy_policy_accessible",
        "no_marketing_to_children",
    }
    for item in report.checklist:
        if item.id in always_complete_ids:
            assert item.status == "complete", f"{item.id} should be complete"
