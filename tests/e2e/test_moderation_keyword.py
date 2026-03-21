"""End-to-end tests for keyword filter integration with the moderation API."""

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
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def kw_engine():
    """Create E2E test engine for keyword filter tests."""
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
async def kw_session(kw_engine):
    """Create E2E test session."""
    session = AsyncSession(kw_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def kw_user(kw_session):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email=f"kw-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="KW Tester",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    kw_session.add(user)
    await kw_session.flush()
    return user


@pytest_asyncio.fixture
async def kw_client(kw_engine, kw_session, kw_user):
    """Authenticated HTTP client with admin role."""
    app = create_app()

    async def get_db_override():
        try:
            yield kw_session
            await kw_session.commit()
        except Exception:
            await kw_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=kw_user.id,
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
# Helpers
# ---------------------------------------------------------------------------


async def submit(client, content_text=None, age_tier=None, content_type="post"):
    """Submit content to moderation queue."""
    payload = {
        "content_type": content_type,
        "content_id": str(uuid.uuid4()),
    }
    if age_tier:
        payload["age_tier"] = age_tier
    if content_text is not None:
        payload["content_text"] = content_text
    return await client.post("/api/v1/moderation/queue", json=payload)


# ---------------------------------------------------------------------------
# Critical keyword → auto-block
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_critical_keyword_auto_blocks(kw_client):
    """Content with critical keyword is auto-rejected."""
    resp = await submit(kw_client, content_text="I am considering suicide")
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "rejected"


@pytest.mark.asyncio
async def test_critical_phrase_auto_blocks(kw_client):
    """Multi-word critical phrase triggers auto-reject."""
    resp = await submit(kw_client, content_text="I want to kill myself")
    assert resp.status_code == 201
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_critical_risk_scores_populated(kw_client):
    """risk_scores contains keyword_filter data on critical match."""
    resp = await submit(kw_client, content_text="csam found here")
    assert resp.status_code == 201
    body = resp.json()
    scores = body["risk_scores"]
    assert scores is not None
    kf = scores["keyword_filter"]
    assert kf["action"] == "block"
    assert kf["severity"] == "critical"
    assert kf["confidence"] == 0.95
    assert len(kf["matched_keywords"]) > 0


@pytest.mark.asyncio
async def test_critical_creates_auto_decision(kw_client):
    """Critical keyword creates auto-reject decision (queue is rejected)."""
    resp = await submit(kw_client, content_text="nude children found")
    assert resp.status_code == 201
    queue_id = resp.json()["id"]

    # The entry should already be rejected, so trying to decide again fails
    decide_resp = await kw_client.patch(
        f"/api/v1/moderation/queue/{queue_id}/decide",
        json={"action": "approve"},
    )
    assert decide_resp.status_code == 409  # Already processed


# ---------------------------------------------------------------------------
# Clean text → auto-approve (pre-publish) or pending (post-publish)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clean_text_pre_publish_approved(kw_client):
    """Clean text in pre-publish pipeline is auto-approved."""
    resp = await submit(
        kw_client,
        content_text="I had a great day at school",
        age_tier="young",  # young -> pre_publish
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "approved"
    assert body["pipeline"] == "pre_publish"


@pytest.mark.asyncio
async def test_clean_text_post_publish_published(kw_client):
    """Clean text in post-publish pipeline is published immediately (teen tier)."""
    resp = await submit(
        kw_client,
        content_text="I had a great day at school",
        age_tier="teen",  # teen -> post_publish
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "published"
    assert body["pipeline"] == "post_publish"


@pytest.mark.asyncio
async def test_no_text_stays_pending(kw_client):
    """Submission without content_text stays pending."""
    resp = await submit(kw_client, content_text=None, age_tier="young")
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["risk_scores"] is None


@pytest.mark.asyncio
async def test_clean_text_risk_scores_show_allow(kw_client):
    """Clean text populates risk_scores with allow action."""
    resp = await submit(
        kw_client,
        content_text="Everything is wonderful today",
        age_tier="preteen",
    )
    assert resp.status_code == 201
    body = resp.json()
    kf = body["risk_scores"]["keyword_filter"]
    assert kf["action"] == "allow"
    assert kf["severity"] is None
    assert kf["matched_keywords"] == []


# ---------------------------------------------------------------------------
# Uncertain text → stays pending
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_uncertain_text_teen_published(kw_client):
    """High-severity keyword for teen is published (post-publish pipeline)."""
    resp = await submit(
        kw_client,
        content_text="someone offered me drugs",
        age_tier="teen",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "published"
    kf = body["risk_scores"]["keyword_filter"]
    assert kf["action"] == "uncertain"


@pytest.mark.asyncio
async def test_medium_young_uncertain_pending(kw_client):
    """Medium keyword for young child stays pending (UNCERTAIN)."""
    resp = await submit(
        kw_client,
        content_text="you are so stupid",
        age_tier="young",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    kf = body["risk_scores"]["keyword_filter"]
    assert kf["action"] == "uncertain"
    assert kf["severity"] == "medium"


@pytest.mark.asyncio
async def test_uncertain_allows_manual_decision(kw_client):
    """Uncertain entries can still be manually approved/rejected."""
    resp = await submit(
        kw_client,
        content_text="someone sent a threat",
        age_tier="teen",
    )
    assert resp.status_code == 201
    queue_id = resp.json()["id"]

    decide_resp = await kw_client.patch(
        f"/api/v1/moderation/queue/{queue_id}/decide",
        json={"action": "approve", "reason": "Context was educational"},
    )
    assert decide_resp.status_code == 200
    assert decide_resp.json()["action"] == "approve"


# ---------------------------------------------------------------------------
# High severity + young → auto-block
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_high_keyword_young_auto_blocks(kw_client):
    """High keyword for young child triggers auto-block."""
    resp = await submit(
        kw_client,
        content_text="I found a weapon at school",
        age_tier="young",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "rejected"
    kf = body["risk_scores"]["keyword_filter"]
    assert kf["action"] == "block"
    assert kf["severity"] == "high"


# ---------------------------------------------------------------------------
# Medium for teen → auto-approve in pre-publish
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_medium_teen_post_publish_published(kw_client):
    """Medium keyword for teen in post-publish is published immediately."""
    resp = await submit(
        kw_client,
        content_text="that test was dumb",
        age_tier="teen",
    )
    assert resp.status_code == 201
    body = resp.json()
    # Teen -> post_publish, published immediately (background moderation pending)
    assert body["status"] == "published"


# ---------------------------------------------------------------------------
# Verify risk_scores structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_risk_scores_structure(kw_client):
    """risk_scores has correct structure for keyword filter results."""
    resp = await submit(
        kw_client,
        content_text="someone said bully things",
        age_tier="preteen",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "risk_scores" in body
    kf = body["risk_scores"]["keyword_filter"]
    assert "action" in kf
    assert "severity" in kf
    assert "confidence" in kf
    assert "matched_keywords" in kf
    assert isinstance(kf["matched_keywords"], list)
    assert isinstance(kf["confidence"], float)


# ---------------------------------------------------------------------------
# Content types
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_keyword_filter_with_comment(kw_client):
    """Keyword filter works on comment content type."""
    resp = await submit(
        kw_client,
        content_text="suicide is a serious topic",
        content_type="comment",
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_keyword_filter_with_message(kw_client):
    """Keyword filter works on message content type."""
    resp = await submit(
        kw_client,
        content_text="do you know about drugs",
        content_type="message",
    )
    assert resp.status_code == 201
    body = resp.json()
    kf = body["risk_scores"]["keyword_filter"]
    assert kf["action"] == "uncertain"


# ---------------------------------------------------------------------------
# Verify auto-decision prevents re-processing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_approved_cannot_be_re_decided(kw_client):
    """Auto-approved entry cannot be decided again."""
    resp = await submit(
        kw_client,
        content_text="I love reading books",
        age_tier="young",  # pre_publish + clean -> approved
    )
    assert resp.status_code == 201
    queue_id = resp.json()["id"]
    assert resp.json()["status"] == "approved"

    decide_resp = await kw_client.patch(
        f"/api/v1/moderation/queue/{queue_id}/decide",
        json={"action": "reject"},
    )
    assert decide_resp.status_code == 409


@pytest.mark.asyncio
async def test_queue_entry_retrievable_after_auto_block(kw_client):
    """Auto-blocked entry can be retrieved via GET."""
    resp = await submit(kw_client, content_text="csam detected")
    assert resp.status_code == 201
    queue_id = resp.json()["id"]

    get_resp = await kw_client.get(f"/api/v1/moderation/queue/{queue_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "rejected"
    assert get_resp.json()["risk_scores"]["keyword_filter"]["action"] == "block"


@pytest.mark.asyncio
async def test_queue_list_shows_auto_rejected(kw_client):
    """Auto-rejected entries appear in queue list with status=rejected filter."""
    await submit(kw_client, content_text="suicide note")
    await submit(kw_client, content_text="nice day at school")

    resp = await kw_client.get("/api/v1/moderation/queue?status=rejected")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["status"] == "rejected"


@pytest.mark.asyncio
async def test_empty_text_no_risk_scores(kw_client):
    """Empty content_text results in no risk_scores."""
    resp = await submit(kw_client, content_text="")
    assert resp.status_code == 201
    body = resp.json()
    # Empty text passes the `if content_text:` check as falsy
    assert body["risk_scores"] is None


@pytest.mark.asyncio
async def test_preteen_pre_publish_clean_auto_approved(kw_client):
    """Clean text for preteen (pre-publish) is auto-approved."""
    resp = await submit(
        kw_client,
        content_text="I learned about photosynthesis today",
        age_tier="preteen",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["pipeline"] == "pre_publish"
    assert body["status"] == "approved"
