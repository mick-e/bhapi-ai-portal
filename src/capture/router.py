"""Capture gateway API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.capture.schemas import (
    APIWebhookEvent,
    CaptureEventResponse,
    DeviceRegisterRequest,
    DeviceResponse,
    DNSEvent,
    EventPayload,
)
from src.capture.service import ingest_event, list_devices, list_events, register_device
from src.database import get_db
from src.schemas import GroupContext

router = APIRouter()


@router.post("/events", response_model=CaptureEventResponse, status_code=201)
async def capture_event(
    payload: EventPayload,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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


@router.get("/events", response_model=list[CaptureEventResponse])
async def list_capture_events(
    group_id: UUID = Query(...),
    member_id: UUID | None = Query(None),
    platform: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List capture events for a group (FR-023)."""
    return await list_events(db, group_id, member_id, platform, limit, offset)


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
    group_id: UUID = Query(...),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List registered devices for a group."""
    return await list_devices(db, group_id)
