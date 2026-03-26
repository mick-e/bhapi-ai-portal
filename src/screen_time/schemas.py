"""Pydantic v2 schemas for the screen time module."""

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Screen Time Rules
# ---------------------------------------------------------------------------


class ScreenTimeRuleCreate(BaseModel):
    """Schema for creating a screen time rule."""

    group_id: UUID | None = None
    member_id: UUID
    app_category: str = Field(
        default="all",
        pattern=r"^(social|games|education|entertainment|productivity|all)$",
    )
    daily_limit_minutes: int = Field(..., gt=0, le=1440)
    age_tier_enforcement: str = Field(
        default="warning_then_block",
        pattern=r"^(hard_block|warning_then_block|warning_only)$",
    )
    enabled: bool = True


class ScreenTimeRuleResponse(BaseModel):
    """Schema for screen time rule responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    member_id: UUID
    app_category: str
    daily_limit_minutes: int
    age_tier_enforcement: str
    enabled: bool
    created_at: datetime


class ScreenTimeRuleListResponse(BaseModel):
    """Paginated list of screen time rules."""

    items: list[ScreenTimeRuleResponse]
    total: int


# ---------------------------------------------------------------------------
# Screen Time Schedules
# ---------------------------------------------------------------------------


class ScreenTimeScheduleCreate(BaseModel):
    """Schema for creating a screen time schedule."""

    rule_id: UUID
    day_type: str = Field(
        default="weekday",
        pattern=r"^(weekday|weekend|custom)$",
    )
    blocked_start: time
    blocked_end: time
    description: str | None = Field(default=None, max_length=200)


class ScreenTimeScheduleResponse(BaseModel):
    """Schema for screen time schedule responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: UUID
    day_type: str
    blocked_start: time
    blocked_end: time
    description: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Extension Requests
# ---------------------------------------------------------------------------


class ExtensionRequestCreate(BaseModel):
    """Schema for creating an extension request."""

    member_id: UUID
    rule_id: UUID
    requested_minutes: int = Field(..., gt=0, le=120)


class ExtensionRequestResponse(BaseModel):
    """Schema for extension request responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    rule_id: UUID
    requested_minutes: int
    status: str
    requested_at: datetime
    responded_at: datetime | None = None
    responded_by: UUID | None = None
    created_at: datetime


class ExtensionRequestListResponse(BaseModel):
    """Paginated list of extension requests."""

    items: list[ExtensionRequestResponse]
    total: int
    has_more: bool
