"""Incident management for SOC 2 compliance."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import NotFoundError, ValidationError
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class IncidentRecord(Base, UUIDMixin, TimestampMixin):
    """A security or operational incident record."""

    __tablename__ = "incident_records"

    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical
    # security, availability, data_breach, policy_violation
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # open, investigating, resolved, closed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    reported_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeline: Mapped[list | None] = mapped_column(JSONType, nullable=True)


async def create_incident(
    db: AsyncSession,
    title: str,
    severity: str,
    category: str,
    description: str,
    group_id: uuid.UUID | None = None,
    reported_by: uuid.UUID | None = None,
) -> IncidentRecord:
    """Create a new incident record."""
    if severity not in ("low", "medium", "high", "critical"):
        raise ValidationError("Severity must be low, medium, high, or critical")
    if category not in ("security", "availability", "data_breach", "policy_violation"):
        raise ValidationError("Invalid category")

    incident = IncidentRecord(
        id=uuid.uuid4(),
        group_id=group_id,
        title=title,
        severity=severity,
        category=category,
        description=description,
        status="open",
        reported_by=reported_by,
        timeline=[{"action": "created", "timestamp": datetime.now(timezone.utc).isoformat()}],
    )
    db.add(incident)
    await db.flush()
    await db.refresh(incident)
    logger.info("incident_created", incident_id=str(incident.id), severity=severity)
    return incident


async def update_incident_status(
    db: AsyncSession,
    incident_id: uuid.UUID,
    status: str,
    resolution: str | None = None,
    root_cause: str | None = None,
) -> IncidentRecord:
    """Update incident status."""
    result = await db.execute(select(IncidentRecord).where(IncidentRecord.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise NotFoundError("Incident", str(incident_id))

    incident.status = status
    if resolution:
        incident.resolution = resolution
    if root_cause:
        incident.root_cause = root_cause
    if status in ("resolved", "closed"):
        incident.resolved_at = datetime.now(timezone.utc)

    timeline = incident.timeline or []
    timeline.append({"action": f"status_changed_to_{status}", "timestamp": datetime.now(timezone.utc).isoformat()})
    incident.timeline = timeline

    await db.flush()
    return incident


async def list_incidents(
    db: AsyncSession, group_id: uuid.UUID | None = None, status: str | None = None
) -> list[IncidentRecord]:
    """List incidents with optional filters."""
    query = select(IncidentRecord).order_by(IncidentRecord.created_at.desc())
    if group_id:
        query = query.where(IncidentRecord.group_id == group_id)
    if status:
        query = query.where(IncidentRecord.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())
