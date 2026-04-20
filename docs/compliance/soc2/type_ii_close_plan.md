# SOC 2 Type II Audit Close — Phase 4 Task 31

**Status:** Awaiting observation window close. **Auditor fieldwork PENDING — engage selected audit firm for Q1 2027.**
**Owner:** Founder + Head of Compliance (human action required)
**Scope close:** Q1 2027 (end of 6-month observation window, started Oct 2026 per `engagement.md`)
**Date:** 2026-04-20

## Prerequisites (must land before auditor fieldwork)

- [x] Audit firm selected (see `engagement.md`) — **CONFIRM STATUS**
- [x] Evidence platform active (Vanta / Drata / Secureframe) — **CONFIRM STATUS**
- [ ] 6-month observation window concluded without material control failures
- [ ] All Phase 4 remediations landed (Tasks 1-2: CSP tightening, exception audit — DONE)
- [ ] Quarterly evidence bundles shipped to auditor

## Close plan

### Step 1 — Confirm observation window
Observation started Week 4 of Phase 4 Layer 1 (mid-October 2026). Closes mid-April 2027.

If the window was interrupted (e.g. material incident mid-window), reset the clock — auditor determines exact handling.

### Step 2 — Final evidence bundle
Run `python scripts/soc2/evidence_collector.py --quarter 2027-Q1` and upload to auditor portal alongside the three prior quarters' evidence.

Evidence bundle contents (per `src/compliance/soc2_evidence.py`):
- Access control sample (quarterly user-access reviews)
- Encryption verification (Fernet / KMS key rotation records)
- Incident response records (all logged incidents + response times)
- Change management (PR reviews, deployment logs)
- Vendor management (third-party access review)
- Monitoring + logging (sample log retention + alerting records)
- Business continuity (backup + restore drill records)

### Step 3 — Auditor fieldwork (2-3 weeks)
- Auditor conducts interviews with named control owners
- Sample testing of transactions + access logs
- Evidence reconciliation against claimed controls
- Draft report findings shared with compliance team

### Step 4 — Remediate findings (1-2 weeks)
Close all findings in auditor's draft. Common last-mile findings:
- Missing written procedures for already-implemented controls → write them up
- Access logs not retained long enough → extend retention or document exception
- Incident response documentation gaps → fill with real past incidents

### Step 5 — Receive final report
Signed SOC 2 Type II report delivered by auditor. Store at:
- `docs/compliance/soc2/2027_q1_type_ii_report.pdf` — **gitignored** (confidential)
- Evidence bundle archive — offline storage per retention policy

### Step 6 — Update marketing + sales collateral
- Pricing page (`portal/src/app/(landing)/pricing/page.tsx`) — add SOC 2 Type II badge to School / Enterprise tiers
- Landing page — add SOC 2 Type II to the trust signals section
- Sales decks — add certification logo + issue date
- RFP template responses — update SOC 2 answer from "in progress" to "issued, report available under NDA"
- `CLAUDE.md` — note SOC 2 Type II issued in compliance section

### Step 7 — Announce (Phase 4 launch comms — Task 32)
Blog post + customer email: "Bhapi is SOC 2 Type II certified."

## Commit pattern (non-confidential parts only)

When the report is issued:
```bash
# Never commit the PDF itself — confidential
# Instead commit the marketing updates:
git add portal/src/app/\(landing\)/pricing/page.tsx docs/compliance/soc2/type_ii_close_plan.md
git commit -m "feat(soc2): SOC 2 Type II report issued — update marketing collateral

Audit report received and on file (not committed — confidential per
gitignore). Pricing page, landing trust signals, and sales collateral
updated with certification badge + issue date.

Closes R-21 from review-recommendations plan."
```

## Failure modes + mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Auditor finds material gap mid-window | Low | Critical | Gap assessment complete (per engagement.md); monitor monthly |
| Auditor fieldwork slips past target close | Medium | High | Start fieldwork 3 weeks before target, not on target |
| Evidence platform integration breaks mid-window | Medium | Medium | Weekly evidence sync health check; ticket immediately on drift |
| Remediation can't close findings in window | Low | High | Engage SOC 2-experienced counsel for draft-findings review |

## Counsel / auditor questions log

(Fill in during fieldwork.)

## Roll-forward after close

- Automate quarterly evidence bundle submission
- Schedule annual Type II renewal (due Q1 2028)
- Plan ISO 27001 co-audit (efficiency — shares ~70% controls with SOC 2)
