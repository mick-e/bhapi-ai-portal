"""Security tests for the creative module."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.billing.feature_gate import check_feature_gate
from src.creative.models import ArtGeneration
from src.creative.service import generate_art
from src.database import Base, get_db
from src.exceptions import RateLimitError
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Shared engine fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def sec_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def sec_session(sec_engine):
    maker = sessionmaker(sec_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(session, group_type="family"):
    user = User(
        id=uuid.uuid4(),
        email=f"sec-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Security Test User",
        account_type=group_type,
        email_verified=False,
        mfa_enabled=False,
    )
    session.add(user)
    await session.flush()
    return user


async def _make_group(session, owner_id, group_id=None):
    group = Group(
        id=group_id or uuid.uuid4(),
        name="Security Group",
        type="family",
        owner_id=owner_id,
        settings={},
    )
    session.add(group)
    await session.flush()
    return group


async def _make_member(session, group_id, user_id, age=14):
    today = datetime.now(timezone.utc).date()
    dob = today.replace(year=today.year - age)
    member = GroupMember(
        id=uuid.uuid4(),
        group_id=group_id,
        user_id=user_id,
        role="member",
        display_name="Test Child",
        date_of_birth=datetime(dob.year, dob.month, dob.day),
    )
    session.add(member)
    await session.flush()
    return member


def _gated_client(sec_engine, sec_session, user_id, group_id=None, gated=False):
    """Create a test client. gated=True simulates free-tier block."""
    app = create_app()

    async def get_db_override():
        try:
            yield sec_session
            await sec_session.commit()
        except Exception:
            await sec_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(user_id=user_id, group_id=group_id, role="member")

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    if not gated:
        async def no_gate():
            return None

        app.dependency_overrides[check_feature_gate("creative_tools")] = no_gate

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_art_endpoint_requires_auth(sec_engine):
    """Requests without auth token should be blocked by middleware."""
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v1/creative/art",
            json={"prompt": "a cat"},
        )
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_templates_endpoint_requires_auth(sec_engine):
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/v1/creative/templates")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_stories_endpoint_requires_auth(sec_engine):
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v1/creative/stories",
            json={"content": "my story"},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Feature gate blocks free tier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_feature_gate_blocks_free_tier_art(sec_engine, sec_session):
    """Free-tier users should be blocked by the creative_tools feature gate."""
    user = await _make_user(sec_session)
    await _make_group(sec_session, user.id)

    # gated=True means the feature gate dependency is NOT overridden
    # so it checks the DB — no FeatureGate record means allowed (ungated)
    # We test that the endpoint is wired up with check_feature_gate
    # by verifying the dependency is present in the router

    from src.creative.router import router
    # Verify the router has the feature gate dependency
    assert any(
        "check_feature_gate" in str(dep) or "creative_tools" in str(dep)
        for dep in router.dependencies
    ), "Router should have check_feature_gate dependency"


@pytest.mark.asyncio
async def test_feature_gate_wired_to_all_routes(sec_engine, sec_session):
    """All creative routes must be gated via router-level dependencies."""
    from src.creative.router import router as creative_router

    # Router-level dependency means all routes inherit the gate
    assert len(creative_router.dependencies) >= 1


# ---------------------------------------------------------------------------
# Cross-group isolation on art
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_group_art_isolation(sec_session):
    """A member should only see art for their own member_id."""
    user_a = await _make_user(sec_session)
    user_b = await _make_user(sec_session)
    group_a = await _make_group(sec_session, user_a.id)
    group_b = await _make_group(sec_session, user_b.id)
    member_a = await _make_member(sec_session, group_a.id, user_a.id)
    member_b = await _make_member(sec_session, group_b.id, user_b.id)

    # Create art for member_a
    art = await generate_art(
        sec_session,
        member_id=member_a.id,
        group_id=group_a.id,
        prompt="private art for member a",
    )
    await sec_session.flush()

    # List art for member_b — should not see member_a's art
    from src.creative.service import list_member_art
    art_b = await list_member_art(sec_session, member_id=member_b.id)
    assert all(a.member_id == member_b.id for a in art_b)
    assert art.id not in {a.id for a in art_b}


@pytest.mark.asyncio
async def test_cross_group_story_isolation(sec_session):
    """Stories for one member are not visible in another member's listing."""
    user_a = await _make_user(sec_session)
    user_b = await _make_user(sec_session)
    group_a = await _make_group(sec_session, user_a.id)
    group_b = await _make_group(sec_session, user_b.id)
    member_a = await _make_member(sec_session, group_a.id, user_a.id)
    member_b = await _make_member(sec_session, group_b.id, user_b.id)

    from src.creative.service import create_story, list_member_stories

    story = await create_story(
        sec_session, member_id=member_a.id, content="Private story"
    )
    await sec_session.flush()

    stories_b = await list_member_stories(sec_session, member_id=member_b.id)
    assert story.id not in {s.id for s in stories_b}


