# 02 — Content Takedown SLA (OSA Part 3 + Part 6, 24h SLA)

**Requirement:** Upon receipt of an eSafety removal notice (cyberbullying, image-based abuse, or Class 1 material), providers must remove the material within 24 hours or face civil penalties up to AUD $555,000.

## Code references

- `src/moderation/` — pre-publish (under-13) + post-publish (13-15) pipelines
- `src/moderation/service.py:handle_takedown_notice()` — receipt to removal workflow
- `src/moderation/router.py` — SLA dashboard endpoints
- `portal/src/app/(dashboard)/moderation/page.tsx` — live p50/p95 latency, queue depth, breach count

## SLA Monitoring

Report timestamp is the SLA start. Alerts:
- 12h elapsed → warning to on-call moderator
- 18h elapsed → urgent warning + escalation to platform admin
- 22h elapsed → auto-escalate; must-resolve
- 24h breach → logged as SLA violation in `moderation_sla_breaches` table (see migration 039)

## Tests

- `tests/e2e/test_moderation_sla.py` — SLA metric computation
- `tests/unit/test_moderation_sla.py` — countdown + escalation logic
- `tests/e2e/test_takedown_workflow.py` — end-to-end takedown notice flow

## Operational

- Moderation dashboard: `https://bhapi.ai/moderation` (role-gated to admins)
- p50 target: <60 minutes
- p95 target: <6 hours
- Breach alert channel: email + Slack (configured via `SLA_ALERT_EMAIL`)

## Counsel review items

- Is our 24h countdown acceptable (starts from report receipt, not from admin review)?
- Do we need evidence of a backup on-call schedule to cover nights/weekends?
- What's the correct legal contact for receiving eSafety removal notices? (See 09-au-contact-point.md)
