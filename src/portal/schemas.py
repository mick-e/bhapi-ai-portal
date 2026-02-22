"""Portal BFF Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema


class ActivityFeedItem(BaseSchema):
    """Single activity feed item."""

    id: UUID
    member_name: str
    platform: str
    event_type: str  # prompt, response, session_start, session_end
    timestamp: datetime
    risk_level: str | None = None  # critical, high, medium, low, none


class SpendSummary(BaseSchema):
    """Spend summary for dashboard."""

    total_current_period: float = 0.0
    total_prior_period: float = 0.0
    currency: str = "USD"
    by_platform: dict[str, float] = Field(default_factory=dict)
    by_member: dict[str, float] = Field(default_factory=dict)


class AlertSummary(BaseSchema):
    """Alert summary for dashboard."""

    total_unresolved: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class MemberStatus(BaseSchema):
    """Member status for dashboard."""

    id: UUID
    display_name: str
    role: str
    last_active: datetime | None = None
    active_platforms: list[str] = Field(default_factory=list)
    unresolved_alerts: int = 0


class DashboardResponse(BaseSchema):
    """Primary dashboard response (FR-010)."""

    group_id: UUID
    group_name: str
    active_members: int = 0
    total_members: int = 0
    recent_activity: list[ActivityFeedItem] = Field(default_factory=list)
    alert_summary: AlertSummary = Field(default_factory=AlertSummary)
    spend_summary: SpendSummary = Field(default_factory=SpendSummary)
    members: list[MemberStatus] = Field(default_factory=list)
