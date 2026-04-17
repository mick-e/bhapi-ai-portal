# Identity Protection Partnership — Vendor Selection (Phase 4 Task 22)

**Status:** Code skeleton deployed with `MockPartnerClient`. **Vendor selection PENDING BD outreach.**
**Owner:** Founder / BD lead (human action required)
**Date:** 2026-04-18

## Why this matters

Bhapi Family+ ($19.99/mo, Phase 4 Task 21) bundles identity protection as a differentiator vs. Aura ($32/mo). To honour that bundle promise we need a partner contract before public Family+ launch.

## Code state

- `src/billing/partnerships.py` — partner-agnostic `PartnerClient` ABC + `MockPartnerClient` default
- Migration 058 — `identity_protection_links` table with audit trail (consent_text_version, partner_account_id, status)
- Endpoints — `POST /activate`, `GET /status`, `POST /cancel` under `/api/v1/billing/identity-protection`
- 8 E2E tests passing (consent enforcement, tier-gating, idempotency, cancellation)

When a real partner is signed, drop a new `PartnerClient` subclass into `partnerships.py`, set `BHAPI_IDENTITY_PARTNER=<name>` in production, and the rest of the stack works unchanged.

## Candidate partners

| Partner | API access? | Family plan? | Pricing tier | Notes |
|---|---|---|---|---|
| Aura | Limited (consumer focus) | Yes ($25-32/mo) | $$$ | Direct competitor — unlikely to white-label |
| IDX | Yes (B2B/B2B2C) | Yes | $$ | Strong post-breach positioning, less consumer brand |
| Identity Guard (Aura subsidiary) | Yes | Yes | $$ | Same parent as Aura — may get blocked |
| LifeLock (Norton/Gen) | Limited (mostly direct) | Yes | $$$ | Brand recognition; complicated white-label terms |
| Allstate Identity Protection | Yes (B2B) | Yes | $$ | Insurance-bundled angle, willing to white-label |

## Diligence checklist (per partner)

- API capability — account creation, dependent enrollment, alert webhook, cancellation
- Coverage — credit monitoring (3 bureaus), dark web, SSN trace, court records, social media monitoring
- Geographic coverage — US (yes), UK (varies), EU/AU (rare)
- Revenue share — typical ranges 10-25% rev-share or fixed wholesale
- Cancellation/refund policy
- Brand placement — co-branded vs. white-label vs. powered-by
- Liability/legal — incident response coordination, insurance requirements
- Contract length and renewal terms

## Legal (must complete before launch)

- Per-user consent flow distinct from Family+ subscription consent (already enforced in code via `agreed=True` boundary)
- DPA/BAA for cross-product PII transfer (SSN, dependent info)
- Data retention agreement on partner side
- GDPR / UK Data Protection Act compliance review
- COPPA review — adding minor SSNs to partner monitoring requires separate parental consent gate

## Ship criteria for replacing the mock

1. Signed contract with partner X
2. `BHAPI_IDENTITY_PARTNER` env var documented and set in Render `core-api` service
3. Concrete `PartnerClient` subclass implemented + integration test against partner sandbox
4. Webhook handler for partner→Bhapi alerts (path: `POST /api/v1/billing/identity-protection/webhook`)
5. Updated marketing copy in `portal/src/app/(landing)/pricing/page.tsx` to name the partner brand

Until then the Family+ tier still ships — the activation endpoint will provision a `mock-` partner account, which logs but takes no real action. Marketing copy must avoid promising real identity protection until a partner is live.
