"""Unit tests for media variant caching, batch upload, and cache invalidation."""

import time
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.exceptions import NotFoundError, ValidationError
from src.media.service import (
    _VariantCache,
    create_batch_upload_urls,
    get_cached_variants,
    handle_image_ready,
    variant_cache,
)
from src.moderation.models import MediaAsset

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(session: AsyncSession) -> User:
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"media-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Media Tester",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_asset(
    session: AsyncSession,
    owner_id: uuid.UUID,
    media_type: str = "image",
    variants: dict | None = None,
) -> MediaAsset:
    asset = MediaAsset(
        id=uuid.uuid4(),
        cloudflare_r2_key=f"media/{owner_id}/test.jpg",
        media_type=media_type,
        moderation_status="approved",
        owner_id=owner_id,
        variants=variants,
    )
    session.add(asset)
    await session.flush()
    return asset


# ---------------------------------------------------------------------------
# _VariantCache unit tests (pure in-memory, no DB)
# ---------------------------------------------------------------------------


class TestVariantCachePure:
    """Test the LRU cache class in isolation."""

    def test_cache_miss_returns_ellipsis(self):
        cache = _VariantCache()
        assert cache.get(uuid.uuid4()) is ...

    def test_put_and_get(self):
        cache = _VariantCache()
        mid = uuid.uuid4()
        data = {"thumbnail": "https://cdn/thumb.jpg"}
        cache.put(mid, data)
        assert cache.get(mid) == data

    def test_put_specific_variant(self):
        cache = _VariantCache()
        mid = uuid.uuid4()
        cache.put(mid, {"thumbnail": "url"}, variant="thumbnail")
        assert cache.get(mid, variant="thumbnail") == {"thumbnail": "url"}
        # Different variant key is still a miss
        assert cache.get(mid, variant="large") is ...

    def test_invalidate_removes_all_variants(self):
        cache = _VariantCache()
        mid = uuid.uuid4()
        cache.put(mid, {"thumb": "a"}, variant="thumb")
        cache.put(mid, {"large": "b"}, variant="large")
        cache.put(mid, {"thumb": "a", "large": "b"})
        assert cache.size == 3
        cache.invalidate(mid)
        assert cache.size == 0
        assert cache.get(mid) is ...

    def test_clear_removes_everything(self):
        cache = _VariantCache()
        for _ in range(5):
            cache.put(uuid.uuid4(), {"x": "y"})
        assert cache.size == 5
        cache.clear()
        assert cache.size == 0

    def test_lru_eviction(self):
        cache = _VariantCache(max_size=3)
        ids = [uuid.uuid4() for _ in range(4)]
        for mid in ids:
            cache.put(mid, {"v": "url"})
        # First entry should be evicted
        assert cache.get(ids[0]) is ...
        # Last 3 should still be there
        for mid in ids[1:]:
            assert cache.get(mid) == {"v": "url"}

    def test_ttl_expiry(self):
        cache = _VariantCache(ttl=1)
        mid = uuid.uuid4()
        cache.put(mid, {"thumb": "url"})
        assert cache.get(mid) == {"thumb": "url"}
        # Manually expire by patching the stored timestamp
        key = cache._make_key(mid)
        val, _ = cache._store[key]
        cache._store[key] = (val, time.monotonic() - 2)
        assert cache.get(mid) is ...

    def test_cache_none_variants(self):
        """None is a valid cached value (asset has no variants yet)."""
        cache = _VariantCache()
        mid = uuid.uuid4()
        cache.put(mid, None)
        assert cache.get(mid) is None

    def test_move_to_end_on_access(self):
        cache = _VariantCache(max_size=3)
        ids = [uuid.uuid4() for _ in range(3)]
        for mid in ids:
            cache.put(mid, {"v": "url"})
        # Access the first one to move it to end
        cache.get(ids[0])
        # Add a new entry — should evict ids[1], not ids[0]
        new_id = uuid.uuid4()
        cache.put(new_id, {"v": "url"})
        assert cache.get(ids[0]) == {"v": "url"}
        assert cache.get(ids[1]) is ...


# ---------------------------------------------------------------------------
# get_cached_variants — integration with DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cached_variants_miss_then_hit(test_session: AsyncSession):
    """First call reads from DB, second comes from cache."""
    variant_cache.clear()
    user = await _make_user(test_session)
    variants = {
        "thumbnail": "https://cdn/thumb.jpg",
        "medium": "https://cdn/medium.jpg",
        "large": "https://cdn/large.jpg",
    }
    asset = await _make_asset(test_session, user.id, variants=variants)

    # First call — cache miss, reads DB
    result1 = await get_cached_variants(test_session, asset.id)
    assert result1 == variants

    # Second call — should come from cache (we can verify by checking cache state)
    assert variant_cache.get(asset.id) == variants
    result2 = await get_cached_variants(test_session, asset.id)
    assert result2 == variants


@pytest.mark.asyncio
async def test_cached_variants_specific_variant(test_session: AsyncSession):
    """Requesting a specific variant returns only that variant."""
    variant_cache.clear()
    user = await _make_user(test_session)
    variants = {
        "thumbnail": "https://cdn/thumb.jpg",
        "medium": "https://cdn/medium.jpg",
    }
    asset = await _make_asset(test_session, user.id, variants=variants)

    result = await get_cached_variants(test_session, asset.id, variant="thumbnail")
    assert result == {"thumbnail": "https://cdn/thumb.jpg"}


