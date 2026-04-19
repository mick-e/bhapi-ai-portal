# 08 — Reporting & Complaints (OSA Part 3)

**Requirement:** Provide accessible reporting tools in-product. Respond to user complaints within a defined SLA. Retain records of all reports and responses.

## In-product reporting

- Every social content item has a "Report" button (keyboard-accessible, WCAG AA)
- Report form categorises by reason: bullying, harassment, hate speech, self-harm, sexual content, illegal activity, other
- Submission creates a `ModerationReport` row with `source=user_report`
- User receives confirmation + case number immediately

## Email intake

- `safety@bhapi.ai` — dedicated safety inbox, monitored during business hours + on-call rotation
- `abuse@bhapi.ai` — mirror inbox for compatibility with external abuse-reporting tooling

## eSafety removal notices

- Intake at `safety@bhapi.ai` (can be escalated to counsel if needed)
- Manual flow: triage → feed into moderation queue → execute removal within 24h SLA

## Code references

- `src/moderation/reporting.py` — in-product report handler
- `src/email/service.py` — inbound email routing
- `portal/src/app/(dashboard)/moderation/page.tsx` — admin queue view

## Tests

- `tests/e2e/test_reporting_flow.py` — end-to-end user report
- `tests/e2e/test_email_intake.py` — email-to-queue routing

## Counsel review items

- Is our single safety inbox sufficient, or do we need jurisdiction-specific inboxes (e.g., `au-safety@bhapi.ai`)?
- Do we need to publish a "trusted flagger" program for eSafety and similar regulators?
- Complaint retention: current 7-year default policy — counsel to confirm for AU market
