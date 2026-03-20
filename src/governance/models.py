"""Governance database models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class GovernancePolicy(Base, UUIDMixin, TimestampMixin):
    """AI governance policy for a school."""

    __tablename__ = "governance_policies"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    state_code: Mapped[str] = mapped_column(String(2), nullable=False)
    policy_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # ai_usage, tool_inventory, risk_assessment, governance
    content: Mapped[dict] = mapped_column(JSONType, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft",
    )  # draft, active, archived
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class GovernanceAudit(Base, UUIDMixin, TimestampMixin):
    """Audit trail for governance policy changes."""

    __tablename__ = "governance_audits"

    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("governance_policies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    diff: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
