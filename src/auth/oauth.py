"""OAuth2 service for SSO providers (Google, Microsoft, Apple)."""

import secrets
import time
from dataclasses import dataclass
from uuid import uuid4

import httpx
import structlog
from jose import JWTError
from jose import jwt as jose_jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import OAuthConnection, User
from src.config import get_settings
from src.encryption import encrypt_credential
from src.exceptions import UnauthorizedError, ValidationError

logger = structlog.get_logger()
settings = get_settings()

# Apple JWKS cache for JWT signature verification
_apple_jwks_cache: dict = {"keys": [], "fetched_at": 0}
_JWKS_CACHE_TTL = 3600  # 1 hour


@dataclass
class OAuthProviderConfig:
    """Configuration for an OAuth2 provider."""

    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: list[str]
    # Apple uses form_post response mode
    response_mode: str | None = None


PROVIDER_CONFIGS: dict[str, OAuthProviderConfig] = {
    "google": OAuthProviderConfig(
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
        scopes=["openid", "email", "profile"],
    ),
    "microsoft": OAuthProviderConfig(
        authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        userinfo_url="https://graph.microsoft.com/v1.0/me",
        scopes=["openid", "email", "profile"],
    ),
    "apple": OAuthProviderConfig(
        authorize_url="https://appleid.apple.com/auth/authorize",
        token_url="https://appleid.apple.com/auth/token",
        userinfo_url="",  # Apple returns user info in the ID token
        scopes=["name", "email"],
        response_mode="form_post",
    ),
}

SUPPORTED_PROVIDERS = set(PROVIDER_CONFIGS.keys())


@dataclass
class OAuthUserInfo:
    """User information extracted from OAuth provider."""

    provider: str
    provider_user_id: str
    email: str
    display_name: str
    access_token: str
    refresh_token: str | None = None


def _generate_apple_client_secret() -> str:
    """Generate Apple client secret JWT.

    Apple requires a JWT signed with your private key as the client_secret
    for the token exchange. The JWT is valid for up to 6 months.
    See: https://developer.apple.com/documentation/sign_in_with_apple/generate_and_validate_tokens
    """
    now = int(time.time())
    claims = {
        "iss": settings.oauth_apple_team_id,
        "iat": now,
        "exp": now + (86400 * 180),  # 6 months
        "aud": "https://appleid.apple.com",
        "sub": settings.oauth_apple_client_id,
    }
    headers = {
        "kid": settings.oauth_apple_key_id,
        "alg": "ES256",
    }
    return jose_jwt.encode(claims, settings.oauth_apple_client_secret, algorithm="ES256", headers=headers)


def _get_client_id(provider: str) -> str:
    """Get client ID for a provider. Raises if not configured."""
    if provider == "google":
        client_id = settings.oauth_google_client_id
    elif provider == "microsoft":
        client_id = settings.oauth_microsoft_client_id
    elif provider == "apple":
        client_id = settings.oauth_apple_client_id
    else:
        raise ValidationError(f"Unsupported OAuth provider: {provider}")

    if not client_id:
        raise ValidationError(f"OAuth provider '{provider}' is not configured")

    return client_id


def _get_client_credentials(provider: str) -> tuple[str, str]:
    """Get client ID and secret for a provider. Raises if not configured."""
    client_id = _get_client_id(provider)

    if provider == "apple":
        if not all([settings.oauth_apple_team_id, settings.oauth_apple_key_id, settings.oauth_apple_client_secret]):
            raise ValidationError("Apple OAuth requires TEAM_ID, KEY_ID, and private key (CLIENT_SECRET)")
        return client_id, _generate_apple_client_secret()

    if provider == "google":
        client_secret = settings.oauth_google_client_secret
    elif provider == "microsoft":
        client_secret = settings.oauth_microsoft_client_secret
    else:
        raise ValidationError(f"Unsupported OAuth provider: {provider}")

    if not client_secret:
        raise ValidationError(f"OAuth provider '{provider}' is not configured")

    return client_id, client_secret


