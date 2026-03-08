"""Risk service — business logic for risk event CRUD and config management."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError
from src.risk.models import RiskConfig, RiskEvent
from src.risk.schemas import (
    RiskClassification,
    RiskConfigResponse,
    RiskConfigUpdate,
    RiskEventAcknowledge,
    RiskEventResponse,
)
from src.risk.taxonomy import ALL_CATEGORIES, ALL_SEVERITIES

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Risk event CRUD
# ---------------------------------------------------------------------------

async def create_risk_event(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    classification: RiskClassification,
    capture_event_id: UUID | None = None,
    details: dict | None = None,
) -> RiskEvent:
    """Persist a risk classification as a risk event."""
    event = RiskEvent(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        capture_event_id=capture_event_id,
        category=classification.category,
        severity=classification.severity,
        confidence=classification.confidence,
        details={
            "reasoning": classification.reasoning,
            **(details or {}),
        },
        acknowledged=False,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    logger.info(
        "risk_event_created",
        event_id=str(event.id),
        category=event.category,
        severity=event.severity,
        confidence=event.confidence,
        group_id=str(group_id),
        member_id=str(member_id),
    )

    return event


async def list_risk_events(
    db: AsyncSession,
    group_id: UUID,
    category: str | None = None,
    severity: str | None = None,
    member_id: UUID | None = None,
    acknowledged: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[RiskEvent], int]:
    """List risk events for a group with optional filters.

    Returns (events, total_count).
    """
    # Validate filter values
    if category and category not in ALL_CATEGORIES:
        raise ValidationError(f"Invalid category: {category}")
    if severity and severity not in ALL_SEVERITIES:
        raise ValidationError(f"Invalid severity: {severity}")

    # Base query
    query = select(RiskEvent).where(RiskEvent.group_id == group_id)
    count_query = select(func.count(RiskEvent.id)).where(RiskEvent.group_id == group_id)

    # Apply filters
    if category:
        query = query.where(RiskEvent.category == category)
        count_query = count_query.where(RiskEvent.category == category)
    if severity:
        query = query.where(RiskEvent.severity == severity)
        count_query = count_query.where(RiskEvent.severity == severity)
    if member_id:
        query = query.where(RiskEvent.member_id == member_id)
        count_query = count_query.where(RiskEvent.member_id == member_id)
    if acknowledged is not None:
        query = query.where(RiskEvent.acknowledged == acknowledged)
        count_query = count_query.where(RiskEvent.acknowledged == acknowledged)

    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    query = query.order_by(RiskEvent.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    events = list(result.scalars().all())

    return events, total


async def get_risk_event(
    db: AsyncSession,
    event_id: UUID,
    group_id: UUID,
) -> RiskEvent:
    """Get a single risk event by ID within a group."""
    result = await db.execute(
        select(RiskEvent).where(
            RiskEvent.id == event_id,
            RiskEvent.group_id == group_id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundError("RiskEvent", str(event_id))
    return event


async def acknowledge_risk_event(
    db: AsyncSession,
    event_id: UUID,
    group_id: UUID,
    data: RiskEventAcknowledge,
) -> RiskEvent:
    """Acknowledge a risk event."""
    event = await get_risk_event(db, event_id, group_id)

    if event.acknowledged:
        raise ValidationError("Risk event is already acknowledged")

    event.acknowledged = True
    event.acknowledged_by = data.acknowledged_by
    event.acknowledged_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(event)

    logger.info(
        "risk_event_acknowledged",
        event_id=str(event_id),
        acknowledged_by=str(data.acknowledged_by),
    )

    return event


async def get_content_excerpt(db: AsyncSession, risk_event_id: UUID, group_id: UUID) -> str | None:
    """Get decrypted content excerpt for a risk event. Verifies group ownership."""
    from src.risk.models import ContentExcerpt
    from src.encryption import decrypt_credential

    event = await get_risk_event(db, risk_event_id, group_id)
    result = await db.execute(
        select(ContentExcerpt).where(
            ContentExcerpt.risk_event_id == risk_event_id,
            ContentExcerpt.expires_at > datetime.now(timezone.utc),
        )
    )
    excerpt = result.scalar_one_or_none()
    if not excerpt:
        return None
    return decrypt_credential(excerpt.encrypted_content)


# ---------------------------------------------------------------------------
# Risk configuration management
# ---------------------------------------------------------------------------

async def get_risk_config(
    db: AsyncSession,
    group_id: UUID,
) -> list[RiskConfig]:
    """Get all risk configs for a group.

    If a category has no stored config, a default is created on-the-fly
    and persisted so it can be edited later.
    """
    result = await db.execute(
        select(RiskConfig).where(RiskConfig.group_id == group_id)
    )
    existing = {cfg.category: cfg for cfg in result.scalars().all()}

    # Ensure every category has a config row
    created_new = False
    for category in ALL_CATEGORIES:
        if category not in existing:
            cfg = RiskConfig(
                id=uuid4(),
                group_id=group_id,
                category=category,
                sensitivity=50,
                enabled=True,
                custom_keywords=None,
            )
            db.add(cfg)
            existing[category] = cfg
            created_new = True

    if created_new:
        await db.flush()

    return list(existing.values())


async def update_risk_config(
    db: AsyncSession,
    group_id: UUID,
    category: str,
    data: RiskConfigUpdate,
) -> RiskConfig:
    """Update risk configuration for a specific category."""
    if category not in ALL_CATEGORIES:
        raise ValidationError(f"Invalid category: {category}")

    # Find or create config for this category
    result = await db.execute(
        select(RiskConfig).where(
            RiskConfig.group_id == group_id,
            RiskConfig.category == category,
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        config = RiskConfig(
            id=uuid4(),
            group_id=group_id,
            category=category,
            sensitivity=50,
            enabled=True,
            custom_keywords=None,
        )
        db.add(config)

    # Apply updates
    if data.sensitivity is not None:
        config.sensitivity = data.sensitivity
    if data.enabled is not None:
        config.enabled = data.enabled
    if data.custom_keywords is not None:
        config.custom_keywords = data.custom_keywords

    await db.flush()
    await db.refresh(config)

    logger.info(
        "risk_config_updated",
        group_id=str(group_id),
        category=category,
        sensitivity=config.sensitivity,
        enabled=config.enabled,
    )

    return config


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

def risk_event_to_response(event: RiskEvent) -> RiskEventResponse:
    """Convert RiskEvent model to RiskEventResponse schema."""
    return RiskEventResponse(
        id=event.id,
        group_id=event.group_id,
        member_id=event.member_id,
        capture_event_id=event.capture_event_id,
        category=event.category,
        severity=event.severity,
        confidence=event.confidence,
        details=event.details,
        acknowledged=event.acknowledged,
        acknowledged_by=event.acknowledged_by,
        acknowledged_at=event.acknowledged_at,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def risk_config_to_response(config: RiskConfig) -> RiskConfigResponse:
    """Convert RiskConfig model to RiskConfigResponse schema."""
    return RiskConfigResponse(
        id=config.id,
        group_id=config.group_id,
        category=config.category,
        sensitivity=config.sensitivity,
        enabled=config.enabled,
        custom_keywords=config.custom_keywords,
    )
