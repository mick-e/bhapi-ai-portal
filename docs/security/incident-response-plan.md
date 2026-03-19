# Bhapi Platform — Incident Response Plan

**Version:** 1.0
**Date:** March 19, 2026
**Status:** Active
**Owner:** Engineering Lead
**Review Cycle:** Quarterly
**Classification:** Internal — Confidential

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Category 1: Data Breach](#2-category-1-data-breach)
3. [Category 2: Child Safety Incident](#3-category-2-child-safety-incident)
4. [Category 3: Platform Abuse](#4-category-3-platform-abuse)
5. [Category 4: Service Outage](#5-category-4-service-outage)
6. [Decision Authority Matrix](#6-decision-authority-matrix)
7. [Contact Directory](#7-contact-directory)
8. [Post-Incident Review Template](#8-post-incident-review-template)
9. [Testing the Plan](#9-testing-the-plan)
10. [Document History](#10-document-history)

---

## 1. Purpose and Scope

This document defines how Bhapi responds to security incidents, child safety events, platform abuse, and service outages. It applies to all Bhapi products — Bhapi Safety (parent app), Bhapi Social (child app), the browser extension, and the bhapi.ai web portal.

Bhapi operates a children's digital safety platform subject to COPPA (US), GDPR (EU), the Online Safety Act (AU), the Age Appropriate Design Code (UK), and the EU AI Act. All incident response actions must account for these regulatory obligations.

**Guiding principle:** When in doubt, prioritize child safety over platform availability. Every employee is authorized to escalate a child safety concern without approval.

---

## 2. Category 1: Data Breach

### Response Phases

| Phase | Action | Timeline | Owner |
|-------|--------|----------|-------|
| Detection | Identify breach via monitoring alerts, user report, security researcher disclosure, or external notification | Immediate | On-call engineer |
| Containment | Isolate affected systems, revoke compromised credentials (API keys, JWT signing keys, database passwords), block the attack vector, rotate Fernet encryption keys if content excerpts exposed | <1 hour | On-call + Engineering Lead |
| Assessment | Determine: what data was exposed, how many users affected, attack vector, duration of exposure, whether children's data is involved, jurisdictions affected | <4 hours | Engineering Lead |
| Regulatory Notification | FTC (COPPA): "as soon as possible". EU GDPR: relevant DPA within 72 hours. AU OAIC: "as soon as practicable". Ohio: per state breach notification requirements. UK ICO: within 72 hours. | Per jurisdiction | Legal |
| Parent/School Notification | Direct notification to affected parents and school admins with: what happened, what data was involved, what we are doing about it, what they should do | Within 72 hours of confirmation | Customer Comms |
| Remediation | Fix root cause, patch vulnerability, update security controls, deploy fix to production | <48 hours for critical severity | Engineering |
| Post-Incident Review | Written post-mortem, lessons learned, control improvements, publish transparency report if children's data was involved | Within 2 weeks | Leadership |

### Special Considerations for Children's Data

Children's data carries heightened regulatory and ethical obligations:

- If the breach involves data of children under 13, the COPPA notification to the FTC must be prioritized above all other regulatory filings.
- Encrypted content excerpts (Fernet-encrypted conversation captures) require assessment of whether the encryption keys were also compromised.
- API keys with the `bhapi_sk_` prefix must be immediately revoked and reissued if the key hashing salt or stored hashes were exposed.
- If Stripe billing data was exposed, notify Stripe's fraud team in addition to regulatory authorities.

### Notification Templates

#### Template A: Parent Email Notification

```
Subject: Important Security Notice from Bhapi

Dear [Parent Name],

We are writing to inform you of a security incident that may have
affected your family's data on the Bhapi platform.

WHAT HAPPENED
On [date], we discovered that [brief description of breach]. The
incident occurred between [start date] and [end date].

WHAT DATA WAS INVOLVED
The following data associated with your account may have been
affected: [list specific data types — e.g., email address, child's
display name, activity summaries].

[If children's data]: This includes data related to your child
[child's first name].

WHAT WE ARE DOING
- We have contained the incident and secured affected systems.
- We have notified the relevant regulatory authorities.
- We have [specific remediation actions taken].
- We are conducting a thorough investigation with the help of
  [external security firm, if applicable].

WHAT YOU SHOULD DO
- Change your Bhapi account password immediately.
- If you reuse this password on other services, change those as well.
- Monitor your child's accounts on other platforms for unusual activity.
- Review your child's recent AI activity in the Bhapi Safety dashboard.

If you have questions, contact us at security@bhapi.ai or call
[support phone number].

We take the safety and privacy of your family's data extremely
seriously, and we sincerely apologize for this incident.

[Engineering Lead Name]
Engineering Lead, Bhapi
```

#### Template B: School Admin Notification

```
Subject: Security Incident Notification — Bhapi Platform

Dear [School Admin Name],

We are notifying [School Name] of a security incident affecting the
Bhapi platform that may have impacted student and staff data
associated with your institution's account.

INCIDENT SUMMARY
- Date discovered: [date]
- Date contained: [date]
- Data potentially affected: [list data types]
- Number of students potentially affected: [count]
- Number of staff potentially affected: [count]

REGULATORY FILINGS
We have notified [list authorities: FTC, DPA, OAIC, etc.] as
required by applicable law. Reference number(s): [if available].

RECOMMENDED ACTIONS FOR YOUR SCHOOL
- Notify affected families per your school's data breach notification
  policy.
- Review student accounts in the Bhapi school admin dashboard for
  unusual activity.
- If your school uses Clever or ClassLink integration, verify that
  directory sync credentials have not been compromised (we have
  rotated credentials on our side).
- Contact your school district's data privacy officer.

We will provide a written incident report within [timeframe]. A
dedicated point of contact for your school is [name, email, phone].

[Engineering Lead Name]
Engineering Lead, Bhapi
```

#### Template C: Regulatory Notification (FTC / DPA / OAIC)

```
INCIDENT NOTIFICATION

Reporting Organization: Bhapi Inc.
Platform: bhapi.ai (children's digital safety platform)
Contact: [Legal contact name, email, phone]

1. DATE OF DISCOVERY: [date]
2. DATE OF CONTAINMENT: [date]
3. NATURE OF INCIDENT: [unauthorized access / data exfiltration /
   system compromise / other]
4. DATA CATEGORIES AFFECTED: [list: email, display name, age,
   activity data, AI conversation captures, etc.]
5. CHILDREN'S DATA INVOLVED: [Yes/No]
   - If yes: Number of children affected: [count]
   - Age range: [range]
   - Jurisdictions: [US/EU/AU/UK]
6. NUMBER OF DATA SUBJECTS AFFECTED: [count]
7. LIKELY CONSEQUENCES: [assessment of risk to affected individuals]
8. MEASURES TAKEN:
   - Containment: [actions]
   - Remediation: [actions]
   - Notification: [who has been notified and when]
9. DATA PROTECTION OFFICER CONTACT: [name, email]

[For FTC/COPPA]: This notification is made pursuant to the Children's
Online Privacy Protection Act. The affected platform collects
children's personal information with verifiable parental consent as
required by 16 CFR Part 312.

[For EU DPA]: This notification is made pursuant to Article 33 of the
General Data Protection Regulation (EU) 2016/679.

[For OAIC]: This notification is made pursuant to Part IIIC of the
Privacy Act 1988 (Notifiable Data Breaches scheme).
```

---

## 3. Category 2: Child Safety Incident

Child safety incidents require the fastest response times of any incident category. Every Bhapi employee is authorized to act on a child safety concern without waiting for management approval.

### Scenario 1: Self-Harm Disclosure Detected

A child discloses self-harm ideation or intent through an AI chat session, social post, or message on the Bhapi Social platform.

| Step | Action | Timeline | Owner |
|------|--------|----------|-------|
| 1 | Risk pipeline flags content with self-harm taxonomy category | Automated, <30 seconds | System |
| 2 | Alert parent immediately via all available channels: push notification, SMS (Twilio), and email (SendGrid) | <5 minutes | System (automated) |
| 3 | Display crisis helpline information in the child's app interface | <5 minutes | System (automated) |
| 4 | If no parent acknowledgment within 30 minutes, escalate to emergency contacts on file | 30 minutes after initial alert | System (automated) |
| 5 | If no response from any contact within 1 hour, escalate to on-call engineer for manual follow-up | 1 hour after initial alert | On-call engineer |
| 6 | Log all actions with timestamps for audit trail | Ongoing | System |

**Crisis helplines to display:**

| Region | Service | Number |
|--------|---------|--------|
| United States | Childhelp National Child Abuse Hotline | 1-800-422-4453 |
| United States | 988 Suicide & Crisis Lifeline | 988 |
| Australia | Kids Helpline | 1800 55 1800 |
| United Kingdom | Childline | 0800 1111 |
| EU (general) | European Emergency Number | 112 |
| Crisis Text Line (US) | Text HOME to | 741741 |

**Consent consideration:** Self-harm alerts bypass normal third-party consent gating. Under COPPA's "safety exception," alerts may be sent even if the parent has not consented to SendGrid/Twilio data processing. Document the safety exception invocation in the audit log.

### Scenario 2: Predator Contact Identified

An adult is identified attempting to contact or groom a child on the platform.

| Step | Action | Timeline | Owner |
|------|--------|----------|-------|
| 1 | Block suspect account immediately — prevent all messaging, posting, and contact requests | <15 minutes | System (automated) or T&S staff |
| 2 | Preserve all evidence: messages, profile data, activity log, IP addresses, device fingerprints. Store in encrypted, access-restricted evidence locker. | Immediately upon block | System |
| 3 | Alert the child's parent via push + SMS + email | <15 minutes | System (automated) |
| 4 | If US jurisdiction: submit report to NCMEC CyberTipline | <24 hours (target: <4 hours) | Engineering Lead or T&S |
| 5 | If imminent threat to a specific child: contact FBI ICAC task force via local field office | Immediate | Engineering Lead (any engineer if imminent) |
| 6 | If AU jurisdiction: report to eSafety Commissioner | Per eSafety timelines | T&S |
| 7 | Review social graph — check if the suspect has contacted other children on the platform | <4 hours | T&S + Engineering |
| 8 | Document incident for law enforcement referral package | Within 48 hours | Engineering Lead |

**Evidence preservation requirements:**
- Do NOT delete any data associated with the suspect account, even if requested by the suspect.
- Encrypted storage with access restricted to Engineering Lead and designated T&S staff.
- Retain for minimum 7 years or as required by law enforcement.
- Chain of custody documentation required for any evidence access.

### Scenario 3: CSAM Discovered

Child Sexual Abuse Material is detected on the platform, whether uploaded by a user, generated by AI, or linked externally.

| Step | Action | Timeline | Owner |
|------|--------|----------|-------|
| 1 | Block content and suspend the uploading account | Automated via PhotoDNA/perceptual hash pipeline | System |
| 2 | Preserve evidence in encrypted, access-restricted storage | Immediate | System |
| 3 | Submit CyberTipline report to NCMEC (API submission) | <30 minutes (automated target) | System / Engineering Lead |
| 4 | **DO NOT notify the suspect** — this could compromise a law enforcement investigation | N/A | All staff |
| 5 | Alert platform admin (Engineering Lead) | <30 minutes | System |
| 6 | Log for law enforcement with full metadata (timestamps, IP, device info, account history) | Immediate | System |
| 7 | Review whether the account contacted any children on the platform | <4 hours | T&S + Engineering |

**Critical rules:**
- Federal law (18 U.S.C. 2258A) requires electronic service providers to report CSAM to NCMEC. Failure to report is a federal offense.
- Do NOT view, copy, or redistribute CSAM except as strictly necessary for reporting. Minimize human exposure.
- Content moderation staff who encounter CSAM must be offered immediate psychological support (see Section 14.2 of the platform design spec for moderator wellbeing policies).
- AI-generated CSAM is treated identically to photographic CSAM for reporting and response purposes.

### Scenario 4: Imminent Physical Danger

A child's safety is at immediate physical risk (threats of violence, kidnapping, domestic violence disclosure).

| Step | Action | Timeline | Owner |
|------|--------|----------|-------|
| 1 | Contact local law enforcement (911 / emergency services) | IMMEDIATE — no internal approval required | Any employee |
| 2 | Alert the child's parent (unless the parent is the suspected threat) | IMMEDIATE | On-call engineer |
| 3 | Preserve all platform data as evidence | IMMEDIATE | System + Engineering |
| 4 | If the parent is the suspected threat: contact local child protective services and DO NOT alert the parent | IMMEDIATE | Engineering Lead |
| 5 | Notify Engineering Lead and leadership | As soon as the child's safety is addressed | On-call engineer |

**Any Bhapi employee who becomes aware of imminent physical danger to a child is authorized and expected to contact emergency services (911) without waiting for any approval.** This is not optional.

---

## 4. Category 3: Platform Abuse

### Scenario 1: Coordinated Harassment of a Child

Multiple accounts targeting a single child with bullying, threats, or harmful content.

| Step | Action | Timeline | Owner |
|------|--------|----------|-------|
| 1 | Remove all harassing content | <1 hour | T&S / Engineering |
| 2 | Suspend all participating accounts | <1 hour | T&S / Engineering |
| 3 | Alert the victim's parent via push + email | <1 hour | System |
| 4 | Review social graph for patterns — are the accounts connected (same IP, same device fingerprint, same registration time)? | <4 hours | T&S + Engineering |
| 5 | If accounts are connected: treat as a coordinated attack, flag for potential law enforcement referral | <24 hours | Engineering Lead |
| 6 | Review victim's recent activity for signs of distress or self-harm | <4 hours | T&S |
| 7 | Document incident with all evidence for potential law enforcement referral | Within 48 hours | T&S |
| 8 | If AU jurisdiction: report to eSafety Commissioner as cyberbullying | Per eSafety timelines | T&S |

### Scenario 2: Viral Harmful Content

Content that is harmful to children spreads rapidly across the platform.

| Step | Action | Timeline | Owner |
|------|--------|----------|-------|
| 1 | Content takedown — remove all instances of the content | <30 minutes | T&S / Engineering |
| 2 | Rate-limit sharing and reposting of the content (perceptual hash block) | <30 minutes | Engineering |
| 3 | Surge moderation queue staffing — pull additional reviewers | <1 hour | Engineering Lead |
| 4 | Identify all children who viewed the content | <2 hours | Engineering |
| 5 | Notify parents of affected children with age-appropriate description of what their child may have seen | <4 hours | Customer Comms |
| 6 | If content constitutes illegal material: escalate to Category 2 (CSAM) or law enforcement | Immediate | Engineering Lead |

### Scenario 3: Mass Account Creation (Bot/Spam/Grooming)

Suspicious pattern of account registrations suggesting bot activity, spam campaigns, or grooming infrastructure.

| Step | Action | Timeline | Owner |
|------|--------|----------|-------|
| 1 | Rate limit registration endpoint (reduce from normal limits) | <30 minutes | Engineering |
| 2 | Enable CAPTCHA on registration flow | <30 minutes | Engineering |
| 3 | Block offending IP ranges | <1 hour | Engineering |
| 4 | Review new accounts for grooming patterns (adult accounts sending contact requests to children) | <2 hours | T&S + Engineering |
| 5 | If grooming pattern detected: escalate to Category 2 (Predator Contact) | Immediate | Engineering Lead |
| 6 | Suspend all accounts matching the suspicious pattern | <4 hours | Engineering |
| 7 | Review device attestation signals (Play Integrity / App Attest) for automation indicators | <4 hours | Engineering |

---

## 5. Category 4: Service Outage

| SEV | Definition | Response | Restoration Target |
|-----|-----------|----------|-------------------|
| SEV-1 | Platform completely down — no user access | All hands on deck. Status page updated immediately. Leadership notified. | <1 hour to restore |
| SEV-2 | Moderation pipeline down — children posting unmoderated content | **DISABLE content creation for pre-publish tiers (ages 5-9, 10-12) IMMEDIATELY.** Safety over availability. Keep read-only access. Parent monitoring dashboard stays up. | <30 minutes to disable creation. <4 hours to restore moderation. |
| SEV-3 | Minor feature degraded (e.g., push notifications delayed, analytics slow) | Normal triage. Fix in next deploy. Affected users notified if impact is visible. | <24 hours |

### Key Principle: Fail Closed

If the moderation pipeline goes down, the system MUST fail closed. Unmoderated content from children under 13 is both a safety risk and a regulatory violation (COPPA, Online Safety Act).

**What "fail closed" means in practice:**
- Content creation endpoints for age tiers 5-9 and 10-12 return HTTP 503 with a child-friendly message ("We're taking a quick break! You can still read and browse.").
- Content creation for age tier 13-15 is rate-limited but not fully disabled (post-publish moderation is acceptable for teens).
- DM/messaging for all tiers is disabled until moderation is restored.
- The Bhapi Safety parent dashboard remains fully operational — parents can still view alerts, activity history, and risk scores.
- The risk pipeline (AI safety scoring, PII detection) degrades gracefully — keyword-only classification mode activates if the Google Cloud AI consent or API is unavailable.

### Outage Communication

| Audience | Channel | When |
|----------|---------|------|
| All users | Status page (status.bhapi.ai) | Immediately on SEV-1 or SEV-2 |
| Parents | Push notification | SEV-1: if outage exceeds 30 minutes. SEV-2: immediately (explain content creation is paused for safety). |
| School admins | Email | SEV-1 or SEV-2 within 1 hour |
| Children | In-app banner | SEV-1: "We'll be right back!" SEV-2: "You can read and browse, but posting is paused for a bit." |

---

## 6. Decision Authority Matrix

| Decision | Authority | Backup | Notes |
|----------|-----------|--------|-------|
| Take platform offline | Any senior engineer | Engineering Lead | No approval needed if active threat to children |
| Contact law enforcement | Engineering Lead | **Any engineer** (for imminent danger) | Imminent danger = no approval needed, act first |
| Notify parents of data breach | Engineering Lead + Legal | CEO | Must happen within 72 hours of confirmation |
| Suspend user account | Automated (CSAM/PhotoDNA) or any T&S staff | Engineering on-call | Automated suspensions are reviewed within 24 hours |
| Submit NCMEC CyberTipline report | Automated (PhotoDNA pipeline) | Manual submission by Engineering Lead | Federal reporting obligation — not discretionary |
| Regulatory notification (FTC, DPA, OAIC) | Legal | Engineering Lead | Timelines vary by jurisdiction (see Category 1) |
| Disable content creation (SEV-2) | Any engineer on-call | Automated circuit breaker | Safety measure — no approval required |
| Invoke COPPA safety exception for alerts | System (automated) | Engineering Lead | Bypasses third-party consent gating |

---

## 7. Contact Directory

### Law Enforcement and Reporting Agencies

| Entity | Contact | When to Contact |
|--------|---------|----------------|
| NCMEC CyberTipline | https://report.cybertip.org / API integration | CSAM detected on platform |
| FBI IC3 | https://www.ic3.gov | Cyber crimes involving children (US) |
| FBI ICAC Task Force | Local field office (https://www.icactaskforce.org) | Predator activity, online exploitation, imminent threat |
| eSafety Commissioner (AU) | https://www.esafety.gov.au/report | AU content takedown requests, cyberbullying reports |
| Local Law Enforcement | 911 (US) / 000 (AU) / 999 (UK) / 112 (EU) | Imminent physical danger to a child |

### Regulatory Authorities (Data Breach)

| Entity | Contact | Notification Deadline |
|--------|---------|----------------------|
| FTC (US — COPPA) | CRC-COPPA@ftc.gov | "As soon as possible" |
| ICO (UK — GDPR/AADC) | https://ico.org.uk/make-a-complaint/ | Within 72 hours |
| CNIL (France) | https://www.cnil.fr/en/notifying-cnil | Within 72 hours |
| BfDI (Germany) | https://www.bfdi.bund.de | Within 72 hours |
| AEPD (Spain) | https://www.aepd.es | Within 72 hours |
| OAIC (Australia) | https://www.oaic.gov.au/privacy/notifiable-data-breaches | "As soon as practicable" |
| Ohio Attorney General | https://www.ohioattorneygeneral.gov/databreach | Per Ohio breach notification statute |

### Crisis Helplines (Displayed to Children)

| Region | Service | Number / Contact |
|--------|---------|-----------------|
| United States | Childhelp National Child Abuse Hotline | 1-800-422-4453 |
| United States | 988 Suicide & Crisis Lifeline | 988 |
| United States | Crisis Text Line | Text HOME to 741741 |
| Australia | Kids Helpline | 1800 55 1800 |
| United Kingdom | Childline | 0800 1111 |
| Europe | European Emergency Number | 112 |
| Brazil | CVV (Centro de Valorização da Vida) | 188 |

### Internal Contacts

| Role | Responsibility | Escalation Path |
|------|---------------|-----------------|
| On-call Engineer | First responder for all incidents | Engineering Lead |
| Engineering Lead | Incident commander, decision authority | CEO |
| Legal | Regulatory notifications, law enforcement liaison | External counsel |
| Customer Comms | Parent and school notifications | Engineering Lead |
| CEO | Final escalation, public statements | Board |

---

## 8. Post-Incident Review Template

Every SEV-1 and SEV-2 incident, every data breach, and every child safety incident requires a written post-mortem. SEV-3 incidents require a post-mortem if they recur within 30 days.

```
# Incident Post-Mortem: [INCIDENT-YYYY-MM-DD-NNN]

**Date:** [date of incident]
**Author:** [post-mortem author]
**Severity:** SEV-1 / SEV-2 / SEV-3
**Category:** Data Breach / Child Safety / Platform Abuse / Service Outage
**Duration:** [time from detection to resolution]
**Impact:** [number of users affected, data exposed, content involved, etc.]
**Regulatory Notifications Filed:** [Yes/No — list if yes]

## Timeline
- HH:MM UTC — [First indication of incident]
- HH:MM UTC — [Detection confirmed]
- HH:MM UTC — [Containment actions taken]
- HH:MM UTC — [Key decisions made]
- HH:MM UTC — [Resolution achieved]
- HH:MM UTC — [Post-incident monitoring confirmed stable]

## Root Cause
[Detailed technical explanation of what caused the incident]

## What Went Well
- [Effective response actions]
- [Systems that worked as designed]
- [Good decisions made under pressure]

## What Went Wrong
- [Gaps in detection]
- [Delays in response]
- [Systems that failed or were inadequate]
- [Communication breakdowns]

## Action Items
| # | Action | Owner | Due Date | Status |
|---|--------|-------|----------|--------|
| 1 | [Specific remediation action] | [Name] | [Date] | Open |
| 2 | [Process improvement] | [Name] | [Date] | Open |
| 3 | [Monitoring improvement] | [Name] | [Date] | Open |

## Lessons Learned
[Key takeaways that should inform future incident response]

## Appendix
- [Links to relevant logs, dashboards, communications]
- [Regulatory filing reference numbers]
```

---

## 9. Testing the Plan

### Quarterly Tabletop Exercises

Every quarter, the engineering team conducts a tabletop exercise simulating one of the four incident categories. The exercise rotates through categories so that each is tested at least once per year.

| Quarter | Exercise | Scenario |
|---------|----------|----------|
| Q1 | Data Breach | Simulated database credential exposure via misconfigured backup |
| Q2 | Child Safety | Simulated self-harm disclosure with escalation chain |
| Q3 | Platform Abuse | Simulated coordinated harassment campaign against a child |
| Q4 | Service Outage | Simulated moderation pipeline failure (SEV-2) — verify fail-closed behavior |

**Tabletop format:**
1. Facilitator presents the scenario (10 minutes)
2. Team walks through the response using this plan (30 minutes)
3. Identify gaps, ambiguities, or outdated information (15 minutes)
4. Update this document with findings (action item, due within 1 week)

### Annual Full Drill

Once per year, conduct a full drill simulating a data breach with the complete notification workflow:
- Trigger detection alerts (synthetic)
- Execute containment procedures (on staging environment)
- Draft regulatory notifications (using templates in this document)
- Draft parent notifications (using templates in this document)
- Time the entire process and compare against the targets in this plan
- Document results in a drill report

### New Employee Onboarding

Every new employee (engineering, T&S, customer support) must:
- Read this incident response plan within their first week
- Acknowledge in writing that they understand the "any employee can call 911" policy for imminent child danger
- Participate in a brief (30-minute) walkthrough of the plan with their manager
- Participate in their first tabletop exercise within their first quarter

---

## 10. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | March 19, 2026 | Engineering Lead | Initial version covering four incident categories |

---

*This document is reviewed quarterly and updated after every incident post-mortem. The next scheduled review is June 2026.*
