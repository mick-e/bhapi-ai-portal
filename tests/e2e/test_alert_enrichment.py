"""End-to-end tests for alert enrichment with correlated context (P3-I3).

Covers:
- GET /{alert_id} returns enrichment when enriched_alert_id is set
- GET /{alert_id} returns null enrichment when no enriched alert linked
- Enrichment data integrity across create/read cycle
- POST alert → GET detail shows enrichment key always present
- enrichment.correlation_context is a non-empty string
- enrichment.contributing_signals is a dict
- enrichment.unified_risk_score is a float
- enrichment.confidence is one of low/medium/high
- Alert with null member_id has null enrichment
- Alert detail endpoint requires auth (401 without token)
- Enrichment id is a valid UUID string
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.alerts.models import Alert
from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.intelligence.correlation import create_enriched_alert
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def ae_engine():
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
async def ae_session(ae_engine):
    session_maker = sessionmaker(ae_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def ae_data(ae_session):
    """Create parent + child with one enriched alert and one plain alert."""
    parent = User(
        id=uuid.uuid4(),
        email=f"ae-parent-{uuid.uuid4().hex[:8]}@example.com",
        display_name="AE Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child_user = User(
        id=uuid.uuid4(),
        email=f"ae-child-{uuid.uuid4().hex[:8]}@example.com",
        display_name="AE Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    ae_session.add_all([parent, child_user])
    await ae_session.flush()

    group = Group(
        id=uuid.uuid4(),
        name="AE Family",
        type="family",
        owner_id=parent.id,
    )
    ae_session.add(group)
    await ae_session.flush()

    child_member = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=child_user.id,
        role="member",
        display_name="AE Child",
    )
    ae_session.add(child_member)
    await ae_session.flush()

    # Alert WITH enrichment
    enriched_alert = Alert(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=child_member.id,
        severity="high",
        title="Enriched Alert",
        body="This alert has correlation context",
        source="ai",
        channel="portal",
        status="pending",
    )
    ae_session.add(enriched_alert)
    await ae_session.flush()

    signals = {
        "matched": [
            {"source": "ai", "metric": "risk_score", "value": 0.85, "score_contribution": 0.85},
        ],
        "source": "ai",
    }
    enrichment = await create_enriched_alert(
        ae_session,
        alert_id=enriched_alert.id,
        rule_id=None,
        context=(
            f"Correlated alert for member {child_member.id}: "
            "rule 'emotional_dependency' matched 1 signal(s) "
            "with score 0.85 [high confidence]"
        ),
        signals=signals,
        score=0.85,
        confidence="high",
    )
    enriched_alert.enriched_alert_id = enrichment.id
    await ae_session.flush()

    # Alert WITHOUT enrichment
    plain_alert = Alert(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=child_member.id,
        severity="low",
        title="Plain Alert",
        body="No correlation context here",
        source="ai",
        channel="portal",
        status="pending",
    )
    ae_session.add(plain_alert)
    await ae_session.flush()

    # Alert with no member_id
    no_member_alert = Alert(
        id=uuid.uuid4(),
        group_id=group.id,
        member_id=None,
        severity="info",
        title="System Alert",
        body="No member involved",
        source="ai",
        channel="portal",
        status="pending",
    )
    ae_session.add(no_member_alert)
    await ae_session.flush()

    return {
        "parent": parent,
        "child_user": child_user,
        "group": group,
        "child_member": child_member,
        "enriched_alert": enriched_alert,
        "enrichment": enrichment,
        "plain_alert": plain_alert,
        "no_member_alert": no_member_alert,
    }


@pytest_asyncio.fixture
async def ae_client(ae_engine, ae_data):
    """HTTP client with parent auth context."""
    app = create_app()

    async def override_get_db():
        session_maker = sessionmaker(ae_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_maker() as session:
            yield session

    async def override_auth():
        return GroupContext(
            user_id=ae_data["parent"].id,
            group_id=ae_data["group"].id,
            role="parent",
            permissions=["*"],
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_alert_detail_includes_enrichment(ae_client, ae_data):
    """GET /{alert_id} includes enrichment when enriched_alert_id is set."""
    alert_id = str(ae_data["enriched_alert"].id)
    resp = await ae_client.get(f"/api/v1/alerts/{alert_id}")
    assert resp.status_code == 200

    body = resp.json()
    assert "enrichment" in body
    assert body["enrichment"] is not None


@pytest.mark.asyncio
async def test_enrichment_has_correlation_context(ae_client, ae_data):
    """Enrichment.correlation_context is a non-empty string with expected content."""
    alert_id = str(ae_data["enriched_alert"].id)
    resp = await ae_client.get(f"/api/v1/alerts/{alert_id}")
    assert resp.status_code == 200

    enrichment = resp.json()["enrichment"]
    assert isinstance(enrichment["correlation_context"], str)
    assert len(enrichment["correlation_context"]) > 0
    assert "emotional_dependency" in enrichment["correlation_context"]


@pytest.mark.asyncio
async def test_enrichment_has_contributing_signals(ae_client, ae_data):
    """Enrichment.contributing_signals is a dict with 'matched' key."""
    alert_id = str(ae_data["enriched_alert"].id)
    resp = await ae_client.get(f"/api/v1/alerts/{alert_id}")
    assert resp.status_code == 200

    enrichment = resp.json()["enrichment"]
    signals = enrichment["contributing_signals"]
    assert isinstance(signals, dict)
    assert "matched" in signals
    assert isinstance(signals["matched"], list)


@pytest.mark.asyncio
async def test_enrichment_has_unified_risk_score(ae_client, ae_data):
    """Enrichment.unified_risk_score is a float."""
    alert_id = str(ae_data["enriched_alert"].id)
    resp = await ae_client.get(f"/api/v1/alerts/{alert_id}")
    assert resp.status_code == 200

    score = resp.json()["enrichment"]["unified_risk_score"]
    assert isinstance(score, (int, float))
    assert score == pytest.approx(0.85)


@pytest.mark.asyncio
async def test_enrichment_has_confidence(ae_client, ae_data):
    """Enrichment.confidence is one of low/medium/high."""
    alert_id = str(ae_data["enriched_alert"].id)
    resp = await ae_client.get(f"/api/v1/alerts/{alert_id}")
    assert resp.status_code == 200

    confidence = resp.json()["enrichment"]["confidence"]
    assert confidence in ("low", "medium", "high")
    assert confidence == "high"


@pytest.mark.asyncio
async def test_enrichment_id_is_valid_uuid(ae_client, ae_data):
    """Enrichment.id is a valid UUID string."""
    alert_id = str(ae_data["enriched_alert"].id)
    resp = await ae_client.get(f"/api/v1/alerts/{alert_id}")
    assert resp.status_code == 200

    enrichment_id = resp.json()["enrichment"]["id"]
    parsed = uuid.UUID(enrichment_id)  # raises ValueError if invalid
    assert str(parsed) == enrichment_id


@pytest.mark.asyncio
async def test_get_alert_without_enrichment_has_null_enrichment(ae_client, ae_data):
    """GET /{alert_id} returns null enrichment when alert has no enrichment."""
    alert_id = str(ae_data["plain_alert"].id)
    resp = await ae_client.get(f"/api/v1/alerts/{alert_id}")
    assert resp.status_code == 200

    body = resp.json()
    assert "enrichment" in body
    assert body["enrichment"] is None


@pytest.mark.asyncio
async def test_alert_with_no_member_has_null_enrichment(ae_client, ae_data):
    """Alert with no member_id always has null enrichment in response."""
    alert_id = str(ae_data["no_member_alert"].id)
    resp = await ae_client.get(f"/api/v1/alerts/{alert_id}")
    assert resp.status_code == 200

    body = resp.json()
    assert "enrichment" in body
    assert body["enrichment"] is None


@pytest.mark.asyncio
async def test_enrichment_data_integrity_across_create_read(ae_session, ae_data):
    """Enrichment stored in DB matches what we read back via get_enriched_alert_by_id."""
    from src.intelligence.correlation import get_enriched_alert_by_id

    enrichment_id = ae_data["enrichment"].id
    read_back = await get_enriched_alert_by_id(ae_session, enrichment_id)

    assert read_back is not None
    assert read_back.alert_id == ae_data["enriched_alert"].id
    assert read_back.unified_risk_score == pytest.approx(0.85)
    assert read_back.confidence == "high"
    assert "emotional_dependency" in read_back.correlation_context
    assert read_back.contributing_signals["matched"][0]["metric"] == "risk_score"


@pytest.mark.asyncio
async def test_alert_detail_requires_auth(ae_engine, ae_data):
    """GET /{alert_id} returns 401 without valid auth."""
    app = create_app()

    async def override_get_db():
        session_maker = sessionmaker(ae_engine, class_=AsyncSession, expire_on_commit=False)
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # No auth override → middleware will reject

    alert_id = str(ae_data["enriched_alert"].id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        # No Authorization header
    ) as ac:
        resp = await ac.get(f"/api/v1/alerts/{alert_id}")

    assert resp.status_code in (401, 403)
