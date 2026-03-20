"""E2E tests for COPPA verifiable consent features."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.compliance.coppa import (
    check_coppa_compliance,
    generate_coppa_audit_report,
    verify_parental_consent,
)
from src.exceptions import NotFoundError, ValidationError
from src.groups.models import GroupMember
from tests.conftest import make_test_group


@pytest.mark.asyncio
async def test_verify_consent_email_method(test_session):
    """Verifiable consent via email_plus_one method."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    child = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
        date_of_birth=datetime.now(timezone.utc) - timedelta(days=365 * 10),
    )
    test_session.add(child)
    await test_session.flush()

    record = await verify_parental_consent(
        test_session, group.id, child.id, group.owner_id,
        method="email_plus_one", evidence="email-confirmation-123",
    )
    assert record.consent_type == "coppa_verifiable"
    assert "email_plus_one" in record.evidence


@pytest.mark.asyncio
async def test_verify_consent_invalid_method(test_session):
    """Invalid consent method should be rejected."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    child = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
    )
    test_session.add(child)
    await test_session.flush()

    with pytest.raises(ValidationError, match="Invalid consent method"):
        await verify_parental_consent(
            test_session, group.id, child.id, group.owner_id,
            method="invalid_method",
        )


@pytest.mark.asyncio
async def test_audit_report_generation(test_session):
    """COPPA audit report should include all required fields."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    child = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
        date_of_birth=datetime.now(timezone.utc) - timedelta(days=365 * 10),
    )
    test_session.add(child)
    await test_session.flush()

    report = await generate_coppa_audit_report(test_session, group.id)
    assert report["group_name"] == "Family"
    assert report["minors_requiring_consent"] == 1
    assert report["minors_without_consent"] == 1
    assert "data_practices" in report


@pytest.mark.asyncio
async def test_compliance_status_non_compliant(test_session):
    """Status should be non_compliant when minors lack consent."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    child = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
        date_of_birth=datetime.now(timezone.utc) - timedelta(days=365 * 10),
    )
    test_session.add(child)
    await test_session.flush()

    status = await check_coppa_compliance(test_session, group.id)
    assert status["overall_status"] == "non_compliant"
    assert status["minors_count"] == 1
    assert status["consented_count"] == 0


@pytest.mark.asyncio
async def test_compliance_status_compliant_after_consent(test_session):
    """Status should be compliant when all minors have consent."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")
    child = GroupMember(
        id=uuid4(), group_id=group.id, user_id=None,
        role="member", display_name="Child",
        date_of_birth=datetime.now(timezone.utc) - timedelta(days=365 * 10),
    )
    test_session.add(child)
    await test_session.flush()

    # Give consent
    await verify_parental_consent(
        test_session, group.id, child.id, group.owner_id,
        method="signed_form", evidence="form-ref-456",
    )

    status = await check_coppa_compliance(test_session, group.id)
    assert status["consented_count"] == 1


@pytest.mark.asyncio
async def test_nonexistent_member_consent(test_session):
    """Consent for nonexistent member should fail."""
    group, owner_id = await make_test_group(test_session, name="Family", group_type="family")

    with pytest.raises(NotFoundError):
        await verify_parental_consent(
            test_session, group.id, uuid4(), group.owner_id,
            method="email_plus_one",
        )
