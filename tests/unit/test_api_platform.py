"""Unit tests for the API platform module."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_platform.models import APIKeyTier, APIUsageRecord, OAuthClient, OAuthToken
from src.api_platform.oauth import (
    _hash_token,
    exchange_code_for_tokens,
    generate_authorization_code,
    refresh_access_token,
    revoke_token,
    validate_access_token,
    validate_pkce,
)
from src.api_platform.schemas import OAuthClientCreate, VALID_SCOPES
from src.api_platform.service import (
    approve_client,
    get_client,
    get_usage,
    list_clients,
    list_tiers,
    record_usage,
    register_client,
)
from src.auth.models import User
from src.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def platform_user(test_session: AsyncSession):
    """Create a user for API platform tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"platform-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="API Partner",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()
    return user


@pytest_asyncio.fixture
async def approved_client(test_session: AsyncSession, platform_user):
    """Create an approved OAuth client with known credentials."""
    import secrets as _secrets
    client_secret = "test-secret-supersecure-xyz-1234567890"
    secret_hash = _hash_token(client_secret)
    client = OAuthClient(
        id=uuid.uuid4(),
        name="Test Partner App",
        client_id=f"test_client_{uuid.uuid4().hex[:16]}",
        client_secret_hash=secret_hash,
        redirect_uris=["https://partner.example.com/callback"],
        scopes=["read:alerts", "read:compliance", "read:activity"],
        tier="partner",
        owner_id=platform_user.id,
        is_approved=True,
        is_active=True,
    )
    test_session.add(client)
    await test_session.flush()
    await test_session.refresh(client)
    return client, client_secret


@pytest_asyncio.fixture
async def seeded_tiers(test_session: AsyncSession):
    """Seed API key tiers into the test DB."""
    tiers = [
        APIKeyTier(id=uuid.uuid4(), name="school", rate_limit_per_hour=1000, max_webhooks=10, price_monthly=None),
        APIKeyTier(id=uuid.uuid4(), name="partner", rate_limit_per_hour=5000, max_webhooks=50, price_monthly=99.0),
        APIKeyTier(id=uuid.uuid4(), name="enterprise", rate_limit_per_hour=10000, max_webhooks=999, price_monthly=None),
    ]
    test_session.add_all(tiers)
    await test_session.flush()
    return tiers


# ---------------------------------------------------------------------------
# Client registration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_client_success(test_session: AsyncSession, platform_user):
    """Registering a client returns (client, secret) and sets is_approved=False."""
    data = OAuthClientCreate(
        name="My School App",
        scopes=["read:alerts", "read:activity"],
        tier="school",
    )
    client, secret = await register_client(test_session, platform_user.id, data)

    assert client.name == "My School App"
    assert client.tier == "school"
    assert client.is_approved is False
    assert client.is_active is True
    assert client.owner_id == platform_user.id
    assert len(secret) > 20
    # Secret is NOT stored in plaintext
    assert client.client_secret_hash != secret


@pytest.mark.asyncio
async def test_register_client_invalid_scope(test_session: AsyncSession, platform_user):
    """Invalid scope raises ValidationError."""
    data = OAuthClientCreate(
        name="Bad Scope App",
        scopes=["read:alerts", "write:god_mode"],
        tier="school",
    )
    with pytest.raises(ValidationError, match="Invalid scopes"):
        await register_client(test_session, platform_user.id, data)


@pytest.mark.asyncio
async def test_register_client_duplicate_name_raises(test_session: AsyncSession, platform_user):
    """Duplicate client name for same owner raises ConflictError."""
    data = OAuthClientCreate(name="Same Name", scopes=["read:alerts"], tier="school")
    await register_client(test_session, platform_user.id, data)
    await test_session.flush()

    with pytest.raises(ConflictError):
        await register_client(test_session, platform_user.id, data)


@pytest.mark.asyncio
async def test_approve_client(test_session: AsyncSession, platform_user):
    """Approving a client sets is_approved=True."""
    data = OAuthClientCreate(name="Pending App", scopes=["read:alerts"], tier="school")
    client, _ = await register_client(test_session, platform_user.id, data)
    await test_session.flush()

    assert client.is_approved is False
    approved = await approve_client(test_session, client.id)
    assert approved.is_approved is True


