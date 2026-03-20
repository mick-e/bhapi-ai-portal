"""End-to-end tests for the media module — HTTP endpoint tests."""

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
        email=f"media-e2e-1-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Media User 1",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user2 = User(
        id=uuid.uuid4(),
        email=f"media-e2e-2-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Media User 2",
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
# Upload URL
# ---------------------------------------------------------------------------


class TestUploadURL:
    """Test POST /api/v1/media/upload."""

    @pytest.mark.asyncio
    async def test_upload_url_image(self, client1):
        resp = await client1.post("/api/v1/media/upload", json={
            "media_type": "image",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "upload_url" in data
        assert "media_id" in data
        assert "expires_at" in data

    @pytest.mark.asyncio
    async def test_upload_url_video(self, client1):
        resp = await client1.post("/api/v1/media/upload", json={
            "media_type": "video",
            "content_length": 5000,
        })
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_url_with_filename(self, client1):
        resp = await client1.post("/api/v1/media/upload", json={
            "media_type": "image",
            "filename": "photo.png",
        })
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_url_invalid_type(self, client1):
        resp = await client1.post("/api/v1/media/upload", json={
            "media_type": "audio",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_url_image_too_large(self, client1):
        resp = await client1.post("/api/v1/media/upload", json={
            "media_type": "image",
            "content_length": 11 * 1024 * 1024,
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Register media
# ---------------------------------------------------------------------------


class TestRegisterMedia:
    """Test POST /api/v1/media/register."""

    @pytest.mark.asyncio
    async def test_register_image(self, client1):
        resp = await client1.post("/api/v1/media/register", json={
            "cloudflare_id": "cf-img-001",
            "media_type": "image",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["cloudflare_image_id"] == "cf-img-001"
        assert data["moderation_status"] == "pending"

    @pytest.mark.asyncio
    async def test_register_video(self, client1):
        resp = await client1.post("/api/v1/media/register", json={
            "cloudflare_id": "cf-vid-001",
            "media_type": "video",
        })
        assert resp.status_code == 201
        assert resp.json()["cloudflare_stream_id"] == "cf-vid-001"


# ---------------------------------------------------------------------------
# Get / List / Variants
# ---------------------------------------------------------------------------


class TestGetAndList:
    """Test GET endpoints."""

    @pytest.mark.asyncio
    async def test_get_media(self, client1, e2e_session, e2e_users):
        asset = await _seed_asset(e2e_session, e2e_users["user1"].id)
        resp = await client1.get(f"/api/v1/media/{asset.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(asset.id)

    @pytest.mark.asyncio
    async def test_get_media_not_found(self, client1):
        resp = await client1.get(f"/api/v1/media/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_media_empty(self, client1):
        resp = await client1.get("/api/v1/media/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_media_with_items(self, client1, e2e_session, e2e_users):
        await _seed_asset(e2e_session, e2e_users["user1"].id, media_type="image")
        await _seed_asset(e2e_session, e2e_users["user1"].id, media_type="video")
        resp = await client1.get("/api/v1/media/")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    @pytest.mark.asyncio
    async def test_list_media_filter_type(self, client1, e2e_session, e2e_users):
        await _seed_asset(e2e_session, e2e_users["user1"].id, media_type="image")
        await _seed_asset(e2e_session, e2e_users["user1"].id, media_type="video")
        resp = await client1.get("/api/v1/media/?media_type=image")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_get_variants(self, client1, e2e_session, e2e_users):
        asset = await _seed_asset(
            e2e_session, e2e_users["user1"].id,
            variants={"thumb": "https://example.com/thumb.jpg"},
        )
        resp = await client1.get(f"/api/v1/media/{asset.id}/variants")
        assert resp.status_code == 200
        data = resp.json()
        assert data["variants"]["thumb"] == "https://example.com/thumb.jpg"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestDeleteMedia:
    """Test DELETE endpoint."""

    @pytest.mark.asyncio
    async def test_delete_own_media(self, client1, e2e_session, e2e_users):
        asset = await _seed_asset(e2e_session, e2e_users["user1"].id)
        resp = await client1.delete(f"/api/v1/media/{asset.id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_others_media_forbidden(self, client2, e2e_session, e2e_users):
        asset = await _seed_asset(e2e_session, e2e_users["user1"].id)
        resp = await client2.delete(f"/api/v1/media/{asset.id}")
        assert resp.status_code == 403
