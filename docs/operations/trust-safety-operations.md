# Trust & Safety Operations

**Bhapi Inc.** | **Document Owner:** Trust & Safety Lead
**Version:** 1.0 | **Effective Date:** 2026-03-20
**Review Cadence:** Quarterly

---

## 1. Purpose

This document defines Bhapi's Trust & Safety (T&S) operational procedures for the bhapi.ai platform. It covers content moderation, incident response, user reporting, appeals, and law enforcement cooperation. These procedures are designed to protect minors and comply with COPPA, FERPA, CSAM reporting obligations (18 U.S.C. 2258A), and platform-specific safety requirements.

---

## 2. Incident Severity Classification

| Severity | Description | Examples | Response Time |
|----------|-------------|----------|---------------|
| **P0 — Critical** | CSAM, imminent danger to a child, active exploitation | CSAM detection, suicide/self-harm crisis, kidnapping/trafficking indicators | Immediate (< 15 min) |
| **P1 — High** | Harassment, threats, predatory behavior | Grooming patterns, death threats, doxxing, sextortion | < 1 hour |
| **P2 — Medium** | Policy violations, inappropriate content | Bypassing safety controls, sharing restricted content, bullying | < 4 hours |
| **P3 — Low** | Spam, minor violations | Spam accounts, minor TOS violations, false positives | < 24 hours |

---

## 3. Content Moderation Escalation Procedures

### 3.1 Automated Detection (Tier 0)

- The risk pipeline continuously analyzes captured AI interactions against 14 taxonomy categories.
- Content flagged with risk score >= 80 is automatically escalated to human review.
- Keyword-based fallback operates when Google AI consent is not provided.
- All flagged content is logged with correlation IDs for audit trail.

### 3.2 Human Review (Tier 1)

- Trained moderators review auto-flagged content within the SLA for the assigned severity.
- Moderators classify the content, confirm or dismiss the flag, and take initial action.
- Actions available: dismiss (false positive), warn user, restrict access, escalate.
- All decisions are logged with moderator ID, timestamp, rationale, and action taken.

### 3.3 Admin Escalation (Tier 2)

- Tier 1 moderators escalate to a senior T&S admin when:
  - Content involves a P0 or P1 incident.
  - The moderator is uncertain about classification.
  - The content involves a repeat offender.
  - Legal or law enforcement involvement may be required.
- Senior admin reviews within 30 minutes for P0, 1 hour for P1.
- Senior admin may involve legal counsel or executive leadership as needed.

### 3.4 Executive Escalation (Tier 3)

- P0 incidents always notify the CEO and legal counsel immediately.
- Decisions involving account termination, law enforcement referral, or public disclosure require executive sign-off.

---

## 4. CSAM Response Protocol

Per the National Center for Missing & Exploited Children (NCMEC) requirements and 18 U.S.C. 2258A:

### 4.1 Detection

- Automated hash matching (PhotoDNA or equivalent) on any image/media content.
- Risk pipeline flags conversations indicating CSAM generation, distribution, or solicitation.
- Staff reports of suspected CSAM during routine moderation.

### 4.2 Preserve

- Immediately preserve all relevant data: content, metadata, user account info, IP addresses, timestamps.
- Do NOT delete or modify any evidence.
- Store preserved data in a secured, access-restricted evidence vault.
- Retention: minimum 90 days or as required by law enforcement.

### 4.3 Report

- File a CyberTipline report with NCMEC within 24 hours of discovery (requirement under 18 U.S.C. 2258A).
- Include all preserved evidence as specified by NCMEC reporting guidelines.
- Designated NCMEC reporting contact: Trust & Safety Lead (or delegate).

### 4.4 Suspend

- Immediately suspend the offending user account.
- Disable all access and API keys associated with the account.
- If the account is a child account within a family group, notify the parent/guardian admin only after consulting legal counsel (to avoid tipping off a potential abuser).

### 4.5 Audit

- Document the full incident timeline in the incident management system.
- Conduct a post-incident review within 7 days.
- Update detection rules if the incident reveals gaps.
- File records are retained per legal hold requirements.

---

## 5. User Report Handling SLA

