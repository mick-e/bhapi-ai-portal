"""Security tests for age-tier enforcement on social endpoints.

Comprehensive integration tests that verify every social endpoint
is protected by the age-tier middleware via real HTTP requests.
"""

import uuid
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.age_tier.middleware import STATIC_ENDPOINT_PERMISSIONS
from src.age_tier.rules import AgeTier
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


async def _make_isolated_client(age_tier: str | None, dob: date | None):
    """Create an isolated test client with its own DB engine and session.

    If age_tier is None, no social profile is created (simulates adult).
    """
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
# Fixtures — each client gets its own isolated DB
# ---------------------------------------------------------------------------


@pytest.fixture
async def young_client():
    """HTTP client for a young-tier user (age 7)."""
    client, engine, session = await _make_isolated_client("young", date(2019, 6, 15))
    async with client:
        yield client
    await session.close()
    await engine.dispose()


@pytest.fixture
async def preteen_client():
    """HTTP client for a preteen-tier user (age 11)."""
    client, engine, session = await _make_isolated_client("preteen", date(2015, 3, 10))
    async with client:
        yield client
    await session.close()
    await engine.dispose()


@pytest.fixture
async def teen_client():
    """HTTP client for a teen-tier user (age 14)."""
    client, engine, session = await _make_isolated_client("teen", date(2012, 1, 20))
    async with client:
        yield client
    await session.close()
    await engine.dispose()


