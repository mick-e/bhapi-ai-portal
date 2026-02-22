"""Compliance API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.compliance.schemas import (
    AuditEntryResponse,
    ConsentResponse,
    DataRequestCreate,
    DataRequestStatus,
)
from src.compliance.service import (
    create_data_request,
    get_data_request_status,
    list_audit_entries,
    list_consents,
)
from src.schemas import GroupContext

router = APIRouter()


@router.post("/data-request", response_model=DataRequestStatus, status_code=201)
async def create_data_request_endpoint(
    data: DataRequestCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a data deletion/export request (GDPR Article 17, COPPA) (FR-051)."""
    request = await create_data_request(db, auth.user_id, data)
    return request


@router.get("/data-request/{request_id}/status", response_model=DataRequestStatus)
async def get_data_request_status_endpoint(
    request_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get data request status (FR-052)."""
    request = await get_data_request_status(db, request_id)
    return request


@router.get("/consents", response_model=list[ConsentResponse])
async def list_consents_endpoint(
    group_id: UUID = Query(..., description="Group ID"),
    member_id: UUID | None = Query(None, description="Filter by member ID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List consent records for a group (FR-053)."""
    consents = await list_consents(db, group_id, member_id=member_id, offset=offset, limit=limit)
    return consents


@router.get("/audit-log", response_model=list[AuditEntryResponse])
async def list_audit_log_endpoint(
    group_id: UUID = Query(..., description="Group ID"),
    action: str | None = Query(None, description="Filter by action"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit log entries (FR-054)."""
    entries = await list_audit_entries(
        db, group_id, action=action, resource_type=resource_type, offset=offset, limit=limit
    )
    return entries
