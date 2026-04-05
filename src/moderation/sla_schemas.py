"""SLA metrics schemas for moderation pipeline performance dashboard."""

from pydantic import BaseModel


class SLAMetrics(BaseModel):
    """Live SLA metrics for the moderation pipeline."""

    pre_publish_p50_ms: float = 0.0
    pre_publish_p95_ms: float = 0.0
    post_publish_p50_ms: float = 0.0
    post_publish_p95_ms: float = 0.0
    queue_depth: int = 0
    oldest_pending_age_seconds: int = 0
    sla_breach_count_24h: int = 0
    total_reviewed_24h: int = 0
