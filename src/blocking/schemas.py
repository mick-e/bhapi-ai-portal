"""Blocking schemas."""

from datetime import datetime
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
