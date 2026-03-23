"""Unit tests for API platform webhook delivery and rate limiting."""

import hashlib
import hmac
import json
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_platform.models import (
    APIKeyTier,
    APIUsageRecord,
    OAuthClient,
    PlatformWebhookDelivery,
    PlatformWebhookEndpoint,
)
from src.api_platform.oauth import _hash_token
from src.api_platform.service import (
    check_rate_limit,
    delete_webhook,
    get_tier,
    get_webhook,
    list_webhook_deliveries,
    list_webhooks,
    record_usage,
    register_webhook,
)
from src.api_platform.webhooks import (
    RETRY_DELAYS,
    WEBHOOK_EVENTS,
    deliver_event_to_subscribers,
    deliver_webhook,
    sign_payload,
    verify_signature,
)
from src.auth.models import User
from src.exceptions import ForbiddenError, NotFoundError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def wh_user(test_session: AsyncSession):
    """A user for webhook tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"wh-user-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Webhook Tester",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest_asyncio.fixture
async def approved_oauth_client(test_session: AsyncSession, wh_user):
    """Approved OAuth client for webhook tests."""
    client = OAuthClient(
        id=uuid.uuid4(),
        name="WH Test App",
        client_id=f"wh_client_{uuid.uuid4().hex[:16]}",
        client_secret_hash=_hash_token("wh-secret-xyz-12345"),
        scopes=["read:alerts", "write:webhooks"],
        tier="partner",
        owner_id=wh_user.id,
        is_approved=True,
        is_active=True,
    )
    test_session.add(client)
    await test_session.flush()
    await test_session.refresh(client)
    return client


@pytest_asyncio.fixture
async def wh_tiers(test_session: AsyncSession):
    """Seed tiers for rate-limit tests."""
    tiers = [
        APIKeyTier(
            id=uuid.uuid4(), name="school",
            rate_limit_per_hour=1000, max_webhooks=10, price_monthly=None,
        ),
        APIKeyTier(
            id=uuid.uuid4(), name="partner",
            rate_limit_per_hour=5000, max_webhooks=50, price_monthly=99.0,
        ),
        APIKeyTier(
            id=uuid.uuid4(), name="enterprise",
            rate_limit_per_hour=10000, max_webhooks=999, price_monthly=None,
        ),
    ]
    test_session.add_all(tiers)
    await test_session.flush()
    return tiers


@pytest_asyncio.fixture
async def wh_endpoint(test_session: AsyncSession, approved_oauth_client):
    """A registered webhook endpoint."""
    webhook_secret = "wh-signing-secret-abc-987654321"
    endpoint = PlatformWebhookEndpoint(
        id=uuid.uuid4(),
        client_id=approved_oauth_client.id,
        url="https://example.com/webhook",
        events=["alert.created", "risk_score.changed"],
        secret_hash=_hash_token(webhook_secret),
        is_active=True,
    )
    test_session.add(endpoint)
    await test_session.flush()
    await test_session.refresh(endpoint)
    return endpoint, webhook_secret


# ---------------------------------------------------------------------------
# 1. HMAC signature generation
# ---------------------------------------------------------------------------


def test_sign_payload_returns_hex_string():
    """sign_payload returns a 64-char hex string (SHA-256 digest)."""
    sig = sign_payload('{"event": "ping"}', "mysecret")
    assert isinstance(sig, str)
    assert len(sig) == 64


def test_sign_payload_consistent():
    """Same payload + secret always produces the same signature."""
    payload = '{"event": "alert.created", "id": "123"}'
    secret = "consistent-secret"
    assert sign_payload(payload, secret) == sign_payload(payload, secret)


def test_sign_payload_differs_by_secret():
    """Different secrets produce different signatures."""
    payload = '{"event": "ping"}'
    assert sign_payload(payload, "secret-a") != sign_payload(payload, "secret-b")


def test_sign_payload_differs_by_payload():
    """Different payloads produce different signatures."""
    secret = "shared-secret"
    assert sign_payload('{"event": "a"}', secret) != sign_payload('{"event": "b"}', secret)


def test_sign_payload_matches_manual_hmac():
    """sign_payload output matches a manually computed HMAC-SHA256."""
    payload = '{"id": 1}'
    secret = "test-secret"
    expected = hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    assert sign_payload(payload, secret) == expected


# ---------------------------------------------------------------------------
# 2. Signature verification
# ---------------------------------------------------------------------------


def test_verify_signature_valid():
    """verify_signature returns True for a correct signature."""
    payload = '{"event": "ping"}'
    secret = "my-secret"
    sig = sign_payload(payload, secret)
    assert verify_signature(payload, secret, sig) is True


def test_verify_signature_tampered_payload():
    """verify_signature returns False when payload is tampered."""
    payload = '{"event": "ping"}'
    secret = "my-secret"
    sig = sign_payload(payload, secret)
    assert verify_signature('{"event": "TAMPERED"}', secret, sig) is False


def test_verify_signature_wrong_secret():
    """verify_signature returns False with a different secret."""
    payload = '{"event": "ping"}'
    sig = sign_payload(payload, "real-secret")
    assert verify_signature(payload, "wrong-secret", sig) is False


# ---------------------------------------------------------------------------
# 3. WEBHOOK_EVENTS constant
# ---------------------------------------------------------------------------


def test_webhook_events_list_contains_expected():
    """WEBHOOK_EVENTS contains all expected platform event types."""
    expected = {
        "alert.created",
        "risk_score.changed",
        "compliance.report_ready",
        "checkin.event",
        "screen_time.limit_reached",
    }
    assert set(WEBHOOK_EVENTS) == expected


def test_retry_delays_are_correct():
    """RETRY_DELAYS are 10s, 60s, 300s."""
    assert RETRY_DELAYS == [10, 60, 300]


# ---------------------------------------------------------------------------
# 4. deliver_webhook — success path (mocked HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deliver_webhook_success(test_session: AsyncSession, wh_endpoint):
    """deliver_webhook returns a delivery record with delivered=True on 200."""
    endpoint, _ = wh_endpoint

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.elapsed.total_seconds.return_value = 0.05

    with patch("src.api_platform.webhooks.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        delivery = await deliver_webhook(
            test_session,
            endpoint,
            event_type="alert.created",
            payload={"alert_id": "abc123", "severity": "high"},
        )

    assert delivery.delivered is True
    assert delivery.status_code == 200
    assert delivery.event_type == "alert.created"
    assert delivery.attempt_count >= 1
    assert delivery.endpoint_id == endpoint.id


# ---------------------------------------------------------------------------
# 5. deliver_webhook — non-2xx response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deliver_webhook_non_2xx(test_session: AsyncSession, wh_endpoint):
    """deliver_webhook sets delivered=False on a 500 response."""
    endpoint, _ = wh_endpoint

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.elapsed.total_seconds.return_value = 0.1

    with patch("src.api_platform.webhooks.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        delivery = await deliver_webhook(
            test_session,
            endpoint,
            event_type="risk_score.changed",
            payload={"score": 80},
        )

    assert delivery.delivered is False
    assert delivery.status_code == 500


# ---------------------------------------------------------------------------
# 6. deliver_webhook — network error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deliver_webhook_network_error(test_session: AsyncSession, wh_endpoint):
    """deliver_webhook captures network errors in the error field."""
    endpoint, _ = wh_endpoint

    with patch("src.api_platform.webhooks.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=ConnectionError("Connection refused"))
        mock_client_cls.return_value = mock_client

        delivery = await deliver_webhook(
            test_session,
            endpoint,
            event_type="alert.created",
            payload={"test": True},
        )

    assert delivery.delivered is False
    assert delivery.error is not None
    assert "Connection refused" in delivery.error


# ---------------------------------------------------------------------------
# 7. deliver_webhook — HMAC header is set correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deliver_webhook_sets_hmac_header(test_session: AsyncSession, wh_endpoint):
    """deliver_webhook sends X-Bhapi-Signature header with sha256= prefix."""
    endpoint, _ = wh_endpoint
    captured_headers = {}

    async def capture_post(url, content, headers):
        captured_headers.update(headers)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.elapsed.total_seconds.return_value = 0.02
        return mock_resp

    with patch("src.api_platform.webhooks.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = capture_post
        mock_client_cls.return_value = mock_client

        await deliver_webhook(
            test_session,
            endpoint,
            event_type="ping",
            payload={"test": True},
        )

    assert "X-Bhapi-Signature" in captured_headers
    assert captured_headers["X-Bhapi-Signature"].startswith("sha256=")
    assert "X-Bhapi-Event" in captured_headers
    assert captured_headers["X-Bhapi-Event"] == "ping"
    assert "X-Bhapi-Timestamp" in captured_headers


# ---------------------------------------------------------------------------
# 8. Event filtering in deliver_event_to_subscribers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deliver_event_to_subscribers_filtering(
    test_session: AsyncSession, approved_oauth_client
):
    """Only endpoints subscribed to the event (or '*') receive delivery."""
    # Endpoint 1: subscribed to alert.created
    ep1 = PlatformWebhookEndpoint(
        id=uuid.uuid4(),
        client_id=approved_oauth_client.id,
        url="https://example.com/ep1",
        events=["alert.created"],
        secret_hash=_hash_token("secret1"),
        is_active=True,
    )
    # Endpoint 2: subscribed to risk_score.changed (should NOT receive alert.created)
    ep2 = PlatformWebhookEndpoint(
        id=uuid.uuid4(),
        client_id=approved_oauth_client.id,
        url="https://example.com/ep2",
        events=["risk_score.changed"],
        secret_hash=_hash_token("secret2"),
        is_active=True,
    )
    # Endpoint 3: wildcard subscriber (should receive everything)
    ep3 = PlatformWebhookEndpoint(
        id=uuid.uuid4(),
        client_id=approved_oauth_client.id,
        url="https://example.com/ep3",
        events=["*"],
        secret_hash=_hash_token("secret3"),
        is_active=True,
    )
    # Endpoint 4: inactive — should be skipped
    ep4 = PlatformWebhookEndpoint(
        id=uuid.uuid4(),
        client_id=approved_oauth_client.id,
        url="https://example.com/ep4",
        events=["alert.created"],
        secret_hash=_hash_token("secret4"),
        is_active=False,
    )
    test_session.add_all([ep1, ep2, ep3, ep4])
    await test_session.flush()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.elapsed.total_seconds.return_value = 0.01

    with patch("src.api_platform.webhooks.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        deliveries = await deliver_event_to_subscribers(
            test_session,
            event_type="alert.created",
            payload={"alert_id": "xyz"},
        )

    # ep1 and ep3 should receive it; ep2 and ep4 should not
    delivered_endpoint_ids = {str(d.endpoint_id) for d in deliveries}
    assert str(ep1.id) in delivered_endpoint_ids
    assert str(ep3.id) in delivered_endpoint_ids
    assert str(ep2.id) not in delivered_endpoint_ids
    assert str(ep4.id) not in delivered_endpoint_ids


# ---------------------------------------------------------------------------
# 9. Service: register_webhook enforces tier limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_webhook_tier_limit(
    test_session: AsyncSession, approved_oauth_client, wh_tiers,
):
    """register_webhook raises ForbiddenError when tier webhook limit reached."""
    # The approved_oauth_client is tier="partner" — max_webhooks=50
    # Set client tier to "school" (max 10) for easier testing
    approved_oauth_client.tier = "school"
    await test_session.flush()

    # Create 10 active webhooks to hit the school tier limit
    for i in range(10):
        ep = PlatformWebhookEndpoint(
            id=uuid.uuid4(),
            client_id=approved_oauth_client.id,
            url=f"https://example.com/wh{i}",
            events=["alert.created"],
            secret_hash=_hash_token(f"secret-{i}"),
            is_active=True,
        )
        test_session.add(ep)
    await test_session.flush()

    with pytest.raises(ForbiddenError, match="Webhook limit"):
        await register_webhook(
            test_session,
            client_db_id=approved_oauth_client.id,
            url="https://example.com/overflow",
            events=["alert.created"],
            secret="new-secret-12345",
        )


# ---------------------------------------------------------------------------
# 10. Service: delete_webhook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_webhook_sets_inactive(test_session: AsyncSession, wh_endpoint):
    """delete_webhook deactivates the endpoint."""
    endpoint, _ = wh_endpoint
    await delete_webhook(
        test_session,
        endpoint_id=endpoint.id,
        client_db_id=endpoint.client_id,
    )
    await test_session.flush()

    fetched = await get_webhook(test_session, endpoint.id)
    assert fetched.is_active is False


@pytest.mark.asyncio
async def test_delete_webhook_wrong_client_raises(
    test_session: AsyncSession, wh_endpoint
):
    """delete_webhook raises ForbiddenError for wrong client_id."""
    endpoint, _ = wh_endpoint
    wrong_client_id = uuid.uuid4()

    with pytest.raises(ForbiddenError, match="does not belong"):
        await delete_webhook(
            test_session,
            endpoint_id=endpoint.id,
            client_db_id=wrong_client_id,
        )


@pytest.mark.asyncio
async def test_delete_webhook_not_found_raises(
    test_session: AsyncSession, approved_oauth_client
):
    """delete_webhook raises NotFoundError for unknown endpoint ID."""
    with pytest.raises(NotFoundError):
        await delete_webhook(
            test_session,
            endpoint_id=uuid.uuid4(),
            client_db_id=approved_oauth_client.id,
        )


# ---------------------------------------------------------------------------
# 11. Service: list_webhook_deliveries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_webhook_deliveries(test_session: AsyncSession, wh_endpoint):
    """list_webhook_deliveries returns paginated delivery records."""
    endpoint, _ = wh_endpoint

    # Seed some delivery records
    for i in range(3):
        test_session.add(PlatformWebhookDelivery(
            id=uuid.uuid4(),
            endpoint_id=endpoint.id,
            event_type="alert.created",
            payload={"i": i},
            status_code=200 if i < 2 else 500,
            attempt_count=1,
            delivered=i < 2,
        ))
    await test_session.flush()

    deliveries, total = await list_webhook_deliveries(
        test_session, endpoint_id=endpoint.id, limit=10,
    )
    assert total == 3
    assert len(deliveries) == 3


# ---------------------------------------------------------------------------
# 12. Service: check_rate_limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_rate_limit_allows_under_limit(
    test_session: AsyncSession, approved_oauth_client, wh_tiers,
):
    """check_rate_limit returns True when request count is under hourly limit."""
    allowed = await check_rate_limit(
        test_session,
        client_db_id=approved_oauth_client.id,
        tier_name="partner",  # 5000/hr limit
    )
    assert allowed is True  # No usage record yet


@pytest.mark.asyncio
async def test_check_rate_limit_blocks_over_limit(
    test_session: AsyncSession, approved_oauth_client, wh_tiers,
):
    """check_rate_limit returns False when request count exceeds hourly limit."""
    # Seed a usage record exceeding the school tier limit (1000)
    record = APIUsageRecord(
        id=uuid.uuid4(),
        client_id=approved_oauth_client.id,
        date=date.today(),
        request_count=1001,
        webhook_deliveries=0,
    )
    test_session.add(record)
    await test_session.flush()

    allowed = await check_rate_limit(
        test_session,
        client_db_id=approved_oauth_client.id,
        tier_name="school",  # 1000/hr limit
    )
    assert allowed is False


@pytest.mark.asyncio
async def test_check_rate_limit_unknown_tier_allows(
    test_session: AsyncSession, approved_oauth_client,
):
    """check_rate_limit returns True for an unknown tier (fail-open)."""
    allowed = await check_rate_limit(
        test_session,
        client_db_id=approved_oauth_client.id,
        tier_name="nonexistent_tier",
    )
    assert allowed is True
