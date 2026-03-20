"""Unit tests for SOC 2 evidence collection."""

import pytest

from src.compliance.soc2_evidence import get_soc2_evidence_summary


@pytest.mark.asyncio
class TestSOC2Evidence:
    async def test_evidence_summary_structure(self, test_session):
        summary = await get_soc2_evidence_summary(test_session)
        assert "controls" in summary
        assert "summary" in summary
        assert summary["summary"]["total_controls"] == 8

    async def test_all_controls_have_required_fields(self, test_session):
        summary = await get_soc2_evidence_summary(test_session)
        for control in summary["controls"]:
            assert "id" in control
            assert "name" in control
            assert "status" in control
            assert "evidence" in control
