# Bhapi Family AI Governance Portal

## Overview
AI safety and governance platform for families, schools, and clubs. Monitors children's AI tool usage across ChatGPT, Gemini, Copilot, Claude, and Grok with real-time risk alerting, PII protection, and spend management.

**Platform URL:** bhapi.ai
**Stack:** FastAPI (Python) backend + Next.js React TypeScript frontend
**Version:** 1.0.0 (MVP complete)

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
# All backend tests (566+ tests)
pytest tests/ -v

# E2E tests (in-memory SQLite, no keys needed)
pytest tests/e2e/ -v

# Unit tests
pytest tests/unit/ -v

# Security tests
pytest tests/security/ -v

# Frontend (59+ tests)
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
- `src/encryption.py` — Credential encryption (Fernet dev/test, Cloud KMS production)
- `src/dependencies.py` — FastAPI DI (`DbSession`, `AuthContext`, `Pagination`)
- `src/exceptions.py` — Exception hierarchy (`BhapiException` base)
- `src/constants.py` — Shared constants
- `src/redis_client.py` — Redis connection with graceful degradation

### Modules
| Module | Prefix | Description |
|--------|--------|-------------|
| `auth/` | `/api/v1/auth` | Registration, login, password reset, email verification, API keys, contact inquiry |
| `groups/` | `/api/v1/groups` | Groups, members, invitations, consent (COPPA/GDPR/LGPD) |
| `capture/` | `/api/v1/capture` | Event ingestion from extension/DNS/API, enriched listing |
| `risk/` | `/api/v1/risk` | PII detection, safety classification, rules engine |
| `alerts/` | `/api/v1/alerts` | Notifications, email delivery, digest batching, re-notification |
| `billing/` | `/api/v1/billing` | Stripe subscriptions, checkout, billing portal, LLM spend tracking (OpenAI/Anthropic/Google/Microsoft) |
| `reporting/` | `/api/v1/reports` | Reports, PDF/CSV export, scheduling |
| `portal/` | `/api/v1/portal` | BFF dashboard aggregation, group settings |
| `compliance/` | `/api/v1/compliance` | GDPR/COPPA/LGPD data rights, deletion, export |
| `email/` | (internal) | SendGrid email service, templated emails |
| `jobs/` | `/internal` | Background job runner, scheduled tasks |

### Middleware Stack (LIFO order)
1. Security headers (CSP, HSTS, X-Frame-Options, Permissions-Policy)
2. TimingMiddleware (request duration + correlation IDs via X-Request-ID)
3. RateLimitMiddleware (Redis sliding window + in-memory fallback)
4. AuthMiddleware (JWT bearer token enforcement)
5. LocaleMiddleware (i18n)
6. GZipMiddleware (compression)
7. CORSMiddleware (configurable via CORS_ORIGINS env var)

### Frontend (`portal/`)
- Next.js App Router with Tailwind CSS
- React Query for data fetching
- WCAG 2.1 AA accessible (ARIA labels, keyboard navigation, skip-to-content)
- Pages: dashboard, members, activity, alerts, spend, reports, settings
- **Brand**: Orange `#FF6B35` primary, Teal `#0D9488` accent, Inter font
- **Logo**: `BhapiLogo` component (`portal/src/components/BhapiLogo.tsx`) — plain `<img>` tag rendering `/logo.png` (orange wordmark + smile arc). NEVER use `next/image` — static export (`output: "export"`) breaks it
- **WCAG AA**: Buttons use `bg-primary-600` (not `bg-primary`), text links use `text-primary-700` for contrast compliance
- **Static assets**: `portal/public/logo.png` (wordmark), `icon.png` (circular app icon), `favicon.ico` (generated from icon.png). No SVG assets — use only the PNG images from Downloads

### Browser Extension (`extension/`)
- Manifest V3 (Chrome + Firefox)
- Content scripts for AI platform DOM monitoring
- HMAC-signed event submission to capture gateway

## Architecture: Hybrid 2-Service Model

### Current Deployment (MVP)
- **Service 1 (core-api):** All modules served from single FastAPI app
- **Service 2 (jobs):** Background cron runner for risk processing, email delivery, spend sync
- **Database:** PostgreSQL (Cloud SQL / Render)
- **Cache:** Redis (optional, in-memory fallback for rate limiting)

### Module Communication Rules
1. Modules NEVER import from each other's internal files (models.py, service.py)
2. Cross-module communication goes through public interfaces in __init__.py
3. Shared data uses Pydantic schemas defined in each module's schemas.py
4. Each module only queries its own database tables

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

## Key Features (MVP)

### Risk Pipeline
- Capture events → PII detection → safety classification → rules engine → risk events → alerts
- Keywords-based classification with configurable Vertex AI/Gemini fallback
- Age-band sensitivity scaling (under-8 most conservative, 17+ most lenient)
- Categories: self-harm, violence, academic dishonesty, bullying/harassment

### Consent Enforcement
- COPPA (US, <13), GDPR (EU, <16), LGPD (Brazil, <18), AU Privacy (<16)
- Capture events blocked until guardian consent recorded
- Consent endpoint: POST /api/v1/groups/{group_id}/members/{member_id}/consent

