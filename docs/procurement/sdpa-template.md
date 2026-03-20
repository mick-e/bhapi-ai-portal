# Student Data Privacy Agreement (SDPA)

**Template Version:** 1.0 | **Effective Date:** 2026-03-20

---

## STUDENT DATA PRIVACY AGREEMENT

This Student Data Privacy Agreement ("Agreement") is entered into by and between:

**School District:** ________________________________________ ("District")
**Address:** ________________________________________
**Contact:** ________________________________________

and

**Provider:** Bhapi Inc. ("Bhapi")
**Address:** ________________________________________
**Contact:** privacy@bhapi.ai
**Website:** https://bhapi.ai

**Effective Date:** ________________
**Term:** One (1) year from Effective Date, renewable annually.

---

## 1. Purpose

This Agreement governs the collection, use, and protection of student data by Bhapi in connection with the AI safety monitoring services ("Services") provided to the District. This Agreement supplements and is incorporated into the underlying service agreement between the parties.

---

## 2. Definitions

- **Student Data:** Any data, whether gathered by Bhapi or provided by the District, that is descriptive of the student including but not limited to: name, student ID, email address, grade level, AI interaction logs, risk assessments, and safety alerts.
- **Education Records:** Student Data that constitutes "education records" as defined by FERPA (20 U.S.C. 1232g).
- **De-Identified Data:** Data from which all personally identifiable information has been removed and for which Bhapi has made a reasonable determination that a student's identity is not personally identifiable.
- **Service:** The Bhapi AI safety monitoring platform (bhapi.ai), including the browser extension, parent/school portals, and risk analysis pipeline.

---

## 3. Data Collected

Bhapi collects and processes the following categories of student data solely in connection with providing the Services:

| Category | Data Elements | Purpose |
|----------|--------------|---------|
| **Identity** | Student name, student ID, email, grade level | Account creation, user identification |
| **AI Interactions** | Conversation content with AI platforms, timestamps, platform identifiers | Safety analysis, risk scoring |
| **Risk Data** | Risk scores, safety alerts, flagged content, taxonomy classifications | Safety monitoring, reporting to school |
| **Usage Metadata** | Session duration, platform usage frequency, feature usage | Service delivery, aggregate analytics |
| **Device Context** | Browser type, extension version (no device fingerprinting) | Technical support, compatibility |

**Not Collected:** Bhapi does not collect grades, test scores, disciplinary records, health records, Social Security numbers, financial information, or any education records beyond those listed above.

---

## 4. Data Use Restrictions

Bhapi shall:

- Use Student Data solely for the purpose of providing the Services to the District.
- Not use Student Data for marketing, advertising, or any commercial purpose unrelated to the Services.
- Not sell, rent, or trade Student Data to any third party.
- Not use Student Data to create advertising profiles or target advertising to students.
- Not use Student Data for AI model training or development without explicit, separate written consent from the District.
- Not disclose Student Data to any third party except as required to provide the Services (see Section 8: Subprocessors) or as required by law.

---

## 5. School Official Designation

The District designates Bhapi as a "school official" with a "legitimate educational interest" under FERPA 34 CFR 99.31(a)(1)(i)(B). Bhapi shall:

- Perform an institutional service or function for which the District would otherwise use employees.
- Be under the direct control of the District with respect to the use and maintenance of education records.
- Use education records only for the purposes for which access was granted.
- Comply with FERPA requirements applicable to school officials.

---

## 6. Data Security

Bhapi shall implement and maintain commercially reasonable security measures, including:

| Control | Implementation |
|---------|---------------|
| **Encryption at Rest** | AES-256 encryption for all Student Data |
| **Encryption in Transit** | TLS 1.3 for all data transmission |
| **Credential Encryption** | Fernet/KMS encryption for stored credentials |
| **Access Control** | Role-based access control (RBAC) with least-privilege |
| **Authentication** | Multi-factor authentication (MFA) for administrative access |
| **Multi-Tenant Isolation** | Logical data isolation per school/district |
| **Audit Logging** | Comprehensive logging of all data access with correlation IDs |
| **Vulnerability Management** | Annual penetration testing, continuous monitoring |
| **SOC 2 Type II** | Certification maintained (or equivalent, with timeline if in progress) |

