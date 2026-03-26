# Access Control Policy

**Version:** 1.0
**Effective:** 2026-08-01
**Owner:** CTO
**Review cycle:** Annual

## 1. Purpose

Define access control requirements for the Bhapi platform ensuring least-privilege access, proper authentication, and audit logging.

## 2. User Authentication

### 2.1 Password Requirements
- Minimum 8 characters, bcrypt hashing (cost factor 12)
- Password reset via magic link (token-based, single-use)

### 2.2 Session Management
- JWT tokens with `type: "session"` claim
- Configurable expiry (default 24h, SSO 10min)
- Token refresh without re-authentication

### 2.3 Multi-Factor Authentication
- TOTP-based MFA available for all accounts
- Required for admin roles

### 2.4 SSO Integration
- OIDC token validation (JWT claims)
- SAML assertion validation
- JIT user provisioning from identity providers
- Supported providers: Google Workspace, Microsoft Entra

## 3. Role-Based Access Control (RBAC)

### 3.1 Roles
| Role | Scope | Capabilities |
|------|-------|-------------|
| `owner` | Group | Full access, billing, member management |
| `admin` | Group | Member management, settings, reporting |
| `parent` | Group | View activity, manage children, approve contacts |
| `member` | Group | Own data, age-tier-gated features |
| `school_admin` | School | Class management, safeguarding reports |

### 3.2 Permission Enforcement
- `require_permission()` on all 105+ routers (~500+ write endpoints)
- Wildcard `"*"` scope for admin API keys
- Group isolation — users cannot access data outside their group

### 3.3 Age-Tier Access Control
- Young (5-9): Restricted — no messaging, no contacts, no search
- Pre-teen (10-12): Moderate — messaging, search, no video, no group chat
- Teen (13-15): Standard — all social features except location sharing
- Enforcement: `src/age_tier/middleware.py` dependency on all social endpoints

## 4. API Key Management

- Prefix: `bhapi_sk_` for identification
- Storage: SHA-256 hash in DB (full key shown only on creation)
- Scoped permissions per key
- Revocation: Immediate, cascade to active sessions

## 5. Infrastructure Access

- Render dashboard: SSO with team roles
- Database: No direct access, all queries via ORM
- Redis: Internal network only, no public exposure
- Cloudflare R2: Presigned URLs with TTL

## 6. Audit Logging

- All authentication events logged (login, logout, MFA, failed attempts)
- All data access logged with correlation IDs
- Location data access creates `LocationAuditLog` entries
- Structured JSON logging via structlog
- Request logging middleware: method, path, status, duration_ms
