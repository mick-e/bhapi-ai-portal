"""End-to-end tests for moderation UX — appeal flow, re-submission, rate limiting.

Covers:
  - POST /api/v1/moderation/queue/{queue_id}/appeal
  - PATCH /api/v1/moderation/appeals/{appeal_id}/decide
  - Appeal validation (only rejected, one per user, reason length)
  - Appeal decision flow (accept restores approved, deny reverts to rejected)
  - Non-moderator cannot decide appeals
  - Rate limiting / duplicate prevention
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
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def ux_engine():
    """Create test engine for moderation UX tests."""
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
async def ux_session(ux_engine):
    """Create test session."""
    session = AsyncSession(ux_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def ux_user(ux_session):
    """Create a test user (content author)."""
    user = User(
        id=uuid.uuid4(),
        email=f"ux-author-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Content Author",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    ux_session.add(user)
    await ux_session.flush()
    return user


@pytest_asyncio.fixture
async def ux_moderator(ux_session):
    """Create a moderator user."""
    user = User(
        id=uuid.uuid4(),
        email=f"ux-mod-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Moderator",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    ux_session.add(user)
    await ux_session.flush()
    return user


def _make_client(engine, session, user, role="member"):
    """Create an authenticated HTTP client with the given role."""
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
            group_id=None,
            role=role,
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest_asyncio.fixture
async def author_client(ux_engine, ux_session, ux_user):
    """Authenticated client as content author (member role)."""
    async with _make_client(ux_engine, ux_session, ux_user, role="member") as client:
        yield client


@pytest_asyncio.fixture
async def mod_client(ux_engine, ux_session, ux_moderator):
    """Authenticated client as moderator (admin role)."""
    async with _make_client(ux_engine, ux_session, ux_moderator, role="admin") as client:
        yield client


async def _create_rejected_queue_entry(client) -> dict:
    """Helper: submit content and have it rejected via keyword filter.

    Uses a critical keyword ('suicide') which triggers BLOCK action
    regardless of age tier.
    """
    resp = await client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
        "age_tier": "young",
        "content_text": "I want to commit suicide",  # critical keyword -> BLOCK
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "rejected"
    return data


async def _create_pending_queue_entry(client) -> dict:
    """Helper: submit clean content that stays pending."""
    resp = await client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
        "age_tier": "teen",
        "content_text": "Hello world, nice day today!",
    })
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Appeal creation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_appeal_rejected_content(author_client):
    """User can appeal a rejected queue entry."""
    entry = await _create_rejected_queue_entry(author_client)
    queue_id = entry["id"]

    resp = await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "I believe this was flagged incorrectly, the context was a book discussion."},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["queue_id"] == queue_id
    assert data["status"] == "pending"
    assert "incorrectly" in data["reason"]


@pytest.mark.asyncio
async def test_appeal_escalates_queue_entry(author_client):
    """Appeal changes queue entry status to escalated."""
    entry = await _create_rejected_queue_entry(author_client)
    queue_id = entry["id"]

    await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "This was incorrectly flagged by the filter."},
    )

    # Verify queue entry is now escalated
    resp = await author_client.get(f"/api/v1/moderation/queue/{queue_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "escalated"


@pytest.mark.asyncio
async def test_appeal_duplicate_rejected(author_client):
    """User cannot appeal the same item twice."""
    entry = await _create_rejected_queue_entry(author_client)
    queue_id = entry["id"]

    # First appeal
    resp1 = await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "First appeal with enough characters."},
    )
    assert resp1.status_code == 201

    # Second appeal — should fail
    resp2 = await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "Second appeal attempt should be rejected."},
    )
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_appeal_pending_content_rejected(author_client):
    """Cannot appeal content that is not rejected."""
    entry = await _create_pending_queue_entry(author_client)
    queue_id = entry["id"]

    resp = await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "Trying to appeal non-rejected content here."},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_appeal_nonexistent_queue_returns_404(author_client):
    """Appeal on nonexistent queue ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await author_client.post(
        f"/api/v1/moderation/queue/{fake_id}/appeal",
        json={"reason": "This queue item does not exist at all."},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_appeal_reason_too_short(author_client):
    """Appeal reason must be at least 10 characters."""
    entry = await _create_rejected_queue_entry(author_client)
    queue_id = entry["id"]

    resp = await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "short"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Appeal decision tests (moderators)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_moderator_accepts_appeal(author_client, mod_client):
    """Moderator can accept an appeal, restoring content to approved."""
    entry = await _create_rejected_queue_entry(mod_client)
    queue_id = entry["id"]

    # Author appeals
    appeal_resp = await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "This was incorrectly flagged, please review."},
    )
    assert appeal_resp.status_code == 201
    appeal_id = appeal_resp.json()["id"]

    # Moderator accepts
    decide_resp = await mod_client.patch(
        f"/api/v1/moderation/appeals/{appeal_id}/decide",
        json={"decision": "accepted", "review_note": "Legitimate content."},
    )
    assert decide_resp.status_code == 200
    assert decide_resp.json()["status"] == "accepted"

    # Queue entry should now be approved
    queue_resp = await mod_client.get(f"/api/v1/moderation/queue/{queue_id}")
    assert queue_resp.status_code == 200
    assert queue_resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_moderator_denies_appeal(author_client, mod_client):
    """Moderator can deny an appeal, reverting content to rejected."""
    entry = await _create_rejected_queue_entry(mod_client)
    queue_id = entry["id"]

    appeal_resp = await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "Please reconsider this moderation decision."},
    )
    appeal_id = appeal_resp.json()["id"]

    decide_resp = await mod_client.patch(
        f"/api/v1/moderation/appeals/{appeal_id}/decide",
        json={"decision": "denied", "review_note": "Content violates guidelines."},
    )
    assert decide_resp.status_code == 200
    assert decide_resp.json()["status"] == "denied"

    # Queue entry should be back to rejected
    queue_resp = await mod_client.get(f"/api/v1/moderation/queue/{queue_id}")
    assert queue_resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_member_cannot_decide_appeal(author_client, mod_client):
    """Non-moderator cannot decide on an appeal."""
    entry = await _create_rejected_queue_entry(mod_client)
    queue_id = entry["id"]

    appeal_resp = await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "I think this was flagged by mistake here."},
    )
    appeal_id = appeal_resp.json()["id"]

    # Author (member role) tries to decide
    decide_resp = await author_client.patch(
        f"/api/v1/moderation/appeals/{appeal_id}/decide",
        json={"decision": "accepted"},
    )
    assert decide_resp.status_code == 403


