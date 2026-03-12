# Bhapi Family AI Governance Portal

## 1. Project Overview

AI safety governance platform at **bhapi.ai** for parents, school admins, and club managers monitoring children's AI usage across ChatGPT, Gemini, Copilot, Claude, and Grok.

**Optimizes for:** Child safety, regulatory compliance (COPPA/GDPR/LGPD), real-time alerting, data privacy.
**Stack:** FastAPI (Python 3.11) + Next.js 15 (TypeScript) + PostgreSQL 16
**Version:** 2.1.0 (Post-MVP features complete)

## 2. Tech Stack

**Backend:** Python 3.11, FastAPI, SQLAlchemy 2.x async (asyncpg/aiosqlite), Alembic, Pydantic v2, structlog, httpx
**Frontend:** Next.js 15 App Router (static export), TypeScript, Tailwind CSS, React Query, Lucide icons
**Infra:** PostgreSQL 16, Redis (optional — disabled in tests, in-memory rate limiter fallback), Stripe, SendGrid, Twilio
**Extension:** Manifest V3 (Chrome + Firefox + Safari)

### Do Not Introduce
- **No `next/image`** — breaks static export (`output: "export"`). Use plain `<img>` tags. `BhapiLogo` uses `<img>` with inline `style` fallback
- **No dynamic `[id]` routes** — `output: "export"` doesn't support them. Use query parameters (`/members/detail?id=xxx`). Pages with `useSearchParams()` must be wrapped in `<Suspense>`
- **No server components or next-intl server features** — uses client-side `LocaleContext` with dynamic JSON imports
- **No SVG logos** — brand assets are PNG only (see UI section)
- **No alternative ORMs** — SQLAlchemy async only
- **No raw `HTTPException`** — raise `BhapiException` subclasses
- **No cross-module internal imports** — use public interfaces in `__init__.py`
- **No component libraries** (shadcn, MUI, Chakra) — custom components in `portal/src/components/ui/`

## 3. Architecture

### 2-Service Model
- **core-api:** All 18 modules served from single FastAPI app (`src/main.py`, 188 routes)
- **jobs:** Background cron runner for risk processing, email delivery, spend sync

### Modules
| Module | Prefix | Description |
|--------|--------|-------------|
| `auth/` | `/api/v1/auth` | Registration, login, password reset, email verification, API keys, contact inquiry |
| `groups/` | `/api/v1/groups` | Groups, members, invitations, consent (COPPA/GDPR/LGPD), member cap enforcement |
| `capture/` | `/api/v1/capture` | Event ingestion from extension/DNS/API, enriched listing, consent enforcement |
| `risk/` | `/api/v1/risk` | PII detection, safety classification, rules engine, content excerpt encryption + TTL, safety scores, deepfake detection |
| `alerts/` | `/api/v1/alerts` | Notifications, email delivery, digest batching, re-notification (persistent) |
| `billing/` | `/api/v1/billing` | Stripe subscriptions/checkout/portal, per-seat pricing, LLM spend (OpenAI/Anthropic/Google/Microsoft/xAI), API key revocation, tiered plans, vendor risk |
| `reporting/` | `/api/v1/reports` | Reports, PDF/CSV export, scheduling |
| `portal/` | `/api/v1/portal` | BFF dashboard aggregation, group settings |
| `compliance/` | `/api/v1/compliance` | GDPR/COPPA/LGPD data rights, EU AI Act transparency/appeals, COPPA certification |
| `integrations/` | `/api/v1/integrations` | Clever + ClassLink SIS, Yoti age verification, Google Workspace + Entra SSO, directory sync, auto-provisioning |
| `blocking/` | `/api/v1/blocking` | Automated AI session blocking, block rules CRUD, extension polling, parent approval flow, DNS blocking, time budgets, bedtime mode |
| `analytics/` | `/api/v1/analytics` | Trends, usage patterns, member baselines, anomaly detection, peer comparison |
| `sms/` | (internal) | Twilio SMS notifications with rate limiting |
| `email/` | (internal) | SendGrid email service, templated emails |
| `literacy/` | `/api/v1/literacy` | AI literacy modules, quizzes, assessments, progress tracking |
| `groups/school_router` | `/api/v1/school` | School admin: classes, class members, safeguarding reports |
| `groups/` (extended) | `/api/v1/groups` | Family agreements, emergency contacts, rewards, member visibility, panic button |
| `jobs/` | `/internal` | Background job runner, scheduled tasks |

