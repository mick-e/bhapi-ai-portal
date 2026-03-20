"""Pydantic v2 schemas for the moderation module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ModerationQueueCreate(BaseModel):
    """Request to submit content for moderation."""

    content_type: str = Field(
        ..., pattern="^(post|comment|message|media)$",
        description="Type of content being moderated",
    )
    content_id: UUID
    age_tier: str | None = Field(
        None, pattern="^(young|preteen|teen)$",
        description="Age tier of the content author",
    )
    content_text: str | None = Field(
        None,
        description="Text content to classify via keyword filter",
        max_length=50000,
    )


class ModerationQueueResponse(BaseModel):
    """Response for a moderation queue entry."""

    id: UUID
    content_type: str
    content_id: UUID
    pipeline: str
    status: str
    risk_scores: dict | None = None
    age_tier: str | None = None
    assigned_to: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModerationDecisionCreate(BaseModel):
    """Request to make a decision on a queue entry."""

    action: str = Field(
        ..., pattern="^(approve|reject|escalate)$",
        description="Moderation action to take",
    )
    reason: str | None = None


class ContentReportCreate(BaseModel):
    """Request to report content."""

    target_type: str = Field(
        ..., pattern="^(post|comment|message|user)$",
        description="Type of content being reported",
    )
    target_id: UUID
    reason: str = Field(..., min_length=1, max_length=2000)


class ContentReportResponse(BaseModel):
    """Response for a content report."""

    id: UUID
    reporter_id: UUID
    target_type: str
    target_id: UUID
    reason: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModerationDashboard(BaseModel):
    """Dashboard statistics for the moderation queue."""

    pending_count: int
    total_processed_today: int
    avg_processing_time_ms: float
    severity_breakdown: dict


class QueueListResponse(BaseModel):
    """Paginated list of moderation queue entries."""

    items: list[ModerationQueueResponse]
    total: int
    page: int
    page_size: int


class ReportListResponse(BaseModel):
    """Paginated list of content reports."""

    items: list[ContentReportResponse]
    total: int
    page: int
    page_size: int


class TakedownRequest(BaseModel):
    """Request to take down content."""

    content_type: str = Field(
        ..., pattern="^(post|comment|message|media)$",
    )
    content_id: UUID
    reason: str = Field(..., min_length=1, max_length=2000)
