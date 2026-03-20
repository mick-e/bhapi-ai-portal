"""Media module FastAPI router — upload URL generation, media registration, variants."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.database import get_db
from src.media import schemas, service
from src.schemas import GroupContext

logger = structlog.get_logger()

router = APIRouter()


@router.post("/upload", response_model=schemas.UploadURLResponse, status_code=201)
async def request_upload_url(
    data: schemas.UploadURLRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a presigned upload URL for media."""
    result = await service.create_upload_url(
        db,
        owner_id=auth.user_id,
        media_type=data.media_type,
        content_length=data.content_length,
        filename=data.filename,
    )
    await db.commit()
    return result


@router.post("/register", response_model=schemas.MediaAssetResponse, status_code=201)
async def register_media(
    data: schemas.RegisterMediaRequest,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a media asset after upload completes."""
    asset = await service.register_media(
        db,
        owner_id=auth.user_id,
        cloudflare_id=data.cloudflare_id,
        media_type=data.media_type,
        r2_key=data.r2_key,
    )
    await db.commit()
    return asset


@router.get("/", response_model=schemas.MediaListResponse)
async def list_my_media(
    media_type: str | None = Query(default=None, pattern=r"^(image|video)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the authenticated user's media assets."""
    return await service.list_media(
        db,
        owner_id=auth.user_id,
        media_type=media_type,
        page=page,
        page_size=page_size,
    )


@router.get("/{media_id}", response_model=schemas.MediaAssetResponse)
async def get_media(
    media_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single media asset by ID."""
    return await service.get_media(db, media_id)


@router.get("/{media_id}/variants")
async def get_variants(
    media_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get processed variants for a media asset."""
    variants = await service.get_variants(db, media_id)
    return {"media_id": str(media_id), "variants": variants}


@router.delete("/{media_id}", status_code=204)
async def delete_media(
    media_id: UUID,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a media asset (owner only)."""
    await service.delete_media(db, media_id, auth.user_id)
    await db.commit()
