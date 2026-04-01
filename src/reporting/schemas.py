"""Reporting Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from src.schemas import BaseSchema


class ReportRequest(BaseSchema):
    """Generate report request."""

    group_id: UUID
    report_type: str = Field(pattern="^(activity|risk|spend|compliance)$")
    format: str = Field(default="pdf", pattern="^(pdf|csv|json)$")
    period_start: datetime | None = None
    period_end: datetime | None = None
    filters: dict | None = None


class ReportResponse(BaseSchema):
    """Report export response."""

    id: UUID
    group_id: UUID
    report_type: str
    format: str
    file_path: str | None
    generated_at: datetime
    expires_at: datetime | None
    created_at: datetime


class ScheduleConfig(BaseSchema):
    """Create/update report schedule request."""

    group_id: UUID
    report_type: str = Field(pattern="^(activity|risk|spend|compliance)$")
    schedule: str = Field(pattern="^(daily|weekly|monthly)$")
    recipients: list[str] = Field(default_factory=list)


class CreateReportRequest(BaseSchema):
    """Create report request from frontend."""

    type: str = Field(default="activity", pattern="^(safety|spend|activity|compliance)$")
    format: str = Field(default="pdf", pattern="^(pdf|csv|json)$")
    period_start: str | None = None
    period_end: str | None = None


class UpdateScheduleRequest(BaseSchema):
    """Update/create report schedule from frontend."""

    type: str = Field(default="activity", pattern="^(safety|spend|activity|compliance)$")
    schedule: str = Field(default="weekly", pattern="^(none|daily|weekly|monthly)$")
    recipients: list[str] = Field(default_factory=list)


class ScheduleResponse(BaseSchema):
    """Scheduled report response."""

    id: UUID
    group_id: UUID
    report_type: str
    schedule: str
    recipients: list[str] | None
    last_generated: datetime | None
    next_generation: datetime | None
    created_at: datetime
