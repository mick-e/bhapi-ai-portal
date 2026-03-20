"""Security tests for the media module."""

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
async def sec_engine():
    """Create a security test engine."""
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
async def sec_session(sec_engine):
    """Create a security test session."""
    async_session_maker = sessionmaker(
        sec_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def sec_users(sec_session):
    """Create test users for security tests."""
    user1 = User(
        id=uuid.uuid4(),
        email=f"secmedia1-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Security Media User 1",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user2 = User(
        id=uuid.uuid4(),
        email=f"secmedia2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Security Media User 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add_all([user1, user2])
    await sec_session.flush()
    return {"user1": user1, "user2": user2}


@pytest_asyncio.fixture
async def unauthed_client(sec_engine, sec_session):
    """HTTP client WITHOUT auth — should get 401."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def user1_client(sec_engine, sec_session, sec_users):
    """HTTP client authenticated as user1."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=sec_users["user1"].id,
            group_id=None,
            role="parent",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


@pytest_asyncio.fixture
async def user2_client(sec_engine, sec_session, sec_users):
    """HTTP client authenticated as user2."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=sec_users["user2"].id,
            group_id=None,
            role="parent",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


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
# Auth required (401) tests
# ---------------------------------------------------------------------------


class TestAuthRequired:
    """Verify all media endpoints require authentication."""

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, unauthed_client):
        resp = await unauthed_client.post("/api/v1/media/upload", json={
            "media_type": "image",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_register_requires_auth(self, unauthed_client):
        resp = await unauthed_client.post("/api/v1/media/register", json={
            "cloudflare_id": "cf-123",
            "media_type": "image",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, unauthed_client):
        resp = await unauthed_client.get("/api/v1/media/")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_requires_auth(self, unauthed_client):
        resp = await unauthed_client.get(f"/api/v1/media/{uuid.uuid4()}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self, unauthed_client):
        resp = await unauthed_client.delete(f"/api/v1/media/{uuid.uuid4()}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_variants_requires_auth(self, unauthed_client):
        resp = await unauthed_client.get(f"/api/v1/media/{uuid.uuid4()}/variants")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authorization (403) tests
# ---------------------------------------------------------------------------


class TestOwnershipEnforcement:
    """Verify ownership checks on destructive operations."""

    @pytest.mark.asyncio
    async def test_cannot_delete_others_media(self, user2_client, sec_session, sec_users):
        asset = await _seed_asset(sec_session, sec_users["user1"].id)
        resp = await user2_client.delete(f"/api/v1/media/{asset.id}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_can_delete_own_media(self, user1_client, sec_session, sec_users):
        asset = await _seed_asset(sec_session, sec_users["user1"].id)
        resp = await user1_client.delete(f"/api/v1/media/{asset.id}")
        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Input validation (422) tests
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Verify input validation rejects bad data."""

    @pytest.mark.asyncio
    async def test_upload_invalid_media_type(self, user1_client):
        resp = await user1_client.post("/api/v1/media/upload", json={
            "media_type": "document",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_empty_cloudflare_id(self, user1_client):
        resp = await user1_client.post("/api/v1/media/register", json={
            "cloudflare_id": "",
            "media_type": "image",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_negative_content_length(self, user1_client):
        resp = await user1_client.post("/api/v1/media/upload", json={
            "media_type": "image",
            "content_length": -1,
        })
        assert resp.status_code == 422