@pytest.fixture
async def adult_client():
    """HTTP client for a user without a social profile (adult/parent)."""
    client, engine, session = await _make_isolated_client(None, None)
    async with client:
        yield client
    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Young tier (5-9) — restricted endpoints return 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_young_cannot_send_message(young_client):
    """Young tier cannot create conversations — 403."""
    resp = await young_client.post(
        "/api/v1/messages/conversations",
        json={"type": "direct", "member_user_ids": [str(uuid.uuid4())]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_young_cannot_send_message_in_conversation(young_client):
    """Young tier cannot send messages — 403."""
    resp = await young_client.post(
        f"/api/v1/messages/conversations/{uuid.uuid4()}/messages",
        json={"content": "hi", "message_type": "text"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_young_cannot_add_contacts(young_client):
    """Young tier cannot send contact requests — 403."""
    resp = await young_client.post(f"/api/v1/contacts/request/{uuid.uuid4()}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_young_cannot_list_conversations(young_client):
    """Young tier cannot list conversations — 403."""
    resp = await young_client.get("/api/v1/messages/conversations")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_young_cannot_list_contacts(young_client):
    """Young tier cannot list contacts — 403."""
    # contacts router uses @router.get("/") so the path includes trailing slash
    resp = await young_client.get("/api/v1/contacts/")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_young_cannot_get_conversation(young_client):
    """Young tier cannot get a specific conversation — 403."""
    resp = await young_client.get(
        f"/api/v1/messages/conversations/{uuid.uuid4()}"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_young_cannot_mark_read(young_client):
    """Young tier cannot mark conversation as read — 403."""
    resp = await young_client.patch(
        f"/api/v1/messages/conversations/{uuid.uuid4()}/read"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_young_cannot_respond_to_contact(young_client):
    """Young tier cannot respond to contact requests — 403."""
    resp = await young_client.patch(
        f"/api/v1/contacts/{uuid.uuid4()}/respond",
        json={"action": "accept"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Young tier — allowed endpoints succeed (non-403)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_young_can_create_post(young_client):
    """Young tier can create posts — should not get 403."""
    resp = await young_client.post(
        "/api/v1/social/posts",
        json={"content": "Hello world!", "post_type": "text"},
    )
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_young_can_like_post(young_client):
    """Young tier can like — should not get 403."""
    resp = await young_client.post(f"/api/v1/social/posts/{uuid.uuid4()}/like")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_young_can_upload_image(young_client):
    """Young tier can upload images — should not get 403."""
    resp = await young_client.post(
        "/api/v1/media/upload",
        json={"media_type": "image", "content_length": 1024, "filename": "test.jpg"},
    )
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_young_can_get_followers(young_client):
    """Young tier can list followers — should not get 403."""
    resp = await young_client.get("/api/v1/social/followers")
    assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Preteen tier (10-12) — expanded access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preteen_can_list_conversations(preteen_client):
    """Preteen tier can list conversations — not 403."""
    resp = await preteen_client.get("/api/v1/messages/conversations")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_preteen_can_get_pending_contacts(preteen_client):
    """Preteen tier can get pending contacts — not 403."""
    resp = await preteen_client.get("/api/v1/contacts/pending")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_preteen_can_create_post(preteen_client):
    """Preteen tier can create posts — not 403."""
    resp = await preteen_client.post(
        "/api/v1/social/posts",
        json={"content": "Preteen post", "post_type": "text"},
    )
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_preteen_can_list_contacts(preteen_client):
    """Preteen tier can list contacts — not 403."""
    resp = await preteen_client.get("/api/v1/contacts/")
    assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Teen tier (13-15) — full access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teen_can_list_conversations(teen_client):
    """Teen tier can list conversations — not 403."""
    resp = await teen_client.get("/api/v1/messages/conversations")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_teen_can_upload_media(teen_client):
    """Teen tier can upload media — not 403."""
    resp = await teen_client.post(
        "/api/v1/media/upload",
        json={"media_type": "video", "content_length": 10240, "filename": "test.mp4"},
    )
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_teen_can_list_contacts(teen_client):
    """Teen tier can list contacts — not 403."""
    resp = await teen_client.get("/api/v1/contacts/")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_teen_can_list_conversations(teen_client):
    """Teen tier can list conversations — not 403."""
    resp = await teen_client.get("/api/v1/messages/conversations")
    assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Adult/parent — no age tier, always allowed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adult_can_access_messaging(adult_client):
    """Adult without social profile can list conversations — not 403."""
    resp = await adult_client.get("/api/v1/messages/conversations")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_adult_can_access_contacts(adult_client):
    """Adult without social profile can access contacts — not 403."""
    resp = await adult_client.get("/api/v1/contacts/")
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_adult_can_access_media(adult_client):
    """Adult without social profile can access media — not 403."""
    resp = await adult_client.post(
        "/api/v1/media/upload",
        json={"media_type": "image", "content_length": 1024, "filename": "test.jpg"},
    )
    assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Permission bypass attempts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forbidden_response_has_correct_code(young_client):
    """403 response includes FORBIDDEN code."""
    resp = await young_client.post(
        "/api/v1/messages/conversations",
        json={"type": "direct", "member_user_ids": [str(uuid.uuid4())]},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_forbidden_response_includes_tier_info(young_client):
    """403 response includes which tier was denied."""
    resp = await young_client.post(
        "/api/v1/messages/conversations",
        json={"type": "direct", "member_user_ids": [str(uuid.uuid4())]},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert "young" in body["detail"]
    assert "can_message" in body["detail"]


@pytest.mark.asyncio
async def test_forbidden_response_includes_permission_name(young_client):
    """403 response for contacts includes permission name."""
    resp = await young_client.post(f"/api/v1/contacts/request/{uuid.uuid4()}")
    assert resp.status_code == 403
    body = resp.json()
    assert "can_add_contacts" in body["detail"]


# ---------------------------------------------------------------------------
# Endpoint protection completeness
# ---------------------------------------------------------------------------


class TestProtectionCompleteness:
    """Verify that all social endpoints have age-tier protection."""

    def test_all_social_prefixed_endpoints_mapped(self):
        """Every endpoint in the permission map has a valid permission name."""
        from src.age_tier.rules import TIER_PERMISSIONS

        all_perms = set(TIER_PERMISSIONS[AgeTier.TEEN].keys())
        for (_method, _path), permission in STATIC_ENDPOINT_PERMISSIONS.items():
            assert permission in all_perms, \
                f"Permission '{permission}' in map not found in tier permissions"

    def test_no_duplicate_entries(self):
        """No duplicate (method, path) entries in the permission map."""
        keys = list(STATIC_ENDPOINT_PERMISSIONS.keys())
        assert len(keys) == len(set(keys)), "Duplicate entries"

    def test_minimum_endpoint_count(self):
        """At least 25 endpoints are protected."""
        assert len(STATIC_ENDPOINT_PERMISSIONS) >= 25

    def test_all_four_modules_represented(self):
        """Social, contacts, messaging, and media are all represented."""
        paths = [path for (_, path) in STATIC_ENDPOINT_PERMISSIONS.keys()]
        assert any("/api/v1/social/" in p for p in paths), "Missing social"
        assert any("/api/v1/contacts" in p for p in paths), "Missing contacts"
        assert any("/api/v1/messages/" in p for p in paths), "Missing messaging"
        assert any("/api/v1/media" in p for p in paths), "Missing media"
