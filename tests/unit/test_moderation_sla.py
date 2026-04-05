"""Unit tests for moderation SLA metrics service."""

import pytest

from src.moderation.sla_schemas import SLAMetrics
from src.moderation.sla_service import get_sla_metrics


class TestSLAMetrics:
    @pytest.mark.asyncio
    async def test_sla_metrics_returns_expected_shape(self, test_session):
        metrics = await get_sla_metrics(test_session)
        assert isinstance(metrics, SLAMetrics)
        assert hasattr(metrics, "pre_publish_p50_ms")
        assert hasattr(metrics, "pre_publish_p95_ms")
        assert hasattr(metrics, "post_publish_p50_ms")
        assert hasattr(metrics, "post_publish_p95_ms")
        assert hasattr(metrics, "queue_depth")
        assert hasattr(metrics, "oldest_pending_age_seconds")
        assert hasattr(metrics, "sla_breach_count_24h")
        assert hasattr(metrics, "total_reviewed_24h")

    @pytest.mark.asyncio
    async def test_sla_metrics_empty_queue(self, test_session):
        metrics = await get_sla_metrics(test_session)
        assert metrics.queue_depth == 0
        assert metrics.oldest_pending_age_seconds == 0
        assert metrics.pre_publish_p50_ms == 0.0
        assert metrics.pre_publish_p95_ms == 0.0
        assert metrics.post_publish_p50_ms == 0.0
        assert metrics.post_publish_p95_ms == 0.0
        assert metrics.sla_breach_count_24h == 0
        assert metrics.total_reviewed_24h == 0

    @pytest.mark.asyncio
    async def test_sla_metrics_all_fields_are_numeric(self, test_session):
        metrics = await get_sla_metrics(test_session)
        assert isinstance(metrics.pre_publish_p50_ms, float)
        assert isinstance(metrics.pre_publish_p95_ms, float)
        assert isinstance(metrics.post_publish_p50_ms, float)
        assert isinstance(metrics.post_publish_p95_ms, float)
        assert isinstance(metrics.queue_depth, int)
        assert isinstance(metrics.oldest_pending_age_seconds, int)
        assert isinstance(metrics.sla_breach_count_24h, int)
        assert isinstance(metrics.total_reviewed_24h, int)

    @pytest.mark.asyncio
    async def test_sla_metrics_non_negative(self, test_session):
        metrics = await get_sla_metrics(test_session)
        assert metrics.pre_publish_p50_ms >= 0.0
        assert metrics.pre_publish_p95_ms >= 0.0
        assert metrics.post_publish_p50_ms >= 0.0
        assert metrics.post_publish_p95_ms >= 0.0
        assert metrics.queue_depth >= 0
        assert metrics.oldest_pending_age_seconds >= 0
        assert metrics.sla_breach_count_24h >= 0
        assert metrics.total_reviewed_24h >= 0
