"""Unit tests for the media module."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.media import service
from src.media.schemas import (
    MediaAssetResponse,
    MediaListResponse,
    RegisterMediaRequest,
    UploadURLRequest,
    UploadURLResponse,
)
from src.moderation.models import MediaAsset
from tests.conftest import make_test_group


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(session: AsyncSession) -> uuid.UUID:
    """Create a test user and return user_id."""
    from src.auth.models import User

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"media-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Media Tester",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()
    return user_id


async def _create_asset(
    session: AsyncSession,
    owner_id: uuid.UUID,
    media_type: str = "image",
    moderation_status: str = "pending",
    **kwargs,
) -> MediaAsset:
    """Create a MediaAsset directly in the DB."""
    asset = MediaAsset(
        id=uuid.uuid4(),
        cloudflare_r2_key=f"media/{owner_id}/{uuid.uuid4()}.jpg",
        media_type=media_type,
        moderation_status=moderation_status,
        owner_id=owner_id,
        **kwargs,
    )
    session.add(asset)
    await session.flush()
    return asset


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestSchemas:
    """Test Pydantic schema validation."""

    def test_upload_url_request_image(self):
        req = UploadURLRequest(media_type="image")
        assert req.media_type == "image"
        assert req.content_length is None

    def test_upload_url_request_video_with_size(self):
        req = UploadURLRequest(media_type="video", content_length=5000, filename="test.mp4")
        assert req.media_type == "video"
        assert req.content_length == 5000

    def test_upload_url_request_invalid_type(self):
        with pytest.raises(Exception):
            UploadURLRequest(media_type="audio")

    def test_register_media_request(self):
        req = RegisterMediaRequest(cloudflare_id="cf-123", media_type="image")
        assert req.cloudflare_id == "cf-123"
        assert req.r2_key is None

    def test_register_media_request_with_r2_key(self):
        req = RegisterMediaRequest(
            cloudflare_id="cf-456",
            media_type="video",
            r2_key="media/user/file.mp4",
        )
        assert req.r2_key == "media/user/file.mp4"

    def test_register_media_request_invalid_type(self):
        with pytest.raises(Exception):
            RegisterMediaRequest(cloudflare_id="cf-123", media_type="document")

    def test_register_media_request_empty_id(self):
        with pytest.raises(Exception):
            RegisterMediaRequest(cloudflare_id="", media_type="image")

    def test_upload_url_response(self):
        from datetime import datetime, timezone

        resp = UploadURLResponse(
            upload_url="https://example.com/upload",
            media_id=uuid.uuid4(),
            expires_at=datetime.now(timezone.utc),
        )
        assert "example.com" in resp.upload_url


# ---------------------------------------------------------------------------
# Service — create_upload_url
# ---------------------------------------------------------------------------


class TestCreateUploadURL:
    """Test service.create_upload_url."""

    @pytest.mark.asyncio
    async def test_create_upload_url_image(self, test_session):
        user_id = await _create_user(test_session)
        result = await service.create_upload_url(test_session, user_id, "image")
        assert "upload_url" in result
        assert "media_id" in result
        assert "expires_at" in result
        assert "r2.example.com" in result["upload_url"]

    @pytest.mark.asyncio
    async def test_create_upload_url_video(self, test_session):
        user_id = await _create_user(test_session)
        result = await service.create_upload_url(test_session, user_id, "video")
        assert result["media_id"] is not None

    @pytest.mark.asyncio
    async def test_create_upload_url_with_filename(self, test_session):
        user_id = await _create_user(test_session)
        result = await service.create_upload_url(
            test_session, user_id, "image", filename="photo.png",
        )
        assert ".png" in result["upload_url"]

    @pytest.mark.asyncio
    async def test_create_upload_url_with_content_length(self, test_session):
        user_id = await _create_user(test_session)
        result = await service.create_upload_url(
            test_session, user_id, "image", content_length=1024,
        )
        assert result["media_id"] is not None

    @pytest.mark.asyncio
    async def test_create_upload_url_image_too_large(self, test_session):
        user_id = await _create_user(test_session)
        from src.exceptions import ValidationError as BhapiValidation

        with pytest.raises(BhapiValidation, match="10MB"):
            await service.create_upload_url(
                test_session, user_id, "image", content_length=11 * 1024 * 1024,
            )

    @pytest.mark.asyncio
    async def test_create_upload_url_video_too_large(self, test_session):
        user_id = await _create_user(test_session)
        from src.exceptions import ValidationError as BhapiValidation

        with pytest.raises(BhapiValidation, match="100MB"):
            await service.create_upload_url(
                test_session, user_id, "video", content_length=101 * 1024 * 1024,
            )

    @pytest.mark.asyncio
    async def test_create_upload_url_invalid_type(self, test_session):
        user_id = await _create_user(test_session)
        from src.exceptions import ValidationError as BhapiValidation

        with pytest.raises(BhapiValidation, match="must be"):
            await service.create_upload_url(test_session, user_id, "audio")


# ---------------------------------------------------------------------------
# Service — register_media
# ---------------------------------------------------------------------------


class TestRegisterMedia:
    """Test service.register_media."""

    @pytest.mark.asyncio
    async def test_register_image(self, test_session):
        user_id = await _create_user(test_session)
        asset = await service.register_media(
            test_session, user_id, "cf-img-123", "image",
        )
        assert asset.cloudflare_image_id == "cf-img-123"
        assert asset.cloudflare_stream_id is None
        assert asset.moderation_status == "pending"

    @pytest.mark.asyncio
    async def test_register_video(self, test_session):
        user_id = await _create_user(test_session)
        asset = await service.register_media(
            test_session, user_id, "cf-vid-456", "video",
        )
        assert asset.cloudflare_stream_id == "cf-vid-456"
        assert asset.cloudflare_image_id is None

    @pytest.mark.asyncio
    async def test_register_with_r2_key(self, test_session):
        user_id = await _create_user(test_session)
        asset = await service.register_media(
            test_session, user_id, "cf-123", "image", r2_key="media/test/file.jpg",
        )
        assert asset.cloudflare_r2_key == "media/test/file.jpg"

    @pytest.mark.asyncio
    async def test_register_invalid_type(self, test_session):
        user_id = await _create_user(test_session)
        from src.exceptions import ValidationError as BhapiValidation

        with pytest.raises(BhapiValidation):
            await service.register_media(test_session, user_id, "cf-123", "audio")


# ---------------------------------------------------------------------------
# Service — get_media / list_media / get_variants
# ---------------------------------------------------------------------------


class TestGetAndListMedia:
    """Test get_media, list_media, get_variants."""

    @pytest.mark.asyncio
    async def test_get_media_found(self, test_session):
        user_id = await _create_user(test_session)
        asset = await _create_asset(test_session, user_id)
        result = await service.get_media(test_session, asset.id)
        assert result.id == asset.id

    @pytest.mark.asyncio
    async def test_get_media_not_found(self, test_session):
        from src.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            await service.get_media(test_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_list_media_empty(self, test_session):
        user_id = await _create_user(test_session)
        result = await service.list_media(test_session, user_id)
        assert result["items"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_media_with_items(self, test_session):
        user_id = await _create_user(test_session)
        await _create_asset(test_session, user_id, media_type="image")
        await _create_asset(test_session, user_id, media_type="video")
        result = await service.list_media(test_session, user_id)
        assert result["total"] == 2
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_media_filter_type(self, test_session):
        user_id = await _create_user(test_session)
        await _create_asset(test_session, user_id, media_type="image")
        await _create_asset(test_session, user_id, media_type="video")
        result = await service.list_media(test_session, user_id, media_type="image")
        assert result["total"] == 1
        assert result["items"][0].media_type == "image"

    @pytest.mark.asyncio
    async def test_list_media_pagination(self, test_session):
        user_id = await _create_user(test_session)
        for _ in range(5):
            await _create_asset(test_session, user_id)
        result = await service.list_media(test_session, user_id, page=1, page_size=2)
        assert result["total"] == 5
        assert len(result["items"]) == 2
        assert result["page"] == 1

    @pytest.mark.asyncio
    async def test_get_variants_none(self, test_session):
        user_id = await _create_user(test_session)
        asset = await _create_asset(test_session, user_id)
        result = await service.get_variants(test_session, asset.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_variants_with_data(self, test_session):
        user_id = await _create_user(test_session)
        variants = {"thumbnail": "url1", "medium": "url2"}
        asset = await _create_asset(test_session, user_id, variants=variants)
        result = await service.get_variants(test_session, asset.id)
        assert result == variants


# ---------------------------------------------------------------------------
# Service — webhooks
# ---------------------------------------------------------------------------


class TestWebhookHandlers:
    """Test webhook handler functions."""

    @pytest.mark.asyncio
    async def test_handle_image_ready(self, test_session):
        user_id = await _create_user(test_session)
        asset = await _create_asset(test_session, user_id)
        payload = {
            "media_id": str(asset.id),
            "image_id": "cf-img-ready",
            "variants": {"thumb": "url"},
            "moderation_status": "approved",
        }
        updated = await service.handle_image_ready(test_session, payload)
        assert updated.cloudflare_image_id == "cf-img-ready"
        assert updated.variants == {"thumb": "url"}
        assert updated.moderation_status == "approved"

    @pytest.mark.asyncio
    async def test_handle_video_ready(self, test_session):
        user_id = await _create_user(test_session)
        asset = await _create_asset(test_session, user_id, media_type="video")
        payload = {
            "media_id": str(asset.id),
            "stream_id": "cf-stream-ready",
        }
        updated = await service.handle_video_ready(test_session, payload)
        assert updated.cloudflare_stream_id == "cf-stream-ready"
        assert updated.moderation_status == "approved"


# ---------------------------------------------------------------------------
# Service — delete_media
# ---------------------------------------------------------------------------


class TestDeleteMedia:
    """Test service.delete_media."""

    @pytest.mark.asyncio
    async def test_delete_own_media(self, test_session):
        user_id = await _create_user(test_session)
        asset = await _create_asset(test_session, user_id)
        await service.delete_media(test_session, asset.id, user_id)
        refreshed = await service.get_media(test_session, asset.id)
        assert refreshed.moderation_status == "deleted"

    @pytest.mark.asyncio
    async def test_delete_others_media_forbidden(self, test_session):
        user_id = await _create_user(test_session)
        other_id = await _create_user(test_session)
        asset = await _create_asset(test_session, user_id)
        from src.exceptions import ForbiddenError

        with pytest.raises(ForbiddenError):
            await service.delete_media(test_session, asset.id, other_id)

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, test_session):
        user_id = await _create_user(test_session)
        from src.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            await service.delete_media(test_session, uuid.uuid4(), user_id)
