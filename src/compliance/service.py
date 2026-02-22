"""Compliance service — business logic for data rights, consent, and audit logging."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError
from src.compliance.models import AuditEntry, ConsentRecord, DataDeletionRequest
from src.compliance.schemas import DataRequestCreate

logger = structlog.get_logger()


async def create_data_request(
    db: AsyncSession, user_id: UUID, data: DataRequestCreate
) -> DataDeletionRequest:
    """Create a data deletion/export request (GDPR Article 17, COPPA)."""
    request = DataDeletionRequest(
        id=uuid4(),
        user_id=user_id,
        request_type=data.request_type,
        status="pending",
    )
    db.add(request)
    await db.flush()
    await db.refresh(request)

    # Create audit entry for the request
    audit = AuditEntry(
        id=uuid4(),
        group_id=uuid4(),  # System-level; in production, derive from user context
        actor_id=user_id,
        action=f"data_request.{data.request_type}",
        resource_type="data_deletion_request",
        resource_id=str(request.id),
        details={"request_type": data.request_type},
    )
    db.add(audit)
    await db.flush()

    logger.info(
        "data_request_created",
        request_id=str(request.id),
        user_id=str(user_id),
        request_type=data.request_type,
    )
    return request


async def get_data_request_status(
    db: AsyncSession, request_id: UUID
) -> DataDeletionRequest:
    """Get the status of a data deletion/export request."""
    result = await db.execute(
        select(DataDeletionRequest).where(DataDeletionRequest.id == request_id)
    )
    request = result.scalar_one_or_none()
    if not request:
        raise NotFoundError("Data request", str(request_id))
    return request


async def list_consents(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[ConsentRecord]:
    """List consent records for a group, optionally filtered by member."""
    query = select(ConsentRecord).where(ConsentRecord.group_id == group_id)

    if member_id:
        query = query.where(ConsentRecord.member_id == member_id)

    query = query.order_by(ConsentRecord.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_audit_entries(
    db: AsyncSession,
    group_id: UUID,
    action: str | None = None,
    resource_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[AuditEntry]:
    """List audit log entries for a group with optional filters."""
    query = select(AuditEntry).where(AuditEntry.group_id == group_id)

    if action:
        query = query.where(AuditEntry.action == action)
    if resource_type:
        query = query.where(AuditEntry.resource_type == resource_type)

    query = query.order_by(AuditEntry.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
