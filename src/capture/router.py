"""Capture gateway API endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.capture.schemas import (
    CaptureEventResponse,
    DeviceRegisterRequest,
    DeviceResponse,
    EventPayload,
)
from src.capture.service import ingest_event, list_devices, list_events_enriched, register_device
from src.capture.validators import verify_hmac_signature
from src.config import get_settings
from src.database import get_db
from src.dependencies import resolve_group_id as _gid
from src.exceptions import UnauthorizedError
from src.schemas import GroupContext

router = APIRouter()


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


@router.post("/events", response_model=CaptureEventResponse, status_code=201)
async def capture_event(
    payload: EventPayload,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _hmac: None = Depends(_validate_hmac),
):
    """Ingest a capture event from browser extension (FR-021)."""
    event = await ingest_event(db, payload, source_channel="extension")
    return event


@router.post("/dns-events", response_model=CaptureEventResponse, status_code=201)
async def capture_dns_event(
    payload: EventPayload,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a DNS proxy event (FR-021)."""
    event = await ingest_event(db, payload, source_channel="dns")
    return event


@router.post("/api-events", response_model=CaptureEventResponse, status_code=201)
async def capture_api_event(
    payload: EventPayload,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest an LLM API webhook event (FR-021)."""
    event = await ingest_event(db, payload, source_channel="api")
    return event


@router.get("/events")
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


@router.post("/devices/register", response_model=DeviceResponse, status_code=201)
async def register_device_endpoint(
    data: DeviceRegisterRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a device with setup code."""
    return await register_device(db, data)


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices_endpoint(
    group_id: UUID | None = Query(None),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List registered devices for a group."""
    return await list_devices(db, _gid(group_id, auth))
