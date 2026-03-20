# Vendor Security Questionnaire — Pre-filled Responses

**Vendor:** Bhapi Inc.
**Product:** Bhapi AI Safety Monitoring Platform
**Version:** 1.0 | **Date:** 2026-03-20

---

This document provides pre-filled responses to common school district vendor security questionnaires. It follows the format used by HECVAT Lite, CSPC, and typical K-12 procurement security assessments.

---

## Section 1: Company Information

| Question | Response |
|----------|----------|
| Company legal name | Bhapi Inc. |
| Product/service name | Bhapi AI Safety Monitoring Platform |
| Website | https://bhapi.ai |
| Contact for security inquiries | security@bhapi.ai |
| Contact for privacy inquiries | privacy@bhapi.ai |
| Year founded | 2025 |
| Number of employees | [Current headcount] |
| Primary business | AI safety monitoring for families, schools, and clubs |

---

## Section 2: Data Hosting and Infrastructure

| Question | Response |
|----------|----------|
| Where is data hosted? | Render (US-based cloud platform) |
| Hosting provider SOC 2 compliance? | Yes — Render maintains SOC 2 Type II certification |
| Data center locations | United States |
| Is data stored outside the US? | No. All student data is stored in US-based data centers. |
| Multi-tenant or single-tenant? | Multi-tenant with logical data isolation per school/district |
| Do you use subprocessors? | Yes. See [SDPA Subprocessors list](sdpa-template.md#8-subprocessors): Render, Cloudflare, Stripe, SendGrid |
| Is the application SaaS? | Yes — web-based portal with browser extension |

---

## Section 3: Encryption

| Question | Response |
|----------|----------|
| Encryption at rest? | Yes — AES-256 |
| Encryption in transit? | Yes — TLS 1.3 |
| How are credentials stored? | Fernet/KMS encryption for stored credentials (API keys, integration secrets) |
| Are database backups encrypted? | Yes — encrypted at rest using provider-managed keys |
| Key management approach | Provider-managed keys (Render) for infrastructure; application-level Fernet keys for credential encryption, rotated per policy |

---

## Section 4: Access Control

| Question | Response |
|----------|----------|
| Role-based access control (RBAC)? | Yes — granular roles: school admin, teacher/staff, parent, student, Bhapi support |
| Multi-factor authentication (MFA)? | Yes — required for all admin accounts |
| SSO support? | Yes — Google Workspace SSO and Microsoft Entra SSO |
| How is admin access managed? | RBAC with least-privilege. School admins manage their own users. Bhapi staff access requires explicit authorization and audit logging. |
| Password policy | Minimum 8 characters, complexity requirements enforced. Bcrypt hashing. |
| Session management | Configurable session timeouts (default 30 minutes). JWT-based authentication. |
| How do you handle employee offboarding? | Access revoked immediately upon separation. Access reviews conducted quarterly. |

---

## Section 5: Incident Response

| Question | Response |
|----------|----------|
| Do you have an incident response plan? | Yes — documented at [docs/security/incident-response-plan.md](../security/incident-response-plan.md) |
| Breach notification timeline | Within 72 hours of confirmed breach |
| Who is notified? | Affected school district(s), with details of breach, data affected, and remediation steps |
| Post-incident reporting | Detailed incident report provided within 30 days |
| Do you carry cyber liability insurance? | Yes — see [Insurance Certificate](insurance-certificate.md) |

---

## Section 6: Compliance

| Question | Response |
|----------|----------|
| COPPA compliant? | Yes — full COPPA 2026 compliance including deny-by-default consent, age-gating for under-13, child-friendly privacy notices, parental data dashboard |
| FERPA compliant? | Yes — operates as "school official" under FERPA. See [FERPA Compliance](../compliance/ferpa-compliance.md) |
| GDPR compliant? | Yes — for applicable users. Data processing agreements available. |
| LGPD compliant? | Yes — for applicable users (Brazil). |
| EU AI Act compliant? | Yes — transparency, human review, and appeals processes implemented |
| State student privacy laws? | Designed for compliance with SOPIPA (CA), Ed Law 2-d (NY), SOPPA (IL), and other state laws |
| Do you sign SDPAs? | Yes — see [SDPA Template](sdpa-template.md) |
| Do you participate in Student Privacy Pledge? | [In progress / Yes] |

---

## Section 7: Background Checks

| Question | Response |
|----------|----------|
| Background checks for employees with data access? | Yes — criminal background checks for all employees with access to student data |
| Background check scope | Criminal history, identity verification |
| Frequency | Pre-employment and as required by policy |

---

## Section 8: Penetration Testing and Vulnerability Management

| Question | Response |
|----------|----------|
| Penetration testing? | Yes — annual third-party penetration testing. Plan documented at [docs/security/pentest-plan.md](../security/pentest-plan.md) |
| Vulnerability scanning? | Continuous dependency scanning (Dependabot), application security testing |
| How are vulnerabilities remediated? | Critical: 24 hours. High: 7 days. Medium: 30 days. Low: 90 days. |
| Bug bounty program? | [Planned / In place] — contact security@bhapi.ai |

---

## Section 9: Data Retention and Deletion

| Question | Response |
|----------|----------|
| Data retention policy | Current school year + 1 prior year (configurable by school admin) |
| Data deletion upon contract termination | Within 30 days. Written confirmation provided. |
| Can the school export data? | Yes — school admin can export all data prior to termination |
| Data deletion from backups | Within 90 days per backup rotation |

---

## Section 10: Business Continuity

| Question | Response |
|----------|----------|
| Disaster recovery plan? | Yes — hosted on Render with automated backups and failover |
| Recovery Time Objective (RTO) | < 4 hours |
| Recovery Point Objective (RPO) | < 1 hour (continuous database backups) |
| Uptime SLA | 99.9% (per Render infrastructure SLA) |

---

## Section 11: Application Security

| Question | Response |
|----------|----------|
| Secure development lifecycle? | Yes — code review, automated testing (1578+ backend tests, 174 frontend tests), CI/CD pipeline |
| OWASP Top 10 addressed? | Yes — input validation, parameterized queries, CSRF protection, security headers |
| API security | JWT authentication, API key scoping, rate limiting (configurable), CORS restricted to configured origins |
| Content Security Policy | Yes — implemented via security headers |
| Logging and monitoring | Structured JSON logging, request logging middleware (method, path, status, duration), correlation IDs |

---

## Related Documents

- [SDPA Template](sdpa-template.md)
- [FERPA Compliance](../compliance/ferpa-compliance.md)
- [Incident Response Plan](../security/incident-response-plan.md)
- [Penetration Test Plan](../security/pentest-plan.md)
- [Security Program](../compliance/security-program.md)
- [Insurance Certificate](insurance-certificate.md)
