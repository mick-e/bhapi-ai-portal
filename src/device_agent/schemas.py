"""Pydantic v2 schemas for the device agent module."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Device Sessions
# ---------------------------------------------------------------------------


class DeviceSessionCreate(BaseModel):
    """Schema for recording a device session."""

    member_id: UUID
    device_id: str = Field(..., min_length=1, max_length=255)
    device_type: str = Field(..., pattern=r"^(ios|android|tablet)$")
    os_version: str | None = Field(default=None, max_length=50)
    app_version: str | None = Field(default=None, max_length=50)
    started_at: datetime
    ended_at: datetime | None = None
    battery_level: float | None = Field(default=None, ge=0.0, le=100.0)


class DeviceSessionResponse(BaseModel):
    """Schema for device session responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    group_id: UUID
    device_id: str
    device_type: str
    os_version: str | None = None
    app_version: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    battery_level: float | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# App Usage
# ---------------------------------------------------------------------------


class AppUsageCreate(BaseModel):
    """Schema for recording app usage."""

    member_id: UUID
    session_id: UUID | None = None
    app_name: str = Field(..., min_length=1, max_length=255)
    bundle_id: str = Field(..., min_length=1, max_length=500)
    category: str = Field(
        default="other",
        pattern=r"^(social|education|games|entertainment|productivity|other)$",
    )
    started_at: datetime
    ended_at: datetime | None = None
    foreground_minutes: float = Field(..., ge=0.0)


class AppUsageResponse(BaseModel):
    """Schema for app usage responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    group_id: UUID
    session_id: UUID | None = None
    app_name: str
    bundle_id: str
    category: str
    started_at: datetime
    ended_at: datetime | None = None
    foreground_minutes: float
    created_at: datetime


class AppUsageListResponse(BaseModel):
    """Paginated list of app usage records."""

    items: list[AppUsageResponse]
    total: int
    offset: int
    limit: int
    has_more: bool


# ---------------------------------------------------------------------------
# Screen Time
# ---------------------------------------------------------------------------


class ScreenTimeSummary(BaseModel):
    """Screen time summary for a date."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    date: date
    total_minutes: float
    app_breakdown: dict | None = None
    category_breakdown: dict | None = None
    pickups: int
    created_at: datetime


class ScreenTimeListResponse(BaseModel):
    """Screen time summaries for a date range."""

    items: list[ScreenTimeSummary]
    total: int


# ---------------------------------------------------------------------------
# Batch Sync
# ---------------------------------------------------------------------------


class DeviceSyncRequest(BaseModel):
    """Batch sync request from device agent."""

    member_id: UUID
    device_id: str = Field(..., min_length=1, max_length=255)
    device_type: str = Field(..., pattern=r"^(ios|android|tablet)$")
    sessions: list[DeviceSessionCreate] = Field(default_factory=list)
    usage_records: list[AppUsageCreate] = Field(default_factory=list)


class DeviceSyncResponse(BaseModel):
    """Batch sync response."""

    sessions_created: int
    usage_records_created: int
    screen_time_updated: bool
