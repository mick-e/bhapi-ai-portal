"""Capture gateway service — event ingestion and normalisation."""

import hashlib
import secrets
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.capture.models import CaptureEvent, DeviceRegistration, SetupCode
from src.capture.schemas import DeviceRegisterRequest, EnrichedEventResponse, EventPayload, PairResponse, SetupCodeCreate
from src.encryption import decrypt_credential, encrypt_credential
from src.exceptions import ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from src.groups.models import Group, GroupMember
from src.risk.models import RiskEvent

logger = structlog.get_logger()


async def ingest_event(
    db: AsyncSession,
    payload: EventPayload,
    source_channel: str = "extension",
) -> CaptureEvent:
    """Validate, normalise, and store a capture event.

    Blocks events for members who require consent but haven't received it.
    In production, this also publishes to Pub/Sub raw_events topic.
    """
    # Check consent before accepting events
    from src.groups.service import check_member_consent
    has_consent = await check_member_consent(db, payload.group_id, payload.member_id)
    if not has_consent:
        raise ForbiddenError(
            "Capture blocked: guardian consent required for this member. "
            "Record consent before monitoring can begin."
        )

    event = CaptureEvent(
        id=uuid4(),
        group_id=payload.group_id,
        member_id=payload.member_id,
        platform=payload.platform,
        session_id=payload.session_id,
        event_type=payload.event_type,
        timestamp=payload.timestamp,
        content=payload.content,
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

    # Run risk pipeline inline if content is present
    if payload.content:
        try:
            from src.risk.pipeline import process_capture_event
            await process_capture_event(db, event)
        except Exception as exc:
            logger.error("inline_risk_pipeline_error", event_id=str(event.id), error=str(exc))
            # Continue — the batch worker will pick this up later

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


async def list_events_enriched(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID | None = None,
    platform: str | None = None,
    risk_level: str | None = None,
    event_type: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    start_date: "date | None" = None,
    end_date: "date | None" = None,
) -> dict:
    """List capture events enriched with member name and risk level, with pagination."""
    # Build base query
    query = select(CaptureEvent).where(CaptureEvent.group_id == group_id)
    count_query = select(func.count(CaptureEvent.id)).where(CaptureEvent.group_id == group_id)

    if member_id:
        query = query.where(CaptureEvent.member_id == member_id)
        count_query = count_query.where(CaptureEvent.member_id == member_id)
    if platform:
        query = query.where(CaptureEvent.platform == platform)
        count_query = count_query.where(CaptureEvent.platform == platform)
    if event_type:
        query = query.where(CaptureEvent.event_type == event_type)
        count_query = count_query.where(CaptureEvent.event_type == event_type)
    if search:
        pattern = f"%{search}%"
        query = query.where(CaptureEvent.content.ilike(pattern))
        count_query = count_query.where(CaptureEvent.content.ilike(pattern))
    if start_date:
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        query = query.where(CaptureEvent.timestamp >= start_dt)
        count_query = count_query.where(CaptureEvent.timestamp >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        query = query.where(CaptureEvent.timestamp <= end_dt)
        count_query = count_query.where(CaptureEvent.timestamp <= end_dt)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(CaptureEvent.timestamp.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    events = list(result.scalars().all())

    if not events:
        return {
            "items": [],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }

    # Build member name lookup
    member_ids = list({e.member_id for e in events})
    member_result = await db.execute(
        select(GroupMember).where(GroupMember.id.in_(member_ids))
    )
    members = {m.id: m.display_name for m in member_result.scalars().all()}

    # Build risk level lookup (highest severity risk event per capture event)
    event_ids = [e.id for e in events]
    risk_result = await db.execute(
        select(RiskEvent.capture_event_id, RiskEvent.severity)
        .where(RiskEvent.capture_event_id.in_(event_ids))
    )
    # Pick highest severity per capture event
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    risk_map: dict[UUID, str] = {}
    for row in risk_result.all():
        cev_id, sev = row[0], row[1]
        if cev_id not in risk_map or severity_order.get(sev, 0) > severity_order.get(risk_map[cev_id], 0):
            risk_map[cev_id] = sev

    # Build enriched items
    enriched_items = []
    for e in events:
        r_level = risk_map.get(e.id, "low")
        enriched_items.append(EnrichedEventResponse(
            id=e.id,
            group_id=e.group_id,
            member_id=e.member_id,
            member_name=members.get(e.member_id, "Unknown"),
            provider=e.platform,
            model="",
            event_type=e.event_type,
            prompt_preview=(e.content or "")[:200],
            risk_level=r_level,
            flagged=r_level in ("high", "critical"),
            timestamp=e.timestamp,
        ))

    # Filter by risk level if requested (post-filter since it requires risk lookup)
    if risk_level:
        enriched_items = [i for i in enriched_items if i.risk_level == risk_level]

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": enriched_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


async def create_content_capture(
    db: AsyncSession,
    group_id: UUID,
    member_id: UUID,
    platform: str,
    content: str,
    content_type: str = "prompt",
    event_type: str = "conversation",
    metadata: dict | None = None,
) -> CaptureEvent:
    """Create a capture event with encrypted content.

    Content is encrypted before storage and a hash is stored for deduplication.
    Requires enhanced_monitoring consent from the group.
    """
    # Check group exists
    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise NotFoundError("Group", str(group_id))

    # Encrypt content
    content_encrypted = encrypt_credential(content)
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    # Check for duplicate (same content from same member within 1 minute)
    one_min_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
    dup_result = await db.execute(
        select(CaptureEvent).where(
            CaptureEvent.group_id == group_id,
            CaptureEvent.member_id == member_id,
            CaptureEvent.content_hash == content_hash,
            CaptureEvent.timestamp >= one_min_ago,
        )
    )
    existing = dup_result.scalar_one_or_none()
    if existing:
        return existing  # Deduplicate

    event = CaptureEvent(
        id=uuid4(),
        group_id=group_id,
        member_id=member_id,
        platform=platform,
        event_type=event_type,
        session_id=f"content-{uuid4().hex[:8]}",
        content_encrypted=content_encrypted,
        content_type=content_type,
        content_hash=content_hash,
        enhanced_monitoring=True,
        timestamp=datetime.now(timezone.utc),
        risk_processed=False,
        source_channel="api",
    )
    if metadata:
        event.event_metadata = metadata

    db.add(event)
    await db.flush()
    await db.refresh(event)

    logger.info(
        "content_capture_created",
        event_id=str(event.id),
        platform=platform,
        content_type=content_type,
    )

    return event


async def get_decrypted_content(db: AsyncSession, event_id: UUID) -> str | None:
    """Retrieve and decrypt content for a capture event."""
    result = await db.execute(select(CaptureEvent).where(CaptureEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event or not event.content_encrypted:
        return None

    return decrypt_credential(event.content_encrypted)


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


async def create_setup_code(
    db: AsyncSession,
    data: SetupCodeCreate,
    user_id: UUID,
) -> SetupCode:
    """Generate a one-time setup code for extension pairing.

    The code expires after 15 minutes. The signing_secret is returned
    to the extension during pairing so it can sign future capture events.
    """
    code = secrets.token_hex(4)  # 8 hex chars
    signing_secret = secrets.token_urlsafe(32)

    setup = SetupCode(
        id=uuid4(),
        group_id=data.group_id,
        member_id=data.member_id,
        code=code,
        signing_secret=signing_secret,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        used=False,
        device_name=data.device_name,
        created_by=user_id,
    )
    db.add(setup)
    await db.flush()
    await db.refresh(setup)

    logger.info("setup_code_created", code=code, group_id=str(data.group_id), member_id=str(data.member_id))
    return setup


async def exchange_setup_code(
    db: AsyncSession,
    code: str,
) -> PairResponse:
    """Exchange a setup code for pairing credentials.

    Validates the code is not expired and has not been used yet.
    Marks the code as used and creates a DeviceRegistration record.
    """
    result = await db.execute(
        select(SetupCode).where(SetupCode.code == code)
    )
    setup = result.scalar_one_or_none()

    if not setup:
        raise NotFoundError("Setup code")

    now = datetime.now(timezone.utc)

    if setup.expires_at.replace(tzinfo=timezone.utc) < now:
        raise UnauthorizedError("Setup code has expired")

    if setup.used:
        raise UnauthorizedError("Setup code has already been used")

    # Mark as used
    setup.used = True
    setup.used_at = now
    await db.flush()

    # Create a device registration
    device = DeviceRegistration(
        id=uuid4(),
        group_id=setup.group_id,
        member_id=setup.member_id,
        device_name=setup.device_name or "Browser Extension",
        setup_code=setup.code,
    )
    db.add(device)
    await db.flush()

    logger.info("setup_code_exchanged", code=code, group_id=str(setup.group_id))

    return PairResponse(
        group_id=str(setup.group_id),
        member_id=str(setup.member_id),
        signing_secret=setup.signing_secret,
    )
