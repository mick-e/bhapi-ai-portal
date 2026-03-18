"""Enterprise AI usage policy management."""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import NotFoundError, ValidationError
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class AIUsagePolicy(Base, UUIDMixin, TimestampMixin):
    """An AI usage policy for an organisation."""

    __tablename__ = "ai_usage_policies"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_type: Mapped[str] = mapped_column(String(50), nullable=False)  # acceptable_use, data_handling, model_access, cost_control
    rules: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    enforcement_level: Mapped[str] = mapped_column(String(20), nullable=False, default="warn")  # warn, block, audit
    applies_to: Mapped[list | None] = mapped_column(JSONType, nullable=True)  # member IDs or "all"
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PolicyViolation(Base, UUIDMixin, TimestampMixin):
    """A recorded violation of an AI usage policy."""

    __tablename__ = "policy_violations"

    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    violation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    action_taken: Mapped[str] = mapped_column(String(50), nullable=False, default="logged")
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


async def create_policy(
    db: AsyncSession,
    group_id: uuid.UUID,
    name: str,
    policy_type: str,
    description: str | None = None,
    rules: list | None = None,
    enforcement_level: str = "warn",
    applies_to: list | None = None,
) -> AIUsagePolicy:
    """Create an AI usage policy."""
    valid_types = ("acceptable_use", "data_handling", "model_access", "cost_control")
    if policy_type not in valid_types:
        raise ValidationError(f"Policy type must be one of: {', '.join(valid_types)}")

    policy = AIUsagePolicy(
        id=uuid.uuid4(),
        group_id=group_id,
        name=name,
        description=description,
        policy_type=policy_type,
        rules=rules or [],
        enforcement_level=enforcement_level,
        applies_to=applies_to,
        active=True,
    )
    db.add(policy)
    await db.flush()
    await db.refresh(policy)
    logger.info("policy_created", policy_id=str(policy.id), name=name)
    return policy


async def list_policies(
    db: AsyncSession, group_id: uuid.UUID, active_only: bool = True
) -> list[AIUsagePolicy]:
    """List policies for a group."""
    query = select(AIUsagePolicy).where(AIUsagePolicy.group_id == group_id)
    if active_only:
        query = query.where(AIUsagePolicy.active.is_(True))
    result = await db.execute(query.order_by(AIUsagePolicy.created_at.desc()))
    return list(result.scalars().all())


async def record_violation(
    db: AsyncSession,
    policy_id: uuid.UUID,
    group_id: uuid.UUID,
    violation_type: str,
    description: str,
    severity: str = "medium",
    member_id: uuid.UUID | None = None,
    action_taken: str = "logged",
) -> PolicyViolation:
    """Record a policy violation."""
    violation = PolicyViolation(
        id=uuid.uuid4(),
        policy_id=policy_id,
        group_id=group_id,
        member_id=member_id,
        violation_type=violation_type,
        description=description,
        severity=severity,
        action_taken=action_taken,
    )
    db.add(violation)
    await db.flush()
    await db.refresh(violation)
    logger.info("policy_violation_recorded", policy_id=str(policy_id), type=violation_type)
    return violation


async def list_violations(
    db: AsyncSession, group_id: uuid.UUID, resolved: bool | None = None
) -> list[PolicyViolation]:
    """List violations for a group."""
    query = select(PolicyViolation).where(PolicyViolation.group_id == group_id)
    if resolved is not None:
        query = query.where(PolicyViolation.resolved == resolved)
    result = await db.execute(query.order_by(PolicyViolation.created_at.desc()))
    return list(result.scalars().all())
