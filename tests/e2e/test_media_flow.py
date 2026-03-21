"""End-to-end tests for media flow — upload, webhook, variants, caching, batch, transcode."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.main import create_app
from src.media.service import variant_cache
from src.moderation.models import MediaAsset
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def e2e_engine():
    """Create an E2E test engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def e2e_session(e2e_engine):
    """Create an E2E test session."""
    async_session_maker = sessionmaker(
        e2e_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def e2e_users(e2e_session):
    """Create test users."""
    user1 = User(
        id=uuid.uuid4(),
        email=f"flow-e2e-1-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Flow User 1",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user2 = User(
        id=uuid.uuid4(),
        email=f"flow-e2e-2-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Flow User 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add_all([user1, user2])
    await e2e_session.flush()
    return {"user1": user1, "user2": user2}


def _make_client(e2e_engine, e2e_session, user_id, group_id=None):
    """Create an authenticated test client for a specific user."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=user_id,
            group_id=group_id,
            role="parent",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest_asyncio.fixture
async def client1(e2e_engine, e2e_session, e2e_users):
    """Authenticated client as user1."""
    async with _make_client(e2e_engine, e2e_session, e2e_users["user1"].id) as c:
        yield c


@pytest_asyncio.fixture
async def client2(e2e_engine, e2e_session, e2e_users):
    """Authenticated client as user2."""
    async with _make_client(e2e_engine, e2e_session, e2e_users["user2"].id) as c:
        yield c


@pytest_asyncio.fixture(autouse=True)
async def clear_cache():
    """Clear variant cache before each test."""
    variant_cache.clear()
    yield
    variant_cache.clear()


async def _seed_asset(session, owner_id, media_type="image", **kwargs):
    """Seed a media asset directly in the DB."""
    asset = MediaAsset(
        id=uuid.uuid4(),
        cloudflare_r2_key=f"media/{owner_id}/{uuid.uuid4()}.jpg",
        media_type=media_type,
        moderation_status="pending",
        owner_id=owner_id,
        **kwargs,
    )
    session.add(asset)
    await session.flush()
    return asset


# ---------------------------------------------------------------------------
# Full flow: upload URL → simulate upload → webhook → variants → cache
# ---------------------------------------------------------------------------


class TestFullImageFlow:
    """Full image upload flow from request to cached variants."""

    @pytest.mark.asyncio
    async def test_image_upload_webhook_variants_cache(self, client1, e2e_session, e2e_users):
        """Full flow: request upload URL -> upload -> webhook -> variants available -> cached URL."""
        # 1. Request upload URL
        resp = await client1.post("/api/v1/media/upload", json={
            "media_type": "image",
            "filename": "family-photo.jpg",
            "content_length": 2048,
        })
        assert resp.status_code == 201
        upload_data = resp.json()
        media_id = upload_data["media_id"]
        assert upload_data["upload_url"].startswith("https://r2.example.com/upload/")

        # 2. Simulate Cloudflare webhook with image variants
        asset = await e2e_session.get(MediaAsset, uuid.UUID(media_id))
        assert asset is not None
        assert asset.moderation_status == "pending"

        # Simulate webhook updating the asset
        asset.cloudflare_image_id = "cf-img-abc123"
        asset.variants = {
            "thumbnail": "https://cdn.bhapi.ai/thumb/abc123.jpg",
            "medium": "https://cdn.bhapi.ai/medium/abc123.jpg",
            "large": "https://cdn.bhapi.ai/large/abc123.jpg",
        }
        asset.moderation_status = "approved"
        await e2e_session.flush()

        # 3. Fetch variants — first call
        resp = await client1.get(f"/api/v1/media/{media_id}/variants")
        assert resp.status_code == 200
        data = resp.json()
        assert data["variants"]["thumbnail"] == "https://cdn.bhapi.ai/thumb/abc123.jpg"
        assert data["variants"]["medium"] == "https://cdn.bhapi.ai/medium/abc123.jpg"
        assert data["variants"]["large"] == "https://cdn.bhapi.ai/large/abc123.jpg"

        # 4. Verify Cache-Control header
        assert "Cache-Control" in resp.headers
        assert "max-age=300" in resp.headers["Cache-Control"]

        # 5. Second fetch — should be cached
        resp2 = await client1.get(f"/api/v1/media/{media_id}/variants")
        assert resp2.status_code == 200
        assert resp2.json()["variants"] == data["variants"]

    @pytest.mark.asyncio
    async def test_image_resize_variants_thumbnail(self, client1, e2e_session, e2e_users):
        """Verify thumbnail variant is accessible."""
        asset = await _seed_asset(
            e2e_session, e2e_users["user1"].id,
            variants={
                "thumbnail": "https://cdn.bhapi.ai/thumb/t1.jpg",
                "medium": "https://cdn.bhapi.ai/medium/t1.jpg",
                "large": "https://cdn.bhapi.ai/large/t1.jpg",
            },
        )
        resp = await client1.get(f"/api/v1/media/{asset.id}/variants?variant=thumbnail")
        assert resp.status_code == 200
        data = resp.json()
        assert data["variants"] == {"thumbnail": "https://cdn.bhapi.ai/thumb/t1.jpg"}

    @pytest.mark.asyncio
    async def test_image_resize_variants_medium(self, client1, e2e_session, e2e_users):
        """Verify medium variant is accessible."""
        asset = await _seed_asset(
            e2e_session, e2e_users["user1"].id,
            variants={
                "thumbnail": "https://cdn.bhapi.ai/thumb/m1.jpg",
                "medium": "https://cdn.bhapi.ai/medium/m1.jpg",
                "large": "https://cdn.bhapi.ai/large/m1.jpg",
            },
        )
        resp = await client1.get(f"/api/v1/media/{asset.id}/variants?variant=medium")
        assert resp.status_code == 200
        assert "medium" in resp.json()["variants"]

    @pytest.mark.asyncio
    async def test_image_resize_variants_large(self, client1, e2e_session, e2e_users):
        """Verify large variant is accessible."""
        asset = await _seed_asset(
            e2e_session, e2e_users["user1"].id,
            variants={
                "thumbnail": "https://cdn.bhapi.ai/thumb/l1.jpg",
                "medium": "https://cdn.bhapi.ai/medium/l1.jpg",
                "large": "https://cdn.bhapi.ai/large/l1.jpg",
            },
        )
        resp = await client1.get(f"/api/v1/media/{asset.id}/variants?variant=large")
        assert resp.status_code == 200
        assert "large" in resp.json()["variants"]


# ---------------------------------------------------------------------------
# Video transcode flow
# ---------------------------------------------------------------------------


class TestVideoTranscodeFlow:
    """Video upload and transcode status polling."""

    @pytest.mark.asyncio
    async def test_video_upload_then_transcode_ready(self, client1, e2e_session, e2e_users):
        """Upload video, simulate transcode webhook, verify status."""
        # 1. Request upload URL for video
        resp = await client1.post("/api/v1/media/upload", json={
            "media_type": "video",
            "filename": "family-clip.mp4",
            "content_length": 5_000_000,
        })
        assert resp.status_code == 201
        media_id = resp.json()["media_id"]

        # 2. Asset starts as pending
        resp = await client1.get(f"/api/v1/media/{media_id}")
        assert resp.status_code == 200
        assert resp.json()["moderation_status"] == "pending"

        # 3. Simulate Cloudflare Stream webhook
        asset = await e2e_session.get(MediaAsset, uuid.UUID(media_id))
        asset.cloudflare_stream_id = "cf-stream-xyz"
        asset.moderation_status = "approved"
        await e2e_session.flush()

        # 4. Poll status — now approved
        resp = await client1.get(f"/api/v1/media/{media_id}")
        assert resp.status_code == 200
        assert resp.json()["moderation_status"] == "approved"
        assert resp.json()["cloudflare_stream_id"] == "cf-stream-xyz"

    @pytest.mark.asyncio
    async def test_video_pending_while_transcoding(self, client1, e2e_session, e2e_users):
        """Video remains pending until transcode webhook arrives."""
        resp = await client1.post("/api/v1/media/upload", json={
            "media_type": "video",
            "filename": "long-video.mp4",
        })
        assert resp.status_code == 201
        media_id = resp.json()["media_id"]

        resp = await client1.get(f"/api/v1/media/{media_id}")
        assert resp.status_code == 200
        assert resp.json()["moderation_status"] == "pending"
        assert resp.json()["cloudflare_stream_id"] is None

    @pytest.mark.asyncio
    async def test_video_size_limit(self, client1):
        """Videos over 100MB are rejected."""
        resp = await client1.post("/api/v1/media/upload", json={
            "media_type": "video",
            "content_length": 101 * 1024 * 1024,
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Batch upload
# ---------------------------------------------------------------------------


class TestBatchUpload:
    """Test POST /api/v1/media/upload/batch."""

    @pytest.mark.asyncio
    async def test_batch_upload_single(self, client1):
        resp = await client1.post("/api/v1/media/upload/batch", json={
            "files": [{"media_type": "image", "filename": "pic.jpg"}],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["uploads"]) == 1
        assert "upload_url" in data["uploads"][0]

    @pytest.mark.asyncio
    async def test_batch_upload_multiple(self, client1):
        resp = await client1.post("/api/v1/media/upload/batch", json={
            "files": [
                {"media_type": "image", "filename": "a.jpg"},
                {"media_type": "image", "filename": "b.png"},
                {"media_type": "video", "filename": "c.mp4"},
            ],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["uploads"]) == 3
        ids = {u["media_id"] for u in data["uploads"]}
        assert len(ids) == 3

    @pytest.mark.asyncio
    async def test_batch_upload_max_10(self, client1):
        files = [{"media_type": "image", "filename": f"img{i}.jpg"} for i in range(10)]
        resp = await client1.post("/api/v1/media/upload/batch", json={"files": files})
        assert resp.status_code == 201
        assert len(resp.json()["uploads"]) == 10

    @pytest.mark.asyncio
    async def test_batch_upload_exceeds_limit(self, client1):
        files = [{"media_type": "image"} for _ in range(11)]
        resp = await client1.post("/api/v1/media/upload/batch", json={"files": files})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_batch_upload_empty(self, client1):
        resp = await client1.post("/api/v1/media/upload/batch", json={"files": []})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_batch_upload_invalid_type(self, client1):
        resp = await client1.post("/api/v1/media/upload/batch", json={
            "files": [{"media_type": "audio"}],
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_batch_upload_with_sizes(self, client1):
        resp = await client1.post("/api/v1/media/upload/batch", json={
            "files": [
                {"media_type": "image", "content_length": 1024, "filename": "small.jpg"},
                {"media_type": "video", "content_length": 50_000_000, "filename": "vid.mp4"},
            ],
        })
        assert resp.status_code == 201
        assert len(resp.json()["uploads"]) == 2


# ---------------------------------------------------------------------------
# Cache headers and variant caching via HTTP
# ---------------------------------------------------------------------------


class TestCacheHeaders:
    """Verify Cache-Control headers on variant responses."""

    @pytest.mark.asyncio
    async def test_variants_cache_control_header(self, client1, e2e_session, e2e_users):
        asset = await _seed_asset(
            e2e_session, e2e_users["user1"].id,
            variants={"thumb": "https://cdn/thumb.jpg"},
        )
        resp = await client1.get(f"/api/v1/media/{asset.id}/variants")
        assert resp.status_code == 200
        assert "Cache-Control" in resp.headers
        cc = resp.headers["Cache-Control"]
        assert "public" in cc
        assert "max-age=300" in cc
        assert "stale-while-revalidate=60" in cc

    @pytest.mark.asyncio
    async def test_variants_not_found_returns_404(self, client1):
        resp = await client1.get(f"/api/v1/media/{uuid.uuid4()}/variants")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_variants_null_when_no_processing(self, client1, e2e_session, e2e_users):
        """Asset with no variants yet returns null variants."""
        asset = await _seed_asset(e2e_session, e2e_users["user1"].id, variants=None)
        resp = await client1.get(f"/api/v1/media/{asset.id}/variants")
        assert resp.status_code == 200
        assert resp.json()["variants"] is None

    @pytest.mark.asyncio
    async def test_variant_filter_param(self, client1, e2e_session, e2e_users):
        """Variant query parameter filters to specific variant."""
        asset = await _seed_asset(
            e2e_session, e2e_users["user1"].id,
            variants={
                "thumbnail": "https://cdn/thumb.jpg",
                "large": "https://cdn/large.jpg",
            },
        )
        resp = await client1.get(f"/api/v1/media/{asset.id}/variants?variant=thumbnail")
        assert resp.status_code == 200
        data = resp.json()
        assert data["variants"] == {"thumbnail": "https://cdn/thumb.jpg"}

    @pytest.mark.asyncio
    async def test_variant_filter_nonexistent(self, client1, e2e_session, e2e_users):
        """Non-existent variant filter returns null."""
        asset = await _seed_asset(
            e2e_session, e2e_users["user1"].id,
            variants={"thumbnail": "url"},
        )
        resp = await client1.get(f"/api/v1/media/{asset.id}/variants?variant=hd")
        assert resp.status_code == 200
        assert resp.json()["variants"] is None


# ---------------------------------------------------------------------------
# Delete invalidates cache
# ---------------------------------------------------------------------------


class TestDeleteInvalidatesCache:
    """Verify deleting an asset invalidates the variant cache."""

    @pytest.mark.asyncio
    async def test_delete_clears_cached_variants(self, client1, e2e_session, e2e_users):
        asset = await _seed_asset(
            e2e_session, e2e_users["user1"].id,
            variants={"thumb": "url"},
        )
        # Populate cache via variants endpoint
        resp = await client1.get(f"/api/v1/media/{asset.id}/variants")
        assert resp.status_code == 200
        assert variant_cache.get(asset.id) is not ...

        # Delete the asset
        resp = await client1.delete(f"/api/v1/media/{asset.id}")
        assert resp.status_code == 204

        # Cache should be invalidated
        assert variant_cache.get(asset.id) is ...
