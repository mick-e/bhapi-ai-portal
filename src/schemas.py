"""Shared Pydantic schemas."""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Pagination query parameters. Use via Depends()."""

    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=50, ge=1, le=100, description="Number of items to return")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    total: int
    offset: int
    limit: int
    has_more: bool


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    code: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    environment: str
    database: str
    redis: str


class GroupContext(BaseModel):
    """Group context for authenticated requests."""

    user_id: UUID
    group_id: UUID | None = None
    role: str | None = None
    permissions: list[str] = Field(default_factory=list)