### Module Communication Rules
1. Modules NEVER import from each other's internal files (models.py, service.py)
2. Cross-module communication goes through public interfaces in `__init__.py`
3. Shared data uses Pydantic schemas defined in each module's `schemas.py`
4. Each module only queries its own database tables

### Middleware Stack (LIFO order)
1. Security headers (CSP, HSTS, X-Frame-Options, Permissions-Policy)
2. TimingMiddleware (request duration + correlation IDs via X-Request-ID)
3. RateLimitMiddleware (Redis sliding window + in-memory fallback)
4. AuthMiddleware (JWT bearer token enforcement)
5. LocaleMiddleware (i18n)
6. GZipMiddleware (compression)
7. CORSMiddleware (configurable via CORS_ORIGINS env var)

### Exception Hierarchy
All custom exceptions inherit from `src.exceptions.BhapiException`:

| Exception | Code | Status |
|-----------|------|--------|
| `NotFoundError` | `NOT_FOUND` | 404 |
| `UnauthorizedError` | `UNAUTHORIZED` | 401 |
| `ForbiddenError` | `FORBIDDEN` | 403 |
| `ValidationError` | `VALIDATION_ERROR` | 422 |
| `ConflictError` | `CONFLICT` | 409 |
| `RateLimitError` | `RATE_LIMITED` | 429 |

### Database
- **ORM:** SQLAlchemy 2.x async (asyncpg for PostgreSQL, aiosqlite for SQLite in tests)
- **Migrations:** Alembic (16 migrations: initial schema, content column, compound indexes, api_keys table, alert snoozed_until, beta schema changes, block approvals, class groups, literacy tables, conversation summaries, family agreements, time budgets, deepfake/dependency, member visibility, rewards, emergency contacts)
- **Mixins:** `UUIDMixin` (UUID PK), `TimestampMixin` (`created_at` + `updated_at`), `SoftDeleteMixin` (`deleted_at` with auto-filtering)
- Content excerpts stored encrypted via `encrypt_credential()`, decrypted on read. TTL cleanup job runs daily.

## 4. Coding Conventions

### Python Backend
- **Async everywhere** — SQLAlchemy async, httpx
- **Dependency injection** — `AuthContext` + `DbSession` from `src/dependencies.py`
- **Validation** — Pydantic schemas for all request/response
- **Logging** — `structlog.get_logger()` with correlation IDs (never `print`)
- **Errors** — raise `BhapiException` subclasses, never raw `HTTPException`
- **Datetimes** — always timezone-aware
- **Credentials** — always encrypted via `src/encryption.py`
- **Async refresh** — `db.refresh(obj)` expires relationships. Always pass relationship names: `await db.refresh(group, ["members"])` to avoid `MissingGreenlet` errors
- **ReportLab** — use unique names for custom styles (the "Bullet" name conflicts)
- **API keys** — `bhapi_sk_` prefix, SHA-256 hashed in DB, full key shown only on creation
- **Auth tokens** — session tokens must have `type: "session"` field

### TypeScript Frontend
- **`"use client"`** as first line of every page/component
- **Default exports** for pages
- **Inline sub-components** — only extract to `components/ui/` if reused 3+ pages
- **Data fetching** — React Query hooks (`useQuery`, `useMutation`)
- **Icons** — Lucide only
- **Hooks** — never place hooks after early returns (Rules of Hooks)

## 5. UI and Design System

