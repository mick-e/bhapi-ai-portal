"""Request timing middleware."""

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000

        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"

        if process_time_ms > 100:
            logger.warning(
                "slow_request",
                path=request.url.path,
                method=request.method,
                process_time_ms=process_time_ms,
            )

        return response
