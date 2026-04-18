"""Blocking schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema


class BlockRuleCreate(BaseSchema):
    group_id: UUID
    member_id: UUID
    platforms: list[str] | None = None
    reason: str | None = None
    expires_at: datetime | None = None


class BlockRuleResponse(BaseSchema):
    id: UUID
    group_id: UUID
    member_id: UUID
    platforms: list[str] | None
    reason: str | None
    active: bool
    created_by: UUID
    expires_at: datetime | None
    created_at: datetime


class BlockStatus(BaseSchema):
    blocked: bool
    rules: list[BlockRuleResponse] = Field(default_factory=list)


# --- Auto block rule schemas ---


class AutoBlockRuleCreate(BaseSchema):
    group_id: UUID
    name: str = ""
    trigger_type: Literal["risk_event_count", "spend_threshold", "time_of_day"]
    trigger_config: dict | None = None
    action: str = "block_all"
    enabled: bool = True
    threshold: int | None = None
    time_window_minutes: int | None = None
    schedule_start: str | None = None
    schedule_end: str | None = None
    platforms: list[str] | None = None
    member_id: UUID | None = None


class AutoBlockRuleRequest(BaseSchema):
    """Request schema for creating an automated blocking rule."""
    group_id: UUID
    name: str
    trigger_type: str = Field(pattern="^(risk_event_count|spend_threshold|time_of_day)$")
    trigger_config: dict | None = None
    action: str = "block_all"
    enabled: bool = True


class AutoBlockRuleResponse(BaseSchema):
    id: UUID
    group_id: UUID
    name: str
    trigger_type: str
    trigger_config: dict | None = None
    action: str = "block_all"
    enabled: bool = True
    threshold: int | None = None
    time_window_minutes: int | None = None
    schedule_start: str | None = None
    schedule_end: str | None = None
    platforms: list[str] | None = None
    member_id: UUID | None = None
    active: bool = True
    created_by: UUID | None = None
    last_triggered_at: datetime | None = None
    created_at: datetime


class BlockApprovalRequest(BaseSchema):
    """Request to unblock a member."""
    group_id: UUID
    block_rule_id: UUID
    member_id: UUID
    reason: str


class BlockApprovalDecision(BaseSchema):
    """Decision on an unblock request."""
    decision_note: str | None = None


class BlockApprovalResponse(BaseSchema):
    """Response for a block approval."""
    id: UUID
    group_id: UUID
    block_rule_id: UUID
    member_id: UUID
    reason: str
    status: str
    decided_by: UUID | None = None
    decided_at: datetime | None = None
    decision_note: str | None = None
    created_at: datetime


class BlockEffectivenessResponse(BaseSchema):
    """Block effectiveness metrics."""
    total_rules: int
    blocked_count: int
    total_events: int
    block_rate_pct: float


# ─── Time Budget schemas ─────────────────────────────────────────────────────


class TimeBudgetUpdate(BaseSchema):
    """Set/update a time budget for a member."""
    weekday_minutes: int = 60
    weekend_minutes: int = 120
    reset_hour: int = 0
    timezone: str = "UTC"
    enabled: bool = True
    warn_at_percent: int = 75


class TimeBudgetResponse(BaseSchema):
    """Time budget config + today's usage."""
    id: UUID | None = None
    group_id: UUID | None = None
    member_id: UUID | None = None
    weekday_minutes: int = 0
    weekend_minutes: int = 0
    reset_hour: int = 0
    timezone: str = "UTC"
    enabled: bool = False
    warn_at_percent: int = 75
    minutes_used: int = 0
    budget_minutes: int = 0
    remaining: int = 0
    exceeded: bool = False
    warn: bool = False


class TimeBudgetUsageItem(BaseSchema):
    """One day of usage history."""
    date: str
    minutes_used: int
    budget_minutes: int
    exceeded: bool


# ─── Bedtime schemas ─────────────────────────────────────────────────────────


class BedtimeUpdate(BaseSchema):
    """Set bedtime hours for a member."""
    start_hour: int = Field(ge=0, le=23)
    end_hour: int = Field(ge=0, le=23)
    timezone: str = "UTC"


class BedtimeResponse(BaseSchema):
    """Bedtime mode config."""
    enabled: bool = False
    start_hour: int | None = None
    end_hour: int | None = None
    timezone: str = "UTC"
    rule_id: UUID | None = None


class AutoBlockRuleUpdate(BaseSchema):
    name: str | None = None
    trigger_type: Literal["risk_event_count", "spend_threshold", "time_of_day"] | None = None
    trigger_config: dict | None = None
    action: str | None = None
    enabled: bool | None = None
    threshold: int | None = None
    time_window_minutes: int | None = None
    schedule_start: str | None = None
    schedule_end: str | None = None
    platforms: list[str] | None = None
    member_id: UUID | None = None
    active: bool | None = None


# --- Bypass attempt schemas (Phase 4 Task 23) ---


class BypassAttemptCreate(BaseSchema):
    """Reported by extension or device agent when a bypass technique is
    detected client-side. ``member_id`` may be omitted if the user is signed
    in via the extension's parent account — the server resolves the linked
    member from device registration.
    """

    member_id: UUID
    bypass_type: Literal["vpn", "proxy", "alt_url", "incognito", "tampering"]
    detection_signals: dict | None = None


class BypassAttemptResponse(BaseSchema):
    id: UUID
    member_id: UUID
    bypass_type: str
    detection_signals: dict | None
    auto_blocked: bool
    created_at: datetime