@pytest.mark.asyncio
async def test_cannot_decide_already_decided_appeal(author_client, mod_client):
    """Cannot decide an appeal that was already decided."""
    entry = await _create_rejected_queue_entry(mod_client)
    queue_id = entry["id"]

    appeal_resp = await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "Please review this moderation action again."},
    )
    appeal_id = appeal_resp.json()["id"]

    # First decision
    await mod_client.patch(
        f"/api/v1/moderation/appeals/{appeal_id}/decide",
        json={"decision": "denied"},
    )

    # Second decision — should fail
    resp = await mod_client.patch(
        f"/api/v1/moderation/appeals/{appeal_id}/decide",
        json={"decision": "accepted"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_appeal_invalid_decision_value(author_client, mod_client):
    """Invalid decision value returns 422."""
    entry = await _create_rejected_queue_entry(mod_client)
    queue_id = entry["id"]

    appeal_resp = await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "This content was flagged incorrectly here."},
    )
    appeal_id = appeal_resp.json()["id"]

    resp = await mod_client.patch(
        f"/api/v1/moderation/appeals/{appeal_id}/decide",
        json={"decision": "maybe"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_appeal_nonexistent_returns_404(mod_client):
    """Deciding on nonexistent appeal returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await mod_client.patch(
        f"/api/v1/moderation/appeals/{fake_id}/decide",
        json={"decision": "accepted"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Re-submission tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resubmission_after_rejection(author_client):
    """User can submit new content after a rejection (different content_id)."""
    # First: rejected
    entry1 = await _create_rejected_queue_entry(author_client)
    assert entry1["status"] == "rejected"

    # Second: new clean content
    resp = await author_client.post("/api/v1/moderation/queue", json={
        "content_type": "post",
        "content_id": str(uuid.uuid4()),
        "age_tier": "young",
        "content_text": "I love reading books about space",
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_appeal_includes_review_note(author_client, mod_client):
    """Appeal decision includes the review note."""
    entry = await _create_rejected_queue_entry(mod_client)
    queue_id = entry["id"]

    appeal_resp = await author_client.post(
        f"/api/v1/moderation/queue/{queue_id}/appeal",
        json={"reason": "The content was about a historical event, not promoting violence."},
    )
    appeal_id = appeal_resp.json()["id"]

    decide_resp = await mod_client.patch(
        f"/api/v1/moderation/appeals/{appeal_id}/decide",
        json={"decision": "accepted", "review_note": "Historical context verified."},
    )
    data = decide_resp.json()
    assert data["review_note"] == "Historical context verified."
