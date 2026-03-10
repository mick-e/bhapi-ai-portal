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
