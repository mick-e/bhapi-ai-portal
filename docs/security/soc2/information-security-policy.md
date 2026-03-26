# Information Security Policy

**Version:** 1.0
**Effective:** 2026-08-01
**Owner:** CTO
**Review cycle:** Annual

## 1. Purpose

Establish the security framework for protecting Bhapi platform data, systems, and users — with emphasis on children's data under COPPA, GDPR, and regional regulations.

## 2. Scope

All Bhapi systems, services, and personnel handling platform data:
- Core API (FastAPI backend, PostgreSQL, Redis)
- Portal (Next.js frontend)
- Mobile apps (Expo — Safety + Social)
- Browser extension (Manifest V3)
- Infrastructure (Render, Cloudflare R2)

## 3. Principles

1. **Defense in depth** — Multiple security layers (WAF, middleware, application, database)
2. **Least privilege** — RBAC with scoped API keys, role-based access
3. **Encrypt everywhere** — TLS in transit, Fernet/KMS at rest for credentials
4. **Audit everything** — Structured JSON logging with correlation IDs, request logging middleware
5. **Child safety first** — COPPA consent enforcement, age-tier restrictions, content moderation

## 4. Authentication and Access Control

- **Users:** JWT session tokens with `type: "session"` field, bcrypt password hashing
- **API clients:** `bhapi_sk_` prefixed keys, SHA-256 hashed in DB, scoped permissions
- **MFA:** Supported for all accounts
- **SSO:** OIDC + SAML with JIT provisioning, 10-minute session expiry
- **Rate limiting:** Redis sliding window + in-memory fallback (100/min default, 5/min register)

## 5. Data Protection

- **Encryption at rest:** Credentials via `encrypt_credential()` (Fernet, Cloud KMS in production)
- **Encryption in transit:** TLS 1.2+ on all endpoints
- **Content excerpts:** Encrypted with TTL, auto-cleanup via daily job
- **Location data:** Lat/lng encrypted at rest, decrypted only for authorized parent/admin
- **Data retention:** 30-day rolling window for location, configurable for school data

## 6. Incident Response

See `docs/security/incident-response-plan.md` for the full incident response procedure.

## 7. Change Management

- All code changes require pull request review
- CI/CD via GitHub Actions — automated testing (4,639+ backend, 665+ mobile tests)
- Alembic migrations run automatically on deploy
- Security tests (348+) run on every push

## 8. Vulnerability Management

- Dependabot for dependency scanning
- Regular penetration testing (see `docs/security/pentest-plan.md`)
- OWASP Top 10 addressed: XSS (CSP headers), SQLi (ORM parameterization), CSRF (SameSite cookies)

## 9. Personnel Security

- Background checks for team members with data access
- Security awareness training on onboarding
- Access revocation within 24 hours of offboarding
