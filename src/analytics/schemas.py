"""Analytics schemas."""

from datetime import date
from uuid import UUID

from pydantic import Field

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


# ---------------------------------------------------------------------------
# Academic Integrity
# ---------------------------------------------------------------------------


class DailyBreakdownItem(BaseSchema):
    date: str
    learning: int
    doing: int
    unclassified: int


class AcademicReportResponse(BaseSchema):
    """Academic integrity report for a member."""

    member_id: UUID
    period_start: date
    period_end: date
    total_ai_sessions: int
    study_hour_sessions: int
    learning_count: int
    doing_count: int
    unclassified_count: int
    learning_ratio: float = Field(ge=0.0, le=1.0)
    top_subjects: list[str]
    daily_breakdown: list[DailyBreakdownItem]
    recommendation: str


class IntentClassificationResponse(BaseSchema):
    """Result of classifying a single prompt."""

    text: str
    intent: str = Field(pattern="^(learning|doing|unclassified)$")


class StudyHoursConfig(BaseSchema):
    """Study hours configuration."""

    weekday_start: str = Field(default="15:00", pattern=r"^\d{2}:\d{2}$")
    weekday_end: str = Field(default="21:00", pattern=r"^\d{2}:\d{2}$")
    weekend_start: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    weekend_end: str = Field(default="21:00", pattern=r"^\d{2}:\d{2}$")
