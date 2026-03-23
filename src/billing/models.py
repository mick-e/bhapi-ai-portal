"""Billing database models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class Subscription(Base, UUIDMixin, TimestampMixin):
    """Stripe subscription for a group."""

    __tablename__ = "subscriptions"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    plan_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # free, starter, family, school, enterprise
    billing_cycle: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly"
    )  # monthly, annual
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active, past_due, cancelled, trialing
    trial_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    platform_limit: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    feature_flags: Mapped[dict | None] = mapped_column(
        JSONType, nullable=True
    )


class LLMAccount(Base, UUIDMixin, TimestampMixin):
    """Connected LLM provider account for spend tracking."""

    __tablename__ = "llm_accounts"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # openai, google, microsoft, anthropic, xai
    credentials_encrypted: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )
    last_synced: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active, inactive, error
    last_error: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0"
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class SpendRecord(Base, UUIDMixin, TimestampMixin):
    """Individual spend record from an LLM provider."""

    __tablename__ = "spend_records"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    llm_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("llm_accounts.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="USD"
    )
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    __table_args__ = (
        Index("ix_spend_records_group_period", "group_id", "period_start", "period_end"),
    )


class BudgetThreshold(Base, UUIDMixin, TimestampMixin):
    """Budget threshold for spend alerts."""

    __tablename__ = "budget_thresholds"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # soft, hard
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="USD"
    )
    notify_at: Mapped[list | None] = mapped_column(
        JSONType, nullable=True, default=lambda: [50, 80, 100]
    )


class FiredThresholdAlert(Base, UUIDMixin, TimestampMixin):
    """Tracks which threshold alerts have been fired to survive restarts."""

    __tablename__ = "fired_threshold_alerts"

    threshold_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budget_thresholds.id"), nullable=False
    )
    percentage_level: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class FeatureGate(Base, UUIDMixin, TimestampMixin):
    """Maps features to required subscription tiers."""

    __tablename__ = "feature_gates"

    feature_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    required_tier: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # free, family, family_plus, school, enterprise
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
