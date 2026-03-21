"""Alerts Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema


class AlertCreate(BaseSchema):
    """Create alert request."""

    group_id: UUID
    member_id: UUID | None = None
    risk_event_id: UUID | None = None
    source: str = Field(default="ai", pattern="^(ai|social|device)$")
    severity: str = Field(pattern="^(critical|high|medium|low|info)$")
    title: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=2000)
    channel: str = Field(default="portal", pattern="^(portal|email)$")


class AlertResponse(BaseSchema):
    """Alert response."""

    id: UUID
    group_id: UUID
    member_id: UUID | None
    risk_event_id: UUID | None
    source: str = "ai"
    severity: str
    title: str
    body: str
    channel: str
    status: str
    acknowledged_at: datetime | None
    acknowledged_by: UUID | None
    re_notify_at: datetime | None
    created_at: datetime


class PreferenceConfig(BaseSchema):
    """Individual preference configuration."""

    category: str = Field(min_length=1, max_length=50)
    channel: str = Field(default="portal", pattern="^(portal|email)$")
    digest_mode: str = Field(default="immediate", pattern="^(immediate|hourly|daily)$")
    enabled: bool = True


class PreferenceUpdate(BaseSchema):
    """Update notification preferences request."""

    group_id: UUID
    preferences: list[PreferenceConfig]


class PreferenceResponse(BaseSchema):
    """Notification preference response."""

    id: UUID
    group_id: UUID
    user_id: UUID
    category: str
    channel: str
    digest_mode: str
    enabled: bool
    created_at: datetime


class AlertUpdateRequest(BaseSchema):
    """Update alert read/actioned status."""

    read: bool | None = None
    actioned: bool | None = None


class DigestSummary(BaseSchema):
    """Digest summary for batched notifications."""

    group_id: UUID
    period_start: datetime
    period_end: datetime
    total_alerts: int
    by_severity: dict[str, int] = Field(default_factory=dict)
    alerts: list[AlertResponse] = Field(default_factory=list)
