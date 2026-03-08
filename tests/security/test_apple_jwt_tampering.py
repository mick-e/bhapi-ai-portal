"""Security tests for Apple JWT tampering prevention."""

import base64
import json

import pytest

from src.auth.oauth import _parse_apple_id_token
from src.exceptions import UnauthorizedError


def _make_fake_jwt(payload: dict, header: dict | None = None) -> str:
    """Create a fake JWT token (unsigned)."""
    hdr = header or {"alg": "RS256", "kid": "test-kid"}
    hdr_b64 = base64.urlsafe_b64encode(json.dumps(hdr).encode()).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    sig_b64 = base64.urlsafe_b64encode(b"fake-signature").rstrip(b"=").decode()
    return f"{hdr_b64}.{payload_b64}.{sig_b64}"


@pytest.mark.asyncio
async def test_empty_token_rejected():
    """Empty Apple ID token should be rejected."""
    with pytest.raises(UnauthorizedError, match="Apple ID token is required"):
        await _parse_apple_id_token("", "access-token")


@pytest.mark.asyncio
async def test_malformed_token_rejected():
    """Token without 3 parts should be rejected."""
    with pytest.raises(UnauthorizedError, match="Invalid Apple ID token"):
        await _parse_apple_id_token("not.a.valid.jwt.token", "access-token")

    with pytest.raises(UnauthorizedError, match="Invalid Apple ID token"):
        await _parse_apple_id_token("onlyonepart", "access-token")


@pytest.mark.asyncio
async def test_valid_dev_mode_token_parsed():
    """In dev/test mode, a structurally valid JWT should be parsed."""
    # In test environment, signature is not verified (dev mode fallback)
    token = _make_fake_jwt({
        "sub": "apple-user-123",
        "email": "test@example.com",
        "iss": "https://appleid.apple.com",
    })
    result = await _parse_apple_id_token(token, "access-token")
    assert result.provider == "apple"
    assert result.provider_user_id == "apple-user-123"
    assert result.email == "test@example.com"
