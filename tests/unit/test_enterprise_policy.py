"""Unit tests for enterprise AI policies."""

import pytest
from uuid import uuid4
from tests.conftest import make_test_group
from src.risk.enterprise_policy import (
    create_policy, list_policies, record_violation, list_violations,
)
from src.exceptions import ValidationError


@pytest.mark.asyncio
class TestEnterprisePolicy:
    async def test_create_policy(self, test_session):
        group, _ = await make_test_group(test_session)
        policy = await create_policy(test_session, group.id, "No PII Sharing", "data_handling")
        assert policy.name == "No PII Sharing"
        assert policy.active is True

    async def test_invalid_policy_type(self, test_session):
        group, _ = await make_test_group(test_session)
        with pytest.raises(ValidationError):
            await create_policy(test_session, group.id, "Test", "invalid_type")

    async def test_list_policies(self, test_session):
        group, _ = await make_test_group(test_session)
        await create_policy(test_session, group.id, "Policy A", "acceptable_use")
        await create_policy(test_session, group.id, "Policy B", "cost_control")
        policies = await list_policies(test_session, group.id)
        assert len(policies) == 2

    async def test_record_violation(self, test_session):
        group, _ = await make_test_group(test_session)
        policy = await create_policy(test_session, group.id, "Test", "acceptable_use")
        violation = await record_violation(test_session, policy.id, group.id, "pii_shared", "PII detected", "high")
        assert violation.severity == "high"

    async def test_list_violations(self, test_session):
        group, _ = await make_test_group(test_session)
        policy = await create_policy(test_session, group.id, "Test", "acceptable_use")
        await record_violation(test_session, policy.id, group.id, "type1", "desc1")
        await record_violation(test_session, policy.id, group.id, "type2", "desc2")
        violations = await list_violations(test_session, group.id)
        assert len(violations) == 2