### Email Delivery
- SendGrid integration with graceful degradation (logged in dev/test)
- Templates: alert notification, invitation, verification, password reset, reports
- Digest modes: immediate, hourly, daily
- Re-notification for critical/high unacknowledged alerts

### LLM Spend Tracking
- Provider connectors: OpenAI, Anthropic, Google, Microsoft
- Credentials encrypted at rest (Fernet dev/test, Cloud KMS production)
- Budget thresholds with alerts at configurable percentages (50/80/100%)

### Reporting
- PDF (ReportLab) + CSV generation
- Report types: safety, spend, activity, compliance
- Scheduled report delivery via email

### Compliance
- Data deletion workflow (cascade soft-delete across all tables)
- Data export workflow (ZIP with JSON exports, 7-day expiry)
- Consent records with audit trail

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
- **Migrations:** Alembic (4 migrations: initial schema, content column, compound indexes, api_keys table)
- **Production:** PostgreSQL 16
- **Tests:** In-memory SQLite

### Mixins
- `UUIDMixin` — UUID primary key
- `TimestampMixin` — `created_at` + `updated_at`
- `SoftDeleteMixin` — `deleted_at` with auto-filtering

### Compound Indexes (migration 003)
- `alerts(group_id, severity, created_at)` — severity-filtered alert listings
- `alerts(group_id, status, created_at)` — unread/pending alert queries
- `capture_events(group_id, member_id, timestamp)` — per-member activity
- `capture_events(group_id, platform, timestamp)` — platform filtering
- `risk_events(group_id, severity, created_at)` — risk dashboard
- `spend_records(group_id, period_start, period_end)` — spend summaries

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection (empty = disabled, in-memory fallback) | No |
| `SECRET_KEY` | JWT signing + Fernet encryption key (min 32 chars in prod) | Yes |
| `ENVIRONMENT` | development/staging/production/test | Yes |
| `CORS_ORIGINS` | Comma-separated allowed origins | No |
| `CAPTURE_HMAC_ENABLED` | Enable HMAC validation on capture | No |
| `CAPTURE_HMAC_SECRET` | HMAC signing secret for capture events | Production |
| `SAFETY_CLASSIFIER_MODE` | keyword_only/vertex_ai/auto | No |
| `STRIPE_SECRET_KEY` | Stripe API key | Production |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | Production |
| `SENDGRID_API_KEY` | SendGrid for email delivery | Production |
| `GCP_PROJECT_ID` | Google Cloud project (enables Cloud KMS) | Production |

## Code Conventions

- Async everywhere (SQLAlchemy async, httpx)
- Pydantic schemas for all request/response validation
- `AuthContext` + `DbSession` dependency injection
- API prefix: `/api/v1/`
- Auth: JWT bearer + session cookie (`bhapi_session`)
- Raise `BhapiException` subclasses (not raw `HTTPException`)
- Use `structlog.get_logger()` for logging with correlation IDs
- No cross-module imports (use public interfaces)
- LLM credentials always encrypted via `src/encryption.py`

## Important Gotchas

1. **Vitest doesn't run tsc** — type errors pass vitest but fail Docker builds
2. **ReportLab "Bullet" style** — use unique names for custom styles
3. **Redis optional** — disabled in tests, in-memory rate limiter used as fallback
4. **Datetime timezone** — always use timezone-aware datetimes
5. **Session auth tokens** — must have `type: "session"` field
6. **React Rules of Hooks** — never put hooks after early returns
7. **Test fixture** — use `test_session` (not `async_db`) for DB session in tests
8. **BudgetThreshold** — uses `type` field (not `threshold_type`), has no `period` field
9. **Capture events API** — returns paginated `{items, total, page, page_size, total_pages}`, not flat list
10. **Email domain validation** — `.test` TLD rejected; use `.com` in test emails
11. **API Keys** — `bhapi_sk_` prefix, SHA-256 hashed in DB, full key shown only on creation
12. **Billing checkout** — Only `family` plan is self-serve via Stripe; `school`/`club` require contacting sales
16. **Registration** — School/club account types show a contact inquiry form (not registration). Only family accounts can self-register. Contact inquiries go to `POST /api/v1/auth/contact-inquiry` (public, no auth) → emails sales@bhapi.ai
13. **Dashboard no-group** — New users without a group see a "Create your first group" onboarding flow instead of an error; `User.group_id` is nullable
14. **next/image + static export** — `next.config.js` uses `output: "export"` with `images: { unoptimized: true }`. Use plain `<img>` tags (NOT `next/image`) for images. `BhapiLogo` uses `<img>` with inline `style` fallback so it never renders oversized even without CSS
15. **Brand assets are PNG only** — Logo (`logo.png`) and icon (`icon.png`) are actual PNG files from user's Downloads. NEVER create custom SVG logos/favicons. Generate `.ico` from `icon.png` via Pillow. Source files: `bhapi logo@2x.png` (wordmark+smile), `bhapi app icon circle.png` (circular icon)
