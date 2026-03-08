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
