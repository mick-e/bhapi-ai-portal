"""API platform business logic — client management, usage tracking."""

import secrets
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_platform.models import (
    APIKeyTier,
    APIUsageRecord,
    OAuthClient,
    PlatformWebhookDelivery,
    PlatformWebhookEndpoint,
)
from src.api_platform.oauth import _hash_token
from src.api_platform.schemas import (
    OAuthClientCreate,
    UsageDayResponse,
    UsageResponse,
    VALID_SCOPES,
)
from src.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Client management
# ---------------------------------------------------------------------------


async def register_client(
    db: AsyncSession,
    owner_id: UUID,
    data: OAuthClientCreate,
) -> tuple[OAuthClient, str]:
    """Create an OAuth client (pending admin approval).

    Returns (client, plaintext_secret).
    """
    # Validate scopes
    invalid = set(data.scopes) - VALID_SCOPES
    if invalid:
        raise ValidationError(f"Invalid scopes requested: {', '.join(sorted(invalid))}")

    # Check for duplicate name for this owner
    existing = await db.execute(
        select(OAuthClient).where(
            OAuthClient.owner_id == owner_id,
            OAuthClient.name == data.name,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(f"Client named '{data.name}' already exists for this account")

    # Generate client credentials
    client_id = secrets.token_urlsafe(32)[:64]
    client_secret = secrets.token_urlsafe(48)
    secret_hash = _hash_token(client_secret)

    client = OAuthClient(
        id=uuid4(),
        name=data.name,
        client_id=client_id,
        client_secret_hash=secret_hash,
        redirect_uris=data.redirect_uris,
        scopes=data.scopes,
        tier=data.tier,
        owner_id=owner_id,
        is_approved=False,
        is_active=True,
    )
    db.add(client)
    await db.flush()
    await db.refresh(client)

    logger.info(
        "oauth_client_registered",
        client_db_id=str(client.id),
        client_id=client_id,
        owner_id=str(owner_id),
        tier=data.tier,
    )
    return client, client_secret


async def approve_client(db: AsyncSession, client_db_id: UUID) -> OAuthClient:
    """Admin approves an OAuth client, enabling token issuance."""
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.id == client_db_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise NotFoundError("OAuthClient", str(client_db_id))

    client.is_approved = True
    await db.flush()
    await db.refresh(client)

    logger.info("oauth_client_approved", client_db_id=str(client_db_id))
    return client


async def deactivate_client(db: AsyncSession, client_db_id: UUID) -> OAuthClient:
    """Deactivate an OAuth client."""
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.id == client_db_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise NotFoundError("OAuthClient", str(client_db_id))

    client.is_active = False
    await db.flush()
    await db.refresh(client)

    logger.info("oauth_client_deactivated", client_db_id=str(client_db_id))
    return client


async def list_clients(
    db: AsyncSession,
    owner_id: UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[OAuthClient], int]:
    """List OAuth clients, optionally filtered by owner."""
    base = select(OAuthClient)
    if owner_id is not None:
        base = base.where(OAuthClient.owner_id == owner_id)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = await db.execute(
        base.order_by(OAuthClient.created_at.desc()).offset(offset).limit(limit)
    )
    return list(rows.scalars().all()), total


async def get_client(db: AsyncSession, client_db_id: UUID) -> OAuthClient:
    """Get an OAuth client by its database UUID."""
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.id == client_db_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise NotFoundError("OAuthClient", str(client_db_id))
    return client


async def get_client_by_client_id(db: AsyncSession, client_id_str: str) -> OAuthClient:
    """Get an OAuth client by its OAuth client_id string."""
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.client_id == client_id_str)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise NotFoundError("OAuthClient", client_id_str)
    return client


# ---------------------------------------------------------------------------
# Usage tracking
# ---------------------------------------------------------------------------


async def record_usage(
    db: AsyncSession,
    client_db_id: UUID,
    webhook_delivery: bool = False,
) -> APIUsageRecord:
    """Increment daily usage counter for a client.

    Creates the record if it doesn't exist yet, otherwise increments atomically.
    """
    today = date.today()

    # Try to find existing record
    result = await db.execute(
        select(APIUsageRecord).where(
            APIUsageRecord.client_id == client_db_id,
            APIUsageRecord.date == today,
        )
    )
    record = result.scalar_one_or_none()

    if record:
        record.request_count += 1
        if webhook_delivery:
            record.webhook_deliveries += 1
    else:
        record = APIUsageRecord(
            id=uuid4(),
            client_id=client_db_id,
            date=today,
            request_count=1,
            webhook_deliveries=1 if webhook_delivery else 0,
        )
        db.add(record)

    await db.flush()
    await db.refresh(record)
    return record


async def get_usage(
    db: AsyncSession,
    client_db_id: UUID,
    days: int = 30,
) -> UsageResponse:
    """Get usage metrics for a client over the last N days."""
    cutoff = date.today() - timedelta(days=days - 1)

    rows = await db.execute(
        select(APIUsageRecord)
        .where(
            APIUsageRecord.client_id == client_db_id,
            APIUsageRecord.date >= cutoff,
        )
        .order_by(APIUsageRecord.date)
    )
    records = list(rows.scalars().all())

    day_responses = [
        UsageDayResponse(
            date=str(r.date),
            request_count=r.request_count,
            webhook_deliveries=r.webhook_deliveries,
        )
        for r in records
    ]

    total_requests = sum(r.request_count for r in records)
    total_deliveries = sum(r.webhook_deliveries for r in records)

    return UsageResponse(
        client_id=client_db_id,
        days=day_responses,
        total_requests=total_requests,
        total_webhook_deliveries=total_deliveries,
    )


# ---------------------------------------------------------------------------
# Tier configuration
# ---------------------------------------------------------------------------


async def list_tiers(db: AsyncSession) -> list[APIKeyTier]:
    """List all API tier configurations."""
    rows = await db.execute(select(APIKeyTier).order_by(APIKeyTier.name))
    return list(rows.scalars().all())


async def get_tier(db: AsyncSession, name: str) -> APIKeyTier | None:
    """Get a tier configuration by name."""
    result = await db.execute(
        select(APIKeyTier).where(APIKeyTier.name == name)
    )
    return result.scalar_one_or_none()


async def check_rate_limit(
    db: AsyncSession,
    client_db_id: UUID,
    tier_name: str,
) -> bool:
    """Check if client has exceeded their hourly rate limit.

    Returns True if request is allowed, False if rate limited.
    """
    tier = await get_tier(db, tier_name)
    if not tier:
        return True  # Unknown tier — allow

    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    # Count requests in last hour using daily record (approximate)
    # For production, this would use Redis sliding window
    today = date.today()
    result = await db.execute(
        select(APIUsageRecord).where(
            APIUsageRecord.client_id == client_db_id,
            APIUsageRecord.date == today,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        return True

    # Simple check: daily requests vs hourly limit * 24 (rough guard)
    return record.request_count < tier.rate_limit_per_hour


# ---------------------------------------------------------------------------
# Webhook management
# ---------------------------------------------------------------------------


async def register_webhook(
    db: AsyncSession,
    client_db_id: UUID,
    url: str,
    events: list[str],
    secret: str,
) -> PlatformWebhookEndpoint:
    """Register a webhook endpoint for a client."""
    # Check tier webhook limit
    client = await get_client(db, client_db_id)
    tier = await get_tier(db, client.tier)

    if tier:
        count_result = await db.execute(
            select(func.count()).where(
                PlatformWebhookEndpoint.client_id == client_db_id,
                PlatformWebhookEndpoint.is_active == True,  # noqa: E712
            )
        )
        count = count_result.scalar() or 0
        if count >= tier.max_webhooks:
            raise ForbiddenError(
                f"Webhook limit of {tier.max_webhooks} reached for {tier.name} tier"
            )

    endpoint = PlatformWebhookEndpoint(
        id=uuid4(),
        client_id=client_db_id,
        url=url,
        events=events,
        secret_hash=_hash_token(secret),
        is_active=True,
    )
    db.add(endpoint)
    await db.flush()
    await db.refresh(endpoint)

    logger.info(
        "platform_webhook_registered",
        client_id=str(client_db_id),
        url=url,
        events=events,
    )
    return endpoint


async def list_webhooks(
    db: AsyncSession,
    client_db_id: UUID,
) -> list[PlatformWebhookEndpoint]:
    """List webhook endpoints for a client."""
    rows = await db.execute(
        select(PlatformWebhookEndpoint).where(
            PlatformWebhookEndpoint.client_id == client_db_id,
        )
    )
    return list(rows.scalars().all())


async def get_webhook(
    db: AsyncSession,
    endpoint_id: UUID,
) -> PlatformWebhookEndpoint:
    """Get a single webhook endpoint by ID."""
    result = await db.execute(
        select(PlatformWebhookEndpoint).where(PlatformWebhookEndpoint.id == endpoint_id)
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise NotFoundError("PlatformWebhookEndpoint", str(endpoint_id))
    return endpoint


async def delete_webhook(
    db: AsyncSession,
    endpoint_id: UUID,
    client_db_id: UUID,
) -> None:
    """Delete (deactivate) a webhook endpoint.

    Raises ForbiddenError if the endpoint does not belong to client_db_id.
    Raises NotFoundError if it does not exist.
    """
    endpoint = await get_webhook(db, endpoint_id)
    if endpoint.client_id != client_db_id:
        raise ForbiddenError("Webhook does not belong to this client")

    endpoint.is_active = False
    await db.flush()
    logger.info(
        "platform_webhook_deleted",
        endpoint_id=str(endpoint_id),
        client_id=str(client_db_id),
    )


async def list_webhook_deliveries(
    db: AsyncSession,
    endpoint_id: UUID,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[PlatformWebhookDelivery], int]:
    """List delivery attempts for a webhook endpoint (paginated)."""
    base = select(PlatformWebhookDelivery).where(
        PlatformWebhookDelivery.endpoint_id == endpoint_id,
    )
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = await db.execute(
        base.order_by(PlatformWebhookDelivery.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(rows.scalars().all()), total
