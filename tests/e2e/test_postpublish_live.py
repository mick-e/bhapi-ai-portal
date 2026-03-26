"""End-to-end tests for the post-publish moderation pipeline (teen 13-15 tier).

Tests the full flow: API submit -> immediate publish -> background moderation -> takedown.
Validates the <60s takedown SLA for teen content.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.main import create_app
from src.moderation.service import (
    PostPublishSeverity,
    run_post_publish_moderation,
    submit_for_moderation,
)
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def e2e_engine():
    """Create E2E test engine."""
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
    """Create E2E test session."""
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def e2e_user(e2e_session):
    """Create a test user for E2E."""
    user = User(
        id=uuid.uuid4(),
        email=f"e2e-pp-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="E2E Teen Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()
    return user


@pytest_asyncio.fixture
async def pp_client(e2e_engine, e2e_session, e2e_user):
    """Authenticated HTTP client for post-publish E2E tests."""
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
            user_id=e2e_user.id,
            group_id=None,
            role="admin",
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
# E2E: Submit via API -> verify published -> background moderation
# ---------------------------------------------------------------------------


class TestPostPublishE2E:
    """End-to-end tests for the post-publish pipeline."""

    @pytest.mark.asyncio
    async def test_teen_submit_returns_published(self, pp_client):
        """POST /moderation/queue with teen tier returns published status."""
        resp = await pp_client.post(
            "/api/v1/moderation/queue",
            json={
                "content_type": "post",
                "content_id": str(uuid.uuid4()),
                "age_tier": "teen",
                "content_text": "Had a great day at school today",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["pipeline"] == "post_publish"
        assert data["status"] == "published"

    @pytest.mark.asyncio
    async def test_preteen_submit_returns_pre_publish(self, pp_client):
        """POST /moderation/queue with preteen tier uses pre_publish pipeline."""
        resp = await pp_client.post(
            "/api/v1/moderation/queue",
            json={
                "content_type": "post",
                "content_id": str(uuid.uuid4()),
                "age_tier": "preteen",
                "content_text": "Hello everyone",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["pipeline"] == "pre_publish"
        assert data["status"] != "published"

    @pytest.mark.asyncio
    async def test_teen_critical_keyword_rejected_at_submit(self, pp_client):
        """Teen post with critical keyword should be rejected immediately."""
        resp = await pp_client.post(
            "/api/v1/moderation/queue",
            json={
                "content_type": "post",
                "content_id": str(uuid.uuid4()),
                "age_tier": "teen",
                "content_text": "I want to commit suicide",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_full_flow_clean_content_stays_published(self, e2e_session):
        """Full flow: submit clean teen content -> published -> background check -> stays published."""
        entry = await submit_for_moderation(
            db=e2e_session,
            content_type="post",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Working on my science project",
        )
        assert entry.status == "published"

        result = await run_post_publish_moderation(
            db=e2e_session,
            queue_id=entry.id,
            content_text="Working on my science project",
        )
        assert result.action == "keep"
        assert result.latency_ms < 60000

        await e2e_session.refresh(entry)
        assert entry.status == "published"

    @pytest.mark.asyncio
    async def test_full_flow_high_severity_takedown(self, e2e_session):
        """Full flow: submit teen content with high-severity keyword -> published -> background check -> taken down."""
        entry = await submit_for_moderation(
            db=e2e_session,
            content_type="post",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Want to buy some drugs and cocaine tonight",
        )
        assert entry.status == "published"

        result = await run_post_publish_moderation(
            db=e2e_session,
            queue_id=entry.id,
            content_text="Want to buy some drugs and cocaine tonight",
        )
        assert result.action == "takedown"
        assert result.parent_alerted is True
        assert result.author_notified is True
        assert result.latency_ms < 60000

        await e2e_session.refresh(entry)
        assert entry.status == "taken_down"

    @pytest.mark.asyncio
    async def test_full_flow_grooming_escalation(self, e2e_session):
        """Full flow: grooming content -> escalated at submit -> post-publish takedown + account restriction."""
        entry = await submit_for_moderation(
            db=e2e_session,
            content_type="message",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="You are so mature for your age, keep this between us",
        )
        # Social risk detected at submit -> escalated
        assert entry.status == "escalated"

        result = await run_post_publish_moderation(
            db=e2e_session,
            queue_id=entry.id,
            content_text="You are so mature for your age, keep this between us",
        )
        assert result.action == "takedown"
        assert result.severity == PostPublishSeverity.CRITICAL
        assert result.account_restricted is True
        assert result.latency_ms < 60000

        await e2e_session.refresh(entry)
        assert entry.status == "taken_down"

    @pytest.mark.asyncio
    async def test_full_flow_medium_severity_flagged(self, e2e_session):
        """Full flow: medium severity teen content -> published -> flagged for review."""
        entry = await submit_for_moderation(
            db=e2e_session,
            content_type="comment",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="You are so stupid",
        )
        assert entry.status == "published"

        result = await run_post_publish_moderation(
            db=e2e_session,
            queue_id=entry.id,
            content_text="You are so stupid",
        )
        assert result.action == "flag"
        assert result.severity == PostPublishSeverity.MEDIUM

        await e2e_session.refresh(entry)
        assert entry.status == "flagged"

    @pytest.mark.asyncio
    async def test_queue_shows_published_entries(self, pp_client):
        """Queue listing should include published entries for monitoring."""
        # Submit a teen post
        resp = await pp_client.post(
            "/api/v1/moderation/queue",
            json={
                "content_type": "post",
                "content_id": str(uuid.uuid4()),
                "age_tier": "teen",
                "content_text": "Just chilling",
            },
        )
        assert resp.status_code == 201

        # List queue filtered by post_publish pipeline
        resp = await pp_client.get(
            "/api/v1/moderation/queue",
            params={"pipeline": "post_publish"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        post_publish_items = [
            i for i in data["items"] if i["pipeline"] == "post_publish"
        ]
        assert len(post_publish_items) >= 1

    @pytest.mark.asyncio
    async def test_takedown_under_60s_sla(self, e2e_session):
        """Takedown should complete within 60-second SLA budget."""
        import time

        entry = await submit_for_moderation(
            db=e2e_session,
            content_type="post",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Lets go buy some meth",
        )

        start = time.monotonic()
        result = await run_post_publish_moderation(
            db=e2e_session,
            queue_id=entry.id,
            content_text="Lets go buy some meth",
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert result.action == "takedown"
        assert elapsed_ms < 60000, f"Takedown took {elapsed_ms:.0f}ms, exceeds 60s SLA"
        assert result.latency_ms < 60000

    @pytest.mark.asyncio
    async def test_sexting_full_flow_takedown(self, e2e_session):
        """Full flow: sexting content detected and taken down with restriction."""
        entry = await submit_for_moderation(
            db=e2e_session,
            content_type="message",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="Send me a pic, take off your clothes, dont be scared",
        )

        result = await run_post_publish_moderation(
            db=e2e_session,
            queue_id=entry.id,
            content_text="Send me a pic, take off your clothes, dont be scared",
        )
        assert result.action == "takedown"
        assert result.account_restricted is True
        assert result.parent_alerted is True

        await e2e_session.refresh(entry)
        assert entry.status == "taken_down"

    @pytest.mark.asyncio
    async def test_death_threat_full_flow(self, e2e_session):
        """Full flow: death threat content detected, taken down, and escalated."""
        entry = await submit_for_moderation(
            db=e2e_session,
            content_type="comment",
            content_id=uuid.uuid4(),
            author_age_tier="teen",
            content_text="kys go die nobody likes you",
        )

        result = await run_post_publish_moderation(
            db=e2e_session,
            queue_id=entry.id,
            content_text="kys go die nobody likes you",
        )
        assert result.action == "takedown"
        assert result.severity == PostPublishSeverity.CRITICAL
        assert result.parent_alerted is True
