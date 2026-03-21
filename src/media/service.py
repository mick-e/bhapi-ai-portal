"""Media module business logic — Cloudflare R2/Images/Stream."""

import time
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.exceptions import ForbiddenError, NotFoundError, ValidationError
from src.moderation.models import MediaAsset

logger = structlog.get_logger()

# Size limits
IMAGE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
VIDEO_MAX_BYTES = 100 * 1024 * 1024  # 100 MB

UPLOAD_URL_EXPIRY_MINUTES = 30

# Batch limits
MAX_BATCH_SIZE = 10

# ---------------------------------------------------------------------------
# In-memory LRU cache for variant URLs
# ---------------------------------------------------------------------------

VARIANT_CACHE_TTL_SECONDS = 300  # 5 minutes
VARIANT_CACHE_MAX_SIZE = 1024


class _VariantCache:
    """Thread-safe LRU cache for variant URLs keyed by (media_id, variant)."""

    def __init__(self, max_size: int = VARIANT_CACHE_MAX_SIZE, ttl: int = VARIANT_CACHE_TTL_SECONDS):
        self._store: OrderedDict[str, tuple[dict | None, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl

    def _make_key(self, media_id: uuid.UUID, variant: str | None = None) -> str:
        return f"{media_id}:{variant or '__all__'}"

    def get(self, media_id: uuid.UUID, variant: str | None = None) -> dict | None | type[...]:
        """Return cached variants or Ellipsis (sentinel) if not cached / expired."""
        key = self._make_key(media_id, variant)
        entry = self._store.get(key)
        if entry is None:
            return ...
        value, ts = entry
        if time.monotonic() - ts > self._ttl:
            # Expired
            self._store.pop(key, None)
            return ...
        # Move to end (most recently used)
        self._store.move_to_end(key)
        return value

    def put(self, media_id: uuid.UUID, variants: dict | None, variant: str | None = None) -> None:
        """Cache variant data."""
        key = self._make_key(media_id, variant)
        self._store[key] = (variants, time.monotonic())
        self._store.move_to_end(key)
        # Evict oldest if over capacity
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def invalidate(self, media_id: uuid.UUID) -> None:
        """Remove all cached entries for a media asset."""
        prefix = f"{media_id}:"
        keys_to_remove = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_remove:
            del self._store[k]

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)


# Module-level cache instance
variant_cache = _VariantCache()


# ---------------------------------------------------------------------------
# Upload URL generation
# ---------------------------------------------------------------------------


def _generate_upload_url(r2_key: str) -> str:
    """Generate R2 presigned upload URL. In production, uses CF R2 API."""
    settings = get_settings()
    if settings.environment in ("test", "development"):
        return f"https://r2.example.com/upload/{r2_key}?token=dev"
    # Production: use Cloudflare R2 API with boto3/httpx + CF R2 credentials
    return f"https://r2.example.com/upload/{r2_key}"


async def create_upload_url(
    db: AsyncSession,
    owner_id: uuid.UUID,
    media_type: str,
    content_length: int | None = None,
    filename: str | None = None,
) -> dict:
    """Generate a presigned R2 upload URL and create a pending MediaAsset.

    Args:
        db: Database session.
        owner_id: UUID of the asset owner.
        media_type: "image" or "video".
        content_length: Optional file size in bytes.
        filename: Optional original filename.

    Returns:
        Dict with upload_url, media_id, expires_at.

    Raises:
        ValidationError: If media_type is invalid or content_length exceeds limits.
    """
    if media_type not in ("image", "video"):
        raise ValidationError("media_type must be 'image' or 'video'")

    if content_length is not None:
        max_bytes = IMAGE_MAX_BYTES if media_type == "image" else VIDEO_MAX_BYTES
        if content_length > max_bytes:
            limit_mb = max_bytes // (1024 * 1024)
            raise ValidationError(
                f"{media_type} files must be {limit_mb}MB or smaller"
            )

    # Generate a unique R2 key
    asset_id = uuid.uuid4()
    ext = ""
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    r2_key = f"media/{owner_id}/{asset_id}{ext}"

    # Create pending asset record
    asset = MediaAsset(
        id=asset_id,
        cloudflare_r2_key=r2_key,
        media_type=media_type,
        moderation_status="pending",
        owner_id=owner_id,
        content_length=content_length,
    )
    db.add(asset)
    await db.flush()

    upload_url = _generate_upload_url(r2_key)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=UPLOAD_URL_EXPIRY_MINUTES)

    logger.info(
        "upload_url_created",
        media_id=str(asset_id),
        media_type=media_type,
        owner_id=str(owner_id),
    )

    return {
        "upload_url": upload_url,
        "media_id": asset_id,
        "expires_at": expires_at,
    }


