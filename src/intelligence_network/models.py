"""Intelligence Network SQLAlchemy models."""

import uuid

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class ThreatSignal(Base, UUIDMixin, TimestampMixin):
    """Anonymized threat signal shared across the network.

    NO group_id or member_id — anonymization strips all identifiers.
    """

    __tablename__ = "intel_network_threat_signals"

    signal_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    pattern_data: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    contributor_region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_helpful: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feedback_false_positive: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class NetworkSubscription(Base, UUIDMixin, TimestampMixin):
    """Group opt-in to the intelligence network."""

    __tablename__ = "intel_network_subscriptions"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    signal_types: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    minimum_severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium",
    )


class SignalDelivery(Base, UUIDMixin):
    """Audit log of signal deliveries to subscribers."""

    __tablename__ = "intel_network_signal_deliveries"

    signal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    delivered_at: Mapped[None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )


class AnonymizationAudit(Base, UUIDMixin):
    """Audit trail for each anonymization operation."""

    __tablename__ = "intel_network_anonymization_audit"

    signal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source_group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    fields_stripped: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    k_anonymity_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dp_noise_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anonymized_at: Mapped[None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
