"""Intelligence module database models — social graph edges, abuse signals, behavioral baselines."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class CorrelationRule(Base, UUIDMixin, TimestampMixin):
    """A configurable rule that matches patterns across event types."""

    __tablename__ = "correlation_rules"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition: Mapped[dict] = mapped_column(JSONType, nullable=False)
    action_severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium"
    )  # low, medium, high, critical
    notification_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="alert"
    )  # alert, email, push, sms
    age_tier_filter: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # young, preteen, teen, null=all
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EnrichedAlert(Base, UUIDMixin, TimestampMixin):
    """An alert enriched with cross-product correlation context."""

    __tablename__ = "enriched_alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    correlation_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("correlation_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    correlation_context: Mapped[str] = mapped_column(Text, nullable=False)
    contributing_signals: Mapped[dict] = mapped_column(JSONType, nullable=False)
    unified_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium"
    )  # low, medium, high


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
