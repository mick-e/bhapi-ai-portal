"""Capture gateway API endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.capture.schemas import (
    CaptureEventResponse,
    ContentCaptureRequest,
    ConversationSummaryResponse,
    DeviceRegisterRequest,
    DeviceResponse,
    EventPayload,
    PairRequest,
    PairResponse,
    SetupCodeCreate,
    SetupCodeResponse,
    SummarizeRequest,
)
from src.capture.service import (
    create_content_capture,
    create_setup_code,
    exchange_setup_code,
    get_decrypted_content,
    get_member_session_summary,
    ingest_event,
    list_devices,
    list_events_enriched,
    register_device,
)
from src.capture.summary_models import ConversationSummary as _ConversationSummary  # noqa: F401 — register model
from src.capture.validators import verify_hmac_signature
from src.config import get_settings
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription
from src.dependencies import resolve_group_id as _gid
from src.exceptions import NotFoundError, UnauthorizedError, ValidationError
from src.schemas import GroupContext

router = APIRouter()

_trial_dep = Depends(require_active_trial_or_subscription)


async def _validate_hmac(request: Request, x_bhapi_signature: str | None = Header(None)) -> None:
    """Validate HMAC signature on capture events if enabled."""
    settings = get_settings()
    if not settings.capture_hmac_enabled:
        return

    if not x_bhapi_signature:
        raise UnauthorizedError("Missing X-Bhapi-Signature header")

    if not settings.capture_hmac_secret:
        raise UnauthorizedError("HMAC validation enabled but no secret configured")

    body = await request.body()
    payload_str = body.decode("utf-8")

    if not verify_hmac_signature(payload_str, x_bhapi_signature, settings.capture_hmac_secret):
        raise UnauthorizedError("Invalid HMAC signature")


@router.post("/events", response_model=CaptureEventResponse, status_code=201, dependencies=[_trial_dep])
async def capture_event(
    payload: EventPayload,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _hmac: None = Depends(_validate_hmac),
):
    """Ingest a capture event from browser extension (FR-021)."""
    event = await ingest_event(db, payload, source_channel="extension")
    return event


@router.post("/dns-events", response_model=CaptureEventResponse, status_code=201, dependencies=[_trial_dep])
async def capture_dns_event(
    payload: EventPayload,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a DNS proxy event (FR-021)."""
    event = await ingest_event(db, payload, source_channel="dns")
    return event


