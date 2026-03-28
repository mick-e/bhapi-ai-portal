"""Security tests: CORS configuration must not use wildcards with credentials."""

import pytest

from src.main import create_app


def test_cors_no_wildcard_methods_with_credentials():
    """CORS allow_methods must not be ['*'] when allow_credentials=True (A2-4)."""
    app = create_app()

    # Find the CORSMiddleware in the middleware stack
    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls.__name__ == "CORSMiddleware":
            cors_middleware = middleware
            break

    assert cors_middleware is not None, "CORSMiddleware not found in app middleware"

    kwargs = cors_middleware.kwargs
    assert kwargs.get("allow_credentials") is True, "Expected allow_credentials=True"

    # With credentials, wildcards are not allowed per CORS spec
    allow_methods = kwargs.get("allow_methods", [])
    assert "*" not in allow_methods, (
        "allow_methods=['*'] must not be used with allow_credentials=True"
    )

    allow_headers = kwargs.get("allow_headers", [])
    assert "*" not in allow_headers, (
        "allow_headers=['*'] must not be used with allow_credentials=True"
    )


def test_cors_allows_required_methods():
    """CORS config includes all HTTP methods needed by the API."""
    app = create_app()

    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls.__name__ == "CORSMiddleware":
            cors_middleware = middleware
            break

    assert cors_middleware is not None
    allow_methods = cors_middleware.kwargs.get("allow_methods", [])
    for method in ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]:
        assert method in allow_methods, f"Expected {method} in allow_methods"


def test_cors_allows_required_headers():
    """CORS config includes Authorization, Content-Type, and correlation headers."""
    app = create_app()

    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls.__name__ == "CORSMiddleware":
            cors_middleware = middleware
            break

    assert cors_middleware is not None
    allow_headers = cors_middleware.kwargs.get("allow_headers", [])
    for header in ["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"]:
        assert header in allow_headers, f"Expected {header} in allow_headers"
