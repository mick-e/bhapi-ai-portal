"""OAuth 2.0 provider — authorization code flow with PKCE.

Supports scopes: read:alerts, read:compliance, read:activity, write:webhooks,
                 read:risk_scores, read:checkins, read:screen_time

Token lifetimes:
  - Authorization code: 10 minutes
  - Access token: 1 hour
  - Refresh token: 30 days
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api_platform.models import OAuthClient, OAuthToken
from src.api_platform.schemas import VALID_SCOPES
from src.exceptions import ForbiddenError, NotFoundError, UnauthorizedError, ValidationError

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACCESS_TOKEN_TTL = timedelta(hours=1)
REFRESH_TOKEN_TTL = timedelta(days=30)
AUTH_CODE_TTL = timedelta(minutes=10)

# In-memory auth code store: code_hash -> {client_id, user_id, scopes, redirect_uri, expires_at}
# Production would use Redis; for now an in-memory dict suffices (single-process)
_auth_codes: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------


def validate_pkce(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """Validate PKCE code_verifier against stored code_challenge.

    Returns True if the verifier matches the challenge.
    """
    if method != "S256":
        raise ValidationError("Only S256 code_challenge_method is supported")

    digest = hashlib.sha256(code_verifier.encode()).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return secrets.compare_digest(computed, code_challenge)


# ---------------------------------------------------------------------------
# Token hashing helpers
# ---------------------------------------------------------------------------


def _hash_token(token: str) -> str:
    """SHA-256 hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_token(length: int = 48) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


# ---------------------------------------------------------------------------
# Authorization code flow
# ---------------------------------------------------------------------------


def generate_authorization_code(
    client_id: str,
    user_id: UUID,
    scopes: list[str],
    redirect_uri: str,
    code_challenge: str,
    code_challenge_method: str = "S256",
) -> str:
    """Generate and store an authorization code.

    Returns the plaintext code to be sent to the client.
    """
    # Validate requested scopes
    invalid = set(scopes) - VALID_SCOPES
    if invalid:
        raise ValidationError(f"Invalid scopes: {', '.join(sorted(invalid))}")

    code = _generate_token(32)
    code_hash = _hash_token(code)

    expires_at = datetime.now(timezone.utc) + AUTH_CODE_TTL
    _auth_codes[code_hash] = {
        "client_id": client_id,
        "user_id": str(user_id),
        "scopes": scopes,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "expires_at": expires_at,
    }

    logger.info(
        "oauth_code_generated",
        client_id=client_id,
        user_id=str(user_id),
        scopes=scopes,
    )
    return code


