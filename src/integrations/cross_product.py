"""Cross-product API foundation for App+Portal ecosystem."""

import uuid
from datetime import datetime

import structlog
from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.exceptions import ValidationError
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class ProductRegistration(Base, UUIDMixin, TimestampMixin):
    """A registered product in the cross-product ecosystem."""

    __tablename__ = "product_registrations"

    product_name: Mapped[str] = mapped_column(String(100), nullable=False)
    product_type: Mapped[str] = mapped_column(String(50), nullable=False)  # app, portal, extension
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    owner_group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    permissions: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SharedProfile(Base, UUIDMixin, TimestampMixin):
    """A shared user profile across products."""

    __tablename__ = "shared_profiles"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_data: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False, default="synced")


class CrossProductAlert(Base, UUIDMixin, TimestampMixin):
    """An alert that spans multiple products."""

    __tablename__ = "cross_product_alerts"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_product: Mapped[str] = mapped_column(String(50), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


async def register_product(
    db: AsyncSession,
    product_name: str,
    product_type: str,
    api_key_hash: str,
    owner_group_id: uuid.UUID,
    permissions: list | None = None,
) -> ProductRegistration:
    """Register a product for cross-product communication."""
    if product_type not in ("app", "portal", "extension"):
        raise ValidationError("Product type must be app, portal, or extension")

    reg = ProductRegistration(
        id=uuid.uuid4(),
        product_name=product_name,
        product_type=product_type,
        api_key_hash=api_key_hash,
        owner_group_id=owner_group_id,
        permissions=permissions or ["read_alerts", "read_profiles"],
        active=True,
    )
    db.add(reg)
    await db.flush()
    await db.refresh(reg)
    logger.info("product_registered", name=product_name, type=product_type)
    return reg


async def create_cross_product_alert(
    db: AsyncSession,
    group_id: uuid.UUID,
    source_product: str,
    alert_type: str,
    severity: str,
    title: str,
    body: str | None = None,
    member_id: uuid.UUID | None = None,
    metadata_json: dict | None = None,
) -> CrossProductAlert:
    """Create a cross-product alert."""
    alert = CrossProductAlert(
        id=uuid.uuid4(),
        group_id=group_id,
        member_id=member_id,
        source_product=source_product,
        alert_type=alert_type,
        severity=severity,
        title=title,
        body=body,
        metadata_json=metadata_json,
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)
    logger.info("cross_product_alert_created", alert_type=alert_type, source=source_product)
    return alert


async def list_cross_product_alerts(
    db: AsyncSession, group_id: uuid.UUID, limit: int = 50
) -> list[CrossProductAlert]:
    """List cross-product alerts for a group."""
    result = await db.execute(
        select(CrossProductAlert).where(CrossProductAlert.group_id == group_id)
        .order_by(CrossProductAlert.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
