# Skills & Competencies

> **Project:** bhapi-ai-portal (Family AI Governance)
> **URL:** https://bhapi.ai
> **Version:** 2.1.0
> **Last updated:** 2026-03-17

## Purpose

Portfolio artifact demonstrating technical depth and breadth across the bhapi-ai-portal codebase. Aimed at hiring managers, technical reviewers, and collaborators evaluating engineering capability.

## Architecture & System Design

- **Modular monolith** — 19 isolated modules with enforced public interface boundaries (`__init__.py` contracts, no cross-module internal imports)
- **BFF aggregation** — portal module aggregates dashboard data with per-section degraded resilience (try/except per section, amber warning on partial failure)
- **Middleware stack design** — 7-layer LIFO stack (security headers → timing/correlation → rate limiting → auth → locale → compression → CORS)
- **Exception hierarchy** — unified `BhapiException` base with typed subclasses replacing raw HTTP exceptions
- **Multi-tenant data isolation** — group-scoped queries, member cap enforcement, consent-gated access

## Backend Engineering

- **Async Python** — FastAPI with async SQLAlchemy, httpx, dependency injection (`AuthContext`, `DbSession`)
- **Data modeling** — UUID primary keys, soft-delete mixin with auto-filtering, timestamp mixin, encrypted column patterns, compound indexes for query performance
- **Migration safety discipline** — 16 Alembic migrations with operational rigor born from a multi-day production outage caused by an uncommitted migration file
- **Background processing** — scheduled cron jobs (risk processing, email delivery, spend sync, encrypted content TTL cleanup)
- **AI classification pipeline** — 14-category risk taxonomy, safety scoring (0-100), multi-provider spend tracking with API key revocation

## Frontend Engineering

- **Next.js 15 static export** — App Router with managed constraints (no `next/image`, no dynamic routes, no server components)
- **Branded design system** — custom component library (WCAG 2.1 AA compliant), Orange/Teal palette, Inter font
- **Internationalization** — 6 languages via client-side `LocaleContext` with dynamic JSON imports
- **Real-time alerts** — server-sent events for live risk notifications
- **PWA** — progressive web app support for mobile experience

## Browser Extension

- **Manifest V3** — Chrome, Firefox, Safari cross-browser support
- **10 AI platform monitors** — ChatGPT, Gemini, Copilot, Claude, Grok, Character.AI, Replika, Pi, Perplexity, Poe
- **Content script architecture** — DOM observation and conversation capture across heterogeneous platforms
- **Offline resilience** — event buffering queue when network unavailable
- **Webpack multi-target build** — bundled per browser target

## Security & Privacy

- **Authentication** — JWT with session management, API keys (`bhapi_sk_` prefix, SHA-256 hashed)
- **Authorization** — RBAC across all protected endpoints
- **Encryption** — Fernet/KMS credential storage, encrypted content excerpts with TTL cleanup
- **Capture integrity** — HMAC verification for tamper-proof extension-to-backend events
- **Rate limiting** — Redis sliding window with in-memory fallback, per-endpoint configuration
- **Observability** — structlog with correlation IDs, request tracing via `X-Request-ID`

## Integrations

- **Payments** — Stripe checkout/portal, tiered plans (Family/School/Enterprise), per-seat pricing, webhook persistence
- **Identity** — Clever + ClassLink SIS rostering, Yoti age verification, Google Workspace + Entra SSO, directory sync
- **Communications** — Twilio SMS alerting, SendGrid transactional email
- **AI safety** — Hive/Sensity deepfake detection, Vertex AI safety classification

## Testing & Quality

- **1,314 backend tests** — 639 E2E + 521 unit + 154 security, all passing
- **95 production E2E tests** — live verification against bhapi.ai deployment
- **60+ frontend tests** — component and integration coverage via Vitest
- **Test architecture** — E2E against in-memory SQLite (no external services), security tests verify auth/RBAC on every endpoint, fixture design for async DB sessions

## Compliance & Domain Expertise

- **COPPA** — certification readiness, parental consent workflows, child data protection, family member caps
- **EU AI Act** — transparency requirements, human review, appeals workflow
- **GDPR / LGPD** — data subject rights, cross-jurisdiction compliance
- **AI safety domain** — 14-category risk taxonomy, emotional dependency detection, academic integrity monitoring, deepfake guidance

## Infrastructure & Deployment

- **Docker** — multi-stage production builds, compose for local development
- **CI/CD** — GitHub Actions pipeline (test + lint + security), Render auto-deploy from master
- **Operational resilience** — health check endpoints (live/ready/schema), Redis graceful degradation, migration-on-deploy with best-effort startup

<!-- Maintenance notes:
  - Update when shipping significant features, not every commit
  - Review quarterly — remove stale skills, verify test counts against CLAUDE.md
  - Every skill must tie to a concrete artifact (module, test count, migration, metric)
  - Keep under 150 lines total
-->
