"""Rate limiting middleware using Redis sliding window."""

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config import get_settings
from src.redis_client import get_redis, is_redis_available, is_redis_disabled

logger = structlog.get_logger()
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis sliding window algorithm."""

    EXEMPT_PATHS = {
        "/health", "/health/live", "/health/ready",
        "/", "/docs", "/redoc", "/openapi.json", "/favicon.ico",
    }

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)

        if is_redis_disabled():
            return await call_next(request)

        if not is_redis_available():
            if settings.rate_limit_fail_open:
                return await call_next(request)
            return JSONResponse(
                status_code=503,
                content={"error": "Service temporarily unavailable"},
                headers={"Retry-After": "30"},
            )

        # Identify client by Authorization header or IP
        client_id = request.headers.get("Authorization", "")
        if not client_id:
            client_id = request.client.host if request.client else "unknown"
        key_id = client_id[:32]

        is_allowed, remaining, reset_time = await self._check_rate_limit(key_id)

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

    async def _check_rate_limit(self, key_id: str) -> tuple[bool, int, int]:
        """Check if request is within rate limit using sliding window."""
        redis_client = get_redis()
        if not redis_client:
            if settings.rate_limit_fail_open:
                return True, settings.rate_limit_requests, 0
            return False, 0, 30

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

        except Exception as e:
            if settings.rate_limit_fail_open:
                logger.error("rate_limit_check_failed", error=str(e), decision="allow")
                return True, settings.rate_limit_requests, 0
            logger.error("rate_limit_check_failed", error=str(e), decision="deny")
            return False, 0, 30
