"""Audit logging for SOC 2 compliance."""

import uuid

import structlog
from sqlalchemy import String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Immutable audit log entry for SOC 2 compliance."""

    __tablename__ = "audit_logs"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    details: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)


async def log_audit_event(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    actor_id: uuid.UUID | None = None,
    actor_email: str | None = None,
    group_id: uuid.UUID | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Create an immutable audit log entry."""
    entry = AuditLog(
        id=uuid.uuid4(),
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        group_id=group_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    await db.flush()
    logger.info("audit_event", action=action, resource_type=resource_type, resource_id=resource_id)
    return entry


async def query_audit_logs(
    db: AsyncSession,
    group_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    """Query audit logs with filters."""
    from sqlalchemy import func
    base = select(AuditLog)
    count_q = select(func.count(AuditLog.id))

    if group_id:
        base = base.where(AuditLog.group_id == group_id)
        count_q = count_q.where(AuditLog.group_id == group_id)
    if action:
        base = base.where(AuditLog.action == action)
        count_q = count_q.where(AuditLog.action == action)
    if resource_type:
        base = base.where(AuditLog.resource_type == resource_type)
        count_q = count_q.where(AuditLog.resource_type == resource_type)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        base.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total
