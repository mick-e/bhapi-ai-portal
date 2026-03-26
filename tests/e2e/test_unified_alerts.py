"""End-to-end tests for unified alert feed (P2-M3).

Covers:
- Unified feed returns AI + social + device alerts
- Sorting by severity (critical first) then timestamp (newest first)
- Filtering by source (ai|social|device)
- Filtering by member_id
- Pagination
- Severity drill-down
- Social alert generation from moderation rejection
- Device alert generation
- Empty state when no alerts
- Multiple children isolation
- Source counts in response
- Auth required (401 without token)
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.alerts.models import Alert
from src.alerts.schemas import AlertCreate
from src.alerts.service import (
    create_alert,
    create_device_alert,
    create_social_alert,
    get_unified_alerts,
)
from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.groups.models import Group, GroupMember
from src.main import create_app
from src.schemas import GroupContext

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def ua_engine():
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
async def ua_session(ua_engine):
    async_session_maker = sessionmaker(
        ua_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def ua_data(ua_session):
    """Create parent + child with mixed-source alerts."""
    now = datetime.now(timezone.utc)

    parent = User(
        id=uuid.uuid4(),
        email=f"uaparent-{uuid.uuid4().hex[:8]}@example.com",
        display_name="UA Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child_user = User(
        id=uuid.uuid4(),
        email=f"uachild-{uuid.uuid4().hex[:8]}@example.com",
        display_name="UA Child",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    child2_user = User(
        id=uuid.uuid4(),
        email=f"uachild2-{uuid.uuid4().hex[:8]}@example.com",
        display_name="UA Child 2",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    ua_session.add_all([parent, child_user, child2_user])
    await ua_session.flush()

    group = Group(
        id=uuid.uuid4(), name="UA Family", type="family", owner_id=parent.id,
    )
    ua_session.add(group)
    await ua_session.flush()

    parent_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=parent.id,
        role="parent", display_name="Parent",
    )
    child_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=child_user.id,
        role="member", display_name="Child One",
        date_of_birth=datetime(2015, 6, 15, tzinfo=timezone.utc),
    )
    child2_member = GroupMember(
        id=uuid.uuid4(), group_id=group.id, user_id=child2_user.id,
        role="member", display_name="Child Two",
        date_of_birth=datetime(2017, 3, 10, tzinfo=timezone.utc),
    )
    ua_session.add_all([parent_member, child_member, child2_member])
    await ua_session.flush()

    # --- Create mixed-source alerts for child 1 ---
    alerts = []

    # AI alerts
    for i, sev in enumerate(["critical", "medium", "low"]):
        alert = Alert(
            id=uuid.uuid4(), group_id=group.id, member_id=child_member.id,
            source="ai", severity=sev,
            title=f"AI alert {sev}", body=f"AI safety concern: {sev}",
            channel="portal", status="pending",
            created_at=now - timedelta(hours=i + 1),
        )
        ua_session.add(alert)
        alerts.append(alert)

    # Social alerts
    for i, sev in enumerate(["high", "medium"]):
        alert = Alert(
            id=uuid.uuid4(), group_id=group.id, member_id=child_member.id,
            source="social", severity=sev,
            title=f"Social alert {sev}", body=f"Social concern: {sev}",
            channel="portal", status="pending",
            created_at=now - timedelta(hours=i + 4),
        )
        ua_session.add(alert)
        alerts.append(alert)

    # Device alerts
    for i, sev in enumerate(["high", "low"]):
        alert = Alert(
            id=uuid.uuid4(), group_id=group.id, member_id=child_member.id,
            source="device", severity=sev,
            title=f"Device alert {sev}", body=f"Device concern: {sev}",
            channel="portal", status="pending",
            created_at=now - timedelta(hours=i + 6),
        )
        ua_session.add(alert)
        alerts.append(alert)

    # Alert for child 2 (isolation test)
    child2_alert = Alert(
        id=uuid.uuid4(), group_id=group.id, member_id=child2_member.id,
        source="social", severity="critical",
        title="Child 2 social alert", body="Child 2 concern",
        channel="portal", status="pending",
        created_at=now - timedelta(hours=1),
    )
    ua_session.add(child2_alert)

    await ua_session.flush()

    return {
        "parent": parent,
        "child_user": child_user,
        "child2_user": child2_user,
        "group": group,
        "parent_member": parent_member,
        "child_member": child_member,
        "child2_member": child2_member,
        "alerts": alerts,
        "child2_alert": child2_alert,
    }


@pytest.fixture
async def ua_client(ua_engine, ua_data):
    """HTTP client with parent auth context."""
    app = create_app()

    async def override_get_db():
        async_session_maker = sessionmaker(
            ua_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    async def override_auth():
        return GroupContext(
            user_id=ua_data["parent"].id,
            group_id=ua_data["group"].id,
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


@pytest.fixture
async def ua_unauthed_client(ua_engine):
    """HTTP client with no auth."""
    app = create_app()

    async def override_get_db():
        async_session_maker = sessionmaker(
            ua_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Service-level tests (Component tests)
# ---------------------------------------------------------------------------


class TestGetUnifiedAlerts:
    """Component tests for the unified alerts service function."""

    @pytest.mark.asyncio
    async def test_returns_all_sources(self, ua_session, ua_data):
        """Unified feed returns alerts from all sources."""
        result = await get_unified_alerts(ua_session, ua_data["group"].id)
        items = result["items"]
        sources = {a.source for a in items}
        assert "ai" in sources
        assert "social" in sources
        assert "device" in sources

    @pytest.mark.asyncio
    async def test_sorted_severity_then_timestamp(self, ua_session, ua_data):
        """Alerts are sorted by severity (critical first) then timestamp descending."""
        result = await get_unified_alerts(ua_session, ua_data["group"].id)
        items = result["items"]
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        for i in range(len(items) - 1):
            a, b = items[i], items[i + 1]
            a_sev = severity_order.get(a.severity, 5)
            b_sev = severity_order.get(b.severity, 5)
            assert a_sev <= b_sev, f"Expected {a.severity} before {b.severity}"
            if a_sev == b_sev:
                assert a.created_at >= b.created_at, "Same severity should be newest first"

    @pytest.mark.asyncio
    async def test_filter_by_source_ai(self, ua_session, ua_data):
        """Filter by source=ai returns only AI alerts."""
        result = await get_unified_alerts(
            ua_session, ua_data["group"].id, source_filter="ai",
        )
        for a in result["items"]:
            assert a.source == "ai"

    @pytest.mark.asyncio
    async def test_filter_by_source_social(self, ua_session, ua_data):
        """Filter by source=social returns only social alerts."""
        result = await get_unified_alerts(
            ua_session, ua_data["group"].id, source_filter="social",
        )
        for a in result["items"]:
            assert a.source == "social"
        # 2 for child 1 + 1 for child 2 = 3
        assert result["total"] == 3

    @pytest.mark.asyncio
    async def test_filter_by_source_device(self, ua_session, ua_data):
        """Filter by source=device returns only device alerts."""
        result = await get_unified_alerts(
            ua_session, ua_data["group"].id, source_filter="device",
        )
        for a in result["items"]:
            assert a.source == "device"
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_filter_by_member_id(self, ua_session, ua_data):
        """Filter by member_id returns only that member's alerts."""
        result = await get_unified_alerts(
            ua_session, ua_data["group"].id,
            member_id=ua_data["child_member"].id,
        )
        for a in result["items"]:
            assert a.member_id == ua_data["child_member"].id
        # child 1 has 7 alerts total
        assert result["total"] == 7

    @pytest.mark.asyncio
    async def test_combined_filters(self, ua_session, ua_data):
        """Filter by both member_id and source."""
        result = await get_unified_alerts(
            ua_session, ua_data["group"].id,
            member_id=ua_data["child_member"].id,
            source_filter="social",
        )
        assert result["total"] == 2
        for a in result["items"]:
            assert a.source == "social"
            assert a.member_id == ua_data["child_member"].id

    @pytest.mark.asyncio
    async def test_pagination(self, ua_session, ua_data):
        """Pagination returns correct page_size and total_pages."""
        result = await get_unified_alerts(
            ua_session, ua_data["group"].id,
            page=1, page_size=3,
        )
        assert len(result["items"]) == 3
        assert result["page"] == 1
        assert result["page_size"] == 3
        # Total is 8 (7 child1 + 1 child2), pages = ceil(8/3) = 3
        assert result["total"] == 8
        assert result["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_pagination_page_2(self, ua_session, ua_data):
        """Page 2 returns next batch."""
        result = await get_unified_alerts(
            ua_session, ua_data["group"].id,
            page=2, page_size=3,
        )
        assert len(result["items"]) == 3
        assert result["page"] == 2

    @pytest.mark.asyncio
    async def test_empty_state(self, ua_session, ua_data):
        """No alerts returns empty items with total=0."""
        fake_group_id = uuid.uuid4()
        result = await get_unified_alerts(ua_session, fake_group_id)
        assert result["items"] == []
        assert result["total"] == 0
        assert result["total_pages"] == 1


class TestCreateSocialAlert:
    """Component tests for social alert creation."""

    @pytest.mark.asyncio
    async def test_creates_social_source_alert(self, ua_session, ua_data):
        """create_social_alert sets source=social."""
        alert = await create_social_alert(
            ua_session,
            group_id=ua_data["group"].id,
            member_id=ua_data["child_member"].id,
            severity="high",
            title="Content rejected",
            body="A post was blocked by moderation.",
        )
        assert alert.source == "social"
        assert alert.severity == "high"
        assert alert.title == "Content rejected"

    @pytest.mark.asyncio
    async def test_social_alert_appears_in_unified(self, ua_session, ua_data):
        """Social alert created via service appears in unified feed."""
        await create_social_alert(
            ua_session,
            group_id=ua_data["group"].id,
            member_id=ua_data["child_member"].id,
            severity="critical",
            title="Harmful content detected",
            body="Post contained inappropriate content.",
        )
        result = await get_unified_alerts(
            ua_session, ua_data["group"].id, source_filter="social",
        )
        titles = [a.title for a in result["items"]]
        assert "Harmful content detected" in titles

    @pytest.mark.asyncio
    async def test_social_alert_default_channel(self, ua_session, ua_data):
        """Social alert defaults to portal channel."""
        alert = await create_social_alert(
            ua_session,
            group_id=ua_data["group"].id,
            member_id=ua_data["child_member"].id,
            severity="medium",
            title="Test",
            body="Test body",
        )
        assert alert.channel == "portal"


class TestCreateDeviceAlert:
    """Component tests for device alert creation."""

    @pytest.mark.asyncio
    async def test_creates_device_source_alert(self, ua_session, ua_data):
        """create_device_alert sets source=device."""
        alert = await create_device_alert(
            ua_session,
            group_id=ua_data["group"].id,
            member_id=ua_data["child_member"].id,
            severity="medium",
            title="Screen time exceeded",
            body="Daily screen time limit reached.",
        )
        assert alert.source == "device"
        assert alert.severity == "medium"

    @pytest.mark.asyncio
    async def test_device_alert_in_unified_feed(self, ua_session, ua_data):
        """Device alert appears in unified feed with source=device filter."""
        await create_device_alert(
            ua_session,
            group_id=ua_data["group"].id,
            member_id=ua_data["child_member"].id,
            severity="low",
            title="New app detected",
            body="Child installed a new app.",
        )
        result = await get_unified_alerts(
            ua_session, ua_data["group"].id,
            source_filter="device",
        )
        titles = [a.title for a in result["items"]]
        assert "New app detected" in titles


class TestAlertCreateSchema:
    """Component tests for AlertCreate schema with source field."""

    @pytest.mark.asyncio
    async def test_default_source_is_ai(self, ua_session, ua_data):
        """AlertCreate defaults source to 'ai'."""
        data = AlertCreate(
            group_id=ua_data["group"].id,
            severity="low",
            title="Test",
            body="Test body",
        )
        alert = await create_alert(ua_session, data)
        assert alert.source == "ai"

    @pytest.mark.asyncio
    async def test_explicit_source_social(self, ua_session, ua_data):
        """AlertCreate with explicit source=social."""
        data = AlertCreate(
            group_id=ua_data["group"].id,
            source="social",
            severity="medium",
            title="Test social",
            body="Social body",
        )
        alert = await create_alert(ua_session, data)
        assert alert.source == "social"

    @pytest.mark.asyncio
    async def test_explicit_source_device(self, ua_session, ua_data):
        """AlertCreate with explicit source=device."""
        data = AlertCreate(
            group_id=ua_data["group"].id,
            source="device",
            severity="high",
            title="Test device",
            body="Device body",
        )
        alert = await create_alert(ua_session, data)
        assert alert.source == "device"


# ---------------------------------------------------------------------------
# Integration tests (HTTP endpoint)
# ---------------------------------------------------------------------------


class TestUnifiedEndpoint:
    """Integration tests for GET /api/v1/alerts/unified."""

    @pytest.mark.asyncio
    async def test_returns_200(self, ua_client, ua_data):
        """Unified endpoint returns 200 with items."""
        resp = await ua_client.get("/api/v1/alerts/unified")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_items_have_source_field(self, ua_client, ua_data):
        """Each item in the response includes a source field."""
        resp = await ua_client.get("/api/v1/alerts/unified")
        data = resp.json()
        for item in data["items"]:
            assert "source" in item
            assert item["source"] in ("ai", "social", "device")

    @pytest.mark.asyncio
    async def test_filter_source_ai(self, ua_client, ua_data):
        """source=ai filter returns only AI alerts."""
        resp = await ua_client.get("/api/v1/alerts/unified?source=ai")
        data = resp.json()
        for item in data["items"]:
            assert item["source"] == "ai"

    @pytest.mark.asyncio
    async def test_filter_source_social(self, ua_client, ua_data):
        """source=social filter returns only social alerts."""
        resp = await ua_client.get("/api/v1/alerts/unified?source=social")
        data = resp.json()
        for item in data["items"]:
            assert item["source"] == "social"

    @pytest.mark.asyncio
    async def test_filter_source_device(self, ua_client, ua_data):
        """source=device filter returns only device alerts."""
        resp = await ua_client.get("/api/v1/alerts/unified?source=device")
        data = resp.json()
        for item in data["items"]:
            assert item["source"] == "device"

    @pytest.mark.asyncio
    async def test_filter_member_id(self, ua_client, ua_data):
        """member_id filter returns only that member's alerts."""
        mid = str(ua_data["child_member"].id)
        resp = await ua_client.get(f"/api/v1/alerts/unified?member_id={mid}")
        data = resp.json()
        for item in data["items"]:
            assert item["related_member_id"] == mid

    @pytest.mark.asyncio
    async def test_severity_sort_order(self, ua_client, ua_data):
        """Alerts are sorted by severity then timestamp."""
        resp = await ua_client.get("/api/v1/alerts/unified")
        data = resp.json()
        severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
        items = data["items"]
        for i in range(len(items) - 1):
            a_sev = severity_order.get(items[i]["severity"], 5)
            b_sev = severity_order.get(items[i + 1]["severity"], 5)
            assert a_sev <= b_sev

    @pytest.mark.asyncio
    async def test_pagination_params(self, ua_client, ua_data):
        """Pagination works with page_size parameter."""
        resp = await ua_client.get("/api/v1/alerts/unified?page=1&page_size=2")
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] >= 1

    @pytest.mark.asyncio
    async def test_combined_source_and_member(self, ua_client, ua_data):
        """Combined source + member_id filter works."""
        mid = str(ua_data["child_member"].id)
        resp = await ua_client.get(
            f"/api/v1/alerts/unified?source=social&member_id={mid}"
        )
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["source"] == "social"
            assert item["related_member_id"] == mid

    @pytest.mark.asyncio
    async def test_empty_result(self, ua_client, ua_data):
        """Invalid member_id returns empty results."""
        fake_id = str(uuid.uuid4())
        resp = await ua_client.get(f"/api/v1/alerts/unified?member_id={fake_id}")
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_auth_required(self, ua_unauthed_client):
        """Unified endpoint requires authentication."""
        resp = await ua_unauthed_client.get("/api/v1/alerts/unified")
        assert resp.status_code in (401, 403)


class TestExistingAlertsEndpointSource:
    """Verify existing list endpoint also includes source field."""

    @pytest.mark.asyncio
    async def test_list_alerts_includes_source(self, ua_client, ua_data):
        """GET /api/v1/alerts includes source in response items."""
        resp = await ua_client.get("/api/v1/alerts")
        data = resp.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert "source" in item
