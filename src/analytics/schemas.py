"""Analytics schemas."""

from datetime import datetime
from uuid import UUID

from src.schemas import BaseSchema


class TrendPoint(BaseSchema):
    date: str
    value: float


class TrendResponse(BaseSchema):
    group_id: UUID
    metric: str
    direction: str  # increasing, decreasing, stable
    data_points: list[TrendPoint]


class UsagePatternResponse(BaseSchema):
    group_id: UUID
    by_hour: dict[str, int]
    by_day_of_week: dict[str, int]
    by_platform: dict[str, int]


class MemberBaselineResponse(BaseSchema):
    member_id: UUID
    avg_daily_events: float
    avg_risk_score: float
    primary_platform: str
    trend_direction: str


class AnomalyItem(BaseSchema):
    member_id: str
    member_name: str
    recent_daily_avg: float
    baseline_daily_avg: float
    standard_deviations: float
    direction: str  # "above" or "below"
    severity: str  # "warning" or "critical"


class AnomalyResponse(BaseSchema):
    group_id: str
    threshold_sd: float
    anomalies: list[AnomalyItem]


class PeerComparisonItem(BaseSchema):
    member_id: str
    member_name: str
    event_count: int
    percentile: float
    usage_level: str  # "low", "moderate", "high", "very_high"


class PeerComparisonResponse(BaseSchema):
    group_id: str
    period_days: int
    members: list[PeerComparisonItem]
