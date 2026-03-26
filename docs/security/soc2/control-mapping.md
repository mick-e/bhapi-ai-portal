# SOC 2 Control Mapping — Trust Services Criteria

**Version:** 1.0
**Date:** 2026-08-01

Maps AICPA Trust Services Criteria to Bhapi platform controls.

## CC — Common Criteria (Security)

| TSC ID | Criteria | Platform Control | Evidence Source |
|--------|----------|-----------------|----------------|
| CC1.1 | COSO control environment | Security policies in `docs/security/soc2/` | Policy documents |
| CC2.1 | Information communication | Structured logging, correlation IDs | `src/main.py` middleware |
| CC3.1 | Risk assessment | Risk scoring engine, safety classification | `src/intelligence/scoring.py` |
| CC5.1 | Control activities | RBAC, rate limiting, input validation | `require_permission()`, `RateLimitMiddleware` |
| CC6.1 | Logical access | JWT auth, API key scoping, group isolation | `src/auth/middleware.py` |
| CC6.2 | Authentication | bcrypt, MFA, SSO (OIDC/SAML) | `src/auth/`, `src/integrations/` |
| CC6.3 | Authorization | Role-based, age-tier enforcement | `src/age_tier/middleware.py` |
| CC6.6 | System boundary protection | CORS, CSP, HSTS, Permissions-Policy | Security headers middleware |
| CC6.7 | Threat management | Dependabot, security tests (348+) | GitHub Actions CI |
| CC7.1 | System monitoring | Request logging, anomaly detection | `TimingMiddleware`, `src/intelligence/anomaly.py` |
| CC7.2 | Incident detection | Alert enrichment, behavioral baselines | `src/intelligence/`, `src/alerts/` |
| CC7.3 | Incident response | Documented IRP | `docs/security/incident-response-plan.md` |
| CC8.1 | Change management | Git history, CI/CD, migration tracking | GitHub Actions, Alembic |

## A — Availability

| TSC ID | Criteria | Platform Control | Evidence Source |
|--------|----------|-----------------|----------------|
| A1.1 | Capacity management | Rate limiting (100/min), Redis caching | `RateLimitMiddleware` |
| A1.2 | Recovery | Render auto-deploy, migration rollback | `render.yaml`, Alembic downgrade |
| A1.3 | Environmental safeguards | Render managed infrastructure | Render SLA |

## C — Confidentiality

| TSC ID | Criteria | Platform Control | Evidence Source |
|--------|----------|-----------------|----------------|
| C1.1 | Confidential data identification | Data classification policy | This document |
| C1.2 | Confidential data disposal | Soft delete + hard delete + TTL cleanup | `SoftDeleteMixin`, GDPR erasure |

## P — Privacy

| TSC ID | Criteria | Platform Control | Evidence Source |
|--------|----------|-----------------|----------------|
| P1.1 | Privacy notice | Required at registration | `privacy_notice_accepted` field |
| P2.1 | Consent | COPPA deny-by-default, age-gating | `check_third_party_consent()` |
| P3.1 | Data collection | Minimal collection, purpose limitation | Module-scoped data access |
| P4.1 | Data use | Content moderation, safety scoring | `src/risk/`, `src/moderation/` |
| P5.1 | Data retention | 30-day location, TTL excerpts | Cron jobs, daily cleanup |
| P6.1 | Data access | Parental dashboard, child-friendly notices | `src/compliance/`, portal |
| P7.1 | Data disclosure | NCMEC/CSAM mandatory reporting | `src/moderation/` CSAM pipeline |
| P8.1 | Data quality | Input validation, Pydantic schemas | All router schemas |

## Evidence Collection

Automated evidence is collected via `src/compliance/soc2.py` and stored in the `evidence_collections` table:

- `deployment_log` — Current app version and deploy metadata
- `access_control` — RBAC enforcement summary
- `encryption` — Credential encryption verification
- `audit_trail` — Access log summary with correlation IDs

Run evidence collection: `POST /api/v1/compliance/soc2/collect-evidence` (admin only)
View evidence: `GET /api/v1/compliance/soc2/evidence` (admin only)
