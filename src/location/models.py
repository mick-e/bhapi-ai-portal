"""Location tracking database models — records, geofences, school check-in, privacy controls."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import TimestampMixin, UUIDMixin


class LocationRecord(Base, UUIDMixin, TimestampMixin):
    """A location data point from the device agent."""

    __tablename__ = "location_records"
    __table_args__ = (
        Index("ix_location_records_member_recorded", "member_id", "recorded_at"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    latitude: Mapped[str] = mapped_column(String(255), nullable=False)  # Encrypted via encrypt_credential()
    longitude: Mapped[str] = mapped_column(String(255), nullable=False)  # Encrypted
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="gps")  # gps, network, fused
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Geofence(Base, UUIDMixin, TimestampMixin):
    """A geofence boundary defined by parent."""

    __tablename__ = "geofences"
    __table_args__ = (
        Index("ix_geofences_group_member", "group_id", "member_id"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_meters: Mapped[float] = mapped_column(Float, nullable=False)
    notify_on_enter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_on_exit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class GeofenceEvent(Base, UUIDMixin, TimestampMixin):
    """An event when a child enters or exits a geofence."""

    __tablename__ = "geofence_events"
    __table_args__ = (
        Index("ix_geofence_events_geofence_recorded", "geofence_id", "recorded_at"),
    )

    geofence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geofences.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(10), nullable=False)  # enter, exit
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SchoolCheckIn(Base, UUIDMixin, TimestampMixin):
    """School attendance check-in/check-out record."""

    __tablename__ = "school_checkins"
    __table_args__ = (
        Index("ix_school_checkins_member_date", "member_id", "check_in_at"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    geofence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geofences.id", ondelete="CASCADE"),
        nullable=False,
    )
    check_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LocationSharingConsent(Base, UUIDMixin, TimestampMixin):
    """Parent consent to share child's location with a school."""

    __tablename__ = "location_sharing_consents"
    __table_args__ = (
        Index("ix_location_consent_member_group", "member_id", "group_id", unique=True),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )  # school group
    granted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
        nullable=False,
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LocationKillSwitch(Base, UUIDMixin, TimestampMixin):
    """Parent-controlled kill switch to immediately stop all location tracking."""

    __tablename__ = "location_kill_switches"

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    activated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
        nullable=False,
    )
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LocationAuditLog(Base, UUIDMixin, TimestampMixin):
    """Audit log entry for location data access."""

    __tablename__ = "location_audit_logs"
    __table_args__ = (
        Index("ix_location_audit_member_accessed", "member_id", "accessed_at"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    accessor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
        nullable=False,
    )
    data_type: Mapped[str] = mapped_column(String(20), nullable=False)  # current, history, checkin
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
