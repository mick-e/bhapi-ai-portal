# Data Classification Policy

**Version:** 1.0
**Effective:** 2026-08-01
**Owner:** CTO
**Review cycle:** Annual

## 1. Purpose

Define data classification levels and handling requirements for the Bhapi platform, with special attention to children's data.

## 2. Classification Levels

### Level 1: Public
- Marketing content, landing pages, public API documentation
- No access controls required

### Level 2: Internal
- Aggregated analytics, feature flags, configuration
- Requires authentication

### Level 3: Confidential
- User accounts, group membership, billing details
- Requires authentication + group isolation
- Encrypted in transit (TLS)

### Level 4: Restricted
- Children's personal data (names, DOB, activity, location)
- AI conversation content and risk assessments
- API keys, credentials, session tokens
- Requires authentication + RBAC + encryption at rest
- Subject to COPPA, GDPR, and regional regulations

## 3. Data Handling by Type

| Data Type | Classification | Encryption at Rest | Retention | COPPA Consent |
|-----------|---------------|-------------------|-----------|---------------|
| User credentials | Restricted | bcrypt hash | Until deletion | N/A |
| API keys | Restricted | SHA-256 hash | Until revocation | N/A |
| Session tokens | Restricted | JWT signed | 24h (SSO: 10min) | N/A |
| Content excerpts | Restricted | Fernet | TTL (daily cleanup) | Required |
| Location data | Restricted | Fernet (lat/lng) | 30 days rolling | Explicit consent |
| Screen time | Confidential | N/A | 90 days | Required |
| Social posts | Confidential | N/A | Until deletion | Required (age-gated) |
| Risk assessments | Restricted | N/A | With parent account | Required |
| Billing data | Confidential | Stripe-managed | Per Stripe policy | N/A |
| Audit logs | Internal | N/A | 1 year | N/A |

## 4. Children's Data (COPPA/GDPR)

- **Deny-by-default consent** for third-party APIs (SendGrid, Twilio, Google AI, Hive/Sensity)
- **Age-gating:** Children <13 require signed FamilyAgreement for capture events
- **Privacy notice:** Required at registration (`privacy_notice_accepted: True`)
- **Parental dashboard:** Parents can view/export/delete all child data
- **Right to erasure:** GDPR-compliant deletion including location history within 24h
- **Safe harbor certificate:** JSON + PDF export available

## 5. Data Disposal

- Soft-delete with `SoftDeleteMixin` (`deleted_at` with auto-filtering)
- Hard delete available via GDPR erasure endpoints
- Location data: 30-day auto-purge via daily cron
- Content excerpts: TTL-based auto-cleanup
- Database backups: Encrypted, 30-day retention
