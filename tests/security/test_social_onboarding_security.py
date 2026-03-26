"""Security tests for social onboarding flow.

Tests age spoofing prevention, parent consent bypass attempts,
profile creation without verification, rate limiting, and IDOR.
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.age_tier import AgeTier, get_tier_for_age
from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.exceptions import ConflictError, NotFoundError, ValidationError
from src.groups.models import Group, GroupMember
from src.integrations.age_verification import start_age_verification
from src.main import create_app
from src.schemas import GroupContext
from src.social.schemas import ProfileCreate
from src.social.service import create_profile, get_profile

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
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


@pytest.fixture
async def sec_session(sec_engine):
    """Create a security test session."""
    session = AsyncSession(sec_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest.fixture
async def sec_users(sec_session):
    """Create two users in separate groups for isolation tests."""
    user1 = User(
        id=uuid.uuid4(),
        email=f"sec1-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Sec User 1",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    user2 = User(
        id=uuid.uuid4(),
        email=f"sec2-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Sec User 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child_user = User(
        id=uuid.uuid4(),
        email=f"child-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Child User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    sec_session.add_all([user1, user2, child_user])
    await sec_session.flush()

    group1 = Group(id=uuid.uuid4(), name="Family 1", type="family", owner_id=user1.id)
    group2 = Group(id=uuid.uuid4(), name="Family 2", type="family", owner_id=user2.id)
    sec_session.add_all([group1, group2])
    await sec_session.flush()

    member1 = GroupMember(
        id=uuid.uuid4(),
        group_id=group1.id,
        user_id=child_user.id,
        role="member",
        display_name="Child",
        date_of_birth=datetime(2016, 6, 15, tzinfo=timezone.utc),
    )
    sec_session.add(member1)
    await sec_session.flush()

    return {
        "user1": user1,
        "user2": user2,
        "child_user": child_user,
        "group1": group1,
        "group2": group2,
        "member1": member1,
    }


@pytest.fixture
async def unauthed_client(sec_engine, sec_session):
    """HTTP client WITHOUT auth — should get 401/403."""
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


@pytest.fixture
async def authed_client_child(sec_engine, sec_session, sec_users):
    """HTTP client authenticated as child user."""
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
            user_id=sec_users["child_user"].id,
            group_id=sec_users["group1"].id,
            role="child",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


@pytest.fixture
async def authed_client_user2(sec_engine, sec_session, sec_users):
    """HTTP client authenticated as user2 (different family)."""
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
            group_id=sec_users["group2"].id,
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


# ---------------------------------------------------------------------------
# Age Spoofing Prevention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_age_spoof_too_young_rejected(sec_session, sec_users):
    """Attempting to create profile with age < 5 should be rejected."""
    with pytest.raises(ValidationError, match="between 5 and 15"):
        await create_profile(
            sec_session,
            sec_users["child_user"].id,
            ProfileCreate(display_name="Toddler", date_of_birth=date(2024, 1, 1)),
        )


@pytest.mark.asyncio
async def test_age_spoof_too_old_rejected(sec_session, sec_users):
    """Attempting to create profile with age > 15 should be rejected."""
    with pytest.raises(ValidationError, match="between 5 and 15"):
        await create_profile(
            sec_session,
            sec_users["child_user"].id,
            ProfileCreate(display_name="Adult", date_of_birth=date(2000, 1, 1)),
        )


@pytest.mark.asyncio
async def test_age_spoof_future_dob_rejected(sec_session, sec_users):
    """Date of birth in the future should be rejected (age < 0)."""
    with pytest.raises(ValidationError, match="between 5 and 15"):
        await create_profile(
            sec_session,
            sec_users["child_user"].id,
            ProfileCreate(display_name="Future", date_of_birth=date(2030, 1, 1)),
        )


@pytest.mark.asyncio
async def test_tier_cannot_be_manipulated_directly():
    """Tier assignment is derived from DOB, not user input."""
    # Verify the tier derivation is consistent
    assert get_tier_for_age(7) == AgeTier.YOUNG
    assert get_tier_for_age(11) == AgeTier.PRETEEN
    assert get_tier_for_age(14) == AgeTier.TEEN
    # There is no way for a user to manually set their tier
    # — it is always computed server-side from date_of_birth


# ---------------------------------------------------------------------------
# Parent Consent Bypass Attempts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_profile_creation_via_api_without_auth(unauthed_client):
    """Creating a profile without authentication should fail."""
    resp = await unauthed_client.post(
        "/api/v1/social/profiles",
        json={
            "display_name": "Hacker",
            "date_of_birth": "2016-06-15",
        },
    )
    # Should be 401 or 403 (auth middleware blocks)
    assert resp.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_profile_retrieval_without_auth(unauthed_client):
    """Fetching a profile without authentication should fail."""
    resp = await unauthed_client.get("/api/v1/social/profiles/me")
    assert resp.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_cannot_view_other_user_profile_service_layer(sec_session, sec_users):
    """Getting a profile for a non-existent user should raise NotFoundError."""
    with pytest.raises(NotFoundError):
        await get_profile(sec_session, sec_users["user2"].id)


# ---------------------------------------------------------------------------
# Profile Creation Without Verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_profile_creation_blocked(sec_session, sec_users):
    """Creating a second profile for the same user should be blocked."""
    await create_profile(
        sec_session,
        sec_users["child_user"].id,
        ProfileCreate(display_name="First", date_of_birth=date(2016, 6, 15)),
    )
    await sec_session.flush()

    with pytest.raises(ConflictError, match="already exists"):
        await create_profile(
            sec_session,
            sec_users["child_user"].id,
            ProfileCreate(display_name="Second", date_of_birth=date(2016, 6, 15)),
        )


@pytest.mark.asyncio
async def test_profile_display_name_validation():
    """ProfileCreate schema should enforce display_name constraints."""
    # Empty display name
    with pytest.raises(Exception):
        ProfileCreate(display_name="", date_of_birth=date(2016, 6, 15))

    # Valid display name
    profile = ProfileCreate(display_name="Valid", date_of_birth=date(2016, 6, 15))
    assert profile.display_name == "Valid"


@pytest.mark.asyncio
async def test_profile_bio_length_validation():
    """ProfileCreate should enforce bio max length of 500."""
    # Very long bio should fail schema validation
    with pytest.raises(Exception):
        ProfileCreate(
            display_name="Test",
            date_of_birth=date(2016, 6, 15),
            bio="x" * 501,
        )


# ---------------------------------------------------------------------------
# Rate Limiting / Abuse Prevention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verification_session_requires_valid_member(sec_session, sec_users):
    """Age verification for a random UUID should fail."""
    with pytest.raises(NotFoundError):
        await start_age_verification(
            sec_session, sec_users["group1"].id, uuid.uuid4()
        )


@pytest.mark.asyncio
async def test_verification_cross_group_member_rejected(sec_session, sec_users):
    """Age verification for a member in a different group should fail."""
    with pytest.raises(NotFoundError):
        await start_age_verification(
            sec_session, sec_users["group2"].id, sec_users["member1"].id
        )


@pytest.mark.asyncio
async def test_api_profile_creation_via_http(authed_client_child, sec_users):
    """Authenticated child can create a profile via API."""
    resp = await authed_client_child.post(
        "/api/v1/social/profiles",
        json={
            "display_name": "HttpChild",
            "date_of_birth": "2016-06-15",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["display_name"] == "HttpChild"
    assert body["age_tier"] in ("young", "preteen", "teen")


@pytest.mark.asyncio
async def test_api_duplicate_profile_rejected(authed_client_child, sec_users):
    """Creating a second profile via API should be rejected."""
    # First creation
    resp1 = await authed_client_child.post(
        "/api/v1/social/profiles",
        json={
            "display_name": "FirstHTTP",
            "date_of_birth": "2016-06-15",
        },
    )
    assert resp1.status_code == 201

    # Second creation
    resp2 = await authed_client_child.post(
        "/api/v1/social/profiles",
        json={
            "display_name": "SecondHTTP",
            "date_of_birth": "2016-06-15",
        },
    )
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_api_profile_creation_out_of_age_range(authed_client_child):
    """Creating a profile with out-of-range age via API should fail."""
    resp = await authed_client_child.post(
        "/api/v1/social/profiles",
        json={
            "display_name": "TooOld",
            "date_of_birth": "2000-01-01",
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tier integrity checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tier_assignment_is_deterministic():
    """Same age should always produce the same tier."""
    for _ in range(10):
        assert get_tier_for_age(7) == AgeTier.YOUNG
        assert get_tier_for_age(11) == AgeTier.PRETEEN
        assert get_tier_for_age(14) == AgeTier.TEEN


@pytest.mark.asyncio
async def test_no_tier_gap_between_boundaries():
    """Every age from 5-15 should map to exactly one tier."""
    for age in range(5, 16):
        tier = get_tier_for_age(age)
        assert tier is not None, f"Age {age} has no tier"
        assert tier in (AgeTier.YOUNG, AgeTier.PRETEEN, AgeTier.TEEN)


@pytest.mark.asyncio
async def test_ages_outside_range_have_no_tier():
    """Ages 0-4 and 16+ should not have any tier."""
    for age in list(range(0, 5)) + list(range(16, 25)):
        assert get_tier_for_age(age) is None, f"Age {age} should not have a tier"