@router.post("/api-events", response_model=CaptureEventResponse, status_code=201, dependencies=[_trial_dep])
async def capture_api_event(
    payload: EventPayload,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest an LLM API webhook event (FR-021)."""
    event = await ingest_event(db, payload, source_channel="api")
    return event


@router.post("/content", status_code=201, dependencies=[_trial_dep])
async def capture_content(
    data: ContentCaptureRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Capture AI conversation content with encryption (requires enhanced monitoring)."""
    event = await create_content_capture(
        db=db,
        group_id=data.group_id,
        member_id=data.member_id,
        platform=data.platform,
        content=data.content,
        content_type=data.content_type,
        event_type=data.event_type,
        metadata=data.metadata,
    )
    return {
        "id": str(event.id),
        "group_id": str(event.group_id),
        "member_id": str(event.member_id),
        "platform": event.platform,
        "content_type": getattr(event, "content_type", None),
        "enhanced_monitoring": getattr(event, "enhanced_monitoring", True),
        "created_at": event.timestamp.isoformat() if event.timestamp else "",
    }


@router.get("/content/{event_id}", dependencies=[_trial_dep])
async def get_content(
    event_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve decrypted content for a capture event (audit logged)."""
    content = await get_decrypted_content(db, event_id)
    if content is None:
        from src.exceptions import NotFoundError
        raise NotFoundError("Content", str(event_id))
    return {"event_id": str(event_id), "content": content}


@router.get("/events", dependencies=[_trial_dep])
async def list_capture_events(
    group_id: UUID | None = Query(None),
    member_id: UUID | None = Query(None),
    platform: str | None = Query(None),
    provider: str | None = Query(None, description="Alias for platform"),
    risk_level: str | None = Query(None),
    event_type: str | None = Query(None),
    search: str | None = Query(None),
    start_date: date | None = Query(None, description="Filter events from this date (inclusive)"),
    end_date: date | None = Query(None, description="Filter events until this date (inclusive)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List enriched capture events for a group with pagination (FR-023)."""
    # Accept both "platform" and "provider" param names (frontend sends "provider")
    effective_platform = platform or provider
    return await list_events_enriched(
        db, _gid(group_id, auth), member_id, effective_platform, risk_level, event_type, search, page, page_size,
        start_date=start_date, end_date=end_date,
    )


@router.get("/devices/{member_id}/summary", dependencies=[_trial_dep])
async def device_session_summary(
    member_id: UUID,
    target_date: date | None = Query(None, description="Date for summary (defaults to today)"),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get multi-device session summary for a member."""
    return await get_member_session_summary(
        db, _gid(None, auth), member_id, target_date
    )


@router.post("/setup-codes", response_model=SetupCodeResponse, status_code=201, dependencies=[_trial_dep])
async def create_setup_code_endpoint(
    data: SetupCodeCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a one-time setup code for extension pairing."""
    return await create_setup_code(db, data, auth.user_id)


@router.post("/pair", response_model=PairResponse)
async def pair_extension(
    data: PairRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a setup code for pairing credentials (no auth required)."""
    return await exchange_setup_code(db, data.setup_code)


@router.post("/devices/register", response_model=DeviceResponse, status_code=201, dependencies=[_trial_dep])
async def register_device_endpoint(
    data: DeviceRegisterRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a device with setup code."""
    return await register_device(db, data)


@router.get("/devices", response_model=list[DeviceResponse], dependencies=[_trial_dep])
async def list_devices_endpoint(
    group_id: UUID | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List registered devices for a group."""
    return await list_devices(db, _gid(group_id, auth))


# ─── Conversation Summaries ──────────────────────────────────────────────────


@router.get("/summaries", dependencies=[_trial_dep])
async def list_summaries(
    group_id: UUID | None = Query(None),
    member_id: UUID | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List conversation summaries with filters and pagination."""
    if not member_id:
        raise ValidationError("member_id is required")

    from src.capture.summarizer import get_member_summaries

    resolved_group_id = _gid(group_id, auth)
    result = await get_member_summaries(
        db=db,
        group_id=resolved_group_id,
        member_id=member_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    # Serialize items
    items = [
        ConversationSummaryResponse.model_validate(item)
        for item in result["items"]
    ]
    return {
        "items": [item.model_dump(mode="json") for item in items],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"],
    }


@router.get("/summaries/{summary_id}", response_model=ConversationSummaryResponse, dependencies=[_trial_dep])
async def get_summary(
    summary_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single conversation summary."""
    from sqlalchemy import select

    from src.capture.summary_models import ConversationSummary

    result = await db.execute(
        select(ConversationSummary).where(ConversationSummary.id == summary_id)
    )
    summary = result.scalar_one_or_none()
    if not summary:
        raise NotFoundError("Conversation summary", str(summary_id))

    return summary


@router.post("/summarize", dependencies=[_trial_dep], status_code=201)
async def trigger_summarization(
    data: SummarizeRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger manual summarization for a capture event."""
    from sqlalchemy import select

    from src.capture.models import CaptureEvent
    from src.capture.summarizer import summarize_conversation
    from src.encryption import decrypt_credential

    # Look up the capture event
    result = await db.execute(
        select(CaptureEvent).where(CaptureEvent.id == data.event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundError("Capture event", str(data.event_id))

    # Get content — prefer encrypted, fall back to plaintext
    content = None
    if event.content_encrypted:
        content = decrypt_credential(event.content_encrypted)
    elif event.content:
        content = event.content

    if not content:
        raise ValidationError(
            "This capture event has no content to summarize. "
            "Enable enhanced monitoring to capture conversation content."
        )

    try:
        summary = await summarize_conversation(
            db=db,
            group_id=event.group_id,
            member_id=event.member_id,
            content=content,
            platform=event.platform,
            member_age=data.member_age,
            capture_event_id=event.id,
        )
    except RuntimeError as exc:
        raise ValidationError(str(exc))

    return ConversationSummaryResponse.model_validate(summary).model_dump(mode="json")
