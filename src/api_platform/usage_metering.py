"""Usage metering models for Public API GA rate-tier plans.

Three new tables that track API key → tier mapping, per-request logging,
and monthly usage aggregates.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import TimestampMixin, UUIDMixin


class APIKeyRateTier(Base, UUIDMixin, TimestampMixin):
    """Maps an API key to a public API rate tier (free/developer/business/enterprise)."""

    __tablename__ = "api_key_rate_tiers"
    __table_args__ = (
        Index("ix_api_key_rate_tiers_api_key_id", "api_key_id", unique=True),
    )

    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
    )
    tier_name: Mapped[str] = mapped_column(
        String(30), nullable=False, default="free",
    )  # free, developer, business, enterprise


class APIRequestLog(Base, UUIDMixin):
    """Per-request usage log for API keys."""

    __tablename__ = "api_request_logs"
    __table_args__ = (
        Index("ix_api_request_logs_key_created", "api_key_id", "created_at"),
    )

    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
    )
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class MonthlyUsageAggregate(Base, UUIDMixin, TimestampMixin):
    """Aggregated monthly request counts per API key."""

    __tablename__ = "api_usage_monthly_aggregates"
    __table_args__ = (
        Index(
            "ix_api_usage_monthly_key_month",
            "api_key_id",
            "year_month",
            unique=True,
        ),
    )

    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
    )
    year_month: Mapped[str] = mapped_column(
        String(7), nullable=False,
    )  # e.g. "2026-04"
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_response_time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
