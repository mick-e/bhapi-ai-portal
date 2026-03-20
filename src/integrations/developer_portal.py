"""Developer portal and SDK management."""

import hashlib
import secrets
import uuid

import structlog
from sqlalchemy import Boolean, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models import JSONType, TimestampMixin, UUIDMixin

logger = structlog.get_logger()


class DeveloperApp(Base, UUIDMixin, TimestampMixin):
    """A third-party developer application."""

    __tablename__ = "developer_apps"

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    redirect_uris: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    scopes: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class WebhookEndpoint(Base, UUIDMixin, TimestampMixin):
    """A webhook endpoint for event delivery."""

    __tablename__ = "webhook_endpoints"

    app_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    events: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class WebhookDelivery(Base, UUIDMixin, TimestampMixin):
    """Record of a webhook delivery attempt."""

    __tablename__ = "webhook_deliveries"

    endpoint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class MarketplaceModule(Base, UUIDMixin, TimestampMixin):
    """A module in the safety marketplace."""

    __tablename__ = "marketplace_modules"

    developer_app_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    install_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating: Mapped[float | None] = mapped_column(nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class InstalledModule(Base, UUIDMixin, TimestampMixin):
    """A module installed by a group."""

    __tablename__ = "installed_modules"

    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    module_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


async def create_developer_app(
    db: AsyncSession,
    owner_id: uuid.UUID,
    name: str,
    description: str | None = None,
    redirect_uris: list | None = None,
    scopes: list | None = None,
) -> tuple[DeveloperApp, str]:
    """Create a developer app. Returns (app, client_secret)."""
    client_id = f"bhapi_{secrets.token_hex(16)}"
    client_secret = f"bhapi_secret_{secrets.token_hex(32)}"
    secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()

    app = DeveloperApp(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name=name,
        description=description,
        client_id=client_id,
        client_secret_hash=secret_hash,
        redirect_uris=redirect_uris or [],
        scopes=scopes or ["read"],
        active=True,
        approved=False,
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)
    logger.info("developer_app_created", app_id=str(app.id), name=name)
    return app, client_secret


async def list_developer_apps(db: AsyncSession, owner_id: uuid.UUID) -> list[DeveloperApp]:
    """List developer apps for an owner."""
    result = await db.execute(
        select(DeveloperApp).where(DeveloperApp.owner_id == owner_id)
    )
    return list(result.scalars().all())


async def list_marketplace_modules(
    db: AsyncSession, category: str | None = None, published_only: bool = True
) -> list[MarketplaceModule]:
    """List marketplace modules."""
    query = select(MarketplaceModule).order_by(MarketplaceModule.install_count.desc())
    if published_only:
        query = query.where(MarketplaceModule.published.is_(True))
    if category:
        query = query.where(MarketplaceModule.category == category)
    result = await db.execute(query)
    return list(result.scalars().all())


async def install_module(
    db: AsyncSession, group_id: uuid.UUID, module_id: uuid.UUID, config: dict | None = None
) -> InstalledModule:
    """Install a marketplace module for a group."""
    installed = InstalledModule(
        id=uuid.uuid4(),
        group_id=group_id,
        module_id=module_id,
        config=config,
        active=True,
    )
    db.add(installed)
    await db.flush()
    await db.refresh(installed)

    # Increment install count
    result = await db.execute(select(MarketplaceModule).where(MarketplaceModule.id == module_id))
    module = result.scalar_one_or_none()
    if module:
        module.install_count += 1
        await db.flush()

    logger.info("module_installed", group_id=str(group_id), module_id=str(module_id))
    return installed
