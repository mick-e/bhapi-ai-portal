"""FastAPI application factory."""

import time
from contextlib import asynccontextmanager

from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
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
            "script-src 'self' 'unsafe-inline'; "
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

    # --- Serve Next.js static export (production) ---
    _mount_frontend(app)

    return app


def _register_routers(app: FastAPI) -> None:
    """Register all API routers."""
    # Health endpoints
    _health_cache: dict = {"last_check_time": 0.0, "last_result": None}

    @app.get("/health", tags=["Health"])
    async def health_check():
        from src.redis_client import is_redis_available

        now = time.monotonic()
        if (
            _health_cache["last_result"] is not None
            and now - _health_cache["last_check_time"] < 10
        ):
            return _health_cache["last_result"]

        # DB connectivity is verified at startup by init_db().
        # In production, the readiness probe provides a deeper check.
        db_status = "connected"
        db_error = None
        if settings.is_production:
            try:
                from src.database import engine
                async with engine.connect() as conn:
                    await conn.execute(select_text("SELECT 1"))
            except Exception as exc:
                db_status = "error"
                db_error = f"{type(exc).__name__}: {exc}"

        redis_status = "connected" if is_redis_available() else "unavailable"

        overall = "healthy" if db_status == "connected" else "degraded"
        result = {
            "status": overall,
            "version": settings.app_version,
            "environment": settings.environment,
            "database": db_status,
            "redis": redis_status,
        }
        if db_error:
            result["database_error"] = db_error

        _health_cache["last_check_time"] = now
        _health_cache["last_result"] = result
        return result

    @app.get("/health/live", tags=["Health"])
    async def liveness():
        return {"status": "alive"}

    @app.get("/health/schema", tags=["Health"])
    async def schema_check():
        """Temporary diagnostic: check alembic version and key columns."""
        from src.database import engine
        results = {}
        try:
            async with engine.connect() as conn:
                # Check alembic version
                ver = await conn.execute(select_text("SELECT version_num FROM alembic_version"))
                row = ver.first()
                results["alembic_version"] = row[0] if row else "none"

                # Check if migration 017 columns exist
                for table, col in [
                    ("capture_events", "content_encrypted"),
                    ("risk_events", "classifier_source"),
                    ("block_rules", "auto_rule_id"),
                ]:
                    try:
                        await conn.execute(select_text(
                            f"SELECT {col} FROM {table} LIMIT 0"
                        ))
                        results[f"{table}.{col}"] = "exists"
                    except Exception as e:
                        results[f"{table}.{col}"] = f"MISSING: {e}"

                # Check if setup_codes table exists
                try:
                    await conn.execute(select_text("SELECT id FROM setup_codes LIMIT 0"))
                    results["setup_codes"] = "exists"
                except Exception as e:
                    results["setup_codes"] = f"MISSING: {e}"
        except Exception as e:
            results["error"] = str(e)
        return results

    @app.get("/health/ready", tags=["Health"])
    async def readiness():
        if settings.is_production:
            try:
                from src.database import engine
                async with engine.connect() as conn:
                    await conn.execute(select_text("SELECT 1"))
            except Exception:
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "reason": "database unavailable"},
                )
        return {"status": "ready"}

    # Root endpoint — serves frontend landing page if available, else JSON
    @app.get("/", tags=["Root"])
    async def root():
        portal_index = _get_portal_dir() / "index.html"
        if portal_index.is_file():
            return FileResponse(str(portal_index))
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

    from src.risk.router import router as risk_router, public_router as risk_public_router
    app.include_router(risk_router, prefix="/api/v1/risk", tags=["Risk"])
    app.include_router(risk_public_router, prefix="/api/v1/risk", tags=["Risk"])

    from src.jobs.router import router as jobs_router
    app.include_router(jobs_router, prefix="/internal", tags=["Jobs"])

    from src.legal.router import router as legal_router
    app.include_router(legal_router, prefix="/legal", tags=["Legal"])

    from src.integrations.router import router as integrations_router
    app.include_router(integrations_router, prefix="/api/v1/integrations", tags=["Integrations"])

    from src.blocking.router import router as blocking_router
    app.include_router(blocking_router, prefix="/api/v1/blocking", tags=["Blocking"])

    from src.analytics.router import router as analytics_router
    app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])

    from src.groups.school_router import router as school_router
    app.include_router(school_router, prefix="/api/v1/school", tags=["School"])

    from src.literacy.router import router as literacy_router
    app.include_router(literacy_router, prefix="/api/v1/literacy", tags=["Literacy"])


_PORTAL_CANDIDATES = [
    Path("/app/portal/out"),
    Path(__file__).resolve().parent.parent / "portal" / "out",
    Path.cwd() / "portal" / "out",
]

# Cached result — resolved once at import time, stable for process lifetime
_portal_dir: Path | None = None


def _get_portal_dir() -> Path:
    """Resolve the portal static export directory (cached)."""
    global _portal_dir
    if _portal_dir is not None:
        return _portal_dir
    for p in _PORTAL_CANDIDATES:
        if p.is_dir():
            _portal_dir = p
            return p
    _portal_dir = _PORTAL_CANDIDATES[0]  # fallback
    return _portal_dir


def _mount_frontend(app: FastAPI) -> None:
    """Mount the Next.js static export if the build output exists."""
    portal_dir = _get_portal_dir()
    if not portal_dir.is_dir():
        logger.info("frontend_not_found", candidates=[str(p) for p in _PORTAL_CANDIDATES])
        return

    logger.info("frontend_mounted", path=str(portal_dir))

    # Catch-all: serve the correct page HTML for client-side routes
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_frontend(request: Request, path: str):
        # Never serve frontend for API or internal routes
        if path.startswith(("api/", "internal/")):
            return JSONResponse(status_code=404, content={"detail": "Not found"})

        # Try exact file (e.g., favicon.ico, _next/static/chunks/xxx.js)
        file_path = portal_dir / path
        if file_path.is_file():
            return FileResponse(str(file_path))

        # Try path/index.html (e.g., /login -> /login/index.html)
        index_path = portal_dir / path / "index.html"
        if index_path.is_file():
            return FileResponse(str(index_path))

        # Fallback to root index.html (SPA client-side routing)
        root_index = portal_dir / "index.html"
        if root_index.is_file():
            return FileResponse(str(root_index))

        return JSONResponse(status_code=404, content={"detail": "Not found"})


# Create the app instance
app = create_app()
