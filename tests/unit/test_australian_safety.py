"""Unit tests for Australian eSafety Commissioner compliance."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.moderation.esafety import (
    TAKEDOWN_SLA_HOURS,
    ESafetyCategory,
    ESafetyComplaint,
    ESafetyPipeline,
    TakedownStatus,
)


@pytest.fixture
def pipeline():
    """Create a fresh pipeline for each test."""
    p = ESafetyPipeline()
    yield p
    p.reset()


# ---------------------------------------------------------------------------
# ESafetyCategory tests
# ---------------------------------------------------------------------------


class TestESafetyCategory:
    def test_cyberbullying_value(self):
        assert ESafetyCategory.CYBERBULLYING == "cyberbullying"

    def test_image_abuse_value(self):
        assert ESafetyCategory.IMAGE_ABUSE == "image_based_abuse"

    def test_illegal_content_value(self):
        assert ESafetyCategory.ILLEGAL_CONTENT == "illegal_harmful_content"

    def test_online_content_value(self):
        assert ESafetyCategory.ONLINE_CONTENT == "online_content"

    def test_category_from_string(self):
        cat = ESafetyCategory("cyberbullying")
        assert cat == ESafetyCategory.CYBERBULLYING


# ---------------------------------------------------------------------------
# Submit complaint tests
# ---------------------------------------------------------------------------


class TestSubmitComplaint:
    @pytest.mark.asyncio
    async def test_submit_without_api_key(self, pipeline):
        """Without API key, complaint is tracked locally with pending status."""
        result = await pipeline.submit_complaint(
            content_id="content-001",
            category=ESafetyCategory.CYBERBULLYING,
            evidence_description="Bullying messages detected",
        )
        assert result.complaint_id == "local-content-001"
        assert result.status == "pending"
        assert result.category == ESafetyCategory.CYBERBULLYING
        assert result.content_id == "content-001"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_submit_sets_deadline(self, pipeline):
        """Complaint sets 24h takedown deadline."""
        before = datetime.now(timezone.utc)
        result = await pipeline.submit_complaint(
            content_id="content-002",
            category=ESafetyCategory.IMAGE_ABUSE,
            evidence_description="Abusive image shared",
        )
        after = datetime.now(timezone.utc)

        expected_min = before + timedelta(hours=TAKEDOWN_SLA_HOURS)
        expected_max = after + timedelta(hours=TAKEDOWN_SLA_HOURS)
        assert expected_min <= result.takedown_deadline <= expected_max

    @pytest.mark.asyncio
    async def test_submit_tracks_pending_takedown(self, pipeline):
        """Submitting a complaint adds it to pending takedowns."""
        await pipeline.submit_complaint(
            content_id="content-003",
            category=ESafetyCategory.ILLEGAL_CONTENT,
            evidence_description="Illegal content found",
        )
        status = pipeline.get_takedown_status("content-003")
        assert status is not None
        assert status.taken_down is False

    @pytest.mark.asyncio
    async def test_submit_empty_content_id_raises(self, pipeline):
        """Empty content_id raises ValueError."""
        with pytest.raises(ValueError, match="content_id is required"):
            await pipeline.submit_complaint(
                content_id="",
                category=ESafetyCategory.CYBERBULLYING,
                evidence_description="test",
            )

    @pytest.mark.asyncio
    async def test_submit_empty_evidence_raises(self, pipeline):
        """Empty evidence raises ValueError."""
        with pytest.raises(ValueError, match="evidence_description is required"):
            await pipeline.submit_complaint(
                content_id="content-x",
                category=ESafetyCategory.CYBERBULLYING,
                evidence_description="",
            )

    @pytest.mark.asyncio
    async def test_submit_with_api_key_success(self, pipeline):
        """Successful API submission returns submitted status."""
        pipeline.configure(api_key="test-key")

        import httpx as _httpx

        mock_response = _httpx.Response(
            200,
            json={"complaintId": "esafety-12345"},
            request=_httpx.Request("POST", "https://api.esafety.gov.au/v1/complaints"),
        )

        with patch("src.moderation.esafety.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await pipeline.submit_complaint(
                content_id="content-004",
                category=ESafetyCategory.CYBERBULLYING,
                evidence_description="Evidence text",
            )

        assert result.complaint_id == "esafety-12345"
        assert result.status == "submitted"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_submit_with_api_key_failure(self, pipeline):
        """API failure returns failed status with error."""
        pipeline.configure(api_key="test-key")

        with patch("src.moderation.esafety.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_cls.return_value = mock_client

            result = await pipeline.submit_complaint(
                content_id="content-005",
                category=ESafetyCategory.ONLINE_CONTENT,
                evidence_description="Evidence text",
            )

        assert result.status == "failed"
        assert result.error == "Connection refused"
        assert result.complaint_id is None

    @pytest.mark.asyncio
    async def test_submit_with_reporter_info(self, pipeline):
        """Reporter info is accepted without error."""
        result = await pipeline.submit_complaint(
            content_id="content-006",
            category=ESafetyCategory.CYBERBULLYING,
            evidence_description="Evidence",
            reporter_info={"name": "Parent", "email": "parent@example.com"},
        )
        assert result.status == "pending"


# ---------------------------------------------------------------------------
# Takedown marking tests
# ---------------------------------------------------------------------------


class TestMarkTakenDown:
    @pytest.mark.asyncio
    async def test_mark_existing_content(self, pipeline):
        """Mark existing content as taken down."""
        await pipeline.submit_complaint(
            content_id="td-001",
            category=ESafetyCategory.CYBERBULLYING,
            evidence_description="Evidence",
        )
        result = pipeline.mark_taken_down("td-001")
        assert result is True

        status = pipeline.get_takedown_status("td-001")
        assert status.taken_down is True
        assert status.taken_down_at is not None

    @pytest.mark.asyncio
    async def test_mark_nonexistent_content(self, pipeline):
        """Marking nonexistent content returns False."""
        result = pipeline.mark_taken_down("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_mark_already_taken_down(self, pipeline):
        """Re-marking already taken down content returns True."""
        await pipeline.submit_complaint(
            content_id="td-002",
            category=ESafetyCategory.IMAGE_ABUSE,
            evidence_description="Evidence",
        )
        pipeline.mark_taken_down("td-002")
        result = pipeline.mark_taken_down("td-002")
        assert result is True


# ---------------------------------------------------------------------------
# SLA status tests
# ---------------------------------------------------------------------------


class TestTakedownStatus:
    @pytest.mark.asyncio
    async def test_status_not_overdue(self, pipeline):
        """Fresh complaint is not overdue."""
        await pipeline.submit_complaint(
            content_id="sla-001",
            category=ESafetyCategory.CYBERBULLYING,
            evidence_description="Evidence",
        )
        status = pipeline.get_takedown_status("sla-001")
        assert status.is_overdue is False
        assert status.time_remaining_seconds > 0

    @pytest.mark.asyncio
    async def test_status_overdue(self, pipeline):
        """Content past deadline is overdue."""
        await pipeline.submit_complaint(
            content_id="sla-002",
            category=ESafetyCategory.CYBERBULLYING,
            evidence_description="Evidence",
        )
        # Manually set deadline in the past
        pipeline._pending_takedowns["sla-002"]["deadline"] = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        )
        status = pipeline.get_takedown_status("sla-002")
        assert status.is_overdue is True
        assert status.time_remaining_seconds == 0

    @pytest.mark.asyncio
    async def test_status_taken_down_not_overdue(self, pipeline):
        """Taken-down content is not overdue even if past deadline."""
        await pipeline.submit_complaint(
            content_id="sla-003",
            category=ESafetyCategory.CYBERBULLYING,
            evidence_description="Evidence",
        )
        pipeline._pending_takedowns["sla-003"]["deadline"] = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        )
        pipeline.mark_taken_down("sla-003")
        status = pipeline.get_takedown_status("sla-003")
        assert status.is_overdue is False

    def test_status_nonexistent(self, pipeline):
        """Querying nonexistent content returns None."""
        assert pipeline.get_takedown_status("nope") is None


# ---------------------------------------------------------------------------
# Overdue and dashboard tests
# ---------------------------------------------------------------------------


class TestOverdueAndDashboard:
    @pytest.mark.asyncio
    async def test_get_overdue_empty(self, pipeline):
        """No overdue takedowns when none exist."""
        assert pipeline.get_overdue_takedowns() == []

    @pytest.mark.asyncio
    async def test_get_overdue_returns_breached(self, pipeline):
        """Overdue list includes SLA-breached items."""
        await pipeline.submit_complaint(
            content_id="od-001",
            category=ESafetyCategory.CYBERBULLYING,
            evidence_description="Evidence",
        )
        pipeline._pending_takedowns["od-001"]["deadline"] = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        )
        overdue = pipeline.get_overdue_takedowns()
        assert len(overdue) == 1
        assert overdue[0].content_id == "od-001"

    @pytest.mark.asyncio
    async def test_dashboard_empty(self, pipeline):
        """Dashboard with no complaints."""
        dash = pipeline.get_sla_dashboard()
        assert dash["total_complaints"] == 0
        assert dash["sla_compliance_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_dashboard_with_data(self, pipeline):
        """Dashboard reflects complaint counts."""
        await pipeline.submit_complaint(
            content_id="d-001",
            category=ESafetyCategory.CYBERBULLYING,
            evidence_description="Evidence 1",
        )
        await pipeline.submit_complaint(
            content_id="d-002",
            category=ESafetyCategory.IMAGE_ABUSE,
            evidence_description="Evidence 2",
        )
        pipeline.mark_taken_down("d-001")

        dash = pipeline.get_sla_dashboard()
        assert dash["total_complaints"] == 2
        assert dash["taken_down"] == 1
        assert dash["pending"] == 1
        assert dash["overdue"] == 0
        assert dash["sla_compliance_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_dashboard_with_overdue(self, pipeline):
        """Dashboard counts overdue items correctly."""
        await pipeline.submit_complaint(
            content_id="d-003",
            category=ESafetyCategory.CYBERBULLYING,
            evidence_description="Evidence",
        )
        pipeline._pending_takedowns["d-003"]["deadline"] = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        )
        dash = pipeline.get_sla_dashboard()
        assert dash["overdue"] == 1
        assert dash["pending"] == 0


# ---------------------------------------------------------------------------
# Configure and reset tests
# ---------------------------------------------------------------------------


class TestConfigureAndReset:
    def test_configure_api_key(self, pipeline):
        pipeline.configure(api_key="my-key")
        assert pipeline._api_key == "my-key"

    def test_configure_custom_url(self, pipeline):
        pipeline.configure(api_url="https://custom.api/v2")
        assert pipeline._api_url == "https://custom.api/v2"

    def test_reset_clears_state(self, pipeline):
        pipeline.configure(api_key="key")
        pipeline._pending_takedowns["x"] = {"test": True}
        pipeline.reset()
        assert pipeline._api_key is None
        assert len(pipeline._pending_takedowns) == 0

    @pytest.mark.asyncio
    async def test_get_all_takedowns(self, pipeline):
        """get_all_takedowns returns all tracked items."""
        await pipeline.submit_complaint(
            content_id="all-1",
            category=ESafetyCategory.CYBERBULLYING,
            evidence_description="Evidence 1",
        )
        await pipeline.submit_complaint(
            content_id="all-2",
            category=ESafetyCategory.IMAGE_ABUSE,
            evidence_description="Evidence 2",
        )
        all_statuses = pipeline.get_all_takedowns()
        assert len(all_statuses) == 2
        ids = {s.content_id for s in all_statuses}
        assert ids == {"all-1", "all-2"}
