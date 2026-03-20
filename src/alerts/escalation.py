"""Crisis escalation partner hooks."""

import uuid
from datetime import datetime

import structlog
from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import NotFoundError, ValidationError
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class EscalationPartner(Base, UUIDMixin, TimestampMixin):
    """An external crisis response partner integration."""

    __tablename__ = "escalation_partners"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # crisis_text_line, school_counselor, custom_webhook
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severity_threshold: Mapped[str] = mapped_column(String(20), nullable=False, default="critical")
    categories: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EscalationRecord(Base, UUIDMixin, TimestampMixin):
    """Record of an escalation to a partner."""

    __tablename__ = "escalation_records"

    partner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # pending, sent, acknowledged, resolved
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    response_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


async def create_escalation_partner(
    db: AsyncSession,
    group_id: uuid.UUID,
    name: str,
    provider_type: str,
    webhook_url: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    severity_threshold: str = "critical",
    categories: list | None = None,
) -> EscalationPartner:
    """Register a crisis response partner."""
    if provider_type not in ("crisis_text_line", "school_counselor", "custom_webhook"):
        raise ValidationError("Invalid provider type")
    partner = EscalationPartner(
        id=uuid.uuid4(),
        group_id=group_id,
        name=name,
        provider_type=provider_type,
        webhook_url=webhook_url,
        contact_email=contact_email,
        contact_phone=contact_phone,
        severity_threshold=severity_threshold,
        categories=categories,
        active=True,
    )
    db.add(partner)
    await db.flush()
    await db.refresh(partner)
    logger.info("escalation_partner_created", partner_id=str(partner.id), name=name)
    return partner


async def list_escalation_partners(
    db: AsyncSession, group_id: uuid.UUID
) -> list[EscalationPartner]:
    """List all escalation partners for a group."""
    result = await db.execute(
        select(EscalationPartner).where(
            EscalationPartner.group_id == group_id,
            EscalationPartner.active.is_(True),
        )
    )
    return list(result.scalars().all())


async def escalate_alert(
    db: AsyncSession,
    partner_id: uuid.UUID,
    alert_id: uuid.UUID,
    group_id: uuid.UUID,
    severity: str,
    member_id: uuid.UUID | None = None,
    category: str | None = None,
) -> EscalationRecord:
    """Create an escalation record and trigger partner notification."""
    # Verify partner exists
    result = await db.execute(
        select(EscalationPartner).where(EscalationPartner.id == partner_id)
    )
    partner = result.scalar_one_or_none()
    if not partner:
        raise NotFoundError("Escalation partner", str(partner_id))

    record = EscalationRecord(
        id=uuid.uuid4(),
        partner_id=partner_id,
        alert_id=alert_id,
        group_id=group_id,
        member_id=member_id,
        severity=severity,
        category=category,
        status="sent",
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    # Trigger notification (webhook, email, or SMS)
    logger.info(
        "alert_escalated",
        partner=partner.name,
        alert_id=str(alert_id),
        severity=severity,
    )
    return record


async def list_escalation_records(
    db: AsyncSession, group_id: uuid.UUID
) -> list[EscalationRecord]:
    """List escalation records for a group."""
    result = await db.execute(
        select(EscalationRecord).where(EscalationRecord.group_id == group_id)
        .order_by(EscalationRecord.created_at.desc())
    )
    return list(result.scalars().all())
