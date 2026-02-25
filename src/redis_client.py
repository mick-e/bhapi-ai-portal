"""Redis client for caching and rate limiting."""

from contextlib import asynccontextmanager

import redis.asyncio as redis
import structlog

from src.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

_redis_pool: redis.ConnectionPool | None = None
_redis_client: redis.Redis | None = None
_redis_available: bool = False
_redis_disabled: bool = False


def is_redis_disabled() -> bool:
    """Check if Redis was intentionally disabled (redis_url not configured)."""
    return _redis_disabled


async def init_redis() -> redis.Redis | None:
    """Initialize Redis connection pool and client."""
    global _redis_pool, _redis_client, _redis_available, _redis_disabled

    if not settings.redis_url or settings.redis_url.strip() == "":
        logger.info("redis_disabled", msg="REDIS_URL not configured")
        _redis_available = False
        _redis_disabled = True
        return None

    try:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=10,
            decode_responses=True,
        )
        _redis_client = redis.Redis(connection_pool=_redis_pool)
        await _redis_client.ping()
        _redis_available = True
        return _redis_client
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e), msg="Running without Redis")
        _redis_available = False
        _redis_client = None
        _redis_pool = None
        return None


async def close_redis() -> None:
    """Close Redis connections."""
    global _redis_pool, _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None


def get_redis() -> redis.Redis | None:
    """Get Redis client instance. Returns None if unavailable."""
    return _redis_client


def is_redis_available() -> bool:
    """Check if Redis is available."""
    return _redis_available


@asynccontextmanager
async def redis_lock(key: str, timeout: int = 10):
    """Distributed lock using Redis."""
    client = get_redis()
    if not client:
        yield False
        return
    lock = client.lock(key, timeout=timeout)
    acquired = await lock.acquire(blocking=True, blocking_timeout=timeout)
    try:
        yield acquired
    finally:
        if acquired:
            await lock.release()
