"""End-to-end tests for the screen time module."""

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
from src.device_agent.models import ScreenTimeRecord
from src.groups.models import Group, GroupMember
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
    """Create test data for E2E screen time tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"st-e2e-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="ST E2E Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    e2e_session.add(user)
    await e2e_session.flush()

    group = Group(
        id=uuid.uuid4(), name="ST E2E Family", type="family", owner_id=user.id
    )
    e2e_session.add(group)
    await e2e_session.flush()

    # Preteen child (age ~11, 2 extension requests/day)
    preteen = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Preteen E2E",
        date_of_birth=datetime(
            datetime.now(timezone.utc).year - 11, 6, 15, tzinfo=timezone.utc
        ),
    )
    # Young child (0 extension requests/day)
    young = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Young E2E",
        date_of_birth=datetime(
            datetime.now(timezone.utc).year - 7, 3, 10, tzinfo=timezone.utc
        ),
    )
    e2e_session.add_all([preteen, young])
    await e2e_session.flush()

    return {"user": user, "group": group, "preteen": preteen, "young": young}


@pytest.fixture
async def e2e_client(e2e_engine, e2e_session, e2e_data):
    """HTTP client authenticated as the E2E parent user."""
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
# POST /api/v1/screen-time/rules
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_rule_endpoint(e2e_client, e2e_data):
    """POST /screen-time/rules creates a rule."""
    resp = await e2e_client.post("/api/v1/screen-time/rules", json={
        "member_id": str(e2e_data["preteen"].id),
        "app_category": "social",
        "daily_limit_minutes": 60,
        "age_tier_enforcement": "hard_block",
        "enabled": True,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["app_category"] == "social"
    assert body["daily_limit_minutes"] == 60
    assert body["age_tier_enforcement"] == "hard_block"
    assert "id" in body


@pytest.mark.asyncio
async def test_create_rule_invalid_category(e2e_client, e2e_data):
    """POST /screen-time/rules with invalid category returns 422."""
    resp = await e2e_client.post("/api/v1/screen-time/rules", json={
        "member_id": str(e2e_data["preteen"].id),
        "app_category": "adult_content",
        "daily_limit_minutes": 60,
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/screen-time/rules/{child_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_rules_empty(e2e_client, e2e_data):
    """GET /screen-time/rules/{child_id} returns empty list."""
    resp = await e2e_client.get(f"/api/v1/screen-time/rules/{e2e_data['preteen'].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_get_rules_returns_created_rule(e2e_client, e2e_data):
    """GET /screen-time/rules/{child_id} returns created rules."""
    await e2e_client.post("/api/v1/screen-time/rules", json={
        "member_id": str(e2e_data["preteen"].id),
        "app_category": "games",
        "daily_limit_minutes": 45,
    })
    resp = await e2e_client.get(f"/api/v1/screen-time/rules/{e2e_data['preteen'].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["app_category"] == "games"


# ---------------------------------------------------------------------------
# POST /api/v1/screen-time/schedules + GET
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_schedule_endpoint(e2e_client, e2e_data):
    """POST /screen-time/schedules creates a schedule."""
    # Create rule first
    rule_resp = await e2e_client.post("/api/v1/screen-time/rules", json={
        "member_id": str(e2e_data["preteen"].id),
        "app_category": "games",
        "daily_limit_minutes": 45,
    })
    rule_id = rule_resp.json()["id"]

    resp = await e2e_client.post("/api/v1/screen-time/schedules", json={
        "rule_id": rule_id,
        "day_type": "weekday",
        "blocked_start": "22:00:00",
        "blocked_end": "08:00:00",
        "description": "Bedtime block",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["day_type"] == "weekday"
    assert body["description"] == "Bedtime block"


@pytest.mark.asyncio
async def test_get_schedules_endpoint(e2e_client, e2e_data):
    """GET /screen-time/schedules/{rule_id} returns schedules."""
    rule_resp = await e2e_client.post("/api/v1/screen-time/rules", json={
        "member_id": str(e2e_data["preteen"].id),
        "app_category": "games",
        "daily_limit_minutes": 45,
    })
    rule_id = rule_resp.json()["id"]

    await e2e_client.post("/api/v1/screen-time/schedules", json={
        "rule_id": rule_id,
        "day_type": "weekday",
        "blocked_start": "22:00:00",
        "blocked_end": "08:00:00",
    })

    resp = await e2e_client.get(f"/api/v1/screen-time/schedules/{rule_id}")
    assert resp.status_code == 200
    schedules = resp.json()
    assert len(schedules) == 1


# ---------------------------------------------------------------------------
# GET /api/v1/screen-time/evaluate/{child_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_endpoint_no_rules(e2e_client, e2e_data):
    """GET /screen-time/evaluate/{child_id} returns empty evaluations when no rules."""
    resp = await e2e_client.get(f"/api/v1/screen-time/evaluate/{e2e_data['preteen'].id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["evaluations"] == []


# ---------------------------------------------------------------------------
# POST /api/v1/screen-time/extension-request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extension_request_endpoint(e2e_client, e2e_data, e2e_session):
    """Full flow: create rule → child requests extension → parent approves."""
    # Create rule
    rule_resp = await e2e_client.post("/api/v1/screen-time/rules", json={
        "member_id": str(e2e_data["preteen"].id),
        "app_category": "games",
        "daily_limit_minutes": 30,
    })
    rule_id = rule_resp.json()["id"]

    # Child requests extension
    ext_resp = await e2e_client.post("/api/v1/screen-time/extension-request", json={
        "member_id": str(e2e_data["preteen"].id),
        "rule_id": rule_id,
        "requested_minutes": 15,
    })
    assert ext_resp.status_code == 201
    ext_id = ext_resp.json()["id"]
    assert ext_resp.json()["status"] == "pending"

    # Parent approves
    approve_resp = await e2e_client.put(
        f"/api/v1/screen-time/extension-request/{ext_id}",
        params={"approved": "true"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_extension_request_young_denied(e2e_client, e2e_data, e2e_session):
    """Young children cannot make extension requests."""
    rule_resp = await e2e_client.post("/api/v1/screen-time/rules", json={
        "member_id": str(e2e_data["young"].id),
        "app_category": "games",
        "daily_limit_minutes": 30,
    })
    rule_id = rule_resp.json()["id"]

    ext_resp = await e2e_client.post("/api/v1/screen-time/extension-request", json={
        "member_id": str(e2e_data["young"].id),
        "rule_id": rule_id,
        "requested_minutes": 15,
    })
    assert ext_resp.status_code == 422


@pytest.mark.asyncio
async def test_extension_request_rate_limit_exceeded(e2e_client, e2e_data, e2e_session):
    """Extension requests beyond daily limit return 429."""
    rule_resp = await e2e_client.post("/api/v1/screen-time/rules", json={
        "member_id": str(e2e_data["preteen"].id),
        "app_category": "games",
        "daily_limit_minutes": 30,
    })
    rule_id = rule_resp.json()["id"]

    # Make 2 requests (preteen limit)
    for _ in range(2):
        r = await e2e_client.post("/api/v1/screen-time/extension-request", json={
            "member_id": str(e2e_data["preteen"].id),
            "rule_id": rule_id,
            "requested_minutes": 15,
        })
        assert r.status_code == 201

    # Third request should fail
    third = await e2e_client.post("/api/v1/screen-time/extension-request", json={
        "member_id": str(e2e_data["preteen"].id),
        "rule_id": rule_id,
        "requested_minutes": 15,
    })
    assert third.status_code == 429


# ---------------------------------------------------------------------------
# GET /api/v1/screen-time/extension-requests/{child_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_extension_requests(e2e_client, e2e_data):
    """GET /screen-time/extension-requests/{child_id} lists requests."""
    rule_resp = await e2e_client.post("/api/v1/screen-time/rules", json={
        "member_id": str(e2e_data["preteen"].id),
        "app_category": "games",
        "daily_limit_minutes": 30,
    })
    rule_id = rule_resp.json()["id"]

    await e2e_client.post("/api/v1/screen-time/extension-request", json={
        "member_id": str(e2e_data["preteen"].id),
        "rule_id": rule_id,
        "requested_minutes": 15,
    })

    resp = await e2e_client.get(
        f"/api/v1/screen-time/extension-requests/{e2e_data['preteen'].id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "pending"


# ---------------------------------------------------------------------------
# GET /api/v1/screen-time/{child_id}/report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_weekly_report_endpoint_empty(e2e_client, e2e_data):
    """GET /screen-time/{child_id}/report returns empty report."""
    resp = await e2e_client.get(f"/api/v1/screen-time/{e2e_data['preteen'].id}/report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_minutes"] == 0.0
    assert body["days_with_data"] == 0


@pytest.mark.asyncio
async def test_weekly_report_with_device_data(e2e_client, e2e_data, e2e_session):
    """Weekly report aggregates ScreenTimeRecord data from device agent."""
    today = datetime.now(timezone.utc).date()

    rec = ScreenTimeRecord(
        id=uuid.uuid4(),
        member_id=e2e_data["preteen"].id,
        group_id=e2e_data["group"].id,
        date=today,
        total_minutes=90.0,
        category_breakdown={"social": 45.0, "games": 45.0},
        pickups=8,
    )
    e2e_session.add(rec)
    await e2e_session.flush()

    resp = await e2e_client.get(f"/api/v1/screen-time/{e2e_data['preteen'].id}/report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_minutes"] == 90.0
    assert body["days_with_data"] == 1
    assert "social" in body["category_totals"]
    assert "games" in body["category_totals"]
