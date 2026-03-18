"""Unit tests for alert correlation."""

import pytest
from uuid import uuid4
from tests.conftest import make_test_group
from src.alerts.correlation import (
    create_correlation, list_correlations, analyze_member_correlations,
)


@pytest.mark.asyncio
class TestCorrelation:
    async def test_create_correlation(self, test_session):
        group, _ = await make_test_group(test_session)
        c = await create_correlation(
            test_session, group_id=group.id, correlation_type="behavior_pattern",
            title="Increased risk + high spend", confidence_score=0.85,
        )
        assert c.correlation_type == "behavior_pattern"
        assert c.confidence_score == 0.85

    async def test_list_correlations(self, test_session):
        group, _ = await make_test_group(test_session)
        await create_correlation(test_session, group.id, "type1", "Title 1")
        await create_correlation(test_session, group.id, "type2", "Title 2")
        corrs = await list_correlations(test_session, group.id)
        assert len(corrs) == 2

    async def test_analyze_member(self, test_session):
        group, _ = await make_test_group(test_session)
        member_id = uuid4()
        result = await analyze_member_correlations(test_session, group.id, member_id)
        assert result["member_id"] == str(member_id)
        assert "risk_events" in result
        assert "alerts" in result
