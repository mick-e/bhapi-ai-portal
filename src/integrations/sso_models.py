"""SSO configuration models."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import TimestampMixin, UUIDMixin


class SSOConfig(Base, UUIDMixin, TimestampMixin):
    """SSO configuration for a group (school/club)."""
    __tablename__ = "sso_configs"

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # google_workspace, microsoft_entra
    tenant_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Microsoft tenant ID or Google Workspace domain
    auto_provision_members: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
