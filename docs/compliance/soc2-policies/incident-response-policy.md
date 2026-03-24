# Incident Response Policy

**Version:** 1.0
**Effective Date:** 2026-03-24
**Category:** Availability (A1) / Security (CC7)
**Owner:** Engineering Lead
**Review Cycle:** Annual; after any P1/P2 incident

---

## 1. Purpose

This policy defines how Bhapi Family AI Governance Platform detects, responds to, and recovers from security and operational incidents. It maps to SOC 2 CC7.3 (Threat response), CC7.4 (Incident response), and A1.2 (Recovery objectives).

---

## 2. Scope

This policy applies to all security incidents affecting:
- Production systems at bhapi.ai (API, WebSocket service, scheduled jobs)
- Child safety data (conversation logs, risk events, capture events)
- Authentication infrastructure (JWTs, API keys, OAuth flows)
- Third-party integrations (Stripe, Twilio, SendGrid, Clever, ClassLink, Yoti)

---

## 3. Incident Severity Levels

| Severity | Definition | Examples |
|----------|------------|---------|
| P1 — Critical | Service unavailable or child data breach | Production outage, unauthorised access to child PII, database corruption |
| P2 — High | Significant degradation or security event | Auth bypass attempt, third-party API key leak, <50% of alerts failing to deliver |
| P3 — Medium | Partial impact, no data breach | Single module failure, elevated error rates, non-critical dependency down |
| P4 — Low | Cosmetic or negligible impact | UI rendering bug, non-sensitive configuration drift |

---

## 4. Detection

### 4.1 Automated Detection
- **Structured logging:** All requests logged with `structlog` including correlation IDs (`X-Request-ID`), status codes, and `duration_ms`.
- **Health checks:** `/health` endpoint checks DB connectivity (`SELECT 1`) and reports `database: "ok"/"error"`.
- **Render alerting:** CPU, memory, and crash restart notifications configured in Render dashboard.
- **Rate limit events:** Excessive 429 responses logged and surfaced in the audit trail.

### 4.2 Manual Detection
- Engineer monitors Render deploy logs after each release.
- On-call rotation reviews error rate dashboards daily.
- NCMEC CyberTipline failures are logged as P2 incidents automatically.

---

## 5. Response Procedures

### 5.1 Initial Response (within 15 minutes for P1/P2)

1. **Acknowledge** — engineer picks up the incident in the #incidents Slack channel.
2. **Assess** — determine scope: which users affected, what data at risk, is it ongoing?
3. **Contain** — if a data breach: revoke affected API keys via `DELETE /api/v1/auth/api-keys/{id}`; if auth bypass: rotate `SECRET_KEY` and redeploy.
4. **Escalate** — page on-call lead for P1; notify Engineering Lead for P2.

### 5.2 Investigation (within 1 hour for P1)

1. Pull structured logs from Render log stream, filter by `X-Request-ID` of suspicious requests.
2. Query audit log (`GET /api/v1/compliance/audit-log`) for affected `group_id` / `actor_id`.
3. Check incident record: `POST /api/v1/compliance/incidents` to create a formal record; use `PATCH` to update timeline.

### 5.3 Remediation

1. Apply fix via PR → CI → merge to master → Render auto-deploy.
2. If migration is needed: commit migration file, push, confirm Render applies `alembic upgrade head` on restart.
3. Verify fix with targeted smoke tests against production (E2E test suite: `pytest tests/e2e/test_production.py -v`).

### 5.4 Recovery

1. Confirm all affected services report healthy on `/health`.
2. Verify child safety pipeline is operational (capture events ingesting, risk events generating, alerts delivering).
3. Update incident record status to `resolved`.

---

## 6. Notification Timelines

| Audience | P1 Timeline | P2 Timeline |
|----------|-------------|-------------|
| Engineering team | Immediate (Slack) | Within 30 minutes |
| Engineering Lead | Immediate | Within 1 hour |
| Affected users (data breach) | Within 72 hours (GDPR Article 33) | N/A unless breach |
| Regulatory authority (if child data breach) | Within 72 hours (GDPR) / 10 days (COPPA 2026) | N/A unless breach |
| NCMEC (if CSAM involved) | Immediately | N/A |

---

## 7. Post-Incident Review

- P1 incidents: post-mortem required within 5 business days.
- P2 incidents: root cause written to `docs/security/incidents/` within 10 business days.
- Review includes: timeline, root cause, contributing factors, remediation steps, prevention controls.
- Lessons learned are reflected in this policy within the next annual review cycle.

---

## 8. Incident Records

Incidents are tracked via the compliance module:
- Create: `POST /api/v1/compliance/incidents` (title, severity, category, description)
- Update: `PATCH /api/v1/compliance/incidents/{id}` (status, resolution, root_cause)
- List: `GET /api/v1/compliance/incidents`

Incident records are linked to audit log entries for full traceability.

---

## 9. References

- SOC 2 CC7.3: Evaluation and communication of identified security threats
- SOC 2 CC7.4: Incident response program
- SOC 2 A1.2: Environmental, regulatory, and technological changes
- GDPR Article 33: Notification of a personal data breach to supervisory authority
- COPPA 2026: Breach notification requirements for children's data
- `docs/security/incident-response-plan.md` — operational runbook