@pytest.mark.asyncio
async def test_cached_variants_missing_variant(test_session: AsyncSession):
    """Requesting a non-existent variant returns None."""
    variant_cache.clear()
    user = await _make_user(test_session)
    variants = {"thumbnail": "https://cdn/thumb.jpg"}
    asset = await _make_asset(test_session, user.id, variants=variants)

    result = await get_cached_variants(test_session, asset.id, variant="nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_cached_variants_none_when_no_variants(test_session: AsyncSession):
    """Asset with no variants returns None and caches it."""
    variant_cache.clear()
    user = await _make_user(test_session)
    asset = await _make_asset(test_session, user.id, variants=None)

    result = await get_cached_variants(test_session, asset.id)
    assert result is None
    # None is cached
    assert variant_cache.get(asset.id) is None


@pytest.mark.asyncio
async def test_cache_invalidated_on_image_ready(test_session: AsyncSession):
    """handle_image_ready invalidates cache for the asset."""
    variant_cache.clear()
    user = await _make_user(test_session)
    asset = await _make_asset(test_session, user.id, variants={"old": "url"})

    # Populate cache
    await get_cached_variants(test_session, asset.id)
    assert variant_cache.get(asset.id) is not ...

    # Simulate webhook with new variants
    new_variants = {
        "thumbnail": "https://cdn/new-thumb.jpg",
        "medium": "https://cdn/new-medium.jpg",
        "large": "https://cdn/new-large.jpg",
    }
    await handle_image_ready(test_session, {
        "media_id": str(asset.id),
        "image_id": "cf-img-123",
        "variants": new_variants,
    })

    # Cache should be invalidated
    assert variant_cache.get(asset.id) is ...

    # Re-fetch should get new variants
    result = await get_cached_variants(test_session, asset.id)
    assert result == new_variants


@pytest.mark.asyncio
async def test_cache_not_found_raises(test_session: AsyncSession):
    """get_cached_variants raises NotFoundError for non-existent asset."""
    variant_cache.clear()
    with pytest.raises(NotFoundError):
        await get_cached_variants(test_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Batch upload URL creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_upload_single_file(test_session: AsyncSession):
    """Batch upload with a single file works."""
    user = await _make_user(test_session)
    files = [{"media_type": "image", "filename": "photo.jpg"}]
    results = await create_batch_upload_urls(test_session, user.id, files)
    assert len(results) == 1
    assert "upload_url" in results[0]
    assert "media_id" in results[0]
    assert "expires_at" in results[0]


@pytest.mark.asyncio
async def test_batch_upload_multiple_files(test_session: AsyncSession):
    """Batch upload with multiple files returns one URL per file."""
    user = await _make_user(test_session)
    files = [
        {"media_type": "image", "filename": "photo1.jpg"},
        {"media_type": "image", "filename": "photo2.png"},
        {"media_type": "video", "filename": "clip.mp4"},
    ]
    results = await create_batch_upload_urls(test_session, user.id, files)
    assert len(results) == 3
    # All media_ids should be unique
    ids = {r["media_id"] for r in results}
    assert len(ids) == 3


@pytest.mark.asyncio
async def test_batch_upload_max_10(test_session: AsyncSession):
    """Batch upload with exactly 10 files succeeds."""
    user = await _make_user(test_session)
    files = [{"media_type": "image", "filename": f"img{i}.jpg"} for i in range(10)]
    results = await create_batch_upload_urls(test_session, user.id, files)
    assert len(results) == 10


@pytest.mark.asyncio
async def test_batch_upload_exceeds_max(test_session: AsyncSession):
    """Batch upload with >10 files raises ValidationError."""
    user = await _make_user(test_session)
    files = [{"media_type": "image"} for _ in range(11)]
    with pytest.raises(ValidationError, match="must not exceed"):
        await create_batch_upload_urls(test_session, user.id, files)


@pytest.mark.asyncio
async def test_batch_upload_empty(test_session: AsyncSession):
    """Batch upload with empty list raises ValidationError."""
    user = await _make_user(test_session)
    with pytest.raises(ValidationError, match="must not be empty"):
        await create_batch_upload_urls(test_session, user.id, [])


@pytest.mark.asyncio
async def test_batch_upload_invalid_type(test_session: AsyncSession):
    """Batch upload with invalid media_type raises ValidationError."""
    user = await _make_user(test_session)
    files = [{"media_type": "audio"}]
    with pytest.raises(ValidationError, match="must be 'image' or 'video'"):
        await create_batch_upload_urls(test_session, user.id, files)


@pytest.mark.asyncio
async def test_batch_upload_mixed_types(test_session: AsyncSession):
    """Batch upload with images and videos works."""
    user = await _make_user(test_session)
    files = [
        {"media_type": "image", "filename": "photo.jpg", "content_length": 1024},
        {"media_type": "video", "filename": "clip.mp4", "content_length": 5000},
    ]
    results = await create_batch_upload_urls(test_session, user.id, files)
    assert len(results) == 2
    for r in results:
        assert r["upload_url"].startswith("https://")


@pytest.mark.asyncio
async def test_batch_upload_size_limit_enforced(test_session: AsyncSession):
    """Batch upload enforces per-file size limits."""
    user = await _make_user(test_session)
    files = [{"media_type": "image", "content_length": 20 * 1024 * 1024}]  # 20MB > 10MB limit
    with pytest.raises(ValidationError, match="10MB"):
        await create_batch_upload_urls(test_session, user.id, files)
