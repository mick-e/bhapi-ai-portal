"""Reporting database models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class ScheduledReport(Base, UUIDMixin, TimestampMixin):
    """A scheduled recurring report."""

    __tablename__ = "scheduled_reports"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # activity, risk, spend, compliance
    schedule: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # daily, weekly, monthly
    recipients: Mapped[list | None] = mapped_column(
        JSONType, nullable=True
    )  # list of email addresses or user IDs
    last_generated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_generation: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ReportExport(Base, UUIDMixin, TimestampMixin):
    """A generated report export file."""

    __tablename__ = "report_exports"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # activity, risk, spend, compliance
    format: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # pdf, csv, json
    file_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
