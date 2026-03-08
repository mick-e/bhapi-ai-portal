"""SIS integration models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin


class SISConnection(Base, UUIDMixin, TimestampMixin):
    """School Information System connection."""
    __tablename__ = "sis_connections"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # clever, classlink
    credentials_encrypted: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )
    last_synced: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active, inactive, error
    config_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
