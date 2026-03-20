"""Contacts module FastAPI router — contact requests, parent approval, blocking."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.contacts import schemas, service
from src.database import get_db
from src.schemas import GroupContext

logger = structlog.get_logger()

router = APIRouter()


@router.post("/request/{user_id}", response_model=schemas.ContactResponse, status_code=201)
async def send_contact_request(
    user_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a contact request to another user."""
    contact = await service.send_request(db, auth.user_id, user_id)
    await db.commit()
    return contact


@router.patch("/{id}/respond", response_model=schemas.ContactResponse)
async def respond_to_request(
    id: UUID,
    body: schemas.RespondRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept or reject a contact request (target only)."""
    contact = await service.respond_to_request(db, id, auth.user_id, body.action)
    await db.commit()
    return contact


@router.patch("/{id}/parent-approve", response_model=schemas.ContactApprovalResponse)
async def parent_approve(
    id: UUID,
    body: schemas.ParentApprovalRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Parent approve or deny a contact request."""
    approval = await service.approve_as_parent(db, id, auth.user_id, body.decision)
    await db.commit()
    return approval


@router.post("/{user_id}/block", response_model=schemas.ContactResponse, status_code=201)
async def block_user(
    user_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Block a user."""
    contact = await service.block_contact(db, auth.user_id, user_id)
    await db.commit()
    return contact


@router.get("/", response_model=schemas.ContactListResponse)
async def list_contacts(
    status: str | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List my contacts (sent and received)."""
    return await service.list_contacts(
        db, auth.user_id, status=status, page=page, page_size=page_size,
    )


@router.get("/pending", response_model=schemas.ContactListResponse)
async def list_pending_approvals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List contacts pending my parental approval."""
    return await service.get_pending_approvals(
        db, auth.user_id, page=page, page_size=page_size,
    )
