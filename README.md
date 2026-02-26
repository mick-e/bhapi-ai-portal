# Bhapi Family AI Governance Portal

AI safety and governance platform for families, schools, and clubs. Monitors children's AI tool usage across ChatGPT, Gemini, Copilot, Claude, and Grok with real-time risk alerting, PII protection, and spend management.

**URL:** [bhapi.ai](https://bhapi.ai) | **Version:** 1.0.0 (MVP)

## Features

- **AI Activity Monitoring** — Browser extension tracks interactions with ChatGPT, Gemini, Copilot, Claude, and Grok
- **Risk Pipeline** — PII detection, safety classification (self-harm, violence, bullying, academic dishonesty), and configurable rules engine
- **Consent Enforcement** — COPPA (US), GDPR (EU), LGPD (Brazil), AU Privacy compliance with age-gated controls
- **Real-time Alerts** — Severity-based notifications with immediate, hourly, or daily digest modes
- **LLM Spend Tracking** — Budget monitoring across OpenAI, Anthropic, Google, and Microsoft with threshold alerts
- **Reporting** — PDF/CSV/JSON reports for safety, spend, activity, and compliance
- **Compliance** — GDPR Article 17 (right to erasure) and Article 20 (data portability) workflows
- **Group Management** — Family, school, and club account types with role-based access

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy async, Alembic |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, TanStack Query |
| Extension | Manifest V3 (Chrome + Firefox), TypeScript |
| Database | PostgreSQL 16 (prod), SQLite (tests) |
| Cache | Redis 7 (optional, graceful degradation) |
| Email | SendGrid |
| Payments | Stripe |
| Encryption | Fernet (dev), Google Cloud KMS (prod) |
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
# Backend (602 tests)
pytest tests/ -v

# E2E tests (in-memory SQLite, no external keys needed)
pytest tests/e2e/ -v

# Unit tests
pytest tests/unit/ -v

# Security tests
pytest tests/security/ -v

# Frontend (59 tests)
cd portal && npx vitest run

# Type checking
cd portal && npx tsc --noEmit
```

## Project Structure

```
bhapi-ai-portal/
├── src/                    # FastAPI backend
│   ├── main.py             # App factory, middleware, routers
│   ├── auth/               # Authentication (email/password + OAuth SSO)
│   ├── groups/             # Group management + consent enforcement
│   ├── capture/            # Event ingestion from extension/DNS/API
│   ├── risk/               # PII detection + safety classification
│   ├── alerts/             # Notifications + email delivery
│   ├── billing/            # Stripe subscriptions + LLM spend tracking
│   ├── reporting/          # PDF/CSV report generation + scheduling
│   ├── portal/             # Dashboard BFF aggregation
│   ├── compliance/         # GDPR data rights (deletion + export)
│   ├── email/              # SendGrid templated emails
│   └── jobs/               # Background job runner (cron)
├── portal/                 # Next.js frontend
├── extension/              # Browser extension (Manifest V3)
├── alembic/                # Database migrations
├── tests/                  # Test suite (602 backend + 59 frontend)
├── docs/                   # Product spec, DPIA, pen test plan, launch checklist
├── deploy/                 # Deployment configuration
├── docker-compose.yml      # Local dev (Postgres 16 + Redis 7)
├── Dockerfile              # Multi-stage production build
└── render.yaml             # Render blueprint (2 services + DB)
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

- [`docs/bhapi-family-ai-portal-spec.md`](docs/bhapi-family-ai-portal-spec.md) — Product specification
- [`docs/compliance/dpia.md`](docs/compliance/dpia.md) — Data Protection Impact Assessment
- [`docs/security/pentest-plan.md`](docs/security/pentest-plan.md) — Penetration test plan
- [`docs/launch/production-checklist.md`](docs/launch/production-checklist.md) — Production launch checklist

## License

MIT
