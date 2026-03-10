"""Groups database models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models import JSONType, SoftDeleteMixin, TimestampMixin, UUIDMixin


class Group(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """A family, school, or club group."""

    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # family, school, club
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSONType, nullable=True, default=dict)

    # Relationships
    members: Mapped[list["GroupMember"]] = relationship(back_populates="group", lazy="selectin")
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="group", lazy="selectin")


class GroupMember(Base, UUIDMixin, TimestampMixin):
    """A member of a group."""

    __tablename__ = "group_members"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # parent, member, school_admin, club_admin
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    group: Mapped["Group"] = relationship(back_populates="members")


class Invitation(Base, UUIDMixin, TimestampMixin):
    """Group invitation."""

    __tablename__ = "invitations"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    invited_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, accepted, expired
    consent_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    group: Mapped["Group"] = relationship(back_populates="invitations")


class ClassGroup(Base, UUIDMixin, TimestampMixin):
    """A class within a school group."""

    __tablename__ = "class_groups"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    academic_year: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    class_members: Mapped[list["ClassGroupMember"]] = relationship(
        back_populates="class_group", lazy="selectin"
    )


class ClassGroupMember(Base, UUIDMixin, TimestampMixin):
    """A member assigned to a class group."""

    __tablename__ = "class_group_members"

    class_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("class_groups.id"), nullable=False, index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id"), nullable=False, index=True
    )

    # Relationships
    class_group: Mapped["ClassGroup"] = relationship(back_populates="class_members")
