"""FERPA compliance database models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class EducationalRecord(Base, UUIDMixin, TimestampMixin):
    """FERPA-covered educational record designation.

    Tracks which records are classified as educational records under FERPA,
    enabling proper access controls and audit requirements.
    """

    __tablename__ = "ferpa_educational_records"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    record_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # ai_interaction, safety_alert, behavioral, academic, disciplinary
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_directory_info: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    classification: Mapped[str] = mapped_column(
        String(30), nullable=False, default="protected",
    )  # protected, directory, de_identified
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)


class AccessLog(Base, UUIDMixin, TimestampMixin):
    """Audit log of FERPA educational record access per 34 CFR 99.32.

    Schools must maintain a record of each request for and each disclosure
    of personally identifiable information from education records.
    """

    __tablename__ = "ferpa_access_logs"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ferpa_educational_records.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    accessor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    access_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # view, export, disclose, amend
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    legitimate_interest: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )  # school_official, health_safety, judicial_order, directory_info
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )


class AnnualNotification(Base, UUIDMixin, TimestampMixin):
    """Annual FERPA notification tracking.

    Schools must annually notify parents and eligible students of their
    rights under FERPA (34 CFR 99.7).
    """

    __tablename__ = "ferpa_annual_notifications"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    school_year: Mapped[str] = mapped_column(
        String(9), nullable=False,
    )  # e.g. "2025-2026"
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    template_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
    )
    recipient_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    notification_method: Mapped[str] = mapped_column(
        String(30), nullable=False, default="email",
    )  # email, postal, handbook


class DataSharingAgreement(Base, UUIDMixin, TimestampMixin):
    """Third-party data sharing agreements under FERPA.

    Tracks agreements with ed-tech vendors and other third parties
    who receive access to education records.
    """

    __tablename__ = "ferpa_data_sharing_agreements"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    third_party_name: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    data_elements: Mapped[dict] = mapped_column(
        JSONType, nullable=False,
    )  # list of data fields shared
    legal_basis: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # school_official, consent, studies, audit
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
    )  # active, expired, revoked
    effective_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    expiration_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    terms: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
