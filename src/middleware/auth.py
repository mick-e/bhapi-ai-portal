"""Auth enforcement middleware."""


import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = structlog.get_logger()

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/health", "/health/live", "/health/ready",
    "/", "/docs", "/redoc", "/openapi.json", "/favicon.ico",
}

PUBLIC_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/logout",
    "/api/v1/auth/oauth",
    "/api/v1/auth/password/reset",
    "/api/v1/auth/verify-email",
    "/api/v1/billing/webhooks",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforce authentication on protected routes."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for public paths
        if path in PUBLIC_PATHS:
            return await call_next(request)
        if path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)
        if path.startswith("/static") or path.startswith("/_next"):
            return await call_next(request)

        # Only enforce on API routes
        if not path.startswith("/api/"):
            return await call_next(request)

        # Check for auth token
        auth_header = request.headers.get("Authorization")
        session_cookie = request.cookies.get("bhapi_session")

        if not auth_header and not session_cookie:
            return JSONResponse(
                status_code=401,
                content={"error": "Authentication required", "code": "UNAUTHORIZED"},
            )

        return await call_next(request)