- **Brand:** Orange `#FF6B35` primary, Teal `#0D9488` accent, Inter font
- **WCAG AA contrast:** Buttons use `bg-primary-600` (not `bg-primary`), text links use `text-primary-700`
- **UI components:** `portal/src/components/ui/` — Card, Button (variants/sizes/isLoading), Input
- **Logo:** PNG only. `BhapiLogo` component (`portal/src/components/BhapiLogo.tsx`) renders `/logo.png` via plain `<img>`. NEVER create SVG logos/favicons
- **Static assets:** `portal/public/logo.png` (wordmark+smile), `icon.png` (circular app icon), `favicon.ico` (generated from `icon.png` via Pillow)
- **Source files:** `bhapi logo@2x.png` (wordmark+smile), `bhapi app icon circle.png` (circular icon)

## 6. Content and Copy Guidance

- **Audience:** Non-technical parents and school admins
- **Tone:** Reassuring, clear, jargon-free
- **Error messages:** Actionable ("Please add a family member") not technical ("group_id null")
- **Button labels:** Verb-first ("Create Group", "View Activity")
- **Empty states:** Always show helpful prompt. New users without a group see "Create your first group" onboarding, not an error (`User.group_id` is nullable)
- **i18n:** 6 languages (EN, FR, ES, DE, PT-BR, IT) via `useTranslations()` hook, client-side only. All strings in `portal/messages/`

## 7. Testing and Quality Bar

### Commands
```bash
pytest tests/ -v              # All backend (1314 passed, 138 skipped, 4 xfailed)
pytest tests/e2e/ -v          # E2E (639 passed, in-memory SQLite, no keys needed)
pytest tests/unit/ -v          # Unit tests (521 passed)
pytest tests/security/ -v     # Security (154 passed)
cd portal && npx vitest run   # Frontend (60+ tests)
cd portal && npx tsc --noEmit # Type check (MUST run separately)
# Production E2E (requires PROD_API_KEY in .env.local):
PROD_BASE_URL=https://bhapi.ai PROD_API_KEY=<token> pytest tests/e2e/test_production.py -v  # 95 tests
```

### Definition of Done
Every endpoint needs: happy path + auth/403 + validation/422 + edge cases. Every page needs loading + error states. Both `pytest` and `tsc` must pass before merge.

### Critical Warnings
- **vitest does NOT run tsc** — type errors silently pass vitest but break Docker builds. Always run `tsc --noEmit` separately
- **Test fixture** — use `test_session` (not `async_db`) for DB session in tests
- **Email validation** — `.test` TLD is rejected; always use `.com` in test emails
- **Migrations run on deploy** — Dockerfile CMD runs `alembic upgrade head` before starting uvicorn (best-effort — app starts even if migrations fail). If you add new model columns/tables, you MUST create an Alembic migration — the deploy will auto-apply it. Never add model columns without a corresponding migration or production will crash with "column does not exist"
- **Migration files MUST be committed** — Creating a migration file locally is not enough. If the migration `.py` file is not `git add`-ed, committed, and pushed, it will never reach production. After creating a migration, ALWAYS verify it appears in `git status` and include it in your commit. This caused a multi-day production outage (2026-03-12) where all data endpoints returned 500s because migration 017 sat as an untracked file
- **alembic/env.py must import ALL models** — Every SQLAlchemy model class must be imported in `alembic/env.py` or `alembic revision --autogenerate` won't detect its tables/columns, silently skipping them. When adding a new model, add its import to `env.py` in the same commit
- **Health check SQL must be valid** — `src/main.py` uses `text("SELECT 1")` for the DB health check. Never use `text("1")` — asyncpg rejects bare expressions and the health check falsely reports `database: "error"`, masking the real DB status
- **Dashboard resilience** — `get_dashboard()` in `src/portal/service.py` wraps each section (activity, alerts, spend, risk, trends) in try/except with structlog and tracks failures in `degraded_sections`. The router endpoint has a catch-all that returns `DashboardResponse(degraded_sections=["all"])` on unexpected errors. The frontend shows an amber warning banner listing which sections failed

## 8. File and Component Placement

### Backend Module
```
src/<module>/
  __init__.py    # Public interface
  router.py      # FastAPI endpoints
  service.py     # Business logic
  models.py      # SQLAlchemy models
  schemas.py     # Pydantic schemas
```
Register router in `src/main.py`.

