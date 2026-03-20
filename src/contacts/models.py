"""Contacts database models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import TimestampMixin, UUIDMixin


class Contact(Base, UUIDMixin, TimestampMixin):
    """Contact request between users."""

    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint(
            "requester_id", "target_id", name="uq_contacts_requester_target",
        ),
    )

    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
    )  # pending, accepted, rejected, blocked
    parent_approval_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_required",
    )  # pending, approved, denied, not_required


class ContactApproval(Base, UUIDMixin, TimestampMixin):
    """Parent approval decision for a contact request."""

    __tablename__ = "contact_approvals"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    parent_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
