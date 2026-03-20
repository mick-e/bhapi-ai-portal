"""Unit tests for crisis escalation."""

from uuid import uuid4

import pytest

from src.alerts.escalation import (
    create_escalation_partner,
    escalate_alert,
    list_escalation_partners,
)
from src.exceptions import NotFoundError, ValidationError
from tests.conftest import make_test_group


@pytest.mark.asyncio
class TestEscalation:
    async def test_create_partner(self, test_session):
        group, _ = await make_test_group(test_session)
        partner = await create_escalation_partner(
            test_session, group_id=group.id, name="Crisis Line",
            provider_type="crisis_text_line", contact_phone="+1234567890",
        )
        assert partner.name == "Crisis Line"
        assert partner.active is True

    async def test_invalid_provider_type(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ValidationError):
            await create_escalation_partner(test_session, group_id=group.id, name="Test", provider_type="invalid")

    async def test_list_partners(self, test_session):
        group, _ = await make_test_group(test_session)
        await create_escalation_partner(test_session, group_id=group.id, name="A", provider_type="school_counselor")
        await create_escalation_partner(test_session, group_id=group.id, name="B", provider_type="custom_webhook")
        partners = await list_escalation_partners(test_session, group.id)
        assert len(partners) == 2

    async def test_escalate_alert(self, test_session):
        group, _ = await make_test_group(test_session)
        partner = await create_escalation_partner(
            test_session, group_id=group.id, name="Crisis",
            provider_type="crisis_text_line",
        )
        record = await escalate_alert(
            test_session, partner_id=partner.id, alert_id=uuid4(),
            group_id=group.id, severity="critical",
        )
        assert record.status == "sent"

    async def test_escalate_nonexistent_partner(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(NotFoundError):
            await escalate_alert(
                test_session, partner_id=uuid4(), alert_id=uuid4(),
                group_id=group.id, severity="critical",
            )
