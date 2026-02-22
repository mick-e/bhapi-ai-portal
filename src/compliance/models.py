"""Compliance database models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class ConsentRecord(Base, UUIDMixin, TimestampMixin):
    """Record of consent given or withdrawn (GDPR, COPPA, LGPD)."""

    __tablename__ = "consent_records"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False
    )
    consent_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # monitoring, data_collection, ai_interaction, marketing
    parent_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    given_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )  # IPv4 or IPv6
    evidence: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )  # Signed consent form reference, checkbox ID, etc.


class DataDeletionRequest(Base, UUIDMixin, TimestampMixin):
    """GDPR Article 17 / COPPA data deletion request."""

    __tablename__ = "data_deletion_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    request_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # full_deletion, data_export, rectification
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, processing, completed
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuditEntry(Base, UUIDMixin):
    """Immutable audit log entry for compliance tracking."""

    __tablename__ = "audit_entries"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., consent.granted, data.exported, member.added
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # user, group, member, consent, alert
    resource_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    details: Mapped[dict | None] = mapped_column(
        JSONType, nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
