"""Locale detection middleware."""

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()

SUPPORTED_LOCALES = {"en", "fr", "de", "it", "pt", "es"}
DEFAULT_LOCALE = "en"


class LocaleMiddleware(BaseHTTPMiddleware):
    """Detect locale from query param or Accept-Language header."""

    async def dispatch(self, request: Request, call_next) -> Response:
        locale = self._detect_locale(request)
        request.state.locale = locale

        response = await call_next(request)
        response.headers["Content-Language"] = locale
        return response

    def _detect_locale(self, request: Request) -> str:
        # Query param takes precedence
        locale_param = request.query_params.get("locale", "").lower()
        if locale_param in SUPPORTED_LOCALES:
            return locale_param

        # Parse Accept-Language header
        accept_lang = request.headers.get("Accept-Language", "")
        for part in accept_lang.split(","):
            lang = part.split(";")[0].strip().split("-")[0].lower()
            if lang in SUPPORTED_LOCALES:
                return lang

        return DEFAULT_LOCALE
