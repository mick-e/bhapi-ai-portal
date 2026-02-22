"""Security headers middleware."""

from starlette.requests import Request
from starlette.responses import Response


async def add_security_headers(request: Request, response: Response) -> Response:
    """Add security headers to response.

    Complements the base headers (CSP, HSTS, X-Frame-Options) set in main.py.
    """
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

    if request.url.path.startswith("/api/"):
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response
