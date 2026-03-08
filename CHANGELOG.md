# Changelog

All notable changes to the Bhapi AI Portal are documented here.

## [2.0.0] — 2026-03-08 (Beta)

### Added
- **Member cap enforcement**: Family plans limited to 5 members; enforced in `add_member()` and `accept_invitation()`
- **Stripe webhook persistence**: Subscription lifecycle events (created/updated/cancelled/payment_failed) now persist to DB
- **Persistent threshold alerts**: `FiredThresholdAlert` model replaces in-memory tracking; survives restarts
- **Apple OAuth JWT verification**: JWKS-based verification with cached keys (1-hour TTL)
- **Alert re-notification persistence**: `renotify_count` column replaces in-memory dict
- **Content excerpt encryption**: Stored via `encrypt_credential()` with 365-day TTL and daily cleanup job
- **Export file auto-deletion**: Files older than 7 days cleaned up daily
- **Consent enforcement**: Capture events blocked without guardian consent for minors
- **Digest worker**: Hourly and daily email digest delivery fully implemented
- **EU AI Act compliance**: Algorithmic transparency endpoint, human review requests, appeal submission/resolution
- **COPPA certification readiness**: Verifiable parental consent (5 methods), audit reports, compliance status
- **Per-seat billing**: School/club plans use member count as Stripe quantity; seat count auto-updates on member add/remove
- **14-day free trial**: Applied to new subscriptions via Stripe checkout
- **Twilio SMS notifications**: Rate-limited (10/min/group) with dev-mode logging fallback
- **Clever SIS integration**: OAuth2 roster sync with auto member provisioning
- **ClassLink SIS integration**: OneRoster API roster sync
- **Yoti age verification**: Session-based verification with callback
- **xAI (Grok) spend tracking**: New provider following existing base pattern
- **Safari extension scaffold**: Build script, manifest, and documentation
- **Automated AI session blocking**: Block rules with per-member/per-platform targeting and optional expiry
- **Federated SSO**: Google Workspace and Microsoft Entra with tenant isolation
- **API key revocation**: OpenAI and Anthropic admin API integration for remote key disabling
- **Advanced analytics**: Weekly rolling averages, trend direction, usage patterns, member baselines
- **Internationalization**: 6 languages (English, French, Spanish, German, Portuguese, Italian) with client-side locale detection
- **Frontend pages**: Blocking, analytics, integrations, compliance/transparency, compliance/appeals
- **Age verification UI**: Verify button on member detail page
- **Blocking controls UI**: Block/unblock controls on member detail page
- **SMS settings UI**: SMS toggle and phone number field in notification settings

### Changed
- Version bumped from 1.0.0 to 2.0.0 across pyproject.toml, config.py, portal/package.json, extension/package.json
- Billing checkout now accepts school/club plans (previously family-only self-serve)
- Migration count: 4 → 6 (005_add_alert_snoozed_until, 006_beta_schema_changes)
- Module count: 11 → 15 (added integrations, blocking, analytics, sms)
- Backend test count: 566 → 689
- Security test count: 20 → 66

### Fixed
- serialize-javascript RCE vulnerability (extension): overridden to >=7.0.4
- minimatch ReDoS vulnerability (portal + extension): overridden to >=10.2.4

### Security
- 66 security tests covering: JWT tampering, data isolation, SQL/XSS injection, rate limiting, COPPA bypass, content encryption, block bypass, member cap bypass, webhook signature, SIS credential encryption, SMS rate limiting, SSO provider validation

## [1.0.0] — 2026-02-15 (MVP)

### Added
- Core platform: auth, groups, capture, risk, alerts, billing, reporting, portal, compliance, email, jobs
- Browser extension (Chrome + Firefox, Manifest V3)
- Risk pipeline: PII detection, safety classification, rules engine, risk events, alerts
- Consent enforcement: COPPA (US <13), GDPR (EU <16), LGPD (Brazil <18), AU Privacy (<16)
- LLM spend tracking: OpenAI, Anthropic, Google, Microsoft providers
- Budget thresholds with configurable percentage alerts (50/80/100%)
- Stripe checkout and billing portal for family plans
- PDF (ReportLab) and CSV report generation with email delivery
- Data deletion and export workflows (GDPR compliance)
- API key authentication (`bhapi_sk_` prefix, SHA-256 hashed)
- Email delivery via SendGrid with digest modes (immediate, hourly, daily)
- Next.js frontend with WCAG 2.1 AA accessibility
- 566 backend tests, 59 frontend tests
