"""FastAPI application factory."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text as select_text

from src.config import get_settings
from src.database import close_db, init_db
from src.exceptions import BhapiException, bhapi_exception_handler, generic_exception_handler
from src.middleware.auth import AuthMiddleware
from src.middleware.locale import LocaleMiddleware
from src.middleware.rate_limit import RateLimitMiddleware
from src.middleware.security_headers import add_security_headers
from src.middleware.timing import TimingMiddleware
from src.redis_client import close_redis, init_redis

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    logger.info("app_starting", environment=settings.environment, version=settings.app_version)

    await init_redis()
    await init_db()

    logger.info("app_started")
    yield

    # Shutdown
    logger.info("app_shutting_down")
    await close_redis()
    await close_db()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Register exception handlers
    app.add_exception_handler(BhapiException, bhapi_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # --- Middleware stack (LIFO: last added = first executed) ---

    # CORS (executed last in request, first in response)
    if settings.cors_origins:
        cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    elif settings.is_production:
        cors_origins = ["https://bhapi.ai", "https://www.bhapi.ai"]
    else:
        cors_origins = ["http://localhost:3000", "http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZip
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # Auth enforcement
    app.add_middleware(AuthMiddleware)

    # Locale detection
    app.add_middleware(LocaleMiddleware)

    # Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # Request timing
    app.add_middleware(TimingMiddleware)

    # Security headers (executed first in request)
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        # Base security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https://api.stripe.com; "
            "frame-ancestors 'none'"
        )
        # Enhanced security headers
        await add_security_headers(request, response)
        return response

    # --- Register routers ---
    _register_routers(app)

    return app


def _register_routers(app: FastAPI) -> None:
    """Register all API routers."""
    # Health endpoints
    @app.get("/health", tags=["Health"])
    async def health_check():
        from src.redis_client import is_redis_available

        # DB connectivity is verified at startup by init_db().
        # In production, the readiness probe provides a deeper check.
        db_status = "connected"
        if settings.is_production:
            try:
                from src.database import engine
                async with engine.connect() as conn:
                    await conn.execute(select_text("1"))
            except Exception:
                db_status = "error"

        redis_status = "connected" if is_redis_available() else "unavailable"

        overall = "healthy" if db_status == "connected" else "degraded"
        return {
            "status": overall,
            "version": settings.app_version,
            "environment": settings.environment,
            "database": db_status,
            "redis": redis_status,
        }

    @app.get("/health/live", tags=["Health"])
    async def liveness():
        return {"status": "alive"}

    @app.get("/health/ready", tags=["Health"])
    async def readiness():
        if settings.is_production:
            try:
                from src.database import engine
                async with engine.connect() as conn:
                    await conn.execute(select_text("1"))
            except Exception:
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "reason": "database unavailable"},
                )
        return {"status": "ready"}

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
        }

    # Module routers
    from src.auth.router import router as auth_router
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

    from src.groups.router import router as groups_router
    app.include_router(groups_router, prefix="/api/v1/groups", tags=["Groups"])

    from src.portal.router import router as portal_router
    app.include_router(portal_router, prefix="/api/v1/portal", tags=["Portal"])

    from src.capture.router import router as capture_router
    app.include_router(capture_router, prefix="/api/v1/capture", tags=["Capture"])

    from src.alerts.router import router as alerts_router
    app.include_router(alerts_router, prefix="/api/v1/alerts", tags=["Alerts"])

    from src.billing.router import router as billing_router
    app.include_router(billing_router, prefix="/api/v1/billing", tags=["Billing"])

    from src.reporting.router import router as reporting_router
    app.include_router(reporting_router, prefix="/api/v1/reports", tags=["Reporting"])

    from src.compliance.router import router as compliance_router
    app.include_router(compliance_router, prefix="/api/v1/compliance", tags=["Compliance"])

    from src.risk.router import router as risk_router
    app.include_router(risk_router, prefix="/api/v1/risk", tags=["Risk"])

    from src.jobs.router import router as jobs_router
    app.include_router(jobs_router, prefix="/internal", tags=["Jobs"])

    from src.legal.router import router as legal_router
    app.include_router(legal_router, prefix="/legal", tags=["Legal"])


# Create the app instance
app = create_app()
