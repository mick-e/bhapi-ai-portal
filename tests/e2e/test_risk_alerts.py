"""E2E tests for risk events and alerts modules.

Covers risk event creation/listing/filtering/acknowledgement,
risk config get/update, alert creation/listing/acknowledgement,
and notification preferences.
"""

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_login(client, email="risk@test.com"):
    """Register, return (token, user_id as str)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Risk Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


async def _create_group_and_member(client, headers):
    """Create group + child member, return (group_id str, member_id str)."""
    grp = await client.post("/api/v1/groups", json={
        "name": "Risk Family",
        "type": "family",
    }, headers=headers)
    group_id = grp.json()["id"]

    mem = await client.post(f"/api/v1/groups/{group_id}/members", json={
        "display_name": "Child",
        "role": "member",
    }, headers=headers)
    member_id = mem.json()["id"]
    return group_id, member_id


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
async def risk_client():
    """Test client with committing DB session for risk/alerts tests."""
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

    session = AsyncSession(engine, expire_on_commit=False)
    app = create_app()

    async def get_db_override():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, session  # Yield session too for direct DB operations

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Risk event tests (using service layer for creation)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_risk_events_empty(risk_client):
    """GET /risk/events with no events returns empty list."""
    client, session = risk_client
    token, user_id = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/events?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_and_list_risk_event(risk_client):
    """Create a risk event via service and list it."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "risk1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    # Create risk event via service (convert str IDs to UUID)
    from src.risk.schemas import RiskClassification
    from src.risk.service import create_risk_event

    classification = RiskClassification(
        category="SELF_HARM",
        severity="critical",
        confidence=0.85,
        reasoning="Keyword match: suicide",
    )
    await create_risk_event(session, UUID(gid), UUID(mid), classification)
    await session.commit()

    resp = await client.get(
        f"/api/v1/risk/events?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "SELF_HARM"
    assert data["items"][0]["severity"] == "critical"


@pytest.mark.asyncio
async def test_filter_risk_events_by_category(risk_client):
    """Filter risk events by category."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "risk2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    from src.risk.schemas import RiskClassification
    from src.risk.service import create_risk_event

    gid_uuid, mid_uuid = UUID(gid), UUID(mid)
    await create_risk_event(session, gid_uuid, mid_uuid, RiskClassification(
        category="SELF_HARM", severity="critical", confidence=0.9, reasoning="test"
    ))
    await create_risk_event(session, gid_uuid, mid_uuid, RiskClassification(
        category="VIOLENCE", severity="critical", confidence=0.8, reasoning="test"
    ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/risk/events?group_id={gid}&category=SELF_HARM", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "SELF_HARM"


@pytest.mark.asyncio
async def test_filter_risk_events_by_severity(risk_client):
    """Filter risk events by severity."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "risk3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    from src.risk.schemas import RiskClassification
    from src.risk.service import create_risk_event

    gid_uuid, mid_uuid = UUID(gid), UUID(mid)
    await create_risk_event(session, gid_uuid, mid_uuid, RiskClassification(
        category="SELF_HARM", severity="critical", confidence=0.9, reasoning="test"
    ))
    await create_risk_event(session, gid_uuid, mid_uuid, RiskClassification(
        category="ACADEMIC_DISHONESTY", severity="medium", confidence=0.7, reasoning="test"
    ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/risk/events?group_id={gid}&severity=medium", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["severity"] == "medium"


@pytest.mark.asyncio
async def test_filter_risk_events_by_acknowledged(risk_client):
    """Filter risk events by acknowledged status."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "risk4@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    from src.risk.schemas import RiskClassification
    from src.risk.service import create_risk_event

    await create_risk_event(session, UUID(gid), UUID(mid), RiskClassification(
        category="VIOLENCE", severity="critical", confidence=0.9, reasoning="test"
    ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/risk/events?group_id={gid}&acknowledged=false", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["acknowledged"] is False


@pytest.mark.asyncio
async def test_risk_event_pagination(risk_client):
    """Risk events support pagination."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "risk5@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    from src.risk.schemas import RiskClassification
    from src.risk.service import create_risk_event

    gid_uuid, mid_uuid = UUID(gid), UUID(mid)
    for i in range(5):
        await create_risk_event(session, gid_uuid, mid_uuid, RiskClassification(
            category="SELF_HARM", severity="critical", confidence=0.9, reasoning=f"test {i}"
        ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/risk/events?group_id={gid}&page_size=2&page=1", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 3


@pytest.mark.asyncio
async def test_get_single_risk_event(risk_client):
    """GET /risk/events/{id} returns a single event."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "risk6@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    from src.risk.schemas import RiskClassification
    from src.risk.service import create_risk_event

    ev = await create_risk_event(session, UUID(gid), UUID(mid), RiskClassification(
        category="SELF_HARM", severity="critical", confidence=0.85, reasoning="test"
    ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/risk/events/{ev.id}?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(ev.id)
    assert resp.json()["category"] == "SELF_HARM"


@pytest.mark.asyncio
async def test_acknowledge_risk_event(risk_client):
    """POST /risk/events/{id}/acknowledge marks event as acknowledged."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "risk7@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    from src.risk.schemas import RiskClassification
    from src.risk.service import create_risk_event

    ev = await create_risk_event(session, UUID(gid), UUID(mid), RiskClassification(
        category="VIOLENCE", severity="critical", confidence=0.9, reasoning="test"
    ))
    await session.commit()

    resp = await client.post(
        f"/api/v1/risk/events/{ev.id}/acknowledge?group_id={gid}",
        json={"acknowledged_by": user_id},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["acknowledged"] is True
    assert data["acknowledged_by"] == user_id


@pytest.mark.asyncio
async def test_acknowledge_already_acknowledged_event(risk_client):
    """Acknowledging already-acknowledged event returns 422."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "risk8@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    from src.risk.schemas import RiskClassification
    from src.risk.service import create_risk_event

    ev = await create_risk_event(session, UUID(gid), UUID(mid), RiskClassification(
        category="VIOLENCE", severity="critical", confidence=0.9, reasoning="test"
    ))
    await session.commit()

    # First acknowledge
    await client.post(
        f"/api/v1/risk/events/{ev.id}/acknowledge?group_id={gid}",
        json={"acknowledged_by": user_id},
        headers=headers,
    )

    # Second acknowledge should fail
    resp = await client.post(
        f"/api/v1/risk/events/{ev.id}/acknowledge?group_id={gid}",
        json={"acknowledged_by": user_id},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_nonexistent_risk_event(risk_client):
    """GET /risk/events/{nonexistent} returns 404."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "risk9@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    fake_id = str(uuid4())
    resp = await client.get(
        f"/api/v1/risk/events/{fake_id}?group_id={gid}", headers=headers
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Risk config tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_risk_config_defaults(risk_client):
    """GET /risk/config returns default configs for all categories."""
    client, session = risk_client
    token, _ = await _register_and_login(client, "config1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/config?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    configs = resp.json()
    # Should have a config for each of the 14 risk categories
    assert len(configs) == 14
    categories = {c["category"] for c in configs}
    assert "SELF_HARM" in categories
    assert "VIOLENCE" in categories
    assert "ACADEMIC_DISHONESTY" in categories


@pytest.mark.asyncio
async def test_risk_config_default_values(risk_client):
    """Default risk config has sensitivity=50 and enabled=True."""
    client, session = risk_client
    token, _ = await _register_and_login(client, "config2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/risk/config?group_id={gid}", headers=headers
    )
    configs = resp.json()
    for cfg in configs:
        assert cfg["sensitivity"] == 50
        assert cfg["enabled"] is True


@pytest.mark.asyncio
async def test_update_risk_config_sensitivity(risk_client):
    """PATCH /risk/config/{category} updates sensitivity."""
    client, session = risk_client
    token, _ = await _register_and_login(client, "config3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    resp = await client.patch(
        f"/api/v1/risk/config/SELF_HARM?group_id={gid}",
        json={"sensitivity": 90},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["sensitivity"] == 90
    assert resp.json()["category"] == "SELF_HARM"


@pytest.mark.asyncio
async def test_update_risk_config_disable(risk_client):
    """Disable a risk category via config update."""
    client, session = risk_client
    token, _ = await _register_and_login(client, "config4@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    resp = await client.patch(
        f"/api/v1/risk/config/ADULT_CONTENT?group_id={gid}",
        json={"enabled": False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


@pytest.mark.asyncio
async def test_update_invalid_category(risk_client):
    """Update config for invalid category returns 422."""
    client, session = risk_client
    token, _ = await _register_and_login(client, "config5@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    resp = await client.patch(
        f"/api/v1/risk/config/INVALID_CATEGORY?group_id={gid}",
        json={"sensitivity": 50},
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Alert tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_alerts_empty(risk_client):
    """GET /alerts returns empty for new group."""
    client, session = risk_client
    token, _ = await _register_and_login(client, "alert1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/alerts?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_and_list_alert(risk_client):
    """Create alert via service, then list it."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "alert2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    from src.alerts.schemas import AlertCreate
    from src.alerts.service import create_alert

    await create_alert(session, AlertCreate(
        group_id=UUID(gid),
        member_id=UUID(mid),
        severity="critical",
        title="Self-harm content detected",
        body="A member's interaction contains concerning language.",
        channel="portal",
    ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/alerts?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    alerts = data["items"]
    assert len(alerts) == 1
    assert alerts[0]["title"] == "Self-harm content detected"
    assert alerts[0]["read"] is False


@pytest.mark.asyncio
async def test_filter_alerts_by_severity(risk_client):
    """Filter alerts by severity level."""
    client, session = risk_client
    token, _ = await _register_and_login(client, "alert3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, mid = await _create_group_and_member(client, headers)

    from src.alerts.schemas import AlertCreate
    from src.alerts.service import create_alert

    await create_alert(session, AlertCreate(
        group_id=UUID(gid), severity="critical", title="Critical alert", body="Body 1",
    ))
    await create_alert(session, AlertCreate(
        group_id=UUID(gid), severity="low", title="Low alert", body="Body 2",
    ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/alerts?group_id={gid}&severity=critical", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    alerts = data["items"]
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "critical"


@pytest.mark.asyncio
async def test_get_single_alert(risk_client):
    """GET /alerts/{id} returns single alert."""
    client, session = risk_client
    token, _ = await _register_and_login(client, "alert4@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    from src.alerts.schemas import AlertCreate
    from src.alerts.service import create_alert

    alert = await create_alert(session, AlertCreate(
        group_id=UUID(gid), severity="high", title="PII detected", body="Details here",
    ))
    await session.commit()

    resp = await client.get(
        f"/api/v1/alerts/{alert.id}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(alert.id)
    assert resp.json()["title"] == "PII detected"


@pytest.mark.asyncio
async def test_acknowledge_alert(risk_client):
    """POST /alerts/{id}/acknowledge marks alert as acknowledged."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "alert5@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    from src.alerts.schemas import AlertCreate
    from src.alerts.service import create_alert

    alert = await create_alert(session, AlertCreate(
        group_id=UUID(gid), severity="critical", title="Alert", body="Body",
    ))
    await session.commit()

    resp = await client.post(
        f"/api/v1/alerts/{alert.id}/acknowledge", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["read"] is True
    assert resp.json()["actioned"] is True


@pytest.mark.asyncio
async def test_get_nonexistent_alert(risk_client):
    """GET /alerts/{nonexistent} returns 404."""
    client, session = risk_client
    token, _ = await _register_and_login(client, "alert6@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    fake_id = str(uuid4())
    resp = await client.get(
        f"/api/v1/alerts/{fake_id}", headers=headers
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Notification preferences
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_preferences_empty(risk_client):
    """GET /alerts/preferences returns empty for new user."""
    client, session = risk_client
    token, _ = await _register_and_login(client, "pref1@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    resp = await client.get(
        f"/api/v1/alerts/preferences?group_id={gid}", headers=headers
    )
    assert resp.status_code == 200
    # Preferences endpoint still returns flat list (not paginated)
    assert resp.json() == []


@pytest.mark.asyncio
async def test_update_preferences(risk_client):
    """PUT /alerts/preferences creates preferences."""
    client, session = risk_client
    token, user_id = await _register_and_login(client, "pref2@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    resp = await client.put(
        "/api/v1/alerts/preferences",
        json={
            "group_id": gid,
            "preferences": [
                {"category": "risk_alert", "channel": "email", "digest_mode": "immediate", "enabled": True},
                {"category": "spend_alert", "channel": "portal", "digest_mode": "daily", "enabled": False},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    prefs = resp.json()
    assert len(prefs) == 2
    categories = {p["category"] for p in prefs}
    assert "risk_alert" in categories
    assert "spend_alert" in categories


@pytest.mark.asyncio
async def test_update_preferences_upsert(risk_client):
    """Updating preferences for existing category upserts."""
    client, session = risk_client
    token, _ = await _register_and_login(client, "pref3@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    gid, _ = await _create_group_and_member(client, headers)

    # Create initial preference
    await client.put(
        "/api/v1/alerts/preferences",
        json={
            "group_id": gid,
            "preferences": [
                {"category": "risk_alert", "channel": "portal", "digest_mode": "immediate", "enabled": True},
            ],
        },
        headers=headers,
    )

    # Update same category
    resp = await client.put(
        "/api/v1/alerts/preferences",
        json={
            "group_id": gid,
            "preferences": [
                {"category": "risk_alert", "channel": "email", "digest_mode": "daily", "enabled": False},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    prefs = resp.json()
    assert len(prefs) == 1
    assert prefs[0]["channel"] == "email"
    assert prefs[0]["digest_mode"] == "daily"
    assert prefs[0]["enabled"] is False


@pytest.mark.asyncio
async def test_risk_requires_auth(risk_client):
    """Risk endpoints require auth."""
    client, _ = risk_client
    resp = await client.get(f"/api/v1/risk/events?group_id={uuid4()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_alerts_requires_auth(risk_client):
    """Alerts endpoints require auth."""
    client, _ = risk_client
    resp = await client.get(f"/api/v1/alerts?group_id={uuid4()}")
    assert resp.status_code == 401
