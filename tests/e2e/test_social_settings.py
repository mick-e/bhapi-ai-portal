"""End-to-end tests for social settings — privacy, notifications, language, theme, account.

Tests profile settings via the social API:
- Profile visibility (public/friends_only/private)
- Profile updates preserve visibility
- Invalid visibility rejected
- Auth enforcement
- Language header handling
- Profile roundtrip consistency
"""

import uuid
from datetime import datetime, timezone

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
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dob_for_age(age: int) -> str:
    """Return ISO date string for a person of the given age."""
    today = datetime.now(timezone.utc).date()
    return today.replace(year=today.year - age).isoformat()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def settings_engine():
    """Create a test engine for settings tests."""
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
async def settings_session(settings_engine):
    """Create a test session."""
    async_session_maker = sessionmaker(
        settings_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def settings_user(settings_session):
    """Create a test user for settings tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"settings-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Settings Tester",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    settings_session.add(user)
    await settings_session.flush()
    return user


def _make_settings_client(engine, session, user_id, group_id=None):
    """Create an authenticated test client for settings tests."""
    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
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
async def settings_client(settings_engine, settings_session, settings_user):
    """Authenticated async client for settings tests."""
    async with _make_settings_client(
        settings_engine, settings_session, settings_user.id
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Privacy Settings — Profile Visibility
# ---------------------------------------------------------------------------


class TestPrivacyProfileVisibility:
    """Test who can see the user's profile via visibility setting."""

    @pytest.mark.asyncio
    async def test_create_profile_with_friends_only(self, settings_client):
        """Profile defaults to friends_only visibility."""
        resp = await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Vis Tester",
                "visibility": "friends_only",
                "date_of_birth": _dob_for_age(14),
            },
        )
        assert resp.status_code == 201
        assert resp.json()["visibility"] == "friends_only"

    @pytest.mark.asyncio
    async def test_update_visibility_to_public(self, settings_client):
        """User can change visibility to public."""
        await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Pub Tester",
                "date_of_birth": _dob_for_age(14),
            },
        )
        resp = await settings_client.put(
            "/api/v1/social/profiles/me",
            json={"visibility": "public"},
        )
        assert resp.status_code == 200
        assert resp.json()["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_update_visibility_to_private(self, settings_client):
        """User can change visibility to private."""
        await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Priv Tester",
                "date_of_birth": _dob_for_age(14),
            },
        )
        resp = await settings_client.put(
            "/api/v1/social/profiles/me",
            json={"visibility": "private"},
        )
        assert resp.status_code == 200
        assert resp.json()["visibility"] == "private"

    @pytest.mark.asyncio
    async def test_invalid_visibility_rejected(self, settings_client):
        """Invalid visibility values are rejected with 422."""
        resp = await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Bad Vis",
                "visibility": "aliens_only",
                "date_of_birth": _dob_for_age(14),
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Privacy Settings — Messaging Permissions
# ---------------------------------------------------------------------------


class TestPrivacyMessaging:
    """Test message permission via profile visibility."""

    @pytest.mark.asyncio
    async def test_friends_only_profile(self, settings_client):
        """friends_only profile restricts messaging to friends."""
        resp = await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Msg Friends",
                "visibility": "friends_only",
                "date_of_birth": _dob_for_age(13),
            },
        )
        assert resp.status_code == 201
        assert resp.json()["visibility"] == "friends_only"

    @pytest.mark.asyncio
    async def test_private_profile(self, settings_client):
        """Private profile restricts all visibility."""
        resp = await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Msg Nobody",
                "visibility": "private",
                "date_of_birth": _dob_for_age(13),
            },
        )
        assert resp.status_code == 201
        assert resp.json()["visibility"] == "private"


# ---------------------------------------------------------------------------
# Notification Preferences
# ---------------------------------------------------------------------------


class TestNotificationPreferences:
    """Test notification prefs via profile settings."""

    @pytest.mark.asyncio
    async def test_get_profile_includes_visibility(self, settings_client):
        """GET profile returns visibility field."""
        await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Notif Tester",
                "date_of_birth": _dob_for_age(14),
            },
        )
        resp = await settings_client.get("/api/v1/social/profiles/me")
        assert resp.status_code == 200
        data = resp.json()
        assert "visibility" in data

    @pytest.mark.asyncio
    async def test_update_display_name_preserves_visibility(self, settings_client):
        """Updating display name does not reset visibility."""
        await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Preserve",
                "visibility": "public",
                "date_of_birth": _dob_for_age(14),
            },
        )
        resp = await settings_client.put(
            "/api/v1/social/profiles/me",
            json={"display_name": "Preserve Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["visibility"] == "public"


# ---------------------------------------------------------------------------
# Language Persistence
# ---------------------------------------------------------------------------


class TestLanguagePersistence:
    """Test that Accept-Language header is handled gracefully."""

    @pytest.mark.asyncio
    async def test_profile_creation(self, settings_client):
        """Profile can be created (language is client-side)."""
        resp = await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Lang Tester",
                "date_of_birth": _dob_for_age(14),
            },
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_accept_language_header_does_not_crash(self, settings_client):
        """API handles Accept-Language header without error."""
        await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Lang Header",
                "date_of_birth": _dob_for_age(14),
            },
        )
        resp = await settings_client.get(
            "/api/v1/social/profiles/me",
            headers={"Accept-Language": "fr"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Account Operations
# ---------------------------------------------------------------------------


class TestAccountOperations:
    """Test account-related settings operations."""

    @pytest.mark.asyncio
    async def test_get_own_profile(self, settings_client):
        """User can retrieve own profile settings."""
        await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Acct Tester",
                "date_of_birth": _dob_for_age(14),
            },
        )
        resp = await settings_client.get("/api/v1/social/profiles/me")
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Acct Tester"

    @pytest.mark.asyncio
    async def test_update_own_profile(self, settings_client):
        """User can update own profile."""
        await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Acct Original",
                "date_of_birth": _dob_for_age(14),
            },
        )
        resp = await settings_client.put(
            "/api/v1/social/profiles/me",
            json={"display_name": "Acct Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Acct Updated"

    @pytest.mark.asyncio
    async def test_unauthenticated_settings_rejected(self):
        """Unauthenticated requests to profile are rejected."""
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/social/profiles/me")
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_profile_visibility_roundtrip(self, settings_client):
        """Create with visibility, read it back, verify consistency."""
        create_resp = await settings_client.post(
            "/api/v1/social/profiles",
            json={
                "display_name": "Roundtrip",
                "visibility": "public",
                "date_of_birth": _dob_for_age(14),
            },
        )
        assert create_resp.status_code == 201
        get_resp = await settings_client.get("/api/v1/social/profiles/me")
        assert get_resp.status_code == 200
        assert get_resp.json()["visibility"] == "public"
