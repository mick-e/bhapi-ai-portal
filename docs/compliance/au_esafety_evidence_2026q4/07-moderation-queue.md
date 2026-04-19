# 07 — Moderation Queue (Phase 2 industry codes)

**Requirement:** Phase 2 industry codes (effective 2026-03-09) require a moderation queue with documented SLA, reviewer access controls, and audit trail.

## Code references

- `src/moderation/service.py` — queue management
- `src/moderation/router.py` — admin endpoints for queue inspection
- `portal/src/app/(dashboard)/moderation/page.tsx` — live dashboard

## Queue properties

- **Depth tracking:** persistent metric for pending items
- **Latency tracking:** p50/p95 time-from-report-to-action
- **Priority rules:** AU reports + CSAM-adjacent content flagged as HIGH priority
- **Reviewer RBAC:** role-gated — only users with `moderation.review` permission can act
- **Audit trail:** every queue action logged to `audit_entries` with before/after state

## Tests

- `tests/e2e/test_moderation.py` — queue lifecycle
- `tests/e2e/test_moderation_sla.py` — SLA metric computation
- `tests/security/test_moderation_security.py` — reviewer RBAC

## Counsel review items

- Phase 2 codes require "adequate" staffing for moderation. What is "adequate" for Bhapi's expected AU user volume? Counsel to advise on minimum staffing.
- Audit trail retention — how long must we keep moderation audit records? (current default: 7 years per our retention policy)
