"""End-to-end tests for age-tier UX feature gating.

Tests verify that the age-tier permission matrix is correctly enforced
at the API level for all three tiers (young, preteen, teen), matching
the client-side AgeTierGate component behavior.
"""

import uuid
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.age_tier.rules import TIER_PERMISSIONS, AgeTier, check_permission
from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group
from src.main import create_app
from src.schemas import GroupContext
from src.social.models import Profile

# ---------------------------------------------------------------------------
# Helper to create a full test client with isolated DB
# ---------------------------------------------------------------------------


async def _make_client(age_tier: str | None, dob: date | None):
    """Create an isolated test client with its own DB engine and session."""
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

    session = AsyncSession(engine, expire_on_commit=False)

    user = User(
        id=uuid.uuid4(),
        email=f"{age_tier or 'adult'}-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name=f"{(age_tier or 'adult').title()} User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()

    group = Group(
        id=uuid.uuid4(),
        name=f"Family {age_tier or 'adult'}",
        type="family",
        owner_id=user.id,
    )
    session.add(group)
    await session.flush()

    if age_tier and dob:
        profile = Profile(
            id=uuid.uuid4(),
            user_id=user.id,
            display_name=f"{age_tier.title()} Kid",
            age_tier=age_tier,
            date_of_birth=dob,
            visibility="friends_only",
        )
        session.add(profile)
        await session.flush()

    await session.commit()

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
            user_id=user.id,
            group_id=group.id,
            role="member",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )
    return client, engine, session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def young_client():
    """HTTP client for a young-tier user (age 7)."""
    client, engine, session = await _make_client("young", date(2019, 6, 15))
    async with client:
        yield client
    await session.close()
    await engine.dispose()


@pytest.fixture
async def preteen_client():
    """HTTP client for a preteen-tier user (age 11)."""
    client, engine, session = await _make_client("preteen", date(2015, 3, 10))
    async with client:
        yield client
    await session.close()
    await engine.dispose()


@pytest.fixture
async def teen_client():
    """HTTP client for a teen-tier user (age 14)."""
    client, engine, session = await _make_client("teen", date(2012, 1, 20))
    async with client:
        yield client
    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Young tier (5-9) — messaging, contacts, search all blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_young_cannot_access_messaging(young_client):
    """Young user cannot access messaging endpoint — 403."""
    resp = await young_client.get("/api/v1/messages/conversations")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_young_cannot_create_conversation(young_client):
    """Young user cannot create a conversation — 403."""
    resp = await young_client.post(
        "/api/v1/messages/conversations",
        json={"type": "direct", "member_user_ids": [str(uuid.uuid4())]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_young_cannot_search_users():
    """Young user search_users is denied in the permission matrix."""
    assert check_permission(AgeTier.YOUNG, "can_search_users") is False


@pytest.mark.asyncio
async def test_young_cannot_add_contacts(young_client):
    """Young user cannot send contact requests — 403."""
    resp = await young_client.post(
        f"/api/v1/contacts/request/{uuid.uuid4()}"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_young_can_post(young_client):
    """Young user CAN access feed (can_post is true) — not 403."""
    resp = await young_client.get("/api/v1/social/feed")
    # May be 200 or other non-403 (empty feed is fine)
    assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Preteen tier (10-12) — messaging OK, video upload blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preteen_can_access_messaging(preteen_client):
    """Preteen can access messaging — not 403."""
    resp = await preteen_client.get("/api/v1/messages/conversations")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_preteen_can_search_users(preteen_client):
    """Preteen can search users — not 403."""
    resp = await preteen_client.get("/api/v1/social/search?q=test")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_preteen_cannot_upload_video(preteen_client):
    """Preteen cannot upload video — permission matrix says false."""
    # Verify via the rules engine directly (media upload endpoint
    # maps to can_upload_image which preteens CAN do, but
    # can_upload_video is the gating permission for video content).
    assert check_permission(AgeTier.PRETEEN, "can_upload_video") is False


@pytest.mark.asyncio
async def test_preteen_cannot_create_group_chat(preteen_client):
    """Preteen cannot create group chat — permission denied."""
    assert check_permission(AgeTier.PRETEEN, "can_create_group_chat") is False


# ---------------------------------------------------------------------------
# Teen tier (13-15) — all social features accessible
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teen_can_access_messaging(teen_client):
    """Teen can access messaging — not 403."""
    resp = await teen_client.get("/api/v1/messages/conversations")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_teen_can_search_users(teen_client):
    """Teen can search users — not 403."""
    resp = await teen_client.get("/api/v1/social/search?q=test")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_teen_can_add_contacts():
    """Teen has can_add_contacts permission."""
    assert check_permission(AgeTier.TEEN, "can_add_contacts") is True


@pytest.mark.asyncio
async def test_teen_can_upload_video():
    """Teen has can_upload_video permission."""
    assert check_permission(AgeTier.TEEN, "can_upload_video") is True


@pytest.mark.asyncio
async def test_teen_can_create_group_chat():
    """Teen has can_create_group_chat permission."""
    assert check_permission(AgeTier.TEEN, "can_create_group_chat") is True


# ---------------------------------------------------------------------------
# Permission matrix consistency checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_permission_matrix_young_messaging_denied():
    """Young tier messaging is denied in the permission matrix."""
    assert TIER_PERMISSIONS[AgeTier.YOUNG]["can_message"] is False


@pytest.mark.asyncio
async def test_permission_matrix_preteen_messaging_allowed():
    """Preteen tier messaging is allowed in the permission matrix."""
    assert TIER_PERMISSIONS[AgeTier.PRETEEN]["can_message"] is True


@pytest.mark.asyncio
async def test_permission_matrix_young_search_denied():
    """Young tier search is denied."""
    assert TIER_PERMISSIONS[AgeTier.YOUNG]["can_search_users"] is False


@pytest.mark.asyncio
async def test_permission_matrix_young_contacts_denied():
    """Young tier add-contacts is denied."""
    assert TIER_PERMISSIONS[AgeTier.YOUNG]["can_add_contacts"] is False


@pytest.mark.asyncio
async def test_permission_matrix_all_tiers_can_post():
    """All tiers can create posts."""
    for tier in AgeTier:
        assert TIER_PERMISSIONS[tier]["can_post"] is True


@pytest.mark.asyncio
async def test_permission_matrix_location_denied_all():
    """Location sharing is denied for all child tiers."""
    for tier in AgeTier:
        assert TIER_PERMISSIONS[tier]["can_share_location"] is False


# ---------------------------------------------------------------------------
# Unlock request endpoint (age-tier check permission API)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_age_tier_check_permission_api(young_client):
    """The age-tier permission check endpoint returns correct result.

    This is the API that supports the "Ask parent to unlock" flow.
    """
    # The age-tier API itself is not behind age-tier enforcement.
    # We need to test that the check endpoint works for the UX.
    # Since we don't have a member_id-based fixture here, we verify
    # the permission check function directly.
    assert check_permission(AgeTier.YOUNG, "can_message") is False
    assert check_permission(AgeTier.YOUNG, "can_post") is True
    assert check_permission(AgeTier.PRETEEN, "can_message") is True
    assert check_permission(AgeTier.TEEN, "can_upload_video") is True
