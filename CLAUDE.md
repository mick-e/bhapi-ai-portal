# Bhapi Family AI Governance Portal

## Overview
AI safety and governance platform for families, schools, and clubs. Monitors children's AI tool usage across ChatGPT, Gemini, Copilot, Claude, and Grok with real-time risk alerting, PII protection, and spend management.

**Platform URL:** bhapi.ai
**Stack:** FastAPI (Python) backend + Next.js React TypeScript frontend

## Key Commands

### Development
```bash
# Backend
uvicorn src.main:app --reload --port 8000

# Frontend (portal/)
cd portal && npm run dev
```

### Testing
```bash
# All backend tests
pytest tests/ -v

# E2E tests (in-memory SQLite, no keys needed)
pytest tests/e2e/ -v

# Unit tests
pytest tests/unit/ -v

# Security tests
pytest tests/security/ -v

# Frontend
cd portal && npx vitest run
cd portal && npx tsc --noEmit
```

### Build
```bash
docker compose up --build
```

## Project Structure

### Backend (`src/`)
- `src/main.py` — FastAPI app factory, middleware, router registration
- `src/config.py` — Pydantic Settings (env-based), production validation
- `src/database.py` — SQLAlchemy async engine, session factory, soft-delete filter
- `src/dependencies.py` — FastAPI DI (`DbSession`, `AuthContext`, `Pagination`)
- `src/exceptions.py` — Exception hierarchy (`BhapiException` base)
- `src/constants.py` — Shared constants
- `src/redis_client.py` — Redis connection with graceful degradation

### Modules
| Module | Prefix | Description |
|--------|--------|-------------|
| `auth/` | `/api/v1/auth` | Registration, login, SSO, MFA, sessions |
| `groups/` | `/api/v1/groups` | Groups, members, invitations, consent |
| `capture/` | `/api/v1/capture` | Event ingestion from extension/DNS/API |
| `risk/` | `/api/v1/risk` | PII detection, safety classification, rules engine |
| `alerts/` | `/api/v1/alerts` | Notifications, email, digest |
| `billing/` | `/api/v1/billing` | Stripe subscriptions, LLM spend tracking |
| `reporting/` | `/api/v1/reports` | Reports, PDF/CSV export, scheduling |
| `portal/` | `/api/v1/portal` | BFF dashboard aggregation |
| `compliance/` | `/api/v1/compliance` | GDPR, COPPA, LGPD data rights |

### Middleware Stack (LIFO order)
1. Security headers (CSP, HSTS, X-Frame-Options)
2. TimingMiddleware (request duration)
3. RateLimitMiddleware (Redis sliding window)
4. LocaleMiddleware (i18n)
5. GZipMiddleware (compression)
6. CORSMiddleware

### Frontend (`portal/`)
- Next.js App Router with Tailwind CSS
- i18n via next-intl (English, architecture ready for FR/DE/IT/PT/ES)
- React Query for data fetching
- Pages: dashboard, members, activity, alerts, spend, reports, settings

### Browser Extension (`extension/`)
- Manifest V3 (Chrome + Firefox)
- Content scripts for AI platform DOM monitoring
- HMAC-signed event submission to capture gateway

## Architecture: Hybrid 2-Service Model

### Current Deployment (MVP)
- **Service 1 (core-api):** Auth, groups, billing, reporting, portal, compliance
- **Service 2 (risk-pipeline):** Capture gateway, risk engine, alerts
- **Shared:** Cloud SQL PostgreSQL, Pub/Sub topics, Firestore, Cloud KMS

### Module Communication Rules
1. Modules NEVER import from each other's internal files (models.py, service.py)
2. Cross-module communication goes through public interfaces in __init__.py
3. Async flows (capture -> risk -> alerts) use Pub/Sub topics, not direct function calls
4. Shared data uses Pydantic schemas defined in each module's schemas.py
5. Each module only queries its own database tables

### Microservice Extraction Playbook

When a module needs independent scaling, extract it:

1. Create new Cloud Run service with the module's code as its own FastAPI app
2. Replace direct function calls with HTTP client calls (use shared Pydantic schemas as contracts)
3. Split database tables if needed (or keep shared DB with separate connection pools)
4. Update Pub/Sub subscriptions — new service subscribes to same topics
5. Add service-to-service auth — internal JWT or API key
6. Update Cloud Run service mesh — routing rules, health checks

Estimated effort per extraction: 1-3 days.

### Extraction Priority (when scale demands)
1. capture-gateway — highest event volume, independent scaling profile
2. alert-service — delivery latency sensitive, independent retry logic
3. billing-service — Stripe webhook processing, LLM API polling cycles
4. reporting-service — CPU-intensive PDF generation, can be async worker
5. auth-service — only if shared across multiple Bhapi products
6. group-service — only if SIS integration adds significant complexity

## Exception Handling

All custom exceptions inherit from `src.exceptions.BhapiException`:

| Exception | Code | Status |
|-----------|------|--------|
| `NotFoundError` | `NOT_FOUND` | 404 |
| `UnauthorizedError` | `UNAUTHORIZED` | 401 |
| `ForbiddenError` | `FORBIDDEN` | 403 |
| `ValidationError` | `VALIDATION_ERROR` | 422 |
| `ConflictError` | `CONFLICT` | 409 |
| `RateLimitError` | `RATE_LIMITED` | 429 |

## Database

- **ORM:** SQLAlchemy 2.x async (asyncpg for PostgreSQL, aiosqlite for SQLite in tests)
- **Migrations:** Alembic
- **Production:** Cloud SQL PostgreSQL
- **Tests:** In-memory SQLite

### Mixins
- `UUIDMixin` — UUID primary key
- `TimestampMixin` — `created_at` + `updated_at`
- `SoftDeleteMixin` — `deleted_at` with auto-filtering

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection | No (graceful degradation) |
| `SECRET_KEY` | JWT signing key (min 32 chars in prod) | Yes |
| `ENVIRONMENT` | development/staging/production | Yes |
| `STRIPE_SECRET_KEY` | Stripe API key | Production |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | Production |
| `SENDGRID_API_KEY` | SendGrid for email delivery | Production |
| `GCP_PROJECT_ID` | Google Cloud project | Production |

## Code Conventions

- Async everywhere (SQLAlchemy async, httpx)
- Pydantic schemas for all request/response validation
- `AuthContext` + `DbSession` dependency injection
- API prefix: `/api/v1/`
- Auth: JWT bearer + session cookie (`bhapi_session`)
- Raise `BhapiException` subclasses (not raw `HTTPException`)
- Use `structlog.get_logger()` for logging
- No cross-module imports (use public interfaces)

## Important Gotchas

1. **Vitest doesn't run tsc** — type errors pass vitest but fail Docker builds
2. **ReportLab "Bullet" style** — use unique names for custom styles
3. **Redis optional** — disabled in tests, app degrades gracefully
4. **Datetime timezone** — always use timezone-aware datetimes
5. **Session auth tokens** — must have `type: "session"` field
6. **React Rules of Hooks** — never put hooks after early returns