async def exchange_code_for_tokens(
    db: AsyncSession,
    code: str,
    client_id_str: str,
    client_secret: str,
    redirect_uri: str,
    code_verifier: str,
) -> tuple[str, str, list[str]]:
    """Exchange authorization code for access + refresh tokens.

    Returns (access_token, refresh_token, scopes).
    Raises appropriate BhapiException on failure.
    """
    code_hash = _hash_token(code)
    code_data = _auth_codes.pop(code_hash, None)

    if not code_data:
        raise UnauthorizedError("Invalid or expired authorization code")

    now = datetime.now(timezone.utc)
    if now > code_data["expires_at"]:
        raise UnauthorizedError("Authorization code has expired")

    if code_data["client_id"] != client_id_str:
        raise UnauthorizedError("client_id mismatch")

    if code_data["redirect_uri"] != redirect_uri:
        raise ValidationError("redirect_uri mismatch")

    # Validate PKCE
    if not validate_pkce(code_verifier, code_data["code_challenge"], code_data["code_challenge_method"]):
        raise UnauthorizedError("PKCE code_verifier validation failed")

    # Load and validate client
    client = await _get_and_validate_client(db, client_id_str, client_secret)

    # Validate scopes are within client's allowed scopes
    requested = set(code_data["scopes"])
    allowed = set(client.scopes) if client.scopes else set()
    if not requested.issubset(allowed):
        raise ForbiddenError(f"Client not authorized for scopes: {requested - allowed}")

    # Issue tokens
    access_token = _generate_token(48)
    refresh_token = _generate_token(48)

    user_id = UUID(code_data["user_id"])
    token = OAuthToken(
        id=uuid4(),
        client_id=client.id,
        user_id=user_id,
        access_token_hash=_hash_token(access_token),
        refresh_token_hash=_hash_token(refresh_token),
        scopes=code_data["scopes"],
        expires_at=now + ACCESS_TOKEN_TTL,
        refresh_expires_at=now + REFRESH_TOKEN_TTL,
        revoked=False,
    )
    db.add(token)
    await db.flush()

    logger.info(
        "oauth_tokens_issued",
        client_id=client_id_str,
        user_id=str(user_id),
        scopes=code_data["scopes"],
    )
    return access_token, refresh_token, code_data["scopes"]


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
    client_id_str: str,
    client_secret: str,
) -> tuple[str, str, list[str]]:
    """Refresh an access token using a refresh token.

    Returns (new_access_token, new_refresh_token, scopes).
    """
    client = await _get_and_validate_client(db, client_id_str, client_secret)

    refresh_hash = _hash_token(refresh_token)
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.refresh_token_hash == refresh_hash,
            OAuthToken.client_id == client.id,
            OAuthToken.revoked == False,  # noqa: E712
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise UnauthorizedError("Invalid refresh token")

    now = datetime.now(timezone.utc)
    if token.refresh_expires_at:
        # SQLite may return naive datetimes; treat as UTC
        ref_exp = token.refresh_expires_at
        if ref_exp.tzinfo is None:
            ref_exp = ref_exp.replace(tzinfo=timezone.utc)
        if now > ref_exp:
            raise UnauthorizedError("Refresh token has expired")

    # Revoke old token and issue new pair (token rotation)
    token.revoked = True
    await db.flush()

    new_access = _generate_token(48)
    new_refresh = _generate_token(48)

    new_token = OAuthToken(
        id=uuid4(),
        client_id=client.id,
        user_id=token.user_id,
        access_token_hash=_hash_token(new_access),
        refresh_token_hash=_hash_token(new_refresh),
        scopes=token.scopes,
        expires_at=now + ACCESS_TOKEN_TTL,
        refresh_expires_at=now + REFRESH_TOKEN_TTL,
        revoked=False,
    )
    db.add(new_token)
    await db.flush()

    logger.info(
        "oauth_token_refreshed",
        client_id=client_id_str,
        user_id=str(token.user_id),
    )
    return new_access, new_refresh, token.scopes


async def revoke_token(
    db: AsyncSession,
    token_str: str,
    client_id_str: str,
    client_secret: str,
) -> bool:
    """Revoke an access or refresh token.

    Returns True if a token was found and revoked, False if not found
    (per RFC 7009 — revocation of unknown tokens is not an error).
    """
    client = await _get_and_validate_client(db, client_id_str, client_secret)

    token_hash = _hash_token(token_str)

    # Try access token
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.access_token_hash == token_hash,
            OAuthToken.client_id == client.id,
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        # Try refresh token
        result = await db.execute(
            select(OAuthToken).where(
                OAuthToken.refresh_token_hash == token_hash,
                OAuthToken.client_id == client.id,
            )
        )
        token = result.scalar_one_or_none()

    if token and not token.revoked:
        token.revoked = True
        await db.flush()
        logger.info("oauth_token_revoked", client_id=client_id_str, token_id=str(token.id))
        return True

    return False


async def validate_access_token(
    db: AsyncSession,
    access_token: str,
) -> OAuthToken:
    """Validate an access token and return the OAuthToken record.

    Raises UnauthorizedError if invalid, expired, or revoked.
    """
    token_hash = _hash_token(access_token)
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.access_token_hash == token_hash,
            OAuthToken.revoked == False,  # noqa: E712
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise UnauthorizedError("Invalid access token")

    now = datetime.now(timezone.utc)
    # SQLite may return naive datetimes; treat as UTC
    exp = token.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        raise UnauthorizedError("Access token has expired")

    return token


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_and_validate_client(
    db: AsyncSession,
    client_id_str: str,
    client_secret: str,
) -> OAuthClient:
    """Load an OAuth client and validate its secret and status."""
    result = await db.execute(
        select(OAuthClient).where(OAuthClient.client_id == client_id_str)
    )
    client = result.scalar_one_or_none()

    if not client:
        raise NotFoundError("OAuthClient", client_id_str)

    if not client.is_active:
        raise ForbiddenError("OAuth client is inactive")

    if not client.is_approved:
        raise ForbiddenError("OAuth client is not yet approved")

    secret_hash = _hash_token(client_secret)
    if not secrets.compare_digest(secret_hash, client.client_secret_hash):
        raise UnauthorizedError("Invalid client_secret")

    return client