---

## 7. Data Deletion

- **During Term:** District admin may delete individual student records at any time through the platform.
- **Upon Termination:** Bhapi shall delete all Student Data within thirty (30) calendar days of contract termination or expiration. District may request a data export prior to deletion.
- **Backup Purge:** Student Data in backups shall be purged within ninety (90) days of deletion per backup rotation schedules.
- **Confirmation:** Bhapi shall provide written confirmation of deletion to the District upon completion.
- **De-Identified Data:** De-identified aggregate data may be retained for product improvement, provided it cannot be re-identified.

---

## 8. Subprocessors

Bhapi uses the following subprocessors in delivering the Services. Bhapi ensures each subprocessor meets equivalent data protection standards:

| Subprocessor | Service | Data Access | Location |
|-------------|---------|-------------|----------|
| **Render** | Cloud hosting, compute, database | All Student Data (encrypted) | United States |
| **Cloudflare** | CDN, DDoS protection, DNS | Network traffic metadata only | Global (US primary) |
| **Stripe** | Payment processing | District billing data only (no Student Data) | United States |
| **SendGrid** | Transactional email | Email addresses, notification content | United States |

Bhapi shall notify the District at least thirty (30) days before adding a new subprocessor that will have access to Student Data. The District may object to a new subprocessor, and the parties shall negotiate in good faith to resolve the objection.

---

## 9. Breach Notification

In the event of an unauthorized access, disclosure, or loss of Student Data ("Breach"):

- Bhapi shall notify the District within seventy-two (72) hours of confirming the Breach.
- Notification shall include: description of the Breach, data affected, date of discovery, remediation steps taken, and contact information.
- Bhapi shall cooperate with the District in investigating and mitigating the Breach.
- Bhapi shall provide a post-incident report within thirty (30) days.
- Bhapi shall bear reasonable costs of notification and remediation attributable to the Breach.

---

## 10. Annual Audit Rights

- The District (or its designated auditor) may audit Bhapi's compliance with this Agreement once per calendar year.
- Audits shall be conducted during normal business hours with at least thirty (30) days written notice.
- Bhapi shall provide reasonable access to facilities, systems, and documentation relevant to the handling of Student Data.
- Bhapi shall promptly remediate any non-compliance findings identified during an audit.
- In lieu of an on-site audit, the District may accept Bhapi's most recent SOC 2 Type II report or equivalent third-party audit.

---

## 11. Compliance

Bhapi represents and warrants that its Services comply with:

- **FERPA** — Family Educational Rights and Privacy Act (20 U.S.C. 1232g)
- **COPPA** — Children's Online Privacy Protection Act (15 U.S.C. 6501-6506), including COPPA 2026 amendments
- **State Student Privacy Laws** — Including but not limited to applicable state laws (e.g., California SOPIPA, New York Ed Law 2-d, Illinois SOPPA)
- **GDPR/LGPD** — Where applicable to international students
- **EU AI Act** — Transparency and human oversight requirements

---

## 12. Term and Termination

- **Term:** One (1) year from the Effective Date, automatically renewing unless either party provides thirty (30) days written notice of non-renewal.
- **Termination for Cause:** Either party may terminate upon thirty (30) days written notice if the other party materially breaches this Agreement and fails to cure within the notice period.
- **Effect of Termination:** Sections 4, 6, 7, and 9 survive termination.

---

## 13. Signatures

**District:**

Name: ________________________________________
Title: ________________________________________
Signature: ____________________________________
Date: ________________________________________

**Bhapi Inc.:**

Name: ________________________________________
Title: ________________________________________
Signature: ____________________________________
Date: ________________________________________

---

## Related Documents

- [FERPA Compliance Documentation](../compliance/ferpa-compliance.md)
- [Vendor Security Questionnaire](vendor-security-questionnaire.md)
- [Security Program](../compliance/security-program.md)
- [Incident Response Plan](../security/incident-response-plan.md)
