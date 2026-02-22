"""Custom exceptions and exception handlers."""

import traceback

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


class BhapiException(Exception):
    """Base exception for the Bhapi AI Portal."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(BhapiException):
    """Resource not found."""

    def __init__(self, resource: str, resource_id: str | None = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id '{resource_id}' not found"
        super().__init__(message, "NOT_FOUND", status.HTTP_404_NOT_FOUND)


class UnauthorizedError(BhapiException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, "UNAUTHORIZED", status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(BhapiException):
    """Access forbidden."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "FORBIDDEN", status.HTTP_403_FORBIDDEN)


class ValidationError(BhapiException):
    """Validation failed."""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR", 422)


class ConflictError(BhapiException):
    """Resource conflict."""

    def __init__(self, message: str):
        super().__init__(message, "CONFLICT", status.HTTP_409_CONFLICT)


class RateLimitError(BhapiException):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMITED", status.HTTP_429_TOO_MANY_REQUESTS)


async def bhapi_exception_handler(request: Request, exc: BhapiException) -> JSONResponse:
    """Handle BhapiException and return JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "code": exc.code,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=str(request.url.path),
        traceback=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An unexpected error occurred",
            "code": "INTERNAL_ERROR",
        },
    )
