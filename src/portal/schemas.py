"""Portal BFF Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema


class ActivityFeedItem(BaseSchema):
    """Single activity feed item for dashboard — matches frontend CaptureEvent."""

    id: UUID
    group_id: UUID
    member_id: UUID
    member_name: str
    provider: str
    model: str = ""
    event_type: str  # chat, code, image, document
    prompt_preview: str = ""
    response_preview: str = ""
    token_count: int = 0
    cost_usd: float = 0.0
    risk_level: str = "low"  # low, medium, high, critical
    flagged: bool = False
    timestamp: str


class DashboardAlertItem(BaseSchema):
    """Single alert item for dashboard — matches frontend Alert."""

    id: UUID
    group_id: UUID
    type: str = "risk"  # risk, spend, member, system
    severity: str = "info"  # info, warning, error, critical
    title: str
    message: str
    member_name: str | None = None
    read: bool = False
    actioned: bool = False
    related_member_id: UUID | None = None
    related_event_id: UUID | None = None
    created_at: str


class AlertSummary(BaseSchema):
    """Alert summary for dashboard — matches frontend DashboardData.alert_summary."""

    unread_count: int = 0
    critical_count: int = 0
    recent: list[DashboardAlertItem] = Field(default_factory=list)


class SpendSummary(BaseSchema):
    """Spend summary for dashboard — matches frontend DashboardData.spend_summary."""

    today_usd: float = 0.0
    month_usd: float = 0.0
    budget_usd: float = 0.0
    budget_used_percentage: float = 0.0
    top_provider: str = ""
    top_provider_cost_usd: float = 0.0
    top_provider_percentage: float = 0.0
    top_member: str = ""
    top_member_cost_usd: float = 0.0
    top_member_percentage: float = 0.0


class RiskSummary(BaseSchema):
    """Risk summary for dashboard — matches frontend DashboardData.risk_summary."""

    total_events_today: int = 0
    high_severity_count: int = 0
    trend: str = "stable"  # increasing, stable, decreasing


class MemberStatus(BaseSchema):
    """Member status for dashboard (internal use, not in frontend DashboardData)."""

    id: UUID
    display_name: str
    role: str
    last_active: datetime | None = None
    active_platforms: list[str] = Field(default_factory=list)
    unresolved_alerts: int = 0


class TrendDataPoint(BaseSchema):
    """Single data point for trend charts."""
    date: str
    count: int = 0
    amount: float = 0.0


class CategoryCount(BaseSchema):
    """Risk category breakdown item."""
    category: str
    count: int


class DashboardResponse(BaseSchema):
    """Primary dashboard response (FR-010) — matches frontend DashboardData."""

    active_members: int = 0
    total_members: int = 0
    interactions_today: int = 0
    interactions_trend: str = "tracking"
    recent_activity: list[ActivityFeedItem] = Field(default_factory=list)
    alert_summary: AlertSummary = Field(default_factory=AlertSummary)
    spend_summary: SpendSummary = Field(default_factory=SpendSummary)
    risk_summary: RiskSummary = Field(default_factory=RiskSummary)
    activity_trend: list[TrendDataPoint] = Field(default_factory=list)
    risk_breakdown: list[CategoryCount] = Field(default_factory=list)
    spend_trend: list[TrendDataPoint] = Field(default_factory=list)


# ─── Settings ───────────────────────────────────────────────────────────────

class NotificationPreferences(BaseSchema):
    """Notification preferences — matches frontend NotificationPreferences."""

    critical_safety: bool = True
    risk_warnings: bool = True
    spend_alerts: bool = True
    member_updates: bool = True
    weekly_digest: bool = True
    report_notifications: bool = True


class GroupSettingsResponse(BaseSchema):
    """Group settings response — matches frontend GroupSettings."""

    group_id: UUID
    group_name: str
    account_type: str
    safety_level: str = "strict"
    auto_block_critical: bool = True
    prompt_logging: bool = True
    pii_detection: bool = True
    notifications: NotificationPreferences = Field(default_factory=NotificationPreferences)
    monthly_budget_usd: float = 0.0
    plan: str = "free"


class UpdateGroupSettingsRequest(BaseSchema):
    """Update group settings request — matches frontend UpdateGroupSettingsRequest."""

    group_name: str | None = None
    safety_level: str | None = None
    auto_block_critical: bool | None = None
    prompt_logging: bool | None = None
    pii_detection: bool | None = None
    notifications: dict | None = None
    monthly_budget_usd: float | None = None
