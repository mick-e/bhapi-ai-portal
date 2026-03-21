"""Intelligence module database models — social graph edges, abuse signals, behavioral baselines."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class SocialGraphEdge(Base, UUIDMixin, TimestampMixin):
    """An edge in the social graph connecting two members."""

    __tablename__ = "social_graph_edges"
    __table_args__ = (
        Index("ix_social_graph_source_target", "source_id", "target_id"),
        Index("ix_social_graph_source_type", "source_id", "edge_type"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    edge_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # contact, follow, message, mention
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    last_interaction: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )


class AbuseSignal(Base, UUIDMixin, TimestampMixin):
    """A detected abuse signal for a group member."""

    __tablename__ = "abuse_signals"
    __table_args__ = (
        Index("ix_abuse_signals_member_type", "member_id", "signal_type"),
        Index("ix_abuse_signals_severity", "severity"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    signal_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # age_gap, isolation, influence, farming
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium",
    )  # low, medium, high, critical
    details: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )


class BehavioralBaseline(Base, UUIDMixin, TimestampMixin):
    """Behavioral baseline metrics for a group member over a time window."""

    __tablename__ = "behavioral_baselines"
    __table_args__ = (
        Index("ix_behavioral_baselines_member_window", "member_id", "window_days"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    metrics: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
