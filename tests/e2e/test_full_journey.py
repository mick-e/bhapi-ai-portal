"""Comprehensive E2E journey tests covering multi-step user flows.

Three complete journeys:
1. Family Onboarding Flow — register, login, create group, add child, capture, dashboard
2. School Admin Flow — register school admin, create school, add students, invite, settings
3. Billing & Spend Flow — register, create group, subscribe, connect LLM, thresholds
"""

from datetime import datetime, timezone

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

async def _register_and_login(client: AsyncClient, email: str, password: str = "SecurePass1",
                               display_name: str = "Test User",
                               account_type: str = "family"):
    """Register a user, login, and return (token, user_id)."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "display_name": display_name,
        "account_type": account_type,
    })
    assert reg.status_code == 201, f"Register failed: {reg.status_code} {reg.text}"
    user_id = reg.json()["id"]

    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    assert login.status_code == 200, f"Login failed: {login.status_code} {login.text}"
    token = login.json()["access_token"]
    return token, user_id


def _event_payload(group_id, member_id, platform="chatgpt", event_type="prompt"):
    """Build a valid EventPayload dict."""
    return {
        "group_id": group_id,
        "member_id": member_id,
        "platform": platform,
        "session_id": "sess-journey-001",
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Fixture — self-contained client with committing DB session
# ---------------------------------------------------------------------------

@pytest.fixture
async def journey_client():
    """Test client with committing DB session for journey tests.

    Uses the same pattern as test_capture_events.py: in-memory SQLite with
    a single AsyncSession that commits after each request so subsequent
    queries see prior mutations.
    """
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
        yield client

    await session.close()
    await engine.dispose()


# ===========================================================================
# Journey 1: Family Onboarding Flow
# ===========================================================================

class TestFamilyJourney:
    """Complete family onboarding: register -> login -> group -> child ->
    capture event -> list events -> dashboard -> alerts."""

    @pytest.mark.asyncio
    async def test_family_onboarding_journey(self, journey_client):
        client = journey_client

        # ── Step 1: Register parent user ─────────────────────────────────
        reg_resp = await client.post("/api/v1/auth/register", json={
            "email": "parent@familyjourney.com",
            "password": "SecurePass1",
            "display_name": "Jane Parent",
            "account_type": "family",
        })
        assert reg_resp.status_code == 201
        parent_data = reg_resp.json()
        assert parent_data["email"] == "parent@familyjourney.com"
        assert parent_data["display_name"] == "Jane Parent"
        assert parent_data["account_type"] == "family"
        user_id = parent_data["id"]

        # ── Step 2: Login ────────────────────────────────────────────────
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "parent@familyjourney.com",
            "password": "SecurePass1",
        })
        assert login_resp.status_code == 200
        token_data = login_resp.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert token_data["expires_in"] > 0
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}

        # ── Step 3: Create family group ──────────────────────────────────
        grp_resp = await client.post("/api/v1/groups", json={
            "name": "The Johnson Family",
            "type": "family",
        }, headers=headers)
        assert grp_resp.status_code == 201
        group_data = grp_resp.json()
        assert group_data["name"] == "The Johnson Family"
        assert group_data["type"] == "family"
        assert group_data["owner_id"] == user_id
        group_id = group_data["id"]

        # ── Step 4: Add child member ─────────────────────────────────────
        mem_resp = await client.post(f"/api/v1/groups/{group_id}/members", json={
            "display_name": "Timmy Johnson",
            "role": "member",
        }, headers=headers)
        assert mem_resp.status_code == 201
        member_data = mem_resp.json()
        assert member_data["display_name"] == "Timmy Johnson"
        assert member_data["role"] == "member"
        assert member_data["group_id"] == group_id
        member_id = member_data["id"]

        # ── Step 5: Ingest a capture event ───────────────────────────────
        event_resp = await client.post("/api/v1/capture/events", json={
            "group_id": group_id,
            "member_id": member_id,
            "platform": "chatgpt",
            "session_id": "sess-family-001",
            "event_type": "prompt",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, headers=headers)
        assert event_resp.status_code == 201
        event_data = event_resp.json()
        assert event_data["platform"] == "chatgpt"
        assert event_data["event_type"] == "prompt"
        assert event_data["source_channel"] == "extension"
        event_data["id"]

        # Ingest a second event on a different platform
        event2_resp = await client.post("/api/v1/capture/events", json={
            "group_id": group_id,
            "member_id": member_id,
            "platform": "gemini",
            "session_id": "sess-family-002",
            "event_type": "response",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, headers=headers)
        assert event2_resp.status_code == 201
        assert event2_resp.json()["platform"] == "gemini"

        # ── Step 6: List events for the group ────────────────────────────
        list_resp = await client.get(
            f"/api/v1/capture/events?group_id={group_id}",
            headers=headers,
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] == 2
        assert len(list_data["items"]) == 2

        # Verify filtering by member works
        filtered_resp = await client.get(
            f"/api/v1/capture/events?group_id={group_id}&member_id={member_id}",
            headers=headers,
        )
        assert filtered_resp.status_code == 200
        assert filtered_resp.json()["total"] == 2

        # ── Step 7: Get dashboard ────────────────────────────────────────
        dash_resp = await client.get(
            f"/api/v1/portal/dashboard?group_id={group_id}",
            headers=headers,
        )
        assert dash_resp.status_code == 200
        dash_data = dash_resp.json()
        assert "active_members" in dash_data
        assert "total_members" in dash_data
        assert "recent_activity" in dash_data
        assert "alert_summary" in dash_data
        assert "spend_summary" in dash_data
        assert "risk_summary" in dash_data

        # ── Step 8: List alerts for the group ────────────────────────────
        alerts_resp = await client.get(
            f"/api/v1/alerts?group_id={group_id}",
            headers=headers,
        )
        assert alerts_resp.status_code == 200
        alerts_data = alerts_resp.json()
        # Alerts list may be empty for a brand-new group, but the endpoint works
        assert isinstance(alerts_data, list)


# ===========================================================================
# Journey 2: School Admin Flow
# ===========================================================================

class TestSchoolJourney:
    """Complete school admin flow: register -> login -> school group ->
    add students -> invite teacher -> settings."""

    @pytest.mark.asyncio
    async def test_school_admin_journey(self, journey_client):
        client = journey_client

        # ── Step 1: Register school admin ────────────────────────────────
        reg_resp = await client.post("/api/v1/auth/register", json={
            "email": "admin@schooljourney.com",
            "password": "SchoolPass1",
            "display_name": "Principal Smith",
            "account_type": "school",
        })
        assert reg_resp.status_code == 201
        admin_data = reg_resp.json()
        assert admin_data["account_type"] == "school"
        assert admin_data["display_name"] == "Principal Smith"
        admin_id = admin_data["id"]

        # ── Step 2: Login ────────────────────────────────────────────────
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@schooljourney.com",
            "password": "SchoolPass1",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # ── Step 3: Create school group ──────────────────────────────────
        grp_resp = await client.post("/api/v1/groups", json={
            "name": "Westfield Academy",
            "type": "school",
        }, headers=headers)
        assert grp_resp.status_code == 201
        school_data = grp_resp.json()
        assert school_data["name"] == "Westfield Academy"
        assert school_data["type"] == "school"
        assert school_data["owner_id"] == admin_id
        group_id = school_data["id"]

        # ── Step 4: Add 2 student members ────────────────────────────────
        student1_resp = await client.post(
            f"/api/v1/groups/{group_id}/members",
            json={"display_name": "Alice Student", "role": "member"},
            headers=headers,
        )
        assert student1_resp.status_code == 201
        student1 = student1_resp.json()
        assert student1["display_name"] == "Alice Student"
        student1["id"]

        student2_resp = await client.post(
            f"/api/v1/groups/{group_id}/members",
            json={"display_name": "Bob Student", "role": "member"},
            headers=headers,
        )
        assert student2_resp.status_code == 201
        student2 = student2_resp.json()
        assert student2["display_name"] == "Bob Student"
        student2["id"]

        # Verify both students appear in member list
        members_resp = await client.get(
            f"/api/v1/groups/{group_id}/members",
            headers=headers,
        )
        assert members_resp.status_code == 200
        members = members_resp.json()
        member_names = {m["display_name"] for m in members}
        assert "Alice Student" in member_names
        assert "Bob Student" in member_names

        # ── Step 5: Send invitation to a teacher ─────────────────────────
        invite_resp = await client.post(
            f"/api/v1/groups/{group_id}/invite",
            json={
                "email": "teacher@schooljourney.com",
                "role": "school_admin",
            },
            headers=headers,
        )
        assert invite_resp.status_code == 201
        invite_data = invite_resp.json()
        assert invite_data["email"] == "teacher@schooljourney.com"
        assert invite_data["role"] == "school_admin"
        assert invite_data["group_id"] == group_id
        assert invite_data["status"] in ("pending", "sent")
        assert "token" in invite_data
        invite_token = invite_data["token"]

        # Send a second invitation to another teacher
        invite2_resp = await client.post(
            f"/api/v1/groups/{group_id}/invite",
            json={
                "email": "teacher2@schooljourney.com",
                "role": "school_admin",
            },
            headers=headers,
        )
        assert invite2_resp.status_code == 201
        assert invite2_resp.json()["email"] == "teacher2@schooljourney.com"

        # ── Step 6: Verify invitation can be accepted ────────────────────
        # Register the invited teacher
        teacher_reg = await client.post("/api/v1/auth/register", json={
            "email": "teacher@schooljourney.com",
            "password": "TeacherPass1",
            "display_name": "Mrs. Teacher",
            "account_type": "school",
        })
        assert teacher_reg.status_code == 201

        teacher_login = await client.post("/api/v1/auth/login", json={
            "email": "teacher@schooljourney.com",
            "password": "TeacherPass1",
        })
        assert teacher_login.status_code == 200
        teacher_headers = {
            "Authorization": f"Bearer {teacher_login.json()['access_token']}"
        }

        # Accept the invitation
        accept_resp = await client.post(
            f"/api/v1/groups/invitations/{invite_token}/accept",
            headers=teacher_headers,
        )
        assert accept_resp.status_code == 201
        accepted = accept_resp.json()
        assert accepted["group_id"] == group_id
        assert accepted["role"] == "school_admin"

        # ── Step 7: Get settings ─────────────────────────────────────────
        settings_resp = await client.get(
            f"/api/v1/portal/settings?group_id={group_id}",
            headers=headers,
        )
        assert settings_resp.status_code == 200
        settings_data = settings_resp.json()
        assert settings_data["group_id"] == group_id
        assert settings_data["group_name"] == "Westfield Academy"
        assert "safety_level" in settings_data
        assert "notifications" in settings_data
        original_safety = settings_data["safety_level"]

        # ── Step 8: Update settings ──────────────────────────────────────
        new_safety = "moderate" if original_safety == "strict" else "strict"
        update_resp = await client.patch(
            f"/api/v1/portal/settings?group_id={group_id}",
            json={
                "safety_level": new_safety,
                "auto_block_critical": True,
                "pii_detection": True,
                "monthly_budget_usd": 50.0,
            },
            headers=headers,
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["safety_level"] == new_safety
        assert updated["auto_block_critical"] is True
        assert updated["pii_detection"] is True
        assert updated["monthly_budget_usd"] == 50.0

        # Verify settings persisted by re-fetching
        verify_resp = await client.get(
            f"/api/v1/portal/settings?group_id={group_id}",
            headers=headers,
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["safety_level"] == new_safety
        assert verify_resp.json()["monthly_budget_usd"] == 50.0


# ===========================================================================
# Journey 3: Billing & Spend Flow
# ===========================================================================

class TestBillingJourney:
    """Complete billing flow: register -> group -> subscribe -> connect LLM ->
    list accounts -> create threshold -> list thresholds."""

    @pytest.mark.asyncio
    async def test_billing_spend_journey(self, journey_client):
        client = journey_client

        # ── Step 1: Register + login ─────────────────────────────────────
        token, user_id = await _register_and_login(
            client,
            email="billing@billingjourney.com",
            display_name="Billing Admin",
            account_type="family",
        )
        headers = {"Authorization": f"Bearer {token}"}

        # ── Step 2: Create group ─────────────────────────────────────────
        grp_resp = await client.post("/api/v1/groups", json={
            "name": "Billing Test Family",
            "type": "family",
        }, headers=headers)
        assert grp_resp.status_code == 201
        group_id = grp_resp.json()["id"]

        # ── Step 3: Create subscription ──────────────────────────────────
        sub_resp = await client.post("/api/v1/billing/subscribe", json={
            "group_id": group_id,
            "plan_type": "family",
            "billing_cycle": "monthly",
        }, headers=headers)
        assert sub_resp.status_code == 201
        sub_data = sub_resp.json()
        assert sub_data["group_id"] == group_id
        assert sub_data["plan_type"] == "family"
        assert sub_data["billing_cycle"] == "monthly"
        assert sub_data["status"] in ("active", "trialing", "pending")
        subscription_id = sub_data["id"]

        # Verify subscription via GET
        get_sub_resp = await client.get(
            f"/api/v1/billing/subscription?group_id={group_id}",
            headers=headers,
        )
        assert get_sub_resp.status_code == 200
        assert get_sub_resp.json()["id"] == subscription_id
        assert get_sub_resp.json()["plan_type"] == "family"

        # ── Step 4: Connect LLM account (OpenAI) ────────────────────────
        llm_resp = await client.post("/api/v1/billing/llm-accounts", json={
            "group_id": group_id,
            "provider": "openai",
            "api_key": "sk-test-openai-key-for-journey-test-1234567890ab",
        }, headers=headers)
        assert llm_resp.status_code == 201
        llm_data = llm_resp.json()
        assert llm_data["group_id"] == group_id
        assert llm_data["provider"] == "openai"
        assert llm_data["status"] in ("active", "connected", "pending")
        llm_data["id"]

        # Connect a second provider (Anthropic)
        llm2_resp = await client.post("/api/v1/billing/llm-accounts", json={
            "group_id": group_id,
            "provider": "anthropic",
            "api_key": "sk-ant-test-key-for-journey-test-1234567890abcdef",
        }, headers=headers)
        assert llm2_resp.status_code == 201
        assert llm2_resp.json()["provider"] == "anthropic"
        llm2_resp.json()["id"]

        # ── Step 5: List LLM accounts ────────────────────────────────────
        list_resp = await client.get(
            f"/api/v1/billing/llm-accounts?group_id={group_id}",
            headers=headers,
        )
        assert list_resp.status_code == 200
        accounts = list_resp.json()
        assert isinstance(accounts, list)
        assert len(accounts) == 2
        providers = {a["provider"] for a in accounts}
        assert "openai" in providers
        assert "anthropic" in providers

        # ── Step 6: Create budget threshold (group-level) ────────────────
        threshold_resp = await client.post("/api/v1/billing/thresholds", json={
            "group_id": group_id,
            "type": "soft",
            "amount": 100.0,
            "currency": "USD",
            "notify_at": [50, 80, 100],
        }, headers=headers)
        assert threshold_resp.status_code == 201
        threshold_data = threshold_resp.json()
        assert threshold_data["group_id"] == group_id
        assert threshold_data["type"] == "soft"
        assert threshold_data["amount"] == 100.0
        assert threshold_data["currency"] == "USD"
        assert threshold_data["member_id"] is None  # Group-level, not member-specific
        threshold_data["id"]

        # Create a second threshold (hard limit, member-specific)
        # First, add a member to assign a per-member threshold
        mem_resp = await client.post(f"/api/v1/groups/{group_id}/members", json={
            "display_name": "Spending Child",
            "role": "member",
        }, headers=headers)
        assert mem_resp.status_code == 201
        child_member_id = mem_resp.json()["id"]

        threshold2_resp = await client.post("/api/v1/billing/thresholds", json={
            "group_id": group_id,
            "member_id": child_member_id,
            "type": "hard",
            "amount": 25.0,
            "currency": "USD",
            "notify_at": [80, 100],
        }, headers=headers)
        assert threshold2_resp.status_code == 201
        threshold2_data = threshold2_resp.json()
        assert threshold2_data["member_id"] == child_member_id
        assert threshold2_data["type"] == "hard"
        assert threshold2_data["amount"] == 25.0

        # ── Step 7: List thresholds ──────────────────────────────────────
        list_thresh_resp = await client.get(
            f"/api/v1/billing/thresholds?group_id={group_id}",
            headers=headers,
        )
        assert list_thresh_resp.status_code == 200
        thresholds = list_thresh_resp.json()
        assert isinstance(thresholds, list)
        assert len(thresholds) == 2

        # Verify both thresholds are present
        threshold_types = {t["type"] for t in thresholds}
        assert "soft" in threshold_types
        assert "hard" in threshold_types

        # Verify amounts
        amounts = sorted([t["amount"] for t in thresholds])
        assert amounts == [25.0, 100.0]

        # Verify the member-specific threshold has the correct member_id
        member_thresholds = [t for t in thresholds if t["member_id"] is not None]
        assert len(member_thresholds) == 1
        assert member_thresholds[0]["member_id"] == child_member_id
