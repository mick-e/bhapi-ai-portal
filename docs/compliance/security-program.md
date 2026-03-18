# Written Information Security Program (WISP)

## Bhapi AI Portal — bhapi.ai

**Document Classification:** Confidential
**Version:** 1.0
**Effective Date:** March 17, 2026
**Last Reviewed:** March 17, 2026
**Next Scheduled Review:** September 17, 2026
**Approved By:** [Security Coordinator Name], Information Security Coordinator

This Written Information Security Program ("WISP" or "Program") is established pursuant to the Children's Online Privacy Protection Act (COPPA), 15 U.S.C. 6501-6506, and the FTC's COPPA Rule, 16 C.F.R. Part 312, including the requirements of 16 C.F.R. 312.8 regarding the confidentiality, security, and integrity of personal information collected from children.

---

## Table of Contents

1. [Program Overview and Scope](#1-program-overview-and-scope)
2. [Designated Security Coordinator](#2-designated-security-coordinator)
3. [Risk Identification and Assessment](#3-risk-identification-and-assessment)
4. [Safeguards](#4-safeguards)
5. [Service Provider Oversight](#5-service-provider-oversight)
6. [Data Collection and Retention](#6-data-collection-and-retention)
7. [Parental Rights and Controls](#7-parental-rights-and-controls)
8. [Incident Response](#8-incident-response)
9. [Employee Training](#9-employee-training)
10. [Program Evaluation and Updates](#10-program-evaluation-and-updates)
11. [Appendices](#11-appendices)

---

## 1. Program Overview and Scope

### 1.1 Purpose

This Program establishes and documents the administrative, technical, and physical safeguards that Bhapi AI Portal ("Bhapi," "we," "us," or "the Company") maintains to protect the confidentiality, security, and integrity of personal information collected from children under 13 years of age, in compliance with the COPPA Rule (16 C.F.R. Part 312).

### 1.2 Scope

This Program applies to:

- All personal information collected from children under 13, including but not limited to names, email addresses, AI conversation data, usage patterns, and behavioral analytics.
- All personal information collected from parents and guardians in connection with their children's use of the platform.
- All systems, applications, networks, databases, and infrastructure that store, process, or transmit such information.
- All employees, contractors, and agents who have access to children's personal information.
- All third-party service providers who receive, process, or store children's personal information on our behalf.

### 1.3 Platform Description

Bhapi AI Portal (bhapi.ai) is a family AI safety monitoring platform that enables parents, schools, and clubs to monitor and govern children's interactions with artificial intelligence systems. The platform provides:

- AI conversation capture and monitoring across 10 AI platforms (ChatGPT, Gemini, Copilot, Claude, Grok, Character.AI, Replika, Pi, Perplexity, Poe)
- Risk assessment and safety scoring (14 taxonomy categories, 0-100 safety scores)
- Deepfake detection and emotional dependency monitoring
- Content blocking with parental approval workflows
- Academic integrity monitoring
- Time budgets, bedtime mode, and usage controls
- Weekly safety reports and real-time alerts
- Browser extension (Chrome, Firefox, Safari) for data capture

### 1.4 Legal Basis

This Program is maintained to satisfy the requirements of:

- Children's Online Privacy Protection Act (COPPA), 15 U.S.C. 6501-6506
- FTC COPPA Rule, 16 C.F.R. Part 312, specifically Section 312.8
- EU General Data Protection Regulation (GDPR), where applicable
- EU AI Act transparency and human review requirements
- State data breach notification laws
- Industry best practices for child data protection

### 1.5 Guiding Principles

- **Data Minimization:** Collect only information reasonably necessary to provide the service.
- **Purpose Limitation:** Use children's data solely for safety monitoring purposes authorized by verified parents.
- **Retention Limitation:** Delete children's data when no longer necessary or upon parental request.
- **Security by Design:** Incorporate security controls into every phase of system development and operation.
- **Transparency:** Clearly communicate data practices to parents and guardians.
- **Child Safety First:** All design and operational decisions prioritize child safety.

---

## 2. Designated Security Coordinator

### 2.1 Appointment

The Company designates an Information Security Coordinator ("Security Coordinator") who is responsible for the development, implementation, maintenance, and enforcement of this Program.

**Security Coordinator:**
- **Title:** Information Security Coordinator
- **Reports To:** Chief Executive Officer
- **Contact:** security@bhapi.ai

### 2.2 Responsibilities

The Security Coordinator is responsible for:

1. Overseeing the day-to-day administration of this Program.
2. Conducting periodic risk assessments as described in Section 3.
3. Evaluating the effectiveness of safeguards described in Section 4.
4. Managing relationships with third-party service providers regarding data security (Section 5).
5. Coordinating incident response activities (Section 8).
6. Developing and administering security awareness training (Section 9).
7. Conducting the semi-annual Program review (Section 10).
8. Serving as the primary point of contact for regulatory inquiries related to data security.
9. Maintaining documentation of all Program activities, assessments, and decisions.
10. Reporting security matters to executive leadership on at least a quarterly basis.

### 2.3 Authority

The Security Coordinator has the authority to:

- Halt any processing of children's personal information that poses an imminent security risk.
- Require remediation of identified security vulnerabilities within defined timelines.
- Engage external security consultants and auditors as needed.
- Escalate unresolved security issues directly to executive leadership.

---

## 3. Risk Identification and Assessment

### 3.1 Risk Assessment Schedule

Bhapi conducts comprehensive risk assessments:

- **Annual:** Full risk assessment covering all areas of this Program.
- **Semi-Annual:** Focused assessments on high-risk areas including children's data processing.
- **Event-Driven:** Triggered by material changes to systems, new product features, security incidents, or changes in the threat landscape.

### 3.2 Risk Assessment Methodology

Each risk assessment evaluates:

1. **Internal Risks:**
   - Employee access to children's personal information
   - Insider threat potential
   - System misconfiguration
   - Software vulnerabilities in application code and dependencies
   - Data handling errors in AI conversation capture and analysis

2. **External Risks:**
   - Unauthorized access attempts and cyberattacks
   - Phishing and social engineering targeting employees
   - Supply chain and third-party service provider risks
   - AI model poisoning or adversarial attacks against safety scoring
   - Browser extension security (Manifest V3 attack surface)
   - Regulatory and compliance risks

3. **Data Lifecycle Risks:**
   - Collection: Ensuring verifiable parental consent before collecting children's data
   - Processing: AI content moderation and risk scoring accuracy
   - Storage: Database security, encryption effectiveness, backup integrity
   - Transmission: API security, webhook integrity, browser extension communication
   - Retention: Compliance with retention schedules, deletion verification
   - Disposal: Secure data destruction procedures

### 3.3 Risk Scoring

Risks are scored using a likelihood-impact matrix:

| Likelihood / Impact | Low (1) | Medium (2) | High (3) | Critical (4) |
|---------------------|---------|------------|----------|---------------|
| **Rare (1)**        | 1       | 2          | 3        | 4             |
| **Unlikely (2)**    | 2       | 4          | 6        | 8             |
| **Possible (3)**    | 3       | 6          | 9        | 12            |
| **Likely (4)**      | 4       | 8          | 12       | 16            |

- Scores 1-4: Accept with monitoring.
- Scores 5-8: Mitigate with controls within 90 days.
- Scores 9-12: Mitigate with controls within 30 days.
- Scores 13-16: Immediate remediation required; escalate to executive leadership.

### 3.4 Risk Register

The Security Coordinator maintains a risk register documenting:

- Identified risks and their scores
- Assigned risk owners
- Implemented and planned mitigations
- Residual risk assessments
- Review dates and status updates

### 3.5 Data Protection Impact Assessments

A Data Protection Impact Assessment (DPIA) is conducted before implementing any new feature, system, or third-party integration that involves children's personal information. See the separate DPIA document (`docs/compliance/dpia.md`) for methodology and completed assessments.

---

## 4. Safeguards

### 4.1 Administrative Safeguards

#### 4.1.1 Access Control Policy

- **Principle of Least Privilege:** All personnel are granted the minimum level of access necessary to perform their job functions.
- **Role-Based Access Control (RBAC):** The platform enforces RBAC with 14+ defined permissions across all 190+ API routes. Administrative endpoints enforce `require_permission(Permission.ADMIN_USERS)`.
- **Access Reviews:** Quarterly reviews of all user access privileges, with immediate revocation upon role change or termination.
- **Multi-Tenant Isolation:** Strict tenant isolation ensures families, schools, and clubs can only access their own data. Family member cap of 5 per group enforced at the application level.

#### 4.1.2 Background Checks

- All employees and contractors with access to children's personal information undergo background checks prior to access being granted.
- Background checks are repeated biennially for personnel in security-sensitive roles.

#### 4.1.3 Acceptable Use Policy

- All personnel sign an Acceptable Use Policy acknowledging restrictions on accessing, copying, or disclosing children's personal information.
- Personal devices may not store children's personal information.
- Production database access is restricted to authorized operations personnel.

#### 4.1.4 Change Management

- All code changes undergo peer review before deployment.
- Changes affecting children's data processing require Security Coordinator approval.
- Database migrations (59 total as of this writing, managed via Alembic) follow a documented review and approval process.
- Automated CI/CD (GitHub Actions) enforces test passage before deployment.

#### 4.1.5 Vendor Management

- Third-party service providers are evaluated and managed per Section 5.
- COPPA-specific data processing agreements are required before any vendor receives children's data.

### 4.2 Technical Safeguards

#### 4.2.1 Encryption

**Data at Rest:**
- All children's personal information stored in PostgreSQL is encrypted at rest using Fernet symmetric encryption with AWS KMS key management.
- AI conversation content and risk assessment details are encrypted at the application layer before database storage.
- Database backups are encrypted using AES-256.
- Encryption keys are rotated on a defined schedule and managed through KMS with audit logging.

**Data in Transit:**
- All client-server communications are encrypted using TLS 1.2 or higher (HTTPS enforced).
- API communications between backend services and third-party providers use TLS.
- Browser extension communications with the backend use encrypted WebSocket and HTTPS connections.
- Internal service-to-service communications use encrypted channels.

#### 4.2.2 Authentication and Authorization

- **Password Security:** User passwords are hashed using bcrypt with appropriate work factors. Passwords are never stored in plaintext. The User model stores `password_hash` (not plaintext).
- **Session Management:** JWT (JSON Web Token) authentication with configurable expiration. Tokens are validated on every request.
- **API Security:** API key authentication with scoped permissions (PBKDF2-SHA256 hashing for key storage).
- **Webhook Integrity:** HMAC-SHA256 validation on all inbound webhooks (GitHub, Stripe, and other integrations).
- **SSO Integration:** Google Workspace and Microsoft Entra SSO support with SAML/OIDC for school deployments.
- **Age Verification:** Yoti integration for parental age verification during consent flows.

#### 4.2.3 Network Security

- **Rate Limiting:** Redis-backed rate limiting with in-memory fallback. Default: 100 requests/minute. Registration: 5/minute. Login: 10/minute. Custom rate limits on sensitive endpoints.
- **CORS Policy:** Cross-Origin Resource Sharing locked to configured allowed origins only.
- **Input Validation:** All API inputs validated through Pydantic schemas with strict type enforcement.
- **Path Traversal Protection:** Server-side path traversal protections on SPA catch-all routes and file serving endpoints.
- **DDoS Protection:** Render hosting platform provides infrastructure-level DDoS mitigation.

#### 4.2.4 Application Security

- **Framework:** Python/FastAPI backend with async request handling, providing built-in protections against common web vulnerabilities.
- **Database:** SQLAlchemy ORM with parameterized queries, preventing SQL injection. PostgreSQL for production with SQLite for testing.
- **Dependency Management:** Automated dependency scanning via Dependabot. Known vulnerabilities are tracked and remediated per severity.
- **Browser Extension:** Manifest V3 architecture with minimal permissions, content script isolation, and encrypted communication with the backend.
- **Correlation IDs:** Unique correlation IDs are assigned to every request for end-to-end traceability.

#### 4.2.5 Monitoring and Logging

- **Structured Audit Logging:** JSON-structured logs capturing method, path, status code, duration, user context, and correlation IDs. All access to children's data is logged.
- **Prometheus Metrics:** 8+ custom application metrics for monitoring request rates, error rates, and performance.
- **Alerting:** Real-time alerts for anomalous access patterns, failed authentication attempts, and system errors.
- **Log Retention:** Security logs retained for a minimum of 12 months. Logs containing children's personal information are subject to the same retention and deletion policies as the underlying data.
- **No Child Data in Logs:** Application logging is configured to exclude children's personal information from log entries. Sensitive fields are masked or omitted.

#### 4.2.6 Vulnerability Management

- Automated dependency vulnerability scanning (Dependabot, continuous).
- Application-level security testing integrated into CI pipeline.
- Penetration testing conducted annually by qualified third-party assessors.
- Critical vulnerabilities are patched within 24 hours; high within 7 days; medium within 30 days; low within 90 days.

#### 4.2.7 Backup and Recovery

- Automated database backups with point-in-time recovery capability.
- Backups are encrypted and stored in a geographically separate location.
- Backup restoration tested quarterly.
- Recovery Time Objective (RTO): 4 hours. Recovery Point Objective (RPO): 1 hour.

### 4.3 Physical Safeguards

#### 4.3.1 Hosting Infrastructure

Bhapi AI Portal is hosted on Render, a SOC 2 Type II certified cloud platform. Physical security controls at the data center level include:

- 24/7 physical security monitoring
- Biometric and multi-factor access controls
- Environmental controls (fire suppression, climate control, redundant power)
- Video surveillance with retention

#### 4.3.2 Employee Workstations

- Full-disk encryption required on all devices used for development or operations.
- Automatic screen lock after 5 minutes of inactivity.
- Remote wipe capability for lost or stolen devices.
- Production access restricted to company-managed devices.

#### 4.3.3 Physical Document Controls

- Paper documents containing children's personal information are prohibited.
- All data processing occurs electronically with the controls described in this Program.

---

## 5. Service Provider Oversight

### 5.1 COPPA Compliance Requirements

Under 16 C.F.R. 312.8, operators must take reasonable steps to ensure that service providers maintain the confidentiality, security, and integrity of children's personal information. Bhapi requires the following from all service providers who process children's data:

1. Written data processing agreement with COPPA-specific provisions.
2. Commitment to use children's data solely for the purpose of providing the contracted service.
3. Prohibition on disclosing children's data to third parties without our authorization.
4. Commitment to maintain reasonable security measures appropriate to the sensitivity of the data.
5. Data deletion upon contract termination or upon our request.
6. Notification of security incidents within 24 hours of discovery.
7. Annual security attestation or SOC 2 report.

### 5.2 Current Service Providers

| Provider | Service | Data Shared | COPPA DPA | SOC 2 | Last Review |
|----------|---------|-------------|-----------|-------|-------------|
| **Stripe** | Payment processing | Parent billing info only. No children's data shared with Stripe. | N/A (no child data) | Yes, Type II | [Date] |
| **SendGrid** | Transactional email | Parent email addresses for alerts and reports. No children's email addresses. | Yes | Yes, Type II | [Date] |
| **Twilio** | SMS notifications | Parent phone numbers for alerts. No children's phone numbers. | Yes | Yes, Type II | [Date] |
| **Google Cloud AI** | Content moderation | AI conversation excerpts (de-identified where feasible) for risk analysis. | Yes | Yes, Type II | [Date] |
| **Hive / Sensity** | Deepfake detection | Image/media content submitted for deepfake analysis. | Yes | Under review | [Date] |
| **Yoti** | Age verification | Parent identity verification data. No children's data shared with Yoti. | Yes | Yes, Type I | [Date] |
| **Render** | Application hosting | All application data resides on Render infrastructure. | Yes | Yes, Type II | [Date] |

### 5.3 Provider Assessment Process

Before engaging a new service provider that will process children's data:

1. **Security Questionnaire:** Provider completes a detailed security assessment questionnaire.
2. **Contract Review:** Legal and Security Coordinator review the DPA and COPPA-specific terms.
3. **SOC 2 Review:** If available, the provider's SOC 2 report is reviewed for relevant controls.
4. **Risk Assessment:** A risk assessment is conducted and documented, including a DPIA if warranted.
5. **Approval:** Security Coordinator provides written approval before data sharing begins.

### 5.4 Ongoing Monitoring

- Annual review of each provider's security posture, SOC 2 reports, and contractual compliance.
- Providers must notify Bhapi of any material changes to their security controls.
- Providers must notify Bhapi of any security incident affecting our data within 24 hours.
- Right to audit clauses are included in all DPAs.

---

## 6. Data Collection and Retention

### 6.1 Categories of Children's Data Collected

Bhapi collects the following categories of personal information from or about children under 13, with verified parental consent:

| Category | Examples | Legal Basis |
|----------|----------|-------------|
| **Account Information** | Display name, age range, profile settings | Parental consent (COPPA) |
| **AI Conversation Data** | Content of AI interactions captured by the browser extension | Parental consent (COPPA) |
| **Usage Data** | Timestamps, session duration, AI platform used, interaction frequency | Parental consent (COPPA) |
| **Risk Assessment Data** | Safety scores, risk category classifications, flagged content | Parental consent (COPPA); derived from conversation data |
| **Device Information** | Browser type, extension version | Parental consent (COPPA); necessary for service delivery |
| **Behavioral Analytics** | Emotional dependency indicators, time-of-day patterns | Parental consent (COPPA); derived from usage data |

### 6.2 Data NOT Collected from Children

- Email addresses of children under 13 (the `.test` TLD and child email addresses are rejected at the application layer)
- Precise geolocation
- Photos, videos, or audio recordings (except media analyzed for deepfake detection, which is not stored after analysis)
- Social Security numbers or government identifiers
- Financial or payment information

### 6.3 Verifiable Parental Consent

Before collecting any personal information from a child under 13:

1. The parent or guardian must create an account and verify their identity through Yoti age verification.
2. The parent must affirmatively consent to the specific data collection practices described in our privacy policy.
3. Consent is obtained through one of the FTC-approved methods (e.g., signed consent form, credit card verification via Stripe, government ID verification via Yoti).
4. Consent records are stored with timestamps, method used, and scope of consent granted.
5. Parents may modify or revoke consent at any time through the platform dashboard or by contacting support.

### 6.4 Retention Schedule

| Data Category | Retention Period | Deletion Method |
|---------------|-----------------|-----------------|
| AI Conversation Data | 90 days from capture, or until parental deletion request | Cryptographic erasure + database deletion |
| Risk Assessment Scores | Duration of active account + 30 days | Database deletion |
| Usage Analytics | 12 months rolling | Automated purge |
| Account Information | Duration of active account + 30 days post-deletion request | Database deletion |
| Audit Logs (de-identified) | 12 months | Automated purge |
| Parental Consent Records | 3 years after consent revocation or account closure | Secure archive then deletion |

### 6.5 Data Deletion Procedures

- **Parental Request:** Deletion completed within 48 hours of verified parental request.
- **Account Closure:** All children's data is deleted within 30 days of account closure.
- **Automated Retention:** Scheduled jobs enforce retention periods, running daily.
- **Verification:** Deletion is verified through database queries and logged in the audit trail.
- **Backup Handling:** Deleted data is purged from backups within the backup rotation cycle (maximum 30 days).

---

## 7. Parental Rights and Controls

### 7.1 Right to Review

Parents have the right to review the personal information collected from their child. The platform provides:

- **Dashboard Access:** Real-time view of captured AI conversations, risk scores, and usage data through the family dashboard.
- **Data Export:** Parents can export all of their child's data in a machine-readable format (JSON/CSV) from the dashboard.
- **Direct Request:** Parents may request a copy of their child's data by contacting privacy@bhapi.ai, fulfilled within 48 hours.

### 7.2 Right to Delete

Parents have the right to request deletion of their child's personal information:

- **Self-Service:** Delete individual conversations, time periods, or the full account via the dashboard.
- **Written Request:** Submit deletion requests to privacy@bhapi.ai, processed within 48 hours.
- **Consequences:** Parents are informed that deletion of the account will result in loss of monitoring capabilities.

### 7.3 Right to Refuse Further Collection

Parents may revoke consent and halt further data collection at any time:

- **Extension Removal:** Removing the browser extension immediately stops data capture.
- **Account Suspension:** Parents may pause monitoring without deleting historical data.
- **Consent Revocation:** Formal consent revocation processed within 24 hours.

### 7.4 Parental Controls Available

The platform provides the following parent-managed controls:

- **Content Blocking:** Approve or block specific AI platforms and content categories, with parent approval workflows.
- **Time Budgets:** Set daily and weekly time limits for AI platform usage.
- **Bedtime Mode:** Configure time-of-day restrictions on AI platform access.
- **Alert Configuration:** Customize risk thresholds and notification preferences (email, SMS, push).
- **Panic Button:** Children can trigger a panic button that immediately alerts the parent.
- **Family Agreements:** Digital family AI usage agreements that children acknowledge.
- **Sibling Privacy:** Separate privacy boundaries between siblings in the same family.
- **Emergency Contacts:** Configure emergency contacts for critical safety alerts.

### 7.5 Authentication of Parental Identity

Before fulfilling requests to review, delete, or manage a child's data:

- Identity is verified through the parent's authenticated session (JWT token).
- For requests received by email, identity is verified through the account's verified email address and a confirmation step.
- For sensitive operations (deletion, consent revocation), re-authentication is required.

---

## 8. Incident Response

### 8.1 Incident Response Team

| Role | Responsibility |
|------|---------------|
| **Security Coordinator** (Lead) | Incident commander; coordinates response activities |
| **Engineering Lead** | Technical investigation and remediation |
| **Legal Counsel** | Regulatory notification requirements, legal exposure assessment |
| **Communications Lead** | Parent notification, public communications |
| **Executive Sponsor** | Resource allocation, strategic decisions |

### 8.2 Incident Classification

| Severity | Description | Response Time |
|----------|-------------|---------------|
| **Critical (P1)** | Confirmed unauthorized access to children's personal information; active data exfiltration | Immediate (within 1 hour) |
| **High (P2)** | Potential unauthorized access; vulnerability actively being exploited; service outage affecting safety monitoring | Within 4 hours |
| **Medium (P3)** | Suspected vulnerability; unauthorized access attempt blocked; non-critical service degradation | Within 24 hours |
| **Low (P4)** | Minor policy violation; informational security event | Within 72 hours |

### 8.3 Incident Response Phases

#### Phase 1: Detection and Reporting
- Security events detected through monitoring systems, audit logs, employee reports, or external notifications.
- All suspected incidents reported immediately to the Security Coordinator at security@bhapi.ai.
- Incident logged in the incident tracking system with timestamp, reporter, and initial classification.

#### Phase 2: Containment
- Immediate containment actions to stop ongoing unauthorized access or data loss.
- For P1/P2 incidents, the Security Coordinator may order immediate system isolation.
- Preserve forensic evidence (logs, database snapshots, system state).
- Activate the Incident Response Team.

#### Phase 3: Investigation
- Determine the scope of the incident: what data was affected, how many children impacted, root cause.
- Document the timeline of events.
- Identify the attack vector and any exploited vulnerabilities.
- Assess whether children's personal information was actually accessed, acquired, or disclosed.

#### Phase 4: Eradication and Recovery
- Remove the threat actor's access and remediate the exploited vulnerability.
- Restore systems from clean backups if necessary.
- Verify system integrity before restoring service.
- Implement additional controls to prevent recurrence.

#### Phase 5: Notification
- **FTC Notification:** If the incident involves children's personal information, notify the FTC as required.
- **Parent Notification:** Notify affected parents without unreasonable delay, and no later than required by applicable state breach notification laws (typically 30-60 days). Notification includes: description of the incident, types of data involved, steps taken, recommended protective actions, and contact information.
- **State Regulators:** Notify state attorneys general as required by applicable state breach notification laws.
- **Service Providers:** Notify affected third-party service providers.
- **Law Enforcement:** Notify law enforcement if criminal activity is suspected, in coordination with legal counsel.

#### Phase 6: Post-Incident Review
- Conduct a post-incident review within 14 days of incident closure.
- Document lessons learned and update this Program as needed.
- Update risk assessments to reflect newly identified risks.
- Report findings to executive leadership.

### 8.4 Incident Documentation

All incidents are documented with:

- Unique incident identifier
- Date and time of detection, containment, and resolution
- Classification and severity
- Description of the incident and root cause
- Data and individuals affected
- Containment and remediation actions taken
- Notifications made (regulators, parents, law enforcement)
- Lessons learned and Program improvements

### 8.5 Contact Information

- **Internal:** security@bhapi.ai
- **FTC Bureau of Consumer Protection:** CRC-COPPA@ftc.gov
- **FBI Internet Crime Complaint Center:** ic3.gov

---

## 9. Employee Training

### 9.1 Training Program

All employees and contractors receive security and privacy training covering:

#### 9.1.1 Initial Training (Within 30 Days of Hire)

- Overview of COPPA requirements and how they apply to Bhapi's operations.
- This Written Information Security Program and the employee's role within it.
- Data classification and handling procedures for children's personal information.
- Acceptable Use Policy and consequences of violations.
- Incident reporting procedures.
- Phishing awareness and social engineering defense.
- Secure development practices (for engineering staff).

#### 9.1.2 Annual Refresher Training

- Updates to COPPA regulations and FTC enforcement actions.
- Review of incidents and lessons learned from the prior year.
- Updated threat landscape and new attack vectors.
- Changes to this Program or related policies.
- Phishing simulation results and targeted training.

#### 9.1.3 Role-Specific Training

| Role | Additional Training Topics |
|------|---------------------------|
| **Engineering** | Secure coding practices, OWASP Top 10, dependency management, database security, encryption implementation, code review for privacy |
| **Operations** | Production access controls, log handling, backup procedures, incident response procedures |
| **Customer Support** | Parental identity verification, data access request handling, consent management |
| **Management** | Regulatory obligations, risk assessment participation, vendor oversight responsibilities |

### 9.2 Training Records

- All training completion is documented with employee name, training topic, date, and method.
- Training records are retained for the duration of employment plus 3 years.
- The Security Coordinator reviews training completion rates quarterly and follows up on overdue training.

### 9.3 Security Awareness

Ongoing security awareness activities include:

- Monthly security tips and reminders distributed to all staff.
- Quarterly phishing simulation exercises.
- Prompt notification of emerging threats relevant to our technology stack (Python/FastAPI, PostgreSQL, browser extensions).
- Recognition of employees who identify and report security issues.

---

## 10. Program Evaluation and Updates

### 10.1 Review Schedule

| Review Type | Frequency | Conducted By |
|-------------|-----------|-------------|
| **Comprehensive Program Review** | Annually | Security Coordinator + External Assessor |
| **Focused Risk Assessment** | Semi-annually | Security Coordinator |
| **Technical Controls Assessment** | Quarterly | Engineering Lead + Security Coordinator |
| **Policy and Procedure Review** | Annually | Security Coordinator + Legal Counsel |
| **Third-Party Provider Review** | Annually per provider | Security Coordinator |
| **Incident Response Plan Test** | Annually (tabletop exercise) | Incident Response Team |

### 10.2 Triggers for Unscheduled Review

This Program will be reviewed and updated outside the regular schedule upon:

- A security incident involving children's personal information.
- Significant changes to the platform's data collection or processing practices.
- New FTC guidance, COPPA rule amendments, or enforcement actions relevant to our operations.
- Addition of new third-party service providers processing children's data.
- Material changes to the technology stack or infrastructure.
- Acquisition, merger, or significant organizational changes.

### 10.3 Review Process

Each review includes:

1. Assessment of current threats and vulnerabilities.
2. Evaluation of the effectiveness of existing safeguards.
3. Review of incident history and trends.
4. Assessment of third-party provider compliance.
5. Review of employee training effectiveness.
6. Gap analysis against COPPA requirements and industry best practices.
7. Documented findings and remediation plans with assigned owners and deadlines.

### 10.4 Continuous Improvement

- Findings from each review are tracked in the risk register with assigned remediation owners and deadlines.
- The Security Coordinator reports review findings and remediation progress to executive leadership.
- This Program document is versioned, and all changes are tracked in the document revision history.

### 10.5 SOC 2 Readiness

Bhapi maintains controls aligned with SOC 2 Type II Trust Service Criteria (Security, Availability, Processing Integrity, Confidentiality, and Privacy). The following SOC 2 controls are implemented:

- **CC6.1:** Logical access controls (RBAC, JWT, API key scoping)
- **CC6.2:** Authentication mechanisms (bcrypt, HMAC, SSO)
- **CC6.3:** Authorized access enforcement (middleware-level permission checks on all routes)
- **CC6.6:** System boundaries and network security (CORS, rate limiting, TLS)
- **CC7.1:** Monitoring and detection (structured logging, Prometheus metrics)
- **CC7.2:** Incident response procedures (Section 8)
- **CC7.3:** Incident recovery (backup and recovery procedures)
- **CC8.1:** Change management (CI/CD, code review, migration management)

---

## 11. Appendices

### Appendix A: Document Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | March 17, 2026 | Security Coordinator | Initial Program creation |

### Appendix B: Related Documents

| Document | Location | Description |
|----------|----------|-------------|
| Data Protection Impact Assessment | `docs/compliance/dpia.md` | DPIA for children's data processing |
| Privacy Policy | bhapi.ai/privacy | Public-facing privacy policy |
| Terms of Service | bhapi.ai/terms | Platform terms of service |
| COPPA Privacy Policy (Children) | bhapi.ai/coppa | COPPA-specific privacy notice |
| Incident Response Plan | Internal | Detailed incident response procedures |
| Vendor Security Assessment Template | Internal | Questionnaire for third-party providers |
| Employee Acceptable Use Policy | Internal | Acceptable use policy for all personnel |

### Appendix C: Technical Architecture Summary

| Component | Technology | Security Controls |
|-----------|-----------|-------------------|
| Backend API | Python 3.x / FastAPI | Input validation (Pydantic), RBAC middleware, correlation IDs, rate limiting |
| Database | PostgreSQL (prod) / SQLAlchemy ORM | Parameterized queries, Fernet/KMS encryption at rest, Alembic migrations |
| Authentication | JWT + bcrypt + PBKDF2-SHA256 | Token expiration, secure password hashing, API key scoping |
| Frontend Portal | Next.js (App Router) + React Query + Tailwind | CSP headers, WCAG 2.1 AA, i18n (6 languages) |
| Browser Extension | Manifest V3 (Chrome, Firefox, Safari) | Minimal permissions, content script isolation, encrypted backend communication |
| Caching | Redis | Rate limiting, session management, in-memory fallback |
| Webhooks | HMAC-SHA256 | Payload integrity validation on all inbound webhooks |
| Hosting | Render | SOC 2 Type II, TLS termination, DDoS protection |
| CI/CD | GitHub Actions | Automated testing (1,314 tests), linting, dependency scanning |
| Monitoring | Prometheus + structured JSON logging | Request logging (method, path, status, duration_ms), custom metrics |

### Appendix D: Definitions

- **Child / Children:** An individual under the age of 13.
- **COPPA:** Children's Online Privacy Protection Act, 15 U.S.C. 6501-6506.
- **COPPA Rule:** FTC regulations implementing COPPA, 16 C.F.R. Part 312.
- **DPA:** Data Processing Agreement.
- **DPIA:** Data Protection Impact Assessment.
- **Operator:** Bhapi AI Portal, as the entity that operates the bhapi.ai website and platform.
- **Parent:** A parent or legal guardian of a child.
- **Personal Information:** As defined in 16 C.F.R. 312.2, individually identifiable information about a child collected online, including name, address, email, telephone number, Social Security number, persistent identifier that can be used to recognize a user over time and across sites, photograph or video, geolocation information, and any combination of information that permits physical or online contacting of a specific individual.
- **Service Provider:** A third party that collects, maintains, uses, or disseminates personal information on behalf of the operator.
- **Verifiable Parental Consent:** Any reasonable effort (taking into consideration available technology) to ensure that a parent of a child receives notice of the operator's personal information collection, use, and disclosure practices, and authorizes the collection, use, and disclosure, as applicable, of personal information and the subsequent use of that information before that information is collected from that child, as defined in 16 C.F.R. 312.2.

---

**Certification**

I certify that this Written Information Security Program has been reviewed and approved, and that the safeguards described herein are implemented and operating effectively as of the effective date stated above.

_________________________
**Name:** [Security Coordinator Name]
**Title:** Information Security Coordinator
**Date:** March 17, 2026

_________________________
**Name:** [CEO Name]
**Title:** Chief Executive Officer
**Date:** March 17, 2026