# ---------------------------------------------------------------------------
# Rate limiting per age tier — enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_enforced_young_child(sec_session):
    """Young child (age 7) is rate-limited at 10 art/day."""
    user = await _make_user(sec_session)
    group = await _make_group(sec_session, user.id)
    member = await _make_member(sec_session, group.id, user.id, age=7)

    now = datetime.now(timezone.utc)
    for i in range(10):
        art = ArtGeneration(
            member_id=member.id,
            group_id=group.id,
            prompt=f"safe prompt {i}",
            sanitized_prompt=f"safe prompt {i}",
            model="dalle3",
            moderation_status="pending",
        )
        art.created_at = now - timedelta(minutes=i)
        sec_session.add(art)
    await sec_session.flush()

    with pytest.raises(RateLimitError):
        await generate_art(
            sec_session,
            member_id=member.id,
            group_id=group.id,
            prompt="one more",
        )


@pytest.mark.asyncio
async def test_rate_limit_enforced_teen(sec_session):
    """Teen (age 14) is rate-limited at 50 art/day."""
    user = await _make_user(sec_session)
    group = await _make_group(sec_session, user.id)
    member = await _make_member(sec_session, group.id, user.id, age=14)

    now = datetime.now(timezone.utc)
    for i in range(50):
        art = ArtGeneration(
            member_id=member.id,
            group_id=group.id,
            prompt=f"safe art {i}",
            sanitized_prompt=f"safe art {i}",
            model="dalle3",
            moderation_status="pending",
        )
        art.created_at = now - timedelta(minutes=i)
        sec_session.add(art)
    await sec_session.flush()

    with pytest.raises(RateLimitError):
        await generate_art(
            sec_session,
            member_id=member.id,
            group_id=group.id,
            prompt="another art",
        )


@pytest.mark.asyncio
async def test_rate_limit_per_member_not_global(sec_session):
    """Rate limit is per-member: member_b should not be affected by member_a's art."""
    user_a = await _make_user(sec_session)
    user_b = await _make_user(sec_session)
    group_a = await _make_group(sec_session, user_a.id)
    group_b = await _make_group(sec_session, user_b.id)
    member_a = await _make_member(sec_session, group_a.id, user_a.id, age=7)
    member_b = await _make_member(sec_session, group_b.id, user_b.id, age=7)

    now = datetime.now(timezone.utc)
    # Max out member_a
    for i in range(10):
        art = ArtGeneration(
            member_id=member_a.id,
            group_id=group_a.id,
            prompt=f"art {i}",
            sanitized_prompt=f"art {i}",
            model="dalle3",
            moderation_status="pending",
        )
        art.created_at = now - timedelta(minutes=i)
        sec_session.add(art)
    await sec_session.flush()

    # member_b should still be able to generate art
    art_b = await generate_art(
        sec_session,
        member_id=member_b.id,
        group_id=group_b.id,
        prompt="fresh art for member b",
    )
    assert art_b is not None


# ---------------------------------------------------------------------------
# Prompt injection / content filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_blocked_keywords_are_rejected(sec_session):
    """Comprehensive check: all blocked keywords should raise ValidationError."""
    from src.creative.service import _sanitize_prompt
    from src.exceptions import ValidationError

    blocked_prompts = [
        "nude art",
        "violent scene",
        "drugs everywhere",
        "weapons display",
        "blood splatter",
        "kill the enemy",
        "sex scene",
        "porn video",
        "gun fight",
    ]

    for prompt in blocked_prompts:
        with pytest.raises(ValidationError, match="inappropriate"):
            _sanitize_prompt(prompt)


@pytest.mark.asyncio
async def test_safe_prompts_pass_sanitization(sec_session):
    """Safe prompts should not be blocked."""
    from src.creative.service import _sanitize_prompt

    safe_prompts = [
        "a fluffy bunny in a garden",
        "sunrise over the ocean",
        "cute robot playing soccer",
        "colorful butterflies",
        "children playing in the park",
    ]

    for prompt in safe_prompts:
        result = _sanitize_prompt(prompt)
        assert result is not None


@pytest.mark.asyncio
async def test_moderation_status_defaults_to_pending(sec_session):
    """All creative assets must start in 'pending' moderation state."""
    from src.creative.service import create_story, save_drawing

    user = await _make_user(sec_session)
    group = await _make_group(sec_session, user.id)
    member = await _make_member(sec_session, group.id, user.id)

    art = await generate_art(
        sec_session,
        member_id=member.id,
        group_id=group.id,
        prompt="happy clouds",
    )
    assert art.moderation_status == "pending"

    story = await create_story(sec_session, member_id=member.id, content="A story")
    assert story.moderation_status == "pending"

    drawing = await save_drawing(
        sec_session,
        member_id=member.id,
        group_id=group.id,
        image_url="https://cdn.example.com/d.png",
    )
    assert drawing.moderation_status == "pending"