async def create_batch_upload_urls(
    db: AsyncSession,
    owner_id: uuid.UUID,
    files: list[dict],
) -> list[dict]:
    """Generate presigned R2 upload URLs for multiple files.

    Args:
        db: Database session.
        owner_id: UUID of the asset owner.
        files: List of dicts with media_type, content_length, filename.

    Returns:
        List of dicts with upload_url, media_id, expires_at per file.

    Raises:
        ValidationError: If batch size exceeds MAX_BATCH_SIZE or any file is invalid.
    """
    if not files:
        raise ValidationError("files list must not be empty")
    if len(files) > MAX_BATCH_SIZE:
        raise ValidationError(f"Batch size must not exceed {MAX_BATCH_SIZE}")

    results = []
    for f in files:
        result = await create_upload_url(
            db,
            owner_id=owner_id,
            media_type=f["media_type"],
            content_length=f.get("content_length"),
            filename=f.get("filename"),
        )
        results.append(result)

    logger.info(
        "batch_upload_urls_created",
        count=len(results),
        owner_id=str(owner_id),
    )
    return results


# ---------------------------------------------------------------------------
# Media registration and retrieval
# ---------------------------------------------------------------------------


async def register_media(
    db: AsyncSession,
    owner_id: uuid.UUID,
    cloudflare_id: str,
    media_type: str,
    r2_key: str | None = None,
) -> MediaAsset:
    """Register a media asset after upload completes.

    Args:
        db: Database session.
        owner_id: UUID of the asset owner.
        cloudflare_id: Cloudflare image/stream ID.
        media_type: "image" or "video".
        r2_key: Optional R2 key.

    Returns:
        The created MediaAsset.
    """
    if media_type not in ("image", "video"):
        raise ValidationError("media_type must be 'image' or 'video'")

    asset = MediaAsset(
        id=uuid.uuid4(),
        cloudflare_r2_key=r2_key,
        cloudflare_image_id=cloudflare_id if media_type == "image" else None,
        cloudflare_stream_id=cloudflare_id if media_type == "video" else None,
        media_type=media_type,
        moderation_status="pending",
        owner_id=owner_id,
    )
    db.add(asset)
    await db.flush()

    logger.info(
        "media_registered",
        media_id=str(asset.id),
        media_type=media_type,
        owner_id=str(owner_id),
    )
    return asset


