"""End-to-end tests for graph analysis and intelligence endpoints."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.intelligence.models import AbuseSignal, SocialGraphEdge
from src.intelligence.service import create_abuse_signal
from src.intelligence.schemas import AbuseSignalCreate
from src.main import create_app
from src.schemas import GroupContext


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def e2e_engine():
    """Create an E2E test engine."""
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
async def e2e_session(e2e_engine):
    """Create an E2E test session."""
    session = AsyncSession(e2e_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def e2e_data(e2e_session):
    """Create test data with multiple members of different ages."""
    user = User(
        id=uuid.uuid4(),
        email=f"e2e-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="E2E Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()

    group = Group(
        id=uuid.uuid4(), name="E2E Family", type="family", owner_id=user.id,
    )
    e2e_session.add(group)
    await e2e_session.flush()

    # Child aged 7
    child_7 = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child 7yo",
        date_of_birth=datetime(2019, 3, 15, tzinfo=timezone.utc),
    )
    # Child aged 15
    child_15 = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child 15yo",
        date_of_birth=datetime(2011, 1, 10, tzinfo=timezone.utc),
    )
    # Child aged 8
    child_8 = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child 8yo",
        date_of_birth=datetime(2018, 4, 12, tzinfo=timezone.utc),
    )
    # Child aged 10
    child_10 = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Child 10yo",
        date_of_birth=datetime(2016, 6, 20, tzinfo=timezone.utc),
    )

    for m in [child_7, child_15, child_8, child_10]:
        e2e_session.add(m)
    await e2e_session.flush()

    return {
        "user": user,
        "group": group,
        "child_7": child_7,
        "child_15": child_15,
        "child_8": child_8,
        "child_10": child_10,
    }


@pytest.fixture
async def e2e_client(e2e_engine, e2e_session, e2e_data):
    """HTTP client authenticated as the E2E user."""
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
            user_id=e2e_data["user"].id,
            group_id=e2e_data["group"].id,
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
# Helper to add edges via DB
# ---------------------------------------------------------------------------


async def _add_edge(session, source_id, target_id, edge_type="contact", weight=1.0, last_interaction=None):
    """Add a social graph edge directly."""
    edge = SocialGraphEdge(
        id=uuid.uuid4(),
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        weight=weight,
        last_interaction=last_interaction,
    )
    session.add(edge)
    await session.flush()
    return edge


# ---------------------------------------------------------------------------
# GET /api/v1/intelligence/graph-analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_analysis_endpoint(e2e_client, e2e_data, e2e_session):
    """GET /intelligence/graph-analysis returns analysis for a member."""
    await _add_edge(e2e_session, e2e_data["child_15"].id, e2e_data["child_7"].id)

    resp = await e2e_client.get(
        f"/api/v1/intelligence/graph-analysis?member_id={e2e_data['child_15'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["member_id"] == str(e2e_data["child_15"].id)
    assert body["total_contacts"] >= 1


@pytest.mark.asyncio
async def test_graph_analysis_flags_large_age_gap(e2e_client, e2e_data, e2e_session):
    """Age-gap flags appear for 15yo contacting 7yo."""
    await _add_edge(e2e_session, e2e_data["child_15"].id, e2e_data["child_7"].id)

    resp = await e2e_client.get(
        f"/api/v1/intelligence/graph-analysis?member_id={e2e_data['child_15'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["flagged_count"] >= 1
    assert len(body["age_gap_flags"]) >= 1


@pytest.mark.asyncio
async def test_graph_analysis_no_member(e2e_client):
    """Graph analysis for nonexistent member returns empty results."""
    fake_id = uuid.uuid4()
    resp = await e2e_client.get(f"/api/v1/intelligence/graph-analysis?member_id={fake_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_contacts"] == 0
    assert body["flagged_count"] == 0


@pytest.mark.asyncio
async def test_graph_analysis_missing_member_id(e2e_client):
    """Graph analysis without member_id returns 422."""
    resp = await e2e_client.get("/api/v1/intelligence/graph-analysis")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/intelligence/isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_isolation_endpoint_isolated(e2e_client, e2e_data):
    """Isolated member has high isolation score."""
    resp = await e2e_client.get(
        f"/api/v1/intelligence/isolation?member_id={e2e_data['child_7'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["isolation_score"] >= 50
    assert body["contact_count"] == 0


@pytest.mark.asyncio
async def test_isolation_endpoint_connected(e2e_client, e2e_data, e2e_session):
    """Connected member has lower isolation score."""
    for target_key in ["child_8", "child_10", "child_15"]:
        await _add_edge(
            e2e_session,
            e2e_data["child_7"].id,
            e2e_data[target_key].id,
            last_interaction=datetime(2026, 3, 20, tzinfo=timezone.utc),
        )
    # Add incoming edges
    await _add_edge(
        e2e_session,
        e2e_data["child_8"].id,
        e2e_data["child_7"].id,
        last_interaction=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    resp = await e2e_client.get(
        f"/api/v1/intelligence/isolation?member_id={e2e_data['child_7'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["isolation_score"] < 50
    assert body["contact_count"] >= 3


@pytest.mark.asyncio
async def test_isolation_missing_member_id(e2e_client):
    """Isolation without member_id returns 422."""
    resp = await e2e_client.get("/api/v1/intelligence/isolation")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/intelligence/influence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_influence_endpoint(e2e_client, e2e_data, e2e_session):
    """Influence endpoint returns influencers."""
    await _add_edge(e2e_session, e2e_data["child_15"].id, e2e_data["child_7"].id, "message")
    await _add_edge(e2e_session, e2e_data["child_10"].id, e2e_data["child_7"].id, "follow")

    resp = await e2e_client.get(
        f"/api/v1/intelligence/influence?member_id={e2e_data['child_7'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["influencers"]) == 2
    assert body["influence_score"] > 0


@pytest.mark.asyncio
async def test_influence_no_connections(e2e_client, e2e_data):
    """Member with no connections has zero influence."""
    resp = await e2e_client.get(
        f"/api/v1/intelligence/influence?member_id={e2e_data['child_7'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["influence_score"] == 0.0
    assert len(body["influencers"]) == 0


@pytest.mark.asyncio
async def test_influence_missing_member_id(e2e_client):
    """Influence without member_id returns 422."""
    resp = await e2e_client.get("/api/v1/intelligence/influence")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/intelligence/abuse-signals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_abuse_signals_endpoint(e2e_client, e2e_data, e2e_session):
    """Get abuse signals for a member."""
    signal = AbuseSignal(
        id=uuid.uuid4(),
        member_id=e2e_data["child_7"].id,
        signal_type="age_gap",
        severity="high",
        details={"gap": 8},
        resolved=False,
    )
    e2e_session.add(signal)
    await e2e_session.flush()

    resp = await e2e_client.get(
        f"/api/v1/intelligence/abuse-signals?member_id={e2e_data['child_7'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["signal_type"] == "age_gap"


@pytest.mark.asyncio
async def test_abuse_signals_empty(e2e_client, e2e_data):
    """No abuse signals returns empty list."""
    resp = await e2e_client.get(
        f"/api/v1/intelligence/abuse-signals?member_id={e2e_data['child_7'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_abuse_signals_pagination(e2e_client, e2e_data, e2e_session):
    """Abuse signals support pagination."""
    for i in range(5):
        signal = AbuseSignal(
            id=uuid.uuid4(),
            member_id=e2e_data["child_7"].id,
            signal_type="isolation",
            severity="medium",
            details={"index": i},
            resolved=False,
        )
        e2e_session.add(signal)
    await e2e_session.flush()

    resp = await e2e_client.get(
        f"/api/v1/intelligence/abuse-signals?member_id={e2e_data['child_7'].id}&limit=2&offset=0"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["has_more"] is True


@pytest.mark.asyncio
async def test_abuse_signals_missing_member_id(e2e_client):
    """Abuse signals without member_id returns 422."""
    resp = await e2e_client.get("/api/v1/intelligence/abuse-signals")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/intelligence/abuse-signals/{id}/resolve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_signal_endpoint(e2e_client, e2e_data, e2e_session):
    """Resolve an abuse signal via endpoint."""
    signal = AbuseSignal(
        id=uuid.uuid4(),
        member_id=e2e_data["child_7"].id,
        signal_type="age_gap",
        severity="high",
        details={},
        resolved=False,
    )
    e2e_session.add(signal)
    await e2e_session.flush()

    resp = await e2e_client.post(f"/api/v1/intelligence/abuse-signals/{signal.id}/resolve")
    assert resp.status_code == 200
    body = resp.json()
    assert body["resolved"] is True


@pytest.mark.asyncio
async def test_resolve_nonexistent_signal(e2e_client):
    """Resolving nonexistent signal returns 404."""
    fake_id = uuid.uuid4()
    resp = await e2e_client.post(f"/api/v1/intelligence/abuse-signals/{fake_id}/resolve")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/intelligence/age-pattern
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_age_pattern_endpoint_flagged(e2e_client, e2e_data, e2e_session):
    """Age pattern endpoint detects teen contacting young children."""
    for target_key in ["child_7", "child_8"]:
        await _add_edge(e2e_session, e2e_data["child_15"].id, e2e_data[target_key].id)

    resp = await e2e_client.get(
        f"/api/v1/intelligence/age-pattern?member_id={e2e_data['child_15'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["flagged"] is True


@pytest.mark.asyncio
async def test_age_pattern_endpoint_not_flagged(e2e_client, e2e_data, e2e_session):
    """Normal same-tier contacts not flagged."""
    await _add_edge(e2e_session, e2e_data["child_7"].id, e2e_data["child_8"].id)

    resp = await e2e_client.get(
        f"/api/v1/intelligence/age-pattern?member_id={e2e_data['child_7'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["flagged"] is False


@pytest.mark.asyncio
async def test_age_pattern_missing_member_id(e2e_client):
    """Age pattern without member_id returns 422."""
    resp = await e2e_client.get("/api/v1/intelligence/age-pattern")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_age_pattern_tier_distribution(e2e_client, e2e_data, e2e_session):
    """Age pattern returns tier distribution."""
    await _add_edge(e2e_session, e2e_data["child_15"].id, e2e_data["child_7"].id)
    await _add_edge(e2e_session, e2e_data["child_15"].id, e2e_data["child_10"].id)

    resp = await e2e_client.get(
        f"/api/v1/intelligence/age-pattern?member_id={e2e_data['child_15'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "tier_distribution" in body
    assert body["tier_distribution"]["young"] >= 1


# ---------------------------------------------------------------------------
# Cross-endpoint integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_analysis_multiple_edge_types(e2e_client, e2e_data, e2e_session):
    """Graph analysis handles multiple edge types."""
    await _add_edge(e2e_session, e2e_data["child_15"].id, e2e_data["child_7"].id, "contact")
    await _add_edge(e2e_session, e2e_data["child_15"].id, e2e_data["child_7"].id, "message")

    resp = await e2e_client.get(
        f"/api/v1/intelligence/graph-analysis?member_id={e2e_data['child_15'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    # Should still only count as 1 unique contact (same target)
    assert body["total_contacts"] == 1


@pytest.mark.asyncio
async def test_isolation_with_interactions(e2e_client, e2e_data, e2e_session):
    """Isolation score considers interaction recency."""
    await _add_edge(
        e2e_session,
        e2e_data["child_7"].id,
        e2e_data["child_8"].id,
        "contact",
        last_interaction=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )
    await _add_edge(
        e2e_session,
        e2e_data["child_8"].id,
        e2e_data["child_7"].id,
        "follow",
        last_interaction=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    resp = await e2e_client.get(
        f"/api/v1/intelligence/isolation?member_id={e2e_data['child_7'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["interaction_count"] >= 2


@pytest.mark.asyncio
async def test_influence_message_ranked_higher(e2e_client, e2e_data, e2e_session):
    """Message influencer is ranked higher than follow influencer."""
    await _add_edge(e2e_session, e2e_data["child_15"].id, e2e_data["child_7"].id, "message")
    await _add_edge(e2e_session, e2e_data["child_10"].id, e2e_data["child_7"].id, "follow")

    resp = await e2e_client.get(
        f"/api/v1/intelligence/influence?member_id={e2e_data['child_7'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    # Message sender should be first (higher weight)
    assert body["influencers"][0]["member_id"] == str(e2e_data["child_15"].id)


@pytest.mark.asyncio
async def test_abuse_signals_include_resolved(e2e_client, e2e_data, e2e_session):
    """Include resolved signals with query param."""
    signal = AbuseSignal(
        id=uuid.uuid4(),
        member_id=e2e_data["child_7"].id,
        signal_type="age_gap",
        severity="high",
        details={},
        resolved=True,
    )
    e2e_session.add(signal)
    await e2e_session.flush()

    # Without include_resolved, should be excluded
    resp = await e2e_client.get(
        f"/api/v1/intelligence/abuse-signals?member_id={e2e_data['child_7'].id}"
    )
    assert resp.json()["total"] == 0

    # With include_resolved=true
    resp = await e2e_client.get(
        f"/api/v1/intelligence/abuse-signals?member_id={e2e_data['child_7'].id}&include_resolved=true"
    )
    assert resp.json()["total"] == 1
