# Skills & Competencies

> **Project:** bhapi-ai-portal (Family AI Governance)
> **URL:** https://bhapi.ai
> **Version:** 2.1.0
> **Last updated:** 2026-03-16

## Backend Engineering

- **FastAPI** — 19 modules, ~190 routes, modular router architecture
- **Async SQLAlchemy** — PostgreSQL (prod) / SQLite (tests), 16 Alembic migrations
- **Background jobs** — scheduled tasks via Render cron, async job processing
- **Redis** — caching with graceful degradation (in-memory fallback when unavailable)
- **AI safety classification** — risk taxonomy (14 categories), safety scores (0-100), Vertex AI integration
- **Spend tracking** — 5 AI providers (OpenAI, Anthropic, Google, Microsoft, xAI) with API key revocation

## Frontend Engineering

- **Next.js 15** — App Router, static export, React Query for server state
- **Tailwind CSS** — branded design system (Orange `#FF6B35` primary, Teal `#0D9488` accent)
- **i18n** — 6 languages, full translation coverage
- **WCAG 2.1 AA** — accessibility-compliant UI across all pages
- **SSE real-time alerts** — server-sent events for live risk notifications
- **PWA** — progressive web app support for mobile experience
- **60+ frontend tests** — component and integration coverage

## Browser Extension

- **Manifest V3** — Chrome, Firefox, Safari, Edge cross-browser support
- **10 AI platform monitors** — ChatGPT, Gemini, Copilot, Claude, Grok, Character.AI, Replika, Pi, Perplexity, Poe
- **Webpack build** — bundled for each browser target
- **Content scripts** — DOM observation and conversation capture across platforms
- **Offline event buffering** — queued capture when network unavailable

## Security & Auth

- **JWT authentication** — token-based auth with session management
- **RBAC** — role-based access control across all protected endpoints
- **Fernet/KMS encryption** — credential storage with key management
- **COPPA consent** — parental consent workflows, child account protections, family member cap (5)
- **Rate limiting** — Redis-backed with in-memory fallback, per-endpoint configuration
- **Correlation IDs** — request tracing across services
- **HMAC capture verification** — tamper-proof event integrity from extension to backend
- **Deepfake detection** — Hive/Sensity integration for media analysis

## Infrastructure & DevOps

- **Docker multi-stage builds** — optimized production images
- **GitHub Actions** — CI pipeline with test, lint, security checks
- **Render** — auto-deploy with `render.yaml`, cron job scheduling
- **Health checks** — live/ready/schema endpoints for monitoring
- **BhapiLogo component** — branded wordmark with smile arc, consistent across web + extension

## Testing

- **1,314 backend tests** — 639 E2E, 521 unit, 154 security (all passing)
- **95 production E2E** — live deployment verification against bhapi.ai
- **60+ frontend tests** — React component and integration coverage
- **Test fixture patterns** — `test_session` fixture, `.test` TLD rejection, `password_hash`/`email_verified` field conventions

## Integrations & Payments

- **Stripe** — checkout/portal integration, family self-serve ($9.99/mo), school/club per-seat pricing, 14-day trial
- **Tiered billing** — Family / School / Enterprise plans with vendor risk scoring
- **Clever + ClassLink** — SIS integration for school rostering and auto-provisioning
- **Yoti** — age verification for child safety compliance
- **Google Workspace + Entra SSO** — directory sync, single sign-on
- **Twilio SMS** — SMS alerting for parents/guardians
- **SendGrid** — transactional email delivery

## Compliance & Domain Knowledge

- **COPPA** — certification readiness, parental consent, child data protection
- **EU AI Act** — transparency, human review, appeals workflow
- **GDPR / LGPD** — data subject rights, cross-jurisdiction compliance
- **14-category risk taxonomy** — AI safety classification with weighted scoring
- **Emotional dependency detection** — behavioral pattern analysis for child safety
- **Academic integrity** — AI-assisted schoolwork detection
- **Family safety features (F1-F16)** — conversation summaries, time budgets, bedtime mode, panic button, weekly reports, sibling privacy, device correlation, rewards, emergency contacts, child dashboard
- **School safeguarding** — class management, safeguarding officer workflows
- **AI literacy curriculum** — 5 educational modules for digital citizenship

<!-- Maintenance notes:
  - Update when shipping significant features, not every commit
  - Review quarterly — remove stale skills
  - Every skill must tie to a concrete artifact (module, test count, migration, metric)
  - Keep under 150 lines total
-->