def get_authorization_url(provider: str) -> tuple[str, str]:
    """Build OAuth2 authorization URL with state parameter.

    Returns (authorization_url, state).
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise ValidationError(f"Unsupported OAuth provider: {provider}")

    config = PROVIDER_CONFIGS[provider]
    client_id = _get_client_id(provider)
    state = secrets.token_urlsafe(32)

    redirect_uri = f"{settings.oauth_redirect_base_url}/api/v1/auth/oauth/{provider}/callback"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(config.scopes),
        "state": state,
    }

    if config.response_mode:
        params["response_mode"] = config.response_mode

    "&".join(f"{k}={httpx.QueryParams({k: v})}" for k, v in params.items())
    # Use httpx URL building for proper encoding
    url = httpx.URL(config.authorize_url, params=params)
    authorization_url = str(url)

    logger.info("oauth_authorize_url_generated", provider=provider)
    return authorization_url, state


async def exchange_code_for_tokens(
    provider: str, code: str
) -> dict:
    """Exchange authorization code for access/refresh tokens.

    Returns the token response dict.
    """
    config = PROVIDER_CONFIGS[provider]
    client_id, client_secret = _get_client_credentials(provider)
    redirect_uri = f"{settings.oauth_redirect_base_url}/api/v1/auth/oauth/{provider}/callback"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            config.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Accept": "application/json"},
        )

    if resp.status_code != 200:
        logger.error(
            "oauth_token_exchange_failed",
            provider=provider,
            status=resp.status_code,
            body=resp.text[:200],
        )
        raise UnauthorizedError(f"OAuth token exchange failed for {provider}")

    return resp.json()


async def get_oauth_user_info(provider: str, access_token: str, id_token: str | None = None) -> OAuthUserInfo:
    """Fetch user profile from OAuth provider.

    For Apple, user info comes from the ID token (JWT) rather than a userinfo endpoint.
    """
    config = PROVIDER_CONFIGS[provider]

    if provider == "apple":
        return await _parse_apple_id_token(id_token or "", access_token)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            config.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if resp.status_code != 200:
        logger.error("oauth_userinfo_failed", provider=provider, status=resp.status_code)
        raise UnauthorizedError(f"Failed to fetch user info from {provider}")

    data = resp.json()

    if provider == "google":
        return OAuthUserInfo(
            provider="google",
            provider_user_id=data["sub"],
            email=data["email"],
            display_name=data.get("name", data["email"].split("@")[0]),
            access_token=access_token,
        )
    elif provider == "microsoft":
        return OAuthUserInfo(
            provider="microsoft",
            provider_user_id=data["id"],
            email=data.get("mail") or data.get("userPrincipalName", ""),
            display_name=data.get("displayName", ""),
            access_token=access_token,
        )

    raise ValidationError(f"Unsupported provider: {provider}")


async def _fetch_apple_jwks() -> list[dict]:
    """Fetch Apple's JWKS (JSON Web Key Set) for JWT signature verification.

    Results are cached for 1 hour to avoid hitting Apple's endpoint on every request.
    """
    now = time.time()
    if _apple_jwks_cache["keys"] and (now - _apple_jwks_cache["fetched_at"]) < _JWKS_CACHE_TTL:
        return _apple_jwks_cache["keys"]

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://appleid.apple.com/auth/keys", timeout=10.0)
            resp.raise_for_status()
            jwks = resp.json()
            _apple_jwks_cache["keys"] = jwks.get("keys", [])
            _apple_jwks_cache["fetched_at"] = now
            logger.info("apple_jwks_fetched", key_count=len(_apple_jwks_cache["keys"]))
            return _apple_jwks_cache["keys"]
    except httpx.HTTPError as exc:
        logger.error("apple_jwks_fetch_failed", error=str(exc))
        # Return stale cache if available, otherwise raise
        if _apple_jwks_cache["keys"]:
            logger.warning("apple_jwks_using_stale_cache")
            return _apple_jwks_cache["keys"]
        raise UnauthorizedError("Failed to fetch Apple's signing keys") from exc


def _parse_apple_id_token_unverified(id_token: str, access_token: str) -> OAuthUserInfo:
    """Parse Apple's ID token WITHOUT signature verification (dev/test only).

    This is used in development and test environments where real Apple tokens
    are not available.
    """
    import base64
    import json

    if not id_token:
        raise UnauthorizedError("Apple ID token is required")

    parts = id_token.split(".")
    if len(parts) != 3:
        raise UnauthorizedError("Invalid Apple ID token format")

    # Add padding for base64 decode
    payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))

    return OAuthUserInfo(
        provider="apple",
        provider_user_id=payload.get("sub", ""),
        email=payload.get("email", ""),
        display_name=payload.get("email", "").split("@")[0],
        access_token=access_token,
    )


async def _parse_apple_id_token(id_token: str, access_token: str) -> OAuthUserInfo:
    """Parse and verify Apple's ID token (JWT) to extract user info.

    In production, verifies the JWT signature against Apple's JWKS endpoint.
    In development/test, falls back to unverified parsing.
    """
    if not id_token:
        raise UnauthorizedError("Apple ID token is required")

    # Dev/test: skip signature verification (no real Apple tokens available)
    if settings.is_development or settings.is_test:
        return _parse_apple_id_token_unverified(id_token, access_token)

    # Production: full JWT signature verification against Apple's JWKS
    try:
        # Get the key ID from the JWT header
        unverified_header = jose_jwt.get_unverified_header(id_token)
        kid = unverified_header.get("kid")
        if not kid:
            raise UnauthorizedError("Apple ID token missing key ID (kid) in header")

        # Fetch Apple's JWKS and find matching key
        jwks = await _fetch_apple_jwks()
        signing_key = None
        for key in jwks:
            if key.get("kid") == kid:
                signing_key = key
                break

        if not signing_key:
            # Key not found — force refresh cache in case Apple rotated keys
            _apple_jwks_cache["fetched_at"] = 0
            jwks = await _fetch_apple_jwks()
            for key in jwks:
                if key.get("kid") == kid:
                    signing_key = key
                    break

        if not signing_key:
            raise UnauthorizedError("No matching key found in Apple's JWKS")

        # Verify and decode the JWT
        payload = jose_jwt.decode(
            id_token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.oauth_apple_client_id,
            issuer="https://appleid.apple.com",
        )

        return OAuthUserInfo(
            provider="apple",
            provider_user_id=payload.get("sub", ""),
            email=payload.get("email", ""),
            display_name=payload.get("email", "").split("@")[0],
            access_token=access_token,
        )

    except JWTError as exc:
        logger.error("apple_jwt_verification_failed", error=str(exc))
        raise UnauthorizedError(f"Invalid Apple ID token: {exc}") from exc


async def find_or_create_oauth_user(
    db: AsyncSession, user_info: OAuthUserInfo
) -> User:
    """Find existing user by OAuth connection or email, or create a new one.

    Priority:
    1. Match by OAuthConnection.provider_user_id (existing SSO link)
    2. Match by User.email (link SSO to existing email/password account)
    3. Create new User (no password) + OAuthConnection
    """
    # 1. Check existing OAuth connection
    result = await db.execute(
        select(OAuthConnection).where(
            OAuthConnection.provider == user_info.provider,
            OAuthConnection.provider_user_id == user_info.provider_user_id,
        )
    )
    existing_conn = result.scalar_one_or_none()

    if existing_conn:
        # Update tokens
        existing_conn.access_token_encrypted = encrypt_credential(user_info.access_token)
        if user_info.refresh_token:
            existing_conn.refresh_token_encrypted = encrypt_credential(user_info.refresh_token)
        await db.flush()

        user_result = await db.execute(select(User).where(User.id == existing_conn.user_id))
        user = user_result.scalar_one()
        logger.info("oauth_login_existing", provider=user_info.provider, user_id=str(user.id))
        return user

    # 2. Check existing user by email
    result = await db.execute(select(User).where(User.email == user_info.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Link OAuth to existing account
        conn = OAuthConnection(
            id=uuid4(),
            user_id=existing_user.id,
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
            access_token_encrypted=encrypt_credential(user_info.access_token),
            refresh_token_encrypted=(
                encrypt_credential(user_info.refresh_token) if user_info.refresh_token else None
            ),
        )
        db.add(conn)
        await db.flush()
        logger.info("oauth_linked_existing_user", provider=user_info.provider, user_id=str(existing_user.id))
        return existing_user

    # 3. Create new user (no password — OAuth only)
    new_user = User(
        id=uuid4(),
        email=user_info.email,
        password_hash=None,
        display_name=user_info.display_name,
        account_type="family",  # Default; user can change later
        email_verified=True,  # OAuth emails are pre-verified by the provider
    )
    db.add(new_user)
    await db.flush()

    conn = OAuthConnection(
        id=uuid4(),
        user_id=new_user.id,
        provider=user_info.provider,
        provider_user_id=user_info.provider_user_id,
        access_token_encrypted=encrypt_credential(user_info.access_token),
        refresh_token_encrypted=(
            encrypt_credential(user_info.refresh_token) if user_info.refresh_token else None
        ),
    )
    db.add(conn)
    await db.flush()
    await db.refresh(new_user)

    logger.info("oauth_user_created", provider=user_info.provider, user_id=str(new_user.id))
    return new_user
