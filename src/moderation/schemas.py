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
    reason: str = Field(
        ...,
        pattern="^(inappropriate|bullying|spam|impersonation|self_harm|adult_content|other)$",
        description="Report reason from the taxonomy",
    )
    description: str | None = Field(
        None, max_length=2000,
        description="Optional description providing additional context",
    )


class ContentReportStatusUpdate(BaseModel):
    """Request to update a report's status."""

    status: str = Field(
        ...,
        pattern="^(under_review|action_taken|dismissed)$",
        description="New status for the report",
    )


class ContentReportResponse(BaseModel):
    """Response for a content report."""

    id: UUID
    reporter_id: UUID
    target_type: str
    target_id: UUID
    reason: str
    description: str | None = None
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


# ---------------------------------------------------------------------------
# Dashboard schemas
# ---------------------------------------------------------------------------


class AssignModeratorRequest(BaseModel):
    """Request to assign a moderator to a queue item."""

    moderator_id: UUID


class AssignModeratorResponse(BaseModel):
    """Response for moderator assignment."""

    id: UUID
    queue_id: UUID
    moderator_id: UUID
    status: str
    assigned_at: datetime

    model_config = {"from_attributes": True}


class BulkActionRequest(BaseModel):
    """Request to perform a bulk moderation action."""

    queue_ids: list[UUID] = Field(
        ..., min_length=1, max_length=100,
        description="List of queue item IDs to act on",
    )
    action: str = Field(
        ..., pattern="^(approve|reject|escalate)$",
        description="Moderation action to apply",
    )
    reason: str | None = Field(
        None, max_length=2000,
        description="Optional reason for the action",
    )


class BulkActionResponse(BaseModel):
    """Response for bulk moderation action."""

    action: str
    succeeded: list[str]
    failed: list[dict]
    total_succeeded: int
    total_failed: int


class SLAPipelineMetrics(BaseModel):
    """SLA metrics for a single pipeline."""

    pipeline: str
    p95_ms: float
    items_total: int
    items_in_sla: int
    items_breached_sla: int
    sla_target_ms: float
    compliance_pct: float


class SLAMetricsResponse(BaseModel):
    """Response for SLA metrics query."""

    window_hours: int
    window_start: str
    window_end: str
    pipelines: dict[str, SLAPipelineMetrics]


class PatternDetectionItem(BaseModel):
    """A single detected pattern."""

    pattern_type: str
    description: str
    severity: str
    details: dict | None = None
    window_start: str
    window_end: str


class PatternsResponse(BaseModel):
    """Response for pattern detection query."""

    patterns: list[PatternDetectionItem]
    total: int


# ---------------------------------------------------------------------------
# Appeal schemas
# ---------------------------------------------------------------------------


class AppealCreate(BaseModel):
    """Request to appeal a moderation decision."""

    reason: str = Field(
        ..., min_length=10, max_length=2000,
        description="Why do you believe this decision was wrong?",
    )


class AppealResponse(BaseModel):
    """Response for a moderation appeal."""

    id: UUID
    queue_id: UUID
    appellant_id: UUID
    reason: str
    status: str
    review_note: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AppealDecisionRequest(BaseModel):
    """Request to decide on an appeal (moderators only)."""

    decision: str = Field(
        ..., pattern="^(accepted|denied)$",
        description="Accept or deny the appeal",
    )
    review_note: str | None = Field(
        None, max_length=2000,
        description="Note explaining the decision",
    )
