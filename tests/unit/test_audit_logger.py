"""Unit tests for audit logger."""

import pytest
from uuid import uuid4
from tests.conftest import make_test_group
from src.compliance.audit_logger import log_audit_event, query_audit_logs


@pytest.mark.asyncio
class TestAuditLogger:
    async def test_log_event(self, test_session):
        entry = await log_audit_event(
            test_session, action="user.login", resource_type="user",
            resource_id="user-123", actor_email="test@example.com",
        )
        assert entry.action == "user.login"

    async def test_query_by_action(self, test_session):
        group, _ = await make_test_group(test_session)
        await log_audit_event(test_session, action="user.login", resource_type="user", group_id=group.id)
        await log_audit_event(test_session, action="user.logout", resource_type="user", group_id=group.id)
        logs, total = await query_audit_logs(test_session, group_id=group.id, action="user.login")
        assert total == 1

    async def test_query_all(self, test_session):
        group, _ = await make_test_group(test_session)
        await log_audit_event(test_session, action="a", resource_type="t", group_id=group.id)
        await log_audit_event(test_session, action="b", resource_type="t", group_id=group.id)
        logs, total = await query_audit_logs(test_session, group_id=group.id)
        assert total == 2
        assert len(logs) == 2
