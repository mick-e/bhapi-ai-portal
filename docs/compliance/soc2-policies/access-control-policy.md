# Access Control Policy

**Version:** 1.0
**Effective Date:** 2026-03-24
**Category:** Security (CC6 — Logical and Physical Access Controls)
**Owner:** Engineering Lead
**Review Cycle:** Annual

---

## 1. Purpose

This policy defines how Bhapi Family AI Governance Platform controls logical access to systems, data, and APIs. It maps directly to SOC 2 Trust Services Criteria CC6.1 (Logical Access Controls), CC6.2 (Authentication), and CC6.3 (Authorization).

---

## 2. Authentication

### 2.1 Password Requirements
- Minimum 8 characters; enforced at registration via Pydantic validation.
- Passwords stored as bcrypt hashes — plaintext is never persisted.
- Password reset via signed email link with 1-hour expiry.

### 2.2 Session Tokens
- JWT Bearer tokens signed with `SECRET_KEY` (HS256).
- Token payload must include `type: "session"` — other token types are rejected.
- Session expiry enforced via `exp` claim; expired tokens return `401 Unauthorized`.

### 2.3 API Keys
- Prefix: `bhapi_sk_` — enables easy identification in logs and audit trails.
- Full key shown only at creation time; DB stores SHA-256 hash only.
- Keys are scoped (e.g. `capture:write`, `reports:read`) — principle of least privilege.
- Revocation: keys can be deactivated via `/api/v1/auth/api-keys/{id}` (DELETE).

### 2.4 OAuth / SSO
- Google Workspace and Entra ID SSO supported via OIDC token validation.
- JWT claims validated; JIT user provisioning creates accounts on first login.
- SAML assertions validated for school district integrations (ClassLink, Clever).

---

## 3. Authorization

### 3.1 Role-Based Access Control (RBAC)
All routes requiring authentication depend on `get_current_user` from `src/auth/middleware.py`, which returns a `GroupContext` with `user_id` and `group_id`.

| Role | Access Scope |
|------|-------------|
| Owner | Full group administration, billing, member management |
| Admin | Member management, report access, alert management |
| Member | Own activity data only |

### 3.2 Group Isolation
- Every database query is scoped by `group_id` — cross-group data access is structurally prevented at the ORM layer.
- Members may not query other groups' data.

### 3.3 Family Member Cap
- Maximum 5 members per family group (`MAX_FAMILY_MEMBERS = 5`).
- Cap enforced in `add_member()` and `accept_invitation()` — returns 409 Conflict if exceeded.
- School and club groups have no enforced member cap.

### 3.4 Child Data Access
- Children under 13 require a signed `FamilyAgreement` before any capture events are ingested.
- Parental dashboard required COPPA-compliant VPC (Verifiable Parental Consent) before accessing child data.

---

## 4. API Key Management

### 4.1 Issuance
- Keys issued via authenticated `POST /api/v1/auth/api-keys`.
- Caller must be an owner or admin of the associated group.

### 4.2 Rotation
- Recommended rotation cycle: 90 days for production keys.
- Old key deactivated immediately on rotation.

### 4.3 Revocation
- Third-party spend provider keys (OpenAI, Anthropic, Google, Microsoft, xAI) are revocable via billing endpoints.
- Revoked keys are invalidated server-side; Fernet-encrypted copies are overwritten.

---

## 5. Privileged Access

- Backend infrastructure access (Render dashboard, GitHub) is limited to named engineers.
- Production database credentials are stored as Render environment variables — never in code.
- Cloud KMS (GCP) used for key encryption when `GCP_PROJECT_ID` is configured.

---

## 6. Monitoring and Review

- All authentication events are logged via `structlog` with correlation IDs (`X-Request-ID`).
- Audit log entries are immutable (`AuditEntry` model — no UPDATE permitted).
- Failed login attempts are rate-limited (5 per minute) via `RateLimitMiddleware`.
- Access reviews: semi-annual review of active API keys and admin role assignments.

---

## 7. References

- SOC 2 CC6.1: Logical access security controls
- SOC 2 CC6.2: Authentication mechanisms
- SOC 2 CC6.3: Authorization / role-based access
- COPPA 2026: Parental consent for child data access
- GDPR Article 25: Data protection by design and default
