"""Capture gateway service — event ingestion and normalisation."""

import secrets
from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.capture.models import CaptureEvent, DeviceRegistration
from src.capture.schemas import DeviceRegisterRequest, EventPayload
from src.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()


async def ingest_event(
    db: AsyncSession,
    payload: EventPayload,
    source_channel: str = "extension",
) -> CaptureEvent:
    """Validate, normalise, and store a capture event.

    In production, this also publishes to Pub/Sub raw_events topic.
    """
    event = CaptureEvent(
        id=uuid4(),
        group_id=payload.group_id,
        member_id=payload.member_id,
        platform=payload.platform,
        session_id=payload.session_id,
        event_type=payload.event_type,
        timestamp=payload.timestamp,
        event_metadata=payload.metadata,
        risk_processed=False,
        source_channel=source_channel,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    logger.info(
        "event_ingested",
        event_id=str(event.id),
        platform=payload.platform,
        event_type=payload.event_type,
        source=source_channel,
    )

    # TODO: Publish to Pub/Sub raw_events topic for risk pipeline processing
    return event


async def list_events(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID | None = None,
    platform: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[CaptureEvent]:
    """List capture events for a group."""
    query = select(CaptureEvent).where(CaptureEvent.group_id == group_id)
    if member_id:
        query = query.where(CaptureEvent.member_id == member_id)
    if platform:
        query = query.where(CaptureEvent.platform == platform)
    query = query.order_by(CaptureEvent.timestamp.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def register_device(
    db: AsyncSession,
    data: DeviceRegisterRequest,
) -> DeviceRegistration:
    """Register a device with a setup code."""
    device = DeviceRegistration(
        id=uuid4(),
        group_id=data.group_id,
        member_id=data.member_id,
        device_name=data.device_name,
        setup_code=data.setup_code,
    )
    db.add(device)
    await db.flush()
    await db.refresh(device)

    logger.info("device_registered", device_id=str(device.id), device_name=data.device_name)
    return device


async def list_devices(
    db: AsyncSession,
    group_id: UUID,
) -> list[DeviceRegistration]:
    """List registered devices for a group."""
    result = await db.execute(
        select(DeviceRegistration).where(DeviceRegistration.group_id == group_id)
    )
    return list(result.scalars().all())


def generate_setup_code() -> str:
    """Generate a 6-character setup code for device registration."""
    return secrets.token_hex(3).upper()  # 6 hex chars
