"""Cross-product alert correlation engine."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, func, String, DateTime, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class AlertCorrelation(Base, UUIDMixin, TimestampMixin):
    """A correlated pattern across multiple alerts/products."""

    __tablename__ = "alert_correlations"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    correlation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_alerts: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    source_products: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    acknowledged: Mapped[bool | None] = mapped_column(nullable=True, default=False)


async def create_correlation(
    db: AsyncSession,
    group_id: uuid.UUID,
    correlation_type: str,
    title: str,
    description: str | None = None,
    confidence_score: float = 0.5,
    source_alerts: list | None = None,
    source_products: list | None = None,
    member_id: uuid.UUID | None = None,
    severity: str = "medium",
) -> AlertCorrelation:
    """Create a new alert correlation."""
    correlation = AlertCorrelation(
        id=uuid.uuid4(),
        group_id=group_id,
        member_id=member_id,
        correlation_type=correlation_type,
        title=title,
        description=description,
        confidence_score=confidence_score,
        source_alerts=source_alerts or [],
        source_products=source_products or [],
        severity=severity,
    )
    db.add(correlation)
    await db.flush()
    await db.refresh(correlation)
    logger.info("correlation_created", type=correlation_type, confidence=confidence_score)
    return correlation


async def list_correlations(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID | None = None
) -> list[AlertCorrelation]:
    """List correlations for a group."""
    query = select(AlertCorrelation).where(AlertCorrelation.group_id == group_id)
    if member_id:
        query = query.where(AlertCorrelation.member_id == member_id)
    result = await db.execute(query.order_by(AlertCorrelation.created_at.desc()))
    return list(result.scalars().all())


async def analyze_member_correlations(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID
) -> dict:
    """Analyze cross-product correlations for a member."""
    from src.risk.models import RiskEvent
    from src.alerts.models import Alert

    # Get risk event count
    risk_count_result = await db.execute(
        select(func.count(RiskEvent.id)).where(
            RiskEvent.group_id == group_id,
            RiskEvent.member_id == member_id,
        )
    )
    risk_count = risk_count_result.scalar() or 0

    # Get alert count
    alert_count_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.group_id == group_id,
            Alert.member_id == member_id,
        )
    )
    alert_count = alert_count_result.scalar() or 0

    # Get existing correlations
    correlations = await list_correlations(db, group_id, member_id)

    return {
        "member_id": str(member_id),
        "group_id": str(group_id),
        "risk_events": risk_count,
        "alerts": alert_count,
        "correlation_count": len(correlations),
        "correlations": [
            {
                "id": str(c.id),
                "type": c.correlation_type,
                "title": c.title,
                "confidence": c.confidence_score,
                "severity": c.severity,
            }
            for c in correlations
        ],
    }
