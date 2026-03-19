"""Age tier database models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class AgeTierConfig(Base, UUIDMixin, TimestampMixin):
    """Per-member age tier configuration.

    Stores the tier assignment, date of birth, jurisdiction,
    and any permission overrides or locked features.
    """

    __tablename__ = "age_tier_configs"
    __table_args__ = (
        UniqueConstraint("member_id", name="uq_age_tier_configs_member_id"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    date_of_birth: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    jurisdiction: Mapped[str] = mapped_column(
        String(2), nullable=False, default="US",
    )
    feature_overrides: Mapped[dict | None] = mapped_column(
        JSONType, nullable=True, default=dict,
    )
    locked_features: Mapped[list | None] = mapped_column(
        JSONType, nullable=True, default=list,
    )
