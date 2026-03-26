"""End-to-end tests for moderation dashboard endpoints.

Tests: assign moderator, bulk actions, SLA metrics, pattern detection via HTTP.
"""

import uuid
from datetime import datetime, timedelta, timezone

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
from src.moderation.models import ModerationDecision, ModerationQueue
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
    """Create a test moderator user."""
    user = User(
        id=uuid.uuid4(),
        email=f"e2e-mod-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="E2E Moderator",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()
    return user


@pytest_asyncio.fixture
async def mod_client(e2e_engine, e2e_session, e2e_user):
    """Authenticated HTTP client with moderator role."""
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


async def _seed_queue_entry(
    session: AsyncSession,
    *,
    pipeline: str = "pre_publish",
    status: str = "pending",
    content_type: str = "post",
    risk_scores: dict | None = None,
    created_at: datetime | None = None,
) -> ModerationQueue:
    """Create a queue entry directly in the session."""
    entry = ModerationQueue(
        id=uuid.uuid4(),
        content_type=content_type,
        content_id=uuid.uuid4(),
        pipeline=pipeline,
        status=status,
        age_tier="young",
        risk_scores=risk_scores,
    )
    session.add(entry)
    await session.flush()

    if created_at:
        entry.created_at = created_at
        await session.flush()

    return entry


async def _seed_decision(
    session: AsyncSession,
    queue_id: uuid.UUID,
    *,
    action: str = "approve",
    timestamp: datetime | None = None,
) -> ModerationDecision:
    """Create a moderation decision directly in the session."""
    decision = ModerationDecision(
        id=uuid.uuid4(),
        queue_id=queue_id,
        action=action,
        reason="test",
    )
    session.add(decision)
    await session.flush()

    if timestamp:
        decision.timestamp = timestamp
        await session.flush()

    return decision


# ---------------------------------------------------------------------------
# Assign moderator endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_moderator_endpoint(mod_client: AsyncClient, e2e_session, e2e_user):
    """POST /queue/{id}/assign assigns a moderator."""
    entry = await _seed_queue_entry(e2e_session)

    resp = await mod_client.post(
        f"/api/v1/moderation/queue/{entry.id}/assign",
        json={"moderator_id": str(e2e_user.id)},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["queue_id"] == str(entry.id)
    assert data["status"] == "assigned"


@pytest.mark.asyncio
async def test_assign_moderator_not_found(mod_client: AsyncClient, e2e_user):
    """POST /queue/{id}/assign with invalid ID returns 404."""
    resp = await mod_client.post(
        f"/api/v1/moderation/queue/{uuid.uuid4()}/assign",
        json={"moderator_id": str(e2e_user.id)},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_assign_moderator_already_processed(mod_client: AsyncClient, e2e_session, e2e_user):
    """POST /queue/{id}/assign on approved item returns 409."""
    entry = await _seed_queue_entry(e2e_session, status="approved")

    resp = await mod_client.post(
        f"/api/v1/moderation/queue/{entry.id}/assign",
        json={"moderator_id": str(e2e_user.id)},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Bulk action endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_approve_endpoint(mod_client: AsyncClient, e2e_session):
    """POST /bulk-action approves multiple items."""
    e1 = await _seed_queue_entry(e2e_session)
    e2 = await _seed_queue_entry(e2e_session)

    resp = await mod_client.post(
        "/api/v1/moderation/bulk-action",
        json={
            "queue_ids": [str(e1.id), str(e2.id)],
            "action": "approve",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_succeeded"] == 2
    assert data["action"] == "approve"


@pytest.mark.asyncio
async def test_bulk_reject_endpoint(mod_client: AsyncClient, e2e_session):
    """POST /bulk-action rejects with reason."""
    e1 = await _seed_queue_entry(e2e_session)

    resp = await mod_client.post(
        "/api/v1/moderation/bulk-action",
        json={
            "queue_ids": [str(e1.id)],
            "action": "reject",
            "reason": "Policy violation",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_succeeded"] == 1


@pytest.mark.asyncio
async def test_bulk_action_partial_failure_endpoint(mod_client: AsyncClient, e2e_session):
    """POST /bulk-action with mix of valid and already-processed."""
    e1 = await _seed_queue_entry(e2e_session)
    e2 = await _seed_queue_entry(e2e_session, status="rejected")

    resp = await mod_client.post(
        "/api/v1/moderation/bulk-action",
        json={
            "queue_ids": [str(e1.id), str(e2.id)],
            "action": "approve",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_succeeded"] == 1
    assert data["total_failed"] == 1


@pytest.mark.asyncio
async def test_bulk_action_invalid_action_endpoint(mod_client: AsyncClient):
    """POST /bulk-action with invalid action returns 422."""
    resp = await mod_client.post(
        "/api/v1/moderation/bulk-action",
        json={
            "queue_ids": [str(uuid.uuid4())],
            "action": "delete",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_bulk_action_empty_list_endpoint(mod_client: AsyncClient):
    """POST /bulk-action with empty list returns 422."""
    resp = await mod_client.post(
        "/api/v1/moderation/bulk-action",
        json={
            "queue_ids": [],
            "action": "approve",
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# SLA metrics endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sla_endpoint_empty(mod_client: AsyncClient):
    """GET /sla returns zero metrics when no data."""
    resp = await mod_client.get("/api/v1/moderation/sla")

    assert resp.status_code == 200
    data = resp.json()
    assert data["window_hours"] == 24
    assert "pre_publish" in data["pipelines"]
    assert data["pipelines"]["pre_publish"]["items_total"] == 0


@pytest.mark.asyncio
async def test_sla_endpoint_with_data(mod_client: AsyncClient, e2e_session):
    """GET /sla returns computed metrics from queue/decision data."""
    now = datetime.now(timezone.utc)
    for _ in range(3):
        created = now - timedelta(minutes=10)
        entry = await _seed_queue_entry(
            e2e_session, pipeline="pre_publish", status="approved",
            created_at=created,
        )
        decision_time = created + timedelta(milliseconds=500)
        await _seed_decision(e2e_session, entry.id, action="approve", timestamp=decision_time)

    resp = await mod_client.get("/api/v1/moderation/sla?pipeline=pre_publish")

    assert resp.status_code == 200
    data = resp.json()
    assert data["pipelines"]["pre_publish"]["items_total"] == 3


@pytest.mark.asyncio
async def test_sla_endpoint_filter_by_pipeline(mod_client: AsyncClient):
    """GET /sla?pipeline=post_publish filters to single pipeline."""
    resp = await mod_client.get("/api/v1/moderation/sla?pipeline=post_publish")

    assert resp.status_code == 200
    data = resp.json()
    assert "post_publish" in data["pipelines"]
    assert "pre_publish" not in data["pipelines"]


# ---------------------------------------------------------------------------
# Pattern detection endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patterns_endpoint_empty(mod_client: AsyncClient):
    """GET /patterns returns empty list when no patterns detected."""
    resp = await mod_client.get("/api/v1/moderation/patterns")

    assert resp.status_code == 200
    data = resp.json()
    assert data["patterns"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_patterns_endpoint_keyword_spike(mod_client: AsyncClient, e2e_session):
    """GET /patterns detects keyword spikes."""
    for _ in range(4):
        await _seed_queue_entry(
            e2e_session,
            status="rejected",
            risk_scores={
                "keyword_filter": {
                    "action": "block",
                    "matched_keywords": ["harmful"],
                }
            },
        )

    resp = await mod_client.get("/api/v1/moderation/patterns")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    keyword_patterns = [p for p in data["patterns"] if p["pattern_type"] == "keyword_spike"]
    assert len(keyword_patterns) >= 1


@pytest.mark.asyncio
async def test_patterns_endpoint_custom_window(mod_client: AsyncClient):
    """GET /patterns?hours=48 accepts custom window."""
    resp = await mod_client.get("/api/v1/moderation/patterns?hours=48")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["patterns"], list)


@pytest.mark.asyncio
async def test_sla_endpoint_with_breached_items(mod_client: AsyncClient, e2e_session):
    """GET /sla shows breached items when processing exceeds target."""
    now = datetime.now(timezone.utc)
    created = now - timedelta(minutes=5)
    entry = await _seed_queue_entry(
        e2e_session, pipeline="pre_publish", status="approved",
        created_at=created,
    )
    # 3 seconds processing time - breaches 2s SLA
    decision_time = created + timedelta(seconds=3)
    await _seed_decision(e2e_session, entry.id, action="approve", timestamp=decision_time)

    resp = await mod_client.get("/api/v1/moderation/sla?pipeline=pre_publish")

    assert resp.status_code == 200
    data = resp.json()
    pre = data["pipelines"]["pre_publish"]
    assert pre["items_breached_sla"] >= 1