| Stage | SLA | Description |
|-------|-----|-------------|
| **Acknowledge** | < 1 hour | Automated acknowledgment sent to reporter confirming receipt. |
| **Initial Review** | < 4 hours | A moderator reviews the report, classifies severity, and takes initial action if needed. |
| **Resolution** | < 24 hours | Final determination made, action taken, and reporter notified of outcome. |

### 5.1 Report Channels

- In-app report button (available to parents, school admins, and children with age-appropriate UI).
- Email: safety@bhapi.ai
- Portal: parent/school admin dashboard reporting interface.

### 5.2 Report Tracking

- Every report receives a unique tracking ID.
- Reporters can check status via the portal or by replying to the acknowledgment email.
- Reports are never closed without a documented resolution.

---

## 6. Moderator Training Requirements

### 6.1 Initial Training (Before Handling Cases)

- Platform policies and Terms of Service (4 hours).
- Child safety fundamentals: grooming indicators, CSAM identification, age-appropriate content (8 hours).
- COPPA and FERPA compliance essentials (2 hours).
- Moderation tooling and workflow training (4 hours).
- Trauma-informed practices and moderator wellness (2 hours).
- Assessment: must pass with >= 90% before handling live cases.

### 6.2 Quarterly Refresher Training

- Policy updates and new threat patterns (2 hours).
- Case study review of recent escalations (1 hour).
- Wellness check-in and mental health resources review (1 hour).

### 6.3 Age-Specific Training

- Moderators handling content from users under 13 must complete additional COPPA-specific training (4 hours).
- Training covers: consent requirements, data minimization, child-appropriate communication, mandatory reporting obligations.

### 6.4 Moderator Wellness

- Access to Employee Assistance Program (EAP) counseling.
- Maximum 4-hour shifts reviewing graphic or disturbing content.
- Mandatory breaks every 90 minutes during content review shifts.
- Option to rotate off T&S duties temporarily without career penalty.

---

## 7. Appeal Process

### 7.1 Eligibility

- Users may appeal any moderation action (warning, restriction, suspension) except CSAM-related suspensions (non-appealable per policy).
- Appeals must be submitted within 14 days of the action.

### 7.2 Procedure

1. **Submit:** User submits appeal via the portal or email (appeals@bhapi.ai) with the action reference ID and their statement.
2. **Assign:** Appeal is assigned to a different moderator than the one who made the original decision.
3. **Review:** The assigned moderator reviews the original evidence, the user's statement, and any additional context.
4. **Decision:** Appeal is upheld (action stands), modified (reduced action), or overturned (action reversed).
5. **Notify:** User is notified of the outcome within 48 hours of submission.

### 7.3 Records

- All appeals and outcomes are logged for quality assurance and bias monitoring.
- Quarterly review of appeal overturn rates to identify training gaps.

---

## 8. Law Enforcement Cooperation

### 8.1 Designated Contact

- Primary: Trust & Safety Lead
- Secondary: General Counsel
- Contact: legal@bhapi.ai

### 8.2 Lawful Requests

- Bhapi cooperates with valid legal process (subpoenas, court orders, search warrants).
- All requests are reviewed by legal counsel before disclosure.
- Emergency disclosure (without legal process) is permitted when there is imminent risk of death or serious physical injury to a child, per 18 U.S.C. 2702(b)(8).

### 8.3 Evidence Preservation

- Upon receipt of a valid preservation request (18 U.S.C. 2703(f)), Bhapi will preserve the specified records for 90 days (extendable upon renewal).
- Preservation requests must be directed to legal@bhapi.ai.

### 8.4 Response Procedures

1. Log the request in the legal request tracker.
2. Route to legal counsel for review within 4 hours.
3. Scope the response to only the data specified in the legal process.
4. Provide data in a secure, structured format.
5. Notify the user of the request unless prohibited by law (e.g., gag order).

### 8.5 Proactive Reporting

- Bhapi proactively reports to NCMEC (CSAM) and may report to law enforcement when there is reasonable belief of imminent danger to a child.
- See also: [Incident Response Plan](../security/incident-response-plan.md)

---

## 9. Related Documents

- [Incident Response Plan](../security/incident-response-plan.md)
- [Penetration Test Plan](../security/pentest-plan.md)
- [FERPA Compliance](../compliance/ferpa-compliance.md)
- [Security Program](../compliance/security-program.md)
- [DPIA](../compliance/dpia.md)

---

## 10. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-20 | T&S Operations | Initial document |
