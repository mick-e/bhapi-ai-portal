"""Rate limiting middleware — Redis sliding window with in-memory fallback."""

import time
from collections import defaultdict
from collections.abc import Callable
from threading import Lock

import redis.asyncio as redis
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config import get_settings
from src.exceptions import RateLimitError
from src.redis_client import get_redis, is_redis_available, is_redis_disabled

logger = structlog.get_logger()
settings = get_settings()


class _InMemoryRateLimiter:
    """Thread-safe in-memory sliding window rate limiter.

    Used as a fallback when Redis is unavailable. Not shared across
    multiple processes, so limits are per-worker — acceptable for MVP.
    """

    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int, int]:
        """Check rate limit. Returns (allowed, remaining, reset_seconds)."""
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # Evict expired entries
            timestamps = self._buckets[key]
            self._buckets[key] = [t for t in timestamps if t > cutoff]

            count = len(self._buckets[key])
            if count >= max_requests:
                return False, 0, int(window_seconds - (now - cutoff))

            self._buckets[key].append(now)
            remaining = max(0, max_requests - count - 1)
            return True, remaining, int(window_seconds)


# Singleton
_in_memory_limiter = _InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis sliding window algorithm.

    Falls back to an in-memory limiter when Redis is unavailable,
    instead of blocking all requests.
    """

    EXEMPT_PATHS = {
        "/health", "/health/live", "/health/ready",
        "/", "/docs", "/redoc", "/openapi.json", "/favicon.ico",
    }

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)

        if is_redis_disabled():
            # No Redis configured — use in-memory fallback
            return await self._dispatch_with_limit(request, call_next, use_memory=True)

        if not is_redis_available():
            # Redis configured but down — fall back to in-memory
            return await self._dispatch_with_limit(request, call_next, use_memory=True)

        return await self._dispatch_with_limit(request, call_next, use_memory=False)

    async def _dispatch_with_limit(self, request: Request, call_next, *, use_memory: bool):
        # Identify client by Authorization header or IP
        client_id = request.headers.get("Authorization", "")
        if not client_id:
            client_id = request.client.host if request.client else "unknown"
        key_id = client_id[:32]

        if use_memory:
            is_allowed, remaining, reset_time = _in_memory_limiter.check(
                key_id, settings.rate_limit_requests, settings.rate_limit_window_seconds
            )
        else:
            is_allowed, remaining, reset_time = await self._check_rate_limit_redis(key_id)

        if not is_allowed:
            logger.warning("rate_limit_exceeded", client=key_id[:8], path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": reset_time},
                headers={
                    "X-RateLimit-Limit": str(settings.rate_limit_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        return response

    async def _check_rate_limit_redis(self, key_id: str) -> tuple[bool, int, int]:
        """Check rate limit using Redis sliding window."""
        redis_client = get_redis()
        if not redis_client:
            # Redis went away mid-request — fall back to in-memory
            return _in_memory_limiter.check(
                key_id, settings.rate_limit_requests, settings.rate_limit_window_seconds
            )

        now = time.time()
        window_start = now - settings.rate_limit_window_seconds
        cache_key = f"ratelimit:{key_id}"

        try:
            async with redis_client.pipeline() as pipe:
                pipe.zremrangebyscore(cache_key, 0, window_start)
                pipe.zadd(cache_key, {str(now): now})
                pipe.zcard(cache_key)
                pipe.expire(cache_key, settings.rate_limit_window_seconds + 1)
                results = await pipe.execute()

            request_count = results[2]
            remaining = max(0, settings.rate_limit_requests - request_count)
            reset_time = int(settings.rate_limit_window_seconds - (now - window_start))

            if request_count > settings.rate_limit_requests:
                await redis_client.zrem(cache_key, str(now))
                return False, 0, reset_time

            return True, remaining, reset_time

        except (redis.RedisError, ConnectionError, OSError) as e:
            logger.error("rate_limit_redis_failed", error=str(e), decision="fallback_memory")
            return _in_memory_limiter.check(
                key_id, settings.rate_limit_requests, settings.rate_limit_window_seconds
            )


# ---------------------------------------------------------------------------
# Per-endpoint rate limiting dependency
# ---------------------------------------------------------------------------

# Separate in-memory limiter for endpoint-specific limits so that the global
# middleware limiter and per-endpoint limiters don't share buckets.
_endpoint_limiter = _InMemoryRateLimiter()


def endpoint_rate_limit(max_requests: int, window_seconds: int) -> Callable:
    """Return a FastAPI ``Depends()`` callable that enforces a per-IP rate
    limit on a single endpoint.

    Usage::

        @router.post("/register")
        async def register(
            ...,
            _rl=Depends(endpoint_rate_limit(5, 3600)),
        ):
            ...
    """

    async def _check(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        # Build a key that is unique per endpoint + IP
        path = request.url.path
        key = f"ep:{path}:{client_ip}"

        allowed, _remaining, retry_after = _endpoint_limiter.check(
            key, max_requests, window_seconds,
        )
        if not allowed:
            logger.warning(
                "endpoint_rate_limit_exceeded",
                client=client_ip,
                path=path,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )
            raise RateLimitError(
                f"Too many requests. Try again in {retry_after} seconds."
            )

    return _check
