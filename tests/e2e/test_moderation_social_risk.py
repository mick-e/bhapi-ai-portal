"""E2E tests for social risk detection via moderation API.

Tests submit message/comment content through the moderation queue endpoint
and verify social risk scores are populated and escalation occurs for
critical/high severity.
"""

import uuid

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


async def _register(client, email="socialrisk@example.com"):
    """Register a user, return auth headers dict."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePass1",
        "display_name": "Risk Tester",
        "account_type": "family",
        "privacy_notice_accepted": True,
    })
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _submit(client, headers, content_type, content_text, age_tier=None):
    """Submit content to moderation queue, return response."""
    payload = {
        "content_type": content_type,
        "content_id": str(uuid.uuid4()),
        "content_text": content_text,
    }
    if age_tier:
        payload["age_tier"] = age_tier
    return await client.post(
        "/api/v1/moderation/queue", json=payload, headers=headers
    )


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def mod_client():
    """Test client with in-memory DB for moderation tests."""
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

    async def override_get_db():
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
    ) as ac:
        yield ac

    await session.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Tests — social risk detection via moderation API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_message_grooming_detected(mod_client):
    """Grooming patterns in message content populate social_risk scores."""
    headers = await _register(mod_client)

    resp = await _submit(
        mod_client, headers, "message",
        "you're so special, don't tell your parents"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "social_risk" in data["risk_scores"]
    assert data["risk_scores"]["social_risk"]["category"] == "grooming"


@pytest.mark.asyncio
async def test_message_bullying_detected(mod_client):
    """Cyberbullying patterns in message content are detected."""
    headers = await _register(mod_client, "bully@example.com")

    resp = await _submit(
        mod_client, headers, "message", "nobody likes you, go die"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["risk_scores"]["social_risk"]["category"] == "cyberbullying"


@pytest.mark.asyncio
async def test_message_sexting_detected(mod_client):
    """Sexting patterns in message content are detected."""
    headers = await _register(mod_client, "sext@example.com")

    resp = await _submit(
        mod_client, headers, "message", "send me a pic, take off your shirt"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["risk_scores"]["social_risk"]["category"] == "sexting"


@pytest.mark.asyncio
async def test_comment_grooming_detected(mod_client):
    """Social risk also runs on comment content_type."""
    headers = await _register(mod_client, "comment@example.com")

    resp = await _submit(
        mod_client, headers, "comment", "our secret, don't tell anyone"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "social_risk" in data["risk_scores"]


@pytest.mark.asyncio
async def test_post_no_social_risk(mod_client):
    """Post content type does NOT trigger social risk (only message/comment)."""
    headers = await _register(mod_client, "post@example.com")

    resp = await _submit(
        mod_client, headers, "post", "our secret, don't tell anyone"
    )
    assert resp.status_code == 201
    data = resp.json()
    # social_risk should NOT be in risk_scores for posts
    if data.get("risk_scores"):
        assert "social_risk" not in data["risk_scores"]


@pytest.mark.asyncio
async def test_escalation_on_critical_severity(mod_client):
    """Critical severity social risk escalates the queue entry."""
    headers = await _register(mod_client, "critical@example.com")

    resp = await _submit(
        mod_client, headers, "message",
        "kill yourself, you're ugly, nobody likes you, go die"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "escalated"
    assert data["risk_scores"]["social_risk"]["severity"] == "critical"


@pytest.mark.asyncio
async def test_escalation_on_high_severity(mod_client):
    """High severity social risk escalates the queue entry."""
    headers = await _register(mod_client, "high@example.com")

    resp = await _submit(
        mod_client, headers, "message", "I'll hurt you tomorrow"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "escalated"
    assert data["risk_scores"]["social_risk"]["severity"] == "high"


@pytest.mark.asyncio
async def test_no_escalation_on_medium_severity(mod_client):
    """Medium severity social risk does not escalate."""
    headers = await _register(mod_client, "medium@example.com")

    resp = await _submit(
        mod_client, headers, "message", "you're fat"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] != "escalated"


@pytest.mark.asyncio
async def test_safe_message_no_social_risk(mod_client):
    """Safe content does not produce social risk scores."""
    headers = await _register(mod_client, "safe@example.com")

    resp = await _submit(
        mod_client, headers, "message", "Good morning! Nice day today."
    )
    assert resp.status_code == 201
    data = resp.json()
    if data.get("risk_scores"):
        assert "social_risk" not in data["risk_scores"]


@pytest.mark.asyncio
async def test_social_risk_score_populated(mod_client):
    """Social risk result includes score and patterns."""
    headers = await _register(mod_client, "score@example.com")

    resp = await _submit(
        mod_client, headers, "message", "age is just a number"
    )
    assert resp.status_code == 201
    data = resp.json()
    sr = data["risk_scores"]["social_risk"]
    assert sr["score"] > 0
    assert "age_minimizing" in sr["patterns"]


@pytest.mark.asyncio
async def test_keyword_filter_and_social_risk_coexist(mod_client):
    """Both keyword_filter and social_risk can appear in risk_scores."""
    headers = await _register(mod_client, "both@example.com")

    # "hate" is a medium keyword; "nobody likes you" is bullying
    resp = await _submit(
        mod_client, headers, "message", "I hate you, nobody likes you"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "keyword_filter" in data["risk_scores"]
    assert "social_risk" in data["risk_scores"]


@pytest.mark.asyncio
async def test_social_risk_with_young_age_tier(mod_client):
    """Social risk is detected regardless of author age tier."""
    headers = await _register(mod_client, "young@example.com")

    resp = await _submit(
        mod_client, headers, "message",
        "I'll hurt you", age_tier="young"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "social_risk" in data["risk_scores"]


@pytest.mark.asyncio
async def test_grooming_isolation_pattern(mod_client):
    """Isolation grooming pattern triggers detection."""
    headers = await _register(mod_client, "isolation@example.com")

    resp = await _submit(
        mod_client, headers, "message", "meet me alone after class"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["risk_scores"]["social_risk"]["category"] == "grooming"
    assert "isolation" in data["risk_scores"]["social_risk"]["patterns"]


@pytest.mark.asyncio
async def test_sexting_pressure_pattern(mod_client):
    """Sexting pressure patterns detected through API."""
    headers = await _register(mod_client, "pressure@example.com")

    resp = await _submit(
        mod_client, headers, "message",
        "if you loved me you would do it, everyone does it"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["risk_scores"]["social_risk"]["category"] == "sexting"


@pytest.mark.asyncio
async def test_queue_entry_retrievable_with_social_risk(mod_client):
    """Queue entry with social risk can be retrieved by ID."""
    headers = await _register(mod_client, "retrieve@example.com")

    resp = await _submit(
        mod_client, headers, "message", "nobody likes you"
    )
    queue_id = resp.json()["id"]

    get_resp = await mod_client.get(
        f"/api/v1/moderation/queue/{queue_id}", headers=headers
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "social_risk" in data["risk_scores"]


@pytest.mark.asyncio
async def test_social_risk_in_queue_list(mod_client):
    """Social risk entries appear in the moderation queue list."""
    headers = await _register(mod_client, "qlist@example.com")

    await _submit(
        mod_client, headers, "message", "I'll hurt you"
    )

    list_resp = await mod_client.get(
        "/api/v1/moderation/queue?status=escalated", headers=headers
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1
    assert any(
        "social_risk" in item.get("risk_scores", {})
        for item in data["items"]
    )


@pytest.mark.asyncio
async def test_escalated_entry_can_be_decided(mod_client):
    """Escalated social risk entry can be decided by a moderator."""
    headers = await _register(mod_client, "decide@example.com")

    resp = await _submit(
        mod_client, headers, "message", "kill yourself"
    )
    queue_id = resp.json()["id"]

    decision_resp = await mod_client.patch(
        f"/api/v1/moderation/queue/{queue_id}/decide",
        json={"action": "reject", "reason": "Social risk: death threat"},
        headers=headers,
    )
    assert decision_resp.status_code == 200
    assert decision_resp.json()["action"] == "reject"


@pytest.mark.asyncio
async def test_multiple_messages_different_risks(mod_client):
    """Different messages produce different social risk categories."""
    headers = await _register(mod_client, "multi@example.com")

    # Grooming
    r1 = await _submit(
        mod_client, headers, "message", "our secret, don't tell anyone"
    )
    # Bullying
    r2 = await _submit(
        mod_client, headers, "message", "kill yourself"
    )

    assert r1.json()["risk_scores"]["social_risk"]["category"] == "grooming"
    assert r2.json()["risk_scores"]["social_risk"]["category"] == "cyberbullying"


@pytest.mark.asyncio
async def test_empty_message_no_social_risk(mod_client):
    """Empty message text does not trigger social risk."""
    headers = await _register(mod_client, "empty@example.com")

    resp = await mod_client.post(
        "/api/v1/moderation/queue",
        json={
            "content_type": "message",
            "content_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data.get("risk_scores") is None


@pytest.mark.asyncio
async def test_trust_building_grooming_pattern(mod_client):
    """Trust building grooming pattern detected via API."""
    headers = await _register(mod_client, "trust@example.com")

    resp = await _submit(
        mod_client, headers, "message", "you can trust me, I'm your friend"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "social_risk" in data["risk_scores"]
    assert data["risk_scores"]["social_risk"]["category"] == "grooming"
