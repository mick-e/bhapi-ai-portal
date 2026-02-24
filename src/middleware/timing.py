"""Request timing and correlation ID middleware."""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request timing and attach correlation IDs.

    Each request gets a unique X-Request-ID (or uses an incoming one).
    The ID is threaded into structlog context and returned in the response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Correlation ID — honour incoming header or generate a new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind to structlog context for all downstream log calls
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000

        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"
        response.headers["X-Request-ID"] = request_id

        if process_time_ms > 100:
            logger.warning(
                "slow_request",
                process_time_ms=round(process_time_ms, 2),
                status_code=response.status_code,
            )

        return response