@pytest.mark.asyncio
async def test_approve_client_not_found(test_session: AsyncSession):
    """Approving non-existent client raises NotFoundError."""
    with pytest.raises(NotFoundError):
        await approve_client(test_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_list_clients_filters_by_owner(test_session: AsyncSession, platform_user):
    """list_clients with owner filter only returns that owner's clients."""
    other_user = User(
        id=uuid.uuid4(),
        email=f"other-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Other User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(other_user)
    await test_session.flush()

    for i in range(2):
        data = OAuthClientCreate(name=f"App {i}", scopes=["read:alerts"], tier="school")
        await register_client(test_session, platform_user.id, data)
        await test_session.flush()

    # Create one for other_user
    data = OAuthClientCreate(name="Other App", scopes=["read:alerts"], tier="school")
    await register_client(test_session, other_user.id, data)
    await test_session.flush()

    mine, total = await list_clients(test_session, owner_id=platform_user.id)
    assert total == 2
    assert all(c.owner_id == platform_user.id for c in mine)


@pytest.mark.asyncio
async def test_get_client_not_found(test_session: AsyncSession):
    """get_client raises NotFoundError for unknown ID."""
    with pytest.raises(NotFoundError):
        await get_client(test_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# PKCE validation tests
# ---------------------------------------------------------------------------


def test_validate_pkce_success():
    """Valid code_verifier matches code_challenge."""
    import base64, hashlib
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    assert validate_pkce(verifier, challenge) is True


def test_validate_pkce_wrong_verifier():
    """Wrong verifier returns False."""
    import base64, hashlib
    verifier = "correct-verifier-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    assert validate_pkce("wrong-verifier-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", challenge) is False


def test_validate_pkce_invalid_method():
    """Unsupported method raises ValidationError."""
    with pytest.raises(ValidationError, match="S256"):
        validate_pkce("verifier", "challenge", method="plain")


# ---------------------------------------------------------------------------
# Token generation and management tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_and_exchange_authorization_code(
    test_session: AsyncSession, approved_client
):
    """Full authorization code → token exchange flow."""
    import base64, hashlib
    client, secret = approved_client
    user_id = uuid.uuid4()

    # Create a user with this ID
    user = User(
        id=user_id,
        email=f"flow-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Flow User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    code = generate_authorization_code(
        client_id=client.client_id,
        user_id=user_id,
        scopes=["read:alerts"],
        redirect_uri="https://partner.example.com/callback",
        code_challenge=challenge,
    )
    assert len(code) > 10

    access_token, refresh_token, scopes = await exchange_code_for_tokens(
        db=test_session,
        code=code,
        client_id_str=client.client_id,
        client_secret=secret,
        redirect_uri="https://partner.example.com/callback",
        code_verifier=verifier,
    )

    assert len(access_token) > 10
    assert len(refresh_token) > 10
    assert scopes == ["read:alerts"]


@pytest.mark.asyncio
async def test_exchange_code_replay_attack(test_session: AsyncSession, approved_client):
    """Authorization code cannot be reused after exchange."""
    import base64, hashlib
    client, secret = approved_client
    user_id = uuid.uuid4()

    user = User(
        id=user_id,
        email=f"replay-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Replay User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    code = generate_authorization_code(
        client_id=client.client_id,
        user_id=user_id,
        scopes=["read:alerts"],
        redirect_uri="https://partner.example.com/callback",
        code_challenge=challenge,
    )

    # First exchange succeeds
    await exchange_code_for_tokens(
        db=test_session,
        code=code,
        client_id_str=client.client_id,
        client_secret=secret,
        redirect_uri="https://partner.example.com/callback",
        code_verifier=verifier,
    )

    # Second exchange should fail (code consumed)
    with pytest.raises(UnauthorizedError, match="Invalid or expired authorization code"):
        await exchange_code_for_tokens(
            db=test_session,
            code=code,
            client_id_str=client.client_id,
            client_secret=secret,
            redirect_uri="https://partner.example.com/callback",
            code_verifier=verifier,
        )


@pytest.mark.asyncio
async def test_refresh_token_rotation(test_session: AsyncSession, approved_client):
    """Refresh token exchange issues a new pair and revokes the old token."""
    import base64, hashlib
    client, secret = approved_client
    user_id = uuid.uuid4()

    user = User(
        id=user_id,
        email=f"refresh-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Refresh User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    code = generate_authorization_code(
        client_id=client.client_id,
        user_id=user_id,
        scopes=["read:activity"],
        redirect_uri="https://partner.example.com/callback",
        code_challenge=challenge,
    )
    _, refresh_token, _ = await exchange_code_for_tokens(
        db=test_session,
        code=code,
        client_id_str=client.client_id,
        client_secret=secret,
        redirect_uri="https://partner.example.com/callback",
        code_verifier=verifier,
    )

    new_access, new_refresh, scopes = await refresh_access_token(
        db=test_session,
        refresh_token=refresh_token,
        client_id_str=client.client_id,
        client_secret=secret,
    )
    assert new_access != refresh_token
    assert new_refresh != refresh_token
    assert scopes == ["read:activity"]


@pytest.mark.asyncio
async def test_revoke_token(test_session: AsyncSession, approved_client):
    """Revoking a token marks it as revoked."""
    import base64, hashlib
    client, secret = approved_client
    user_id = uuid.uuid4()

    user = User(
        id=user_id,
        email=f"revoke-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Revoke User",
        account_type="school",
        email_verified=True,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    code = generate_authorization_code(
        client_id=client.client_id,
        user_id=user_id,
        scopes=["read:alerts"],
        redirect_uri="https://partner.example.com/callback",
        code_challenge=challenge,
    )
    access_token, _, _ = await exchange_code_for_tokens(
        db=test_session,
        code=code,
        client_id_str=client.client_id,
        client_secret=secret,
        redirect_uri="https://partner.example.com/callback",
        code_verifier=verifier,
    )
    await test_session.flush()

    result = await revoke_token(
        db=test_session,
        token_str=access_token,
        client_id_str=client.client_id,
        client_secret=secret,
    )
    assert result is True


# ---------------------------------------------------------------------------
# Scope enforcement tests
# ---------------------------------------------------------------------------


def test_generate_code_invalid_scope_raises():
    """generate_authorization_code with invalid scope raises ValidationError."""
    with pytest.raises(ValidationError, match="Invalid scopes"):
        generate_authorization_code(
            client_id="some_client",
            user_id=uuid.uuid4(),
            scopes=["read:alerts", "write:everything"],
            redirect_uri="https://example.com/cb",
            code_challenge="abc123",
        )


def test_all_valid_scopes():
    """Confirm all declared scopes are valid."""
    expected = {
        "read:alerts", "read:compliance", "read:activity",
        "write:webhooks", "read:risk_scores", "read:checkins", "read:screen_time",
    }
    assert VALID_SCOPES == expected


# ---------------------------------------------------------------------------
# Tier rate limit config tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tiers(test_session: AsyncSession, seeded_tiers):
    """list_tiers returns all seeded tiers."""
    tiers = await list_tiers(test_session)
    tier_names = {t.name for t in tiers}
    assert "school" in tier_names
    assert "partner" in tier_names
    assert "enterprise" in tier_names


@pytest.mark.asyncio
async def test_tier_rate_limits(test_session: AsyncSession, seeded_tiers):
    """Tier configurations have correct rate limits."""
    tiers = await list_tiers(test_session)
    tier_map = {t.name: t for t in tiers}

    assert tier_map["school"].rate_limit_per_hour == 1000
    assert tier_map["school"].max_webhooks == 10
    assert tier_map["school"].price_monthly is None

    assert tier_map["partner"].rate_limit_per_hour == 5000
    assert tier_map["partner"].max_webhooks == 50
    assert tier_map["partner"].price_monthly == 99.0

    assert tier_map["enterprise"].rate_limit_per_hour == 10000
    assert tier_map["enterprise"].max_webhooks == 999


# ---------------------------------------------------------------------------
# Usage recording tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_usage_creates_record(test_session: AsyncSession, approved_client):
    """record_usage creates a daily record for a client."""
    client, _ = approved_client
    record = await record_usage(test_session, client.id)
    assert record.client_id == client.id
    assert record.request_count == 1


@pytest.mark.asyncio
async def test_record_usage_increments(test_session: AsyncSession, approved_client):
    """record_usage increments count on subsequent calls."""
    client, _ = approved_client
    await record_usage(test_session, client.id)
    await test_session.flush()
    record = await record_usage(test_session, client.id)
    assert record.request_count == 2


@pytest.mark.asyncio
async def test_record_usage_webhook(test_session: AsyncSession, approved_client):
    """record_usage with webhook_delivery=True also increments webhook_deliveries."""
    client, _ = approved_client
    record = await record_usage(test_session, client.id, webhook_delivery=True)
    assert record.webhook_deliveries == 1


@pytest.mark.asyncio
async def test_get_usage_returns_summary(test_session: AsyncSession, approved_client):
    """get_usage returns usage summary with correct totals."""
    client, _ = approved_client
    await record_usage(test_session, client.id)
    await record_usage(test_session, client.id)
    await test_session.flush()

    usage = await get_usage(test_session, client.id, days=30)
    assert usage.client_id == client.id
    assert usage.total_requests >= 2