### Backend Tests
- Unit: `tests/unit/test_<module>.py`
- E2E: `tests/e2e/test_<module>.py`
- Security: `tests/security/test_<module>_security.py`

### Frontend
- Page: `portal/src/app/(dashboard)/<name>/page.tsx`
- Hook: `portal/src/hooks/use-<feature>.ts`
- UI component: `portal/src/components/ui/<Name>.tsx` (only if reused 3+ pages)
- Translations: all 6 files in `portal/messages/`

### Migration
```bash
alembic revision --autogenerate -m "description"
```

## 9. Safe-change Rules

### Never change without explicit request
- Middleware stack order, soft-delete filter, encryption scheme
- Production Alembic migrations, `next.config.js` (static export constraint)
- Stripe webhook handler, HMAC validation, consent enforcement
- `BhapiLogo` component, `__init__.py` public interfaces

### Approach with caution
- **Auth token structure** — `type: "session"` is load-bearing
- **`BudgetThreshold` model** — uses `type` field (not `threshold_type`), has no `period` field
- **Capture events API** — returns paginated `{items, total, page, page_size, total_pages}`, not flat list (contract with extension)
- **Registration flow** — Family: self-register via `POST /register`. School/club: contact inquiry form → `POST /api/v1/auth/contact-inquiry` (public) → emails sales@bhapi.ai → sales creates account → owner uses Stripe checkout
- **Family member cap** — `MAX_FAMILY_MEMBERS = 5` enforced in `add_member()` and `accept_invitation()`. School/club have no cap
- **Billing checkout** — All plans self-serve via Stripe once account exists. School/club use per-seat pricing with member count as quantity
- **Stripe webhooks persist** — `handle_webhook_event()` creates/updates Subscription rows for created/updated/cancelled/payment_failed events
- **Model columns require migrations (commit AND push)** — Adding a column to any SQLAlchemy model WITHOUT a matching Alembic migration will crash production (the ORM generates SQL referencing the column, but PostgreSQL doesn't have it). This is the #1 cause of production regressions. After model changes: (1) run `alembic revision --autogenerate -m "desc"`, (2) verify the generated migration file with `git status`, (3) `git add` the migration file, (4) commit and push it. An uncommitted migration is the same as no migration

## 10. Commands

```bash
# Development
uvicorn src.main:app --reload --port 8000    # Backend
cd portal && npm run dev                      # Frontend

# Build
docker compose up --build

# Migrations
alembic upgrade head                          # Apply all
alembic revision --autogenerate -m "desc"     # Create new (MUST commit the file!)
git status                                    # Verify migration file is tracked
```

## Appendix: Environment Variables

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
| `TWILIO_ACCOUNT_SID` | Twilio account SID for SMS | Production |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | Production |
| `TWILIO_FROM_NUMBER` | Twilio sender phone number | Production |
| `CLEVER_CLIENT_ID` | Clever SIS OAuth client ID | Production |
| `CLEVER_CLIENT_SECRET` | Clever SIS OAuth client secret | Production |
| `CLASSLINK_CLIENT_ID` | ClassLink OneRoster client ID | Production |
| `CLASSLINK_CLIENT_SECRET` | ClassLink OneRoster client secret | Production |
| `YOTI_CLIENT_SDK_ID` | Yoti age verification SDK ID | Production |
| `YOTI_PEM_FILE_PATH` | Path to Yoti PEM key file | Production |
| `DEEPFAKE_PROVIDER` | Deepfake detection provider (hive/sensity) | No |
| `DEEPFAKE_API_KEY` | API key for deepfake detection service | No |

### Compound Indexes (migration 003)
- `alerts(group_id, severity, created_at)` — severity-filtered alert listings
- `alerts(group_id, status, created_at)` — unread/pending alert queries
- `capture_events(group_id, member_id, timestamp)` — per-member activity
- `capture_events(group_id, platform, timestamp)` — platform filtering
- `risk_events(group_id, severity, created_at)` — risk dashboard
- `spend_records(group_id, period_start, period_end)` — spend summaries
