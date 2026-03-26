"""E2E tests for push notification delivery (P2-S8).

Tests the full flow: token registration endpoint → send → unregister,
using the test HTTP client with auth overrides.
"""


import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.auth.middleware import get_current_user
from src.database import get_db
from src.dependencies import require_active_trial_or_subscription
from src.main import create_app
from src.schemas import GroupContext
from tests.conftest import make_test_group

VALID_TOKEN = "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"
VALID_TOKEN_2 = "ExponentPushToken[yyyyyyyyyyyyyyyyyyyyyy]"


@pytest_asyncio.fixture
async def push_client(test_engine):
    """HTTP client with auth override for push notification endpoints."""
    app = create_app()

    # Create user + group in DB
    async_session_maker = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session_maker() as session:
        group, owner_id = await make_test_group(session)
        group_id = group.id
        await session.commit()

    auth_context = GroupContext(
        user_id=owner_id, group_id=group_id, role="owner", permissions=["*"],
    )

    async def override_get_db():
        async with async_session_maker() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    async def fake_auth():
        return auth_context

    async def fake_trial_check():
        return auth_context

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = fake_auth
    app.dependency_overrides[require_active_trial_or_subscription] = fake_trial_check

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as ac:
        ac._test_user_id = owner_id  # type: ignore[attr-defined]
        yield ac


# ---------------------------------------------------------------------------
# Token Registration via API
# ---------------------------------------------------------------------------


class TestPushTokenEndpoints:
    """Test push token CRUD via HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_register_push_token_endpoint(self, push_client):
        """POST /api/v1/alerts/push/token registers a token."""
        resp = await push_client.post(
            "/api/v1/alerts/push/token",
            json={"token": VALID_TOKEN, "device_type": "ios"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["token"] == VALID_TOKEN
        assert data["device_type"] == "ios"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_invalid_device_type(self, push_client):
        """POST with invalid device_type returns 422."""
        resp = await push_client.post(
            "/api/v1/alerts/push/token",
            json={"token": VALID_TOKEN, "device_type": "blackberry"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_push_tokens(self, push_client):
        """GET /api/v1/alerts/push/tokens lists registered tokens."""
        # Register a token first
        await push_client.post(
            "/api/v1/alerts/push/token",
            json={"token": VALID_TOKEN, "device_type": "ios"},
        )
        resp = await push_client.get("/api/v1/alerts/push/tokens")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tokens"]) >= 1
        assert data["tokens"][0]["token"] == VALID_TOKEN

    @pytest.mark.asyncio
    async def test_unregister_push_token_endpoint(self, push_client):
        """DELETE /api/v1/alerts/push/token removes the token."""
        # Register first
        await push_client.post(
            "/api/v1/alerts/push/token",
            json={"token": VALID_TOKEN, "device_type": "ios"},
        )
        # Unregister
        resp = await push_client.request(
            "DELETE",
            "/api/v1/alerts/push/token",
            json={"token": VALID_TOKEN},
        )
        assert resp.status_code == 200
        assert resp.json()["removed"] is True

        # Verify gone
        resp = await push_client.get("/api/v1/alerts/push/tokens")
        assert len(resp.json()["tokens"]) == 0

    @pytest.mark.asyncio
    async def test_register_multiple_tokens(self, push_client):
        """Register multiple tokens for the same user."""
        await push_client.post(
            "/api/v1/alerts/push/token",
            json={"token": VALID_TOKEN, "device_type": "ios"},
        )
        await push_client.post(
            "/api/v1/alerts/push/token",
            json={"token": VALID_TOKEN_2, "device_type": "android"},
        )
        resp = await push_client.get("/api/v1/alerts/push/tokens")
        assert len(resp.json()["tokens"]) == 2

    @pytest.mark.asyncio
    async def test_upsert_token_via_endpoint(self, push_client):
        """Re-registering the same token updates device_type."""
        await push_client.post(
            "/api/v1/alerts/push/token",
            json={"token": VALID_TOKEN, "device_type": "ios"},
        )
        resp = await push_client.post(
            "/api/v1/alerts/push/token",
            json={"token": VALID_TOKEN, "device_type": "android"},
        )
        assert resp.status_code == 201
        assert resp.json()["device_type"] == "android"

        # Still only one token
        resp = await push_client.get("/api/v1/alerts/push/tokens")
        assert len(resp.json()["tokens"]) == 1

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_token(self, push_client):
        """Unregistering a non-existent token returns removed: false."""
        resp = await push_client.request(
            "DELETE",
            "/api/v1/alerts/push/token",
            json={"token": VALID_TOKEN},
        )
        assert resp.status_code == 200
        assert resp.json()["removed"] is False


# ---------------------------------------------------------------------------
# Deep Link Resolution (mobile helper)
# ---------------------------------------------------------------------------


class TestDeepLinkResolution:
    """Test the resolveDeepLink helper logic (Python mirror for validation)."""

    def test_alert_deep_link(self):
        """Alert notification maps to /alerts/:id."""
        assert _resolve({"alert_id": "abc-123"}) == "/alerts/abc-123"

    def test_post_deep_link(self):
        assert _resolve({"post_id": "post-456"}) == "/social/post/post-456"

    def test_message_deep_link(self):
        assert _resolve({"message_id": "msg-789"}) == "/messages/msg-789"

    def test_contact_request_deep_link(self):
        assert _resolve({"contact_request_id": "cr-1"}) == "/contacts/requests"

    def test_screen_override(self):
        assert _resolve({"screen": "/custom/route", "alert_id": "ignored"}) == "/custom/route"

    def test_empty_data(self):
        assert _resolve({}) is None


def _resolve(data: dict) -> str | None:
    """Mirror of TypeScript resolveDeepLink for testing."""
    if data.get("screen"):
        return data["screen"]
    if data.get("alert_id"):
        return f"/alerts/{data['alert_id']}"
    if data.get("post_id"):
        return f"/social/post/{data['post_id']}"
    if data.get("message_id"):
        return f"/messages/{data['message_id']}"
    if data.get("contact_request_id"):
        return "/contacts/requests"
    return None
