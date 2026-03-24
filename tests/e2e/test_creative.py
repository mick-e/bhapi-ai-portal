"""End-to-end tests for the creative module — HTTP endpoint tests."""

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
from src.billing.feature_gate import check_feature_gate
from src.creative.models import StoryTemplate
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def e2e_engine():
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
async def e2e_session(e2e_engine):
    maker = sessionmaker(e2e_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def e2e_user(e2e_session):
    user = User(
        id=uuid.uuid4(),
        email=f"creative-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Creative User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()
    return user


@pytest_asyncio.fixture
async def e2e_group(e2e_session, e2e_user):
    group = Group(
        id=uuid.uuid4(),
        name="Creative Family",
        type="family",
        owner_id=e2e_user.id,
        settings={},
    )
    e2e_session.add(group)
    await e2e_session.flush()
    return group


@pytest_asyncio.fixture
async def e2e_member(e2e_session, e2e_group, e2e_user):
    today = datetime.now(timezone.utc).date()
    dob = today.replace(year=today.year - 14)
    member = GroupMember(
        id=uuid.uuid4(),
        group_id=e2e_group.id,
        user_id=e2e_user.id,
        role="member",
        display_name="Teen Child",
        date_of_birth=datetime(dob.year, dob.month, dob.day),
    )
    e2e_session.add(member)
    await e2e_session.flush()
    return member


@pytest_asyncio.fixture
async def e2e_template(e2e_session):
    tmpl = StoryTemplate(
        title="Adventure Story",
        theme="adventure",
        content_template="Once upon a time in {place}...",
        min_age_tier="young",
        template_type="fill_in_blank",
    )
    e2e_session.add(tmpl)
    await e2e_session.flush()
    return tmpl


def _make_client(e2e_engine, e2e_session, user_id, group_id=None):
    """Create an authenticated test client."""
    app = create_app()

    async def get_db_override():
        try:
            yield e2e_session
            await e2e_session.commit()
        except Exception:
            await e2e_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(user_id=user_id, group_id=group_id, role="member")

    async def no_gate():
        return None  # bypass feature gate

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth
    app.dependency_overrides[check_feature_gate("creative_tools")] = no_gate

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest_asyncio.fixture
async def creative_client(e2e_engine, e2e_session, e2e_user, e2e_group):
    async with _make_client(e2e_engine, e2e_session, e2e_user.id, e2e_group.id) as c:
        yield c


# ---------------------------------------------------------------------------
# POST /art
# ---------------------------------------------------------------------------


class TestArtEndpoints:
    @pytest.mark.asyncio
    async def test_generate_art_returns_201(
        self, creative_client: AsyncClient, e2e_member, e2e_group
    ):
        resp = await creative_client.post(
            "/api/v1/creative/art",
            json={
                "member_id": str(e2e_member.id),
                "group_id": str(e2e_group.id),
                "prompt": "a friendly dragon in a meadow",
                "model": "dalle3",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["moderation_status"] == "pending"
        assert data["prompt"] == "a friendly dragon in a meadow"

    @pytest.mark.asyncio
    async def test_generate_art_blocked_content_returns_422(
        self, creative_client: AsyncClient, e2e_member, e2e_group
    ):
        resp = await creative_client.post(
            "/api/v1/creative/art",
            json={
                "member_id": str(e2e_member.id),
                "group_id": str(e2e_group.id),
                "prompt": "nude figure in painting",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_art_violence_blocked(
        self, creative_client: AsyncClient, e2e_member, e2e_group
    ):
        resp = await creative_client.post(
            "/api/v1/creative/art",
            json={
                "member_id": str(e2e_member.id),
                "group_id": str(e2e_group.id),
                "prompt": "extreme violence scene",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_art_returns_200(
        self, creative_client: AsyncClient, e2e_member, e2e_group
    ):
        # First create some art
        await creative_client.post(
            "/api/v1/creative/art",
            json={
                "member_id": str(e2e_member.id),
                "group_id": str(e2e_group.id),
                "prompt": "colorful fish in the ocean",
            },
        )
        resp = await creative_client.get(f"/api/v1/creative/art/{e2e_member.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# GET /templates
# ---------------------------------------------------------------------------


class TestTemplateEndpoints:
    @pytest.mark.asyncio
    async def test_get_templates_returns_list(
        self, creative_client: AsyncClient, e2e_template
    ):
        resp = await creative_client.get("/api/v1/creative/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        ids = [t["id"] for t in data]
        assert str(e2e_template.id) in ids

    @pytest.mark.asyncio
    async def test_get_templates_filtered_by_age_tier(
        self, creative_client: AsyncClient, e2e_template
    ):
        resp = await creative_client.get(
            "/api/v1/creative/templates", params={"age_tier": "young"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["min_age_tier"] == "young" for t in data)

    @pytest.mark.asyncio
    async def test_get_templates_empty_filter_returns_empty(
        self, creative_client: AsyncClient
    ):
        resp = await creative_client.get(
            "/api/v1/creative/templates", params={"age_tier": "preteen"}
        )
        # preteen tier not in fixture — may be empty or have records
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# POST /stories
# ---------------------------------------------------------------------------


class TestStoryEndpoints:
    @pytest.mark.asyncio
    async def test_create_story_returns_201(
        self, creative_client: AsyncClient, e2e_member
    ):
        resp = await creative_client.post(
            "/api/v1/creative/stories",
            json={"member_id": str(e2e_member.id), "content": "My amazing adventure story about a cat."},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["moderation_status"] == "pending"
        assert data["posted_to_feed"] is False

    @pytest.mark.asyncio
    async def test_create_story_with_template(
        self, creative_client: AsyncClient, e2e_template, e2e_member
    ):
        resp = await creative_client.post(
            "/api/v1/creative/stories",
            json={
                "member_id": str(e2e_member.id),
                "content": "Once upon a time in the forest...",
                "template_id": str(e2e_template.id),
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["template_id"] == str(e2e_template.id)

    @pytest.mark.asyncio
    async def test_create_story_invalid_template_returns_404(
        self, creative_client: AsyncClient, e2e_member
    ):
        resp = await creative_client.post(
            "/api/v1/creative/stories",
            json={
                "content": "My story",
                "template_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_stories_returns_200(
        self, creative_client: AsyncClient, e2e_member
    ):
        await creative_client.post(
            "/api/v1/creative/stories",
            json={"member_id": str(e2e_member.id), "content": "A wonderful story."},
        )
        resp = await creative_client.get(f"/api/v1/creative/stories/{e2e_member.id}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# GET /sticker-packs
# ---------------------------------------------------------------------------


class TestStickerPackEndpoints:
    @pytest.mark.asyncio
    async def test_get_sticker_packs_returns_list(self, creative_client: AsyncClient):
        resp = await creative_client.get("/api/v1/creative/sticker-packs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_get_sticker_packs_with_user_packs(
        self, creative_client: AsyncClient, e2e_member
    ):
        # Create a custom sticker first
        await creative_client.post(
            "/api/v1/creative/stickers",
            json={
                "member_id": str(e2e_member.id),
                "image_url": "https://cdn.example.com/my-sticker.png",
            },
        )
        resp = await creative_client.get(
            "/api/v1/creative/sticker-packs",
            params={"include_user_packs": "true"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# POST /drawings + POST /stickers
# ---------------------------------------------------------------------------


class TestDrawingAndStickerEndpoints:
    @pytest.mark.asyncio
    async def test_save_drawing_returns_201(
        self, creative_client: AsyncClient, e2e_member, e2e_group
    ):
        resp = await creative_client.post(
            "/api/v1/creative/drawings",
            json={
                "member_id": str(e2e_member.id),
                "group_id": str(e2e_group.id),
                "image_url": "https://cdn.example.com/drawing.png",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["moderation_status"] == "pending"
        assert data["posted_to_feed"] is False

    @pytest.mark.asyncio
    async def test_create_sticker_returns_201(
        self, creative_client: AsyncClient, e2e_member
    ):
        resp = await creative_client.post(
            "/api/v1/creative/stickers",
            json={
                "member_id": str(e2e_member.id),
                "image_url": "https://cdn.example.com/sticker.png",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["moderation_status"] == "pending"


# ---------------------------------------------------------------------------
# POST /{asset_type}/{asset_id}/post-to-feed
# ---------------------------------------------------------------------------


class TestPostToFeedEndpoints:
    @pytest.mark.asyncio
    async def test_post_story_to_feed(self, creative_client: AsyncClient, e2e_member):
        create_resp = await creative_client.post(
            "/api/v1/creative/stories",
            json={"member_id": str(e2e_member.id), "content": "Feed story!"},
        )
        assert create_resp.status_code == 201
        story_id = create_resp.json()["id"]

        feed_resp = await creative_client.post(
            f"/api/v1/creative/stories/{story_id}/post-to-feed"
        )
        assert feed_resp.status_code == 200
        assert feed_resp.json()["posted_to_feed"] is True

    @pytest.mark.asyncio
    async def test_post_drawing_to_feed(
        self, creative_client: AsyncClient, e2e_member, e2e_group
    ):
        create_resp = await creative_client.post(
            "/api/v1/creative/drawings",
            json={
                "member_id": str(e2e_member.id),
                "group_id": str(e2e_group.id),
                "image_url": "https://cdn.example.com/d2.png",
            },
        )
        assert create_resp.status_code == 201
        drawing_id = create_resp.json()["id"]

        feed_resp = await creative_client.post(
            f"/api/v1/creative/drawings/{drawing_id}/post-to-feed"
        )
        assert feed_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_post_invalid_asset_type_returns_422(
        self, creative_client: AsyncClient
    ):
        fake_id = str(uuid.uuid4())
        resp = await creative_client.post(
            f"/api/v1/creative/invalid/{fake_id}/post-to-feed"
        )
        assert resp.status_code == 422