async def get_media(db: AsyncSession, media_id: uuid.UUID) -> MediaAsset:
    """Get a single media asset by ID.

    Raises:
        NotFoundError: If the asset does not exist.
    """
    result = await db.execute(
        select(MediaAsset).where(MediaAsset.id == media_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise NotFoundError("Media asset", str(media_id))
    return asset


async def list_media(
    db: AsyncSession,
    owner_id: uuid.UUID,
    media_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List media assets belonging to a user.

    Args:
        db: Database session.
        owner_id: UUID of the owner.
        media_type: Optional filter by 'image' or 'video'.
        page: Page number (1-based).
        page_size: Items per page.

    Returns:
        Dict with items, total, page, page_size.
    """
    query = select(MediaAsset).where(MediaAsset.owner_id == owner_id)
    count_query = select(func.count()).select_from(MediaAsset).where(
        MediaAsset.owner_id == owner_id
    )

    if media_type:
        query = query.where(MediaAsset.media_type == media_type)
        count_query = count_query.where(MediaAsset.media_type == media_type)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated items
    offset = (page - 1) * page_size
    query = query.order_by(MediaAsset.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_variants(db: AsyncSession, media_id: uuid.UUID) -> dict | None:
    """Return processed variants (thumbnails, resized versions) for a media asset.

    Raises:
        NotFoundError: If the asset does not exist.
    """
    asset = await get_media(db, media_id)
    return asset.variants


async def get_cached_variants(
    db: AsyncSession, media_id: uuid.UUID, variant: str | None = None,
) -> dict | None:
    """Return variants with LRU caching — check cache before hitting DB.

    Args:
        db: Database session.
        media_id: UUID of the media asset.
        variant: Optional specific variant name to filter.

    Returns:
        Variants dict or None.
    """
    cached = variant_cache.get(media_id, variant)
    if cached is not ...:
        logger.debug("variant_cache_hit", media_id=str(media_id), variant=variant)
        return cached

    # Cache miss — fetch from DB
    logger.debug("variant_cache_miss", media_id=str(media_id), variant=variant)
    asset = await get_media(db, media_id)
    variants = asset.variants

    # If a specific variant was requested, extract it
    result = variants
    if variant and variants and variant in variants:
        result = {variant: variants[variant]}
    elif variant and (not variants or variant not in variants):
        result = None

    variant_cache.put(media_id, result, variant)
    return result


# ---------------------------------------------------------------------------
# Webhook handlers
# ---------------------------------------------------------------------------


async def handle_image_ready(db: AsyncSession, payload: dict) -> MediaAsset:
    """Handle Cloudflare Images webhook — update MediaAsset with image_id and variants.

    Args:
        db: Database session.
        payload: Webhook payload with media_id, image_id, and variants.

    Returns:
        Updated MediaAsset.
    """
    media_id = uuid.UUID(payload["media_id"])
    asset = await get_media(db, media_id)

    asset.cloudflare_image_id = payload.get("image_id")
    asset.variants = payload.get("variants")
    asset.moderation_status = payload.get("moderation_status", "approved")

    # Invalidate cache so next read gets fresh data
    variant_cache.invalidate(media_id)

    await db.flush()
    logger.info("image_ready", media_id=str(media_id))
    return asset


async def handle_video_ready(db: AsyncSession, payload: dict) -> MediaAsset:
    """Handle Cloudflare Stream webhook — update MediaAsset with stream_id.

    Args:
        db: Database session.
        payload: Webhook payload with media_id and stream_id.

    Returns:
        Updated MediaAsset.
    """
    media_id = uuid.UUID(payload["media_id"])
    asset = await get_media(db, media_id)

    asset.cloudflare_stream_id = payload.get("stream_id")
    asset.moderation_status = payload.get("moderation_status", "approved")

    # Invalidate cache
    variant_cache.invalidate(media_id)

    await db.flush()
    logger.info("video_ready", media_id=str(media_id))
    return asset


async def delete_media(
    db: AsyncSession,
    media_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Soft delete a media asset (owner only).

    Args:
        db: Database session.
        media_id: UUID of the asset.
        user_id: UUID of the requesting user.

    Raises:
        NotFoundError: If the asset does not exist.
        ForbiddenError: If the user is not the owner.
    """
    asset = await get_media(db, media_id)
    if asset.owner_id != user_id:
        raise ForbiddenError("You can only delete your own media")

    asset.moderation_status = "deleted"

    # Invalidate cache
    variant_cache.invalidate(media_id)

    await db.flush()

    logger.info(
        "media_deleted",
        media_id=str(media_id),
        user_id=str(user_id),
    )
