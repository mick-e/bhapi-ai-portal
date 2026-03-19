# ADR-001: Unified Authentication System

**Status:** Accepted
**Date:** 2026-03-17
**Deciders:** Engineering Team

## Context

The Bhapi Platform currently spans multiple codebases with different authentication approaches:

- **Bhapi AI Portal** uses bcrypt password hashing, JWT access tokens, session cookies, and scoped API keys. It supports magic-link login, email verification, multi-tenant isolation, and role-based access control (RBAC) with fine-grained permissions. This system has been validated by 1,400+ tests (including 154 dedicated security tests) and is built to satisfy COPPA and GDPR compliance requirements.
- **Bhapi App (bhapi-inc repos)** uses a simpler token-based auth with no RBAC, no COPPA controls, and 0 tests covering auth flows.

Unifying the platform under a single brand requires a single, consistent authentication and authorization layer. We need to decide whether to adopt an existing system, build a new one, or bring in a third-party provider.

## Decision

Use the bhapi-ai-portal monorepo's existing JWT + API key authentication system as the single auth layer. There is no legacy auth system to unify with — per ADR-010 (clean break), the legacy bhapi-inc repos are archived and their auth code is abandoned. This ADR documents the auth architecture for the unified monorepo only.

Specifically:

- **Password hashing**: bcrypt (already in production).
- **Token strategy**: Short-lived JWT access tokens + refresh tokens, with session cookie support for browser-based flows. Mobile apps (Safety + Social) use the same JWT tokens stored in SecureStore.
- **API keys**: Scoped API keys with PBKDF2-SHA256 hashing, prefix-based identification (`bhapi_sk_`), and per-key permission scopes.
- **Auth pattern**: `GroupContext` + `get_current_user` from `src/auth/middleware.py`. DB sessions via `DbSession` from `src/dependencies.py`. Role checks use `auth.role` and `auth.permissions` from GroupContext.
- **Multi-tenant isolation**: Tenant-scoped queries enforced at the service layer.
- **Child safety**: COPPA-compliant consent flows, parental controls, age-gating, and age-tier permission checks (ADR-009) are integrated into the auth middleware.
- **Scope**: This auth system covers the web portal, browser extension, both mobile apps, and the WebSocket real-time service (ADR-008). All share the same JWT secret and token format.

## Consequences

### Positive

- Leverages a battle-tested system with 1,400+ tests already passing, including 639 E2E and 154 security tests.
- No new vendor dependency or recurring SaaS cost.
- COPPA and GDPR compliance posture is maintained without re-certification effort.
- Single auth codebase means one place to patch vulnerabilities.
- API key scoping model naturally extends to new modules (social, marketplace, etc.).

### Negative

- Engineering team must understand and maintain the auth system in-house rather than offloading to a managed service.
- OAuth2/OIDC social login (Google, Apple) will need to be built on top of the existing system rather than coming out of the box.
- Scaling token validation under high load is our responsibility (mitigated by Redis caching layer with graceful degradation).

### Risks

- **In-house auth complexity**: Custom auth systems accumulate subtle security bugs over time. **Mitigation:** The 154-test security suite provides ongoing regression coverage; all auth changes require security test expansion.
- **Redis dependency for token caching**: Cache outage could degrade token validation performance. **Mitigation:** In-memory fallback is already implemented and tested.
- **OAuth social login gap**: Users who prefer social login may have a worse onboarding experience initially. **Mitigation:** OAuth2/OIDC can be layered on without replacing the core token system.

## Alternatives Considered

### Auth0

- **Pros**: Managed service, social login out of the box, SOC 2 certified, SDKs for web and mobile.
- **Cons**: Recurring cost that scales with MAU ($23/1,000 MAU at Growth tier). Vendor lock-in on token format and user store. COPPA compliance requires careful configuration and is not guaranteed by Auth0 out of the box. Would require migrating 1,400+ tests to work against Auth0's token format. Adds external dependency to critical path (auth outage = full platform outage).
- **Rejected because**: Cost, vendor lock-in, and the effort to re-validate COPPA compliance outweigh the convenience of managed social login.

### Firebase Auth

- **Pros**: Free tier up to 10K MAU, Google ecosystem integration, simple SDK.
- **Cons**: Ties the platform to Google Cloud. Limited RBAC (custom claims only, no built-in permission model). No built-in COPPA consent flow. Firebase tokens are opaque to our backend without the Firebase Admin SDK, adding a hard dependency. Poor fit for API key authentication patterns.
- **Rejected because**: Insufficient RBAC model, no COPPA support, and Google Cloud lock-in.

### Separate Auth Per Product

- **Pros**: Each product team owns its own auth, no coordination needed.
- **Cons**: Duplicate user stores, inconsistent security posture, users need separate accounts for each product, no cross-product SSO, double the attack surface, double the maintenance burden. Directly contradicts the goal of platform unification.
- **Rejected because**: Fundamentally incompatible with the unified platform vision.

## Related ADRs

- [ADR-005](005-platform-unification.md) — Platform unification (this auth system is the designated unified auth layer)
