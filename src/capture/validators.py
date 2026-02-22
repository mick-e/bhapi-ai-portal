"""Capture event validation — HMAC signature and replay prevention."""

import hashlib
import hmac
import time

import structlog

logger = structlog.get_logger()

# Nonce cache for replay prevention (in production, use Redis)
_nonce_cache: set[str] = set()
_nonce_cache_max_size = 10000

# Maximum age of events (5 minutes)
MAX_EVENT_AGE_SECONDS = 300


def verify_hmac_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature of a payload."""
    expected = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def check_replay(nonce: str, timestamp: float) -> bool:
    """Check for replay attacks using nonce and timestamp.

    Returns True if the request is valid (not a replay).
    """
    global _nonce_cache

    # Check timestamp freshness
    now = time.time()
    if abs(now - timestamp) > MAX_EVENT_AGE_SECONDS:
        logger.warning("replay_check_stale_timestamp", age=abs(now - timestamp))
        return False

    # Check nonce uniqueness
    if nonce in _nonce_cache:
        logger.warning("replay_check_duplicate_nonce", nonce=nonce)
        return False

    # Add nonce to cache
    _nonce_cache.add(nonce)

    # Evict old nonces if cache is too large
    if len(_nonce_cache) > _nonce_cache_max_size:
        _nonce_cache = set(list(_nonce_cache)[-(_nonce_cache_max_size // 2):])

    return True


def validate_platform(platform: str) -> bool:
    """Validate that platform is a supported AI platform."""
    return platform in {"chatgpt", "gemini", "copilot", "claude", "grok"}
