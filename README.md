# Bhapi Family AI Governance Portal

AI safety and governance platform for families, schools, and clubs. Monitors children's AI tool usage across ChatGPT, Gemini, Copilot, Claude, and Grok with real-time risk alerting, PII protection, and spend management.

**URL:** [bhapi.ai](https://bhapi.ai) | **Version:** 2.1.0 (Post-MVP Complete)

## Features

### Core (MVP)
- **AI Activity Monitoring** — Browser extension tracks interactions with ChatGPT, Gemini, Copilot, Claude, and Grok
- **Risk Pipeline** — PII detection, safety classification (14 risk categories), AI safety scores (0-100), and configurable rules engine
- **Consent Enforcement** — COPPA (US), GDPR (EU), LGPD (Brazil), AU Privacy compliance with age-gated controls
- **Real-time Alerts** — Severity-based notifications with immediate, hourly, daily, and weekly digest modes
- **LLM Spend Tracking** — Budget monitoring across OpenAI, Anthropic, Google, Microsoft, and xAI with threshold alerts
- **Reporting** — PDF/CSV/JSON reports with scheduling, automated delivery, and compliance export
- **Compliance** — GDPR data rights, EU AI Act transparency/appeals, COPPA certification readiness
- **Group Management** — Family, school, and club account types with role-based access

### Post-MVP
- **AI Conversation Summaries** — LLM-powered conversation analysis with age-based detail levels and content deduplication
- **Emotional Dependency Detection** — Companion chatbot monitoring (Character.ai, Replika, Pi) with dependency scoring
- **Smart AI Screen Time** — Time budgets, bedtime mode, usage allowance rewards
- **Content Blocking** — Real-time AI session blocking with parent approval flow, DNS blocking, effectiveness analytics
- **School Admin Dashboard** — Class-level grouping, teacher alerts, safeguarding reports, SIS integration
- **AI Literacy Assessment** — 5 educational modules with quizzes, scoring, and progress tracking
- **Deepfake Detection** — Hive/Sensity provider abstraction with DEEPFAKE_CONTENT risk category
- **Family Safety** — Family agreements, panic button, emergency contacts, weekly reports, sibling privacy controls
- **Behaviour Analytics** — Anomaly detection, peer comparison, trend analysis with daily job processing
- **Vendor Risk Scoring** — AI platform safety ratings (A-F grading) across 5 weighted categories
- **Federated SSO** — Google Workspace and Microsoft Entra with auto-provisioning and directory sync
- **Safari Extension** — Xcode project with Swift bridge, polyfills, and build scripts
- **Internationalization** — 6 languages (EN, FR, ES, DE, PT-BR, IT) with client-side locale detection

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy async, Alembic |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, TanStack Query |
| Extension | Manifest V3 (Chrome + Firefox + Safari), TypeScript |
| Database | PostgreSQL 16 (prod), SQLite (tests) |
| Cache | Redis 7 (optional, graceful degradation) |
| Email | SendGrid |
| SMS | Twilio |
| Payments | Stripe |
| Encryption | Fernet (dev), Google Cloud KMS (prod) |
| Age Verification | Yoti |
| CI/CD | GitHub Actions, Docker, Render |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16 (or use Docker)
- Redis 7 (optional)

### Using Docker (recommended)

```bash
cp .env.example .env.local
docker compose up --build
```

The API will be available at `http://localhost:8000`.

### Manual Setup

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env.local
uvicorn src.main:app --reload --port 8000

# Frontend
cd portal
npm ci
npm run dev

# Database migrations
alembic upgrade head
```

## Testing

```bash
# Backend (1435 tests: 731 E2E + 521 unit + 183 security)
pytest tests/ -v

# E2E tests (in-memory SQLite, no external keys needed)
pytest tests/e2e/ -v

# Unit tests
pytest tests/unit/ -v

# Security tests
pytest tests/security/ -v

# Frontend (64 tests)
cd portal && npx vitest run

# Type checking (MUST run separately — vitest does NOT run tsc)
cd portal && npx tsc --noEmit
```

## Project Structure

```
bhapi-ai-portal/
├── src/                    # FastAPI backend (18 modules, 188 routes)
│   ├── main.py             # App factory, middleware, 17 routers
│   ├── auth/               # Authentication (email/password + OAuth SSO)
│   ├── groups/             # Group management, consent, school classes
│   ├── capture/            # Event ingestion + conversation summaries
│   ├── risk/               # PII detection, safety classification, scores, deepfake
│   ├── alerts/             # Notifications, digests, panic button
│   ├── billing/            # Stripe billing, LLM spend, vendor risk, plans
│   ├── reporting/          # PDF/CSV reports + scheduling
│   ├── portal/             # Dashboard BFF aggregation
│   ├── compliance/         # GDPR/COPPA/EU AI Act compliance
│   ├── integrations/       # SIS (Clever/ClassLink), SSO, Yoti age verification
│   ├── blocking/           # AI session blocking, time budgets, approval flow
│   ├── analytics/          # Behaviour analytics, anomaly detection
│   ├── literacy/           # AI literacy modules + assessments
│   ├── sms/                # Twilio SMS notifications
│   ├── email/              # SendGrid templated emails
│   └── jobs/               # Background job runner (cron)
├── portal/                 # Next.js 15 frontend (static export)
├── extension/              # Browser extension (Chrome + Firefox + Safari)
├── dns-proxy/              # DNS-level blocking resolver
├── alembic/                # Database migrations (16 versions)
├── tests/                  # Test suite (1435 backend + 64 frontend)
├── docs/                   # Product spec, roadmap, DPIA, security
├── deploy/                 # Deployment configuration
├── docker-compose.yml      # Local dev (Postgres 16 + Redis 7)
├── Dockerfile              # Multi-stage production build
└── render.yaml             # Render blueprint (2 services + DB + cron)
```

## Environment Variables

See [`.env.example`](.env.example) for the full list. Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SECRET_KEY` | JWT signing + encryption key (min 32 chars in prod) | Yes |
| `ENVIRONMENT` | `development` / `staging` / `production` / `test` | Yes |
| `REDIS_URL` | Redis connection (empty = in-memory fallback) | No |
| `STRIPE_SECRET_KEY` | Stripe API key | Production |
| `SENDGRID_API_KEY` | Email delivery | Production |
| `GCP_PROJECT_ID` | Enables Cloud KMS encryption | Production |

## Documentation

- [`docs/bhapi-family-ai-portal-spec.md`](docs/bhapi-family-ai-portal-spec.md) — Product specification (PRD)
- [`docs/bhapi-post-mvp-roadmap.md`](docs/bhapi-post-mvp-roadmap.md) — Post-MVP feature roadmap (17/20 complete)
- [`docs/family-safety-features.md`](docs/family-safety-features.md) — Family safety features spec (F1-F16)
- [`docs/compliance/dpia.md`](docs/compliance/dpia.md) — Data Protection Impact Assessment
- [`docs/security/pentest-plan.md`](docs/security/pentest-plan.md) — Penetration test plan
- [`docs/launch/production-checklist.md`](docs/launch/production-checklist.md) — Production launch checklist

## License

MIT
