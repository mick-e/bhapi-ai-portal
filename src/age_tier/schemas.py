"""Age tier Pydantic schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgeTierConfigCreate(BaseModel):
    """Request schema for assigning/updating a member's age tier."""

    member_id: UUID
    date_of_birth: datetime
    jurisdiction: str = Field(default="US", min_length=2, max_length=2)
    feature_overrides: dict[str, Any] | None = None
    locked_features: list[str] | None = None


class AgeTierConfigResponse(BaseModel):
    """Response schema for age tier configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    tier: str
    date_of_birth: datetime
    jurisdiction: str
    feature_overrides: dict[str, Any] | None = None
    locked_features: list[str] | None = None
    permissions: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PermissionCheckResponse(BaseModel):
    """Response for a single permission check."""

    member_id: UUID
    permission: str
    allowed: bool
    tier: str
