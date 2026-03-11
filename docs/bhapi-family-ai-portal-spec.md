# Bhapi Family AI Governance Portal — Formal Product Specification

**Document Version:** 2.1
**Status:** Implemented (Post-MVP Complete)
**Owner:** Mike, CEO — Bhapi
**Date:** February 2026 (Updated March 2026)
**Platform URL:** bhapi.ai

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision & Goals](#2-product-vision--goals)
3. [Personas & User Roles](#3-personas--user-roles)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Architecture Overview](#6-architecture-overview)
7. [AI Monitoring — Capture Strategy](#7-ai-monitoring--capture-strategy)
8. [Risk & Safety Engine](#8-risk--safety-engine)
9. [LLM Billing Management](#9-llm-billing-management)
10. [Compliance & Regulatory Framework](#10-compliance--regulatory-framework)
11. [Billing & Subscription](#11-billing--subscription)
12. [Internationalisation](#12-internationalisation)
13. [Security Requirements](#13-security-requirements)
14. [Scope Boundaries — MVP](#14-scope-boundaries--mvp)
15. [Backlog & Future Phases](#15-backlog--future-phases)
16. [Open Questions & Assumptions](#16-open-questions--assumptions)
17. [Glossary](#17-glossary)

---

## 1. Executive Summary

The **Bhapi Family AI Governance Portal** is a new product under the bhapi.ai umbrella that provides parents, school administrators, and community club managers with a unified platform to monitor, govern, and manage the AI tool usage of children and members under their care. 

The portal addresses a critical and growing gap: as AI tools like ChatGPT, Gemini, Microsoft Copilot, Anthropic Claude, and Grok become embedded in everyday family, school, and club life, there is no centralised parental or administrator control layer. This product fills that gap with real-time risk alerting, PII protection, content safety monitoring, and — critically — AI spend management so that families and organisations can control both the safety and the cost of AI consumption.

The product is a sibling to Bhapi's core social safety platform and is informed by the AI risk management methodology developed at Littledata, implemented here as a fully independent service.

---

## 2. Product Vision & Goals

**Vision:** To be the trusted AI safety and governance layer for families, schools, and clubs worldwide — making responsible AI use simple to manage without requiring technical expertise.

**MVP Goals:**

- Launch a web-responsive portal at bhapi.ai serving family and institutional (school/club) use cases.
- Provide multi-channel AI usage monitoring across the five major consumer LLMs.
- Detect and flag harmful content, PII exposure, and high-risk AI interactions in real-time.
- Give parents and administrators full visibility into AI spend across their group, with configurable thresholds and alerts.
- Support English as the launch language with architecture ready for five additional languages (FR, DE, IT, PT, ES).
- Meet regulatory obligations for the US, EU, UK, Australia, and Brazil from day one.

---

## 3. Personas & User Roles

### 3.1 Parent / Family Guardian (`role: parent`)

The primary consumer persona. A parent or legal guardian who creates a family account and invites family members. They have full admin rights over their family group: viewing all monitored AI interactions, managing alerts, reviewing flagged content, setting spend limits, and approving or blocking AI tool access for children.

**Key jobs to be done:**
- Know what AI tools my children are using and what they are asking.
- Be alerted immediately if something dangerous or inappropriate is happening.
- Understand and control how much money is being spent on AI across the household.
- Protect my family's personal information from being submitted to AI systems.

### 3.2 Child / Family Member (`role: member`)

A family member (typically a minor, under 18) who is added to a family group by a parent. They use AI tools in their normal life. They do not have administrative access to the portal. Depending on age, they may receive simplified status views. Children are never presented with their own risk scores or flagged content details without parent mediation.

### 3.3 School Administrator (`role: school_admin`)

A designated staff member at a school (IT administrator, head teacher, designated safeguarding lead) who manages a school group. They can see aggregate and individual AI usage across students in their group, manage school-wide AI spend, set content safety policies, and receive risk alerts.

**Key jobs to be done:**
- Ensure students are using approved AI tools within safe boundaries.
- Detect and respond to students attempting to use AI for harmful, dishonest, or unsafe purposes.
- Manage the school's AI licensing costs and enforce budget caps per department or year group.
- Generate compliance reports for governors, Ofsted, or other regulatory bodies.

### 3.4 Club / Organisation Manager (`role: club_admin`)

Similar to the school admin but for youth clubs, sports clubs, faith groups, or community organisations. Typically less technical. Focused on safeguarding members and managing any shared AI tool accounts.

### 3.5 System Administrator (`role: system_admin`)

Internal Bhapi staff role. Full platform access for support, compliance audit, and operations. Not visible to end users.

---

## 4. Functional Requirements

### 4.1 Account & Group Management

**FR-001** — Users must be able to register via email/password or SSO (Google, Microsoft, Apple).  
**FR-002** — Registration flow must differentiate between Family account, School account, and Club account at sign-up.  
**FR-003** — A Parent or Admin must be able to create a named Group (family, class, club) and invite members by email or shareable link.  
**FR-004** — Invitations must require guardian consent for any member identified as under 16 years of age.  
**FR-005** — Group members can be assigned the roles defined in Section 3. Role changes require group admin confirmation.  
**FR-006** — A user may belong to multiple groups (e.g. a parent who is also a school admin).  
**FR-007** — Account deletion must trigger full data erasure workflows compliant with GDPR, LGPD, and COPPA as applicable.

### 4.2 Dashboard

**FR-010** — The portal must present a primary dashboard showing: active monitored members, recent AI activity feed, unresolved risk alerts, and current-period AI spend summary.  
**FR-011** — The dashboard must be fully responsive on mobile web (≥320px width) without loss of core functionality.  
**FR-012** — School and club dashboards must support a group-level summary view and a drill-down to individual member views.  
**FR-013** — Dashboard data must refresh at a maximum interval of 60 seconds for risk alerts and 5 minutes for usage summaries.

### 4.3 AI Usage Monitoring

**FR-020** — The system must monitor interactions with: ChatGPT (OpenAI), Gemini (Google), Microsoft Copilot, Claude (Anthropic), and Grok (xAI).  
**FR-021** — Monitoring must be achievable via three complementary capture channels (see Section 7 for architecture detail):
  - Browser extension (Chrome and Firefox, MVP).
  - DNS-layer proxy for network-wide monitoring.
  - API/webhook integrations where natively supported by the LLM platform.  
**FR-022** — Usage events must capture: timestamp, platform, session identifier, prompt category classification, and risk classification. Raw prompt content must only be retained when a risk flag is raised, and must be handled under strict data minimisation rules.  
**FR-023** — The system must present a usage timeline per member showing sessions, duration, and platform.  
**FR-024** — Administrators must be able to see which AI tools are being accessed across their group and what proportion of total spend each tool represents.

### 4.4 Risk & Safety Monitoring

**FR-030** — The system must evaluate AI interactions in real-time against a risk classification matrix (see Section 8).  
**FR-031** — Risk events must trigger one or more of the following responses based on severity: in-portal dashboard notification, push/email alert to group admin, and automated temporary session flag (displayed to admin for decision on blocking).  
**FR-032** — The following risk categories must be detected: harmful or dangerous content (self-harm, violence, radicalisation), inappropriate or adult content, PII exposure (names, addresses, phone numbers, identity numbers, health data), academic dishonesty indicators, scam or manipulation patterns, and excessive usage anomalies.  
**FR-033** — PII detected in monitored prompts must be masked in the portal display and logged separately under elevated access controls. The system must never display raw PII in the main activity feed.  
**FR-034** — Admins must be able to configure alert sensitivity per risk category (e.g. suppress academic dishonesty alerts for an art club, heighten self-harm sensitivity for a school counselling group).  
**FR-035** — All risk flags must be retained in an audit log for a minimum of 12 months.

### 4.5 LLM Billing Management

**FR-040** — The portal must support connection of LLM provider accounts to track AI spend. Supported providers at MVP: OpenAI, Google (Gemini API), Microsoft (Copilot/Azure OpenAI), Anthropic, xAI.  
**FR-041** — For each connected provider account, the system must display current-period spend, spend trend versus prior period, and projected monthly spend.  
**FR-042** — Admins must be able to set spend thresholds at group level and per-member level. Thresholds must support:
  - Soft threshold: alert only.
  - Hard threshold: alert and flag for admin action (not automatic blocking in MVP, see Section 14).  
**FR-043** — The system must send alerts when spend reaches 50%, 80%, and 100% of any configured threshold.  
**FR-044** — A spend report must be exportable as CSV and PDF showing breakdown by member, by platform, and by time period.  
**FR-045** — The system must display cost per interaction estimate alongside usage data where API cost data is available.  
**FR-046** — Schools and clubs must be able to allocate budget envelopes to sub-groups (e.g. departments, year groups, teams) and track spend within those envelopes.

### 4.6 Alerts & Notifications

**FR-050** — Alerts must be deliverable via: in-portal notification centre, email, and optionally SMS (phase 2).  
**FR-051** — Admins must be able to configure notification preferences per alert category and per member.  
**FR-052** — The system must support a digest mode (immediate, hourly, daily) for lower-severity notifications.  
**FR-053** — All alerts must be acknowledged within the portal. Unacknowledged high-severity alerts must re-notify after 30 minutes.

### 4.7 Reporting

**FR-060** — The portal must provide exportable reports for: AI usage by member and platform, spend by period and member, risk events log, and PII detection events.  
**FR-061** — Reports must be exportable in CSV and PDF formats.  
**FR-062** — School and club admins must be able to generate safeguarding summary reports suitable for governance bodies.  
**FR-063** — Automated scheduled reports (weekly, monthly) must be configurable and sent to designated email addresses.

---

## 5. Non-Functional Requirements

### 5.1 Performance

- Dashboard page load time must be under 3 seconds at the 95th percentile on a standard 4G connection.
- Risk alert processing pipeline must complete within 10 seconds of a monitored interaction occurring.
- The system must support up to 10,000 concurrent users at MVP launch with horizontal scaling to 100,000+ users.

### 5.2 Availability

- Target uptime: 99.9% monthly (excluding planned maintenance windows).
- Planned maintenance windows must be communicated 48 hours in advance and scheduled outside of 06:00–22:00 in any supported region.

### 5.3 Scalability

- All services must be horizontally scalable via containerised deployment.
- Data storage must support multi-region replication for GDPR/data residency compliance (EU data stays in EU, Australian data stays in AU, etc.).

### 5.4 Accessibility

- The portal must conform to WCAG 2.1 Level AA.
- All critical workflows (onboarding, alert review, spend management) must be operable via keyboard navigation.

### 5.5 Browser & Device Support

- Chrome (latest 2 versions), Firefox (latest 2 versions), Safari (latest 2 versions), Edge (latest 2 versions).
- iOS Safari and Android Chrome (mobile web).
- Minimum supported screen width: 320px.

---

## 6. Architecture Overview

### 6.1 Product Positioning

The Bhapi Family AI Governance Portal is a **separate product** under the bhapi.ai brand. It shares Bhapi's brand identity, marketing site, and Stripe billing infrastructure but operates with its own independent backend services, database, and authentication layer. There is a single sign-on bridge available for users who also have a core Bhapi social account, but it is not required.

### 6.2 Cloud Platform

**Primary Cloud: Google Cloud Platform (GCP)** — consistent with the core Bhapi platform, enabling shared networking, security, and operational tooling. Render may be used for lightweight auxiliary services consistent with the Littledata stack where cost and maintenance burden benefit from it.

**GCP Services (indicative):**

- **Cloud Run** — containerised API services (stateless, auto-scaling).
- **Cloud SQL (PostgreSQL)** — primary relational database for accounts, groups, billing, and configuration.
- **Firestore** — real-time event streaming for dashboard live updates and alert state.
- **Pub/Sub** — event bus between the monitoring capture layer and the risk processing pipeline.
- **Cloud DLP (Data Loss Prevention)** — PII detection in the risk engine.
- **Cloud Storage** — report exports, audit logs, and encrypted raw event archives.
- **Cloud Armor** — WAF and DDoS protection.
- **Secret Manager** — credentials and API keys.
- **Cloud CDN + Load Balancer** — global content distribution for the web frontend.

### 6.3 Service Decomposition

The system is decomposed into the following bounded services:

| Service | Responsibility |
|---|---|
| `auth-service` | Registration, login, SSO, session management, role enforcement |
| `group-service` | Group CRUD, member management, invitations, consent flows |
| `capture-gateway` | Ingests monitoring signals from browser extension, DNS proxy, and API webhooks |
| `risk-engine` | Classifies interactions, detects PII and harmful content, generates risk events |
| `alert-service` | Delivers notifications via email, in-portal, and future channels |
| `billing-service` | Stripe subscription management, LLM spend aggregation, threshold management |
| `reporting-service` | Generates and distributes reports and exports |
| `portal-api` | BFF (Backend for Frontend) aggregating data for the web portal |
| `web-portal` | React-based progressive web app served at bhapi.ai |

### 6.4 Data Flow — High Level

```
Member uses AI tool
        |
        v
[Capture Channel]  <-- Browser Extension / DNS Proxy / LLM API Webhook
        |
        v
[capture-gateway]  --> Pub/Sub topic: raw_events
        |
        v
[risk-engine]  <-- Cloud DLP + Safety LLM classifier
        |
        |--> risk_events topic --> [alert-service] --> Admin notification
        |
        v
[Firestore: activity feed + risk log]
        |
        v
[portal-api] --> [web-portal] --> Admin dashboard
```

### 6.5 Frontend

- **Framework:** React (TypeScript) with Next.js for SSR and SEO.
- **Styling:** Tailwind CSS.
- **i18n:** `next-intl` or `react-i18next` for locale switching (see Section 12).
- **Deployment:** Cloud Run (containerised) behind Cloud CDN.

---

## 7. AI Monitoring — Capture Strategy

Monitoring is achieved through a combination of three complementary channels. Coverage and depth vary by channel and by LLM provider. All three are deployed to maximise coverage.

### 7.1 Channel 1 — Browser Extension

A Chrome and Firefox browser extension installed on members' devices.

**Capabilities:**
- Detects when a member navigates to a monitored AI platform (chatgpt.com, gemini.google.com, copilot.microsoft.com, claude.ai, grok.com).
- Captures prompt submission events and response receipt events via DOM monitoring.
- Sends sanitised event metadata (timestamp, platform, session ID, interaction count) and a content signal to the `capture-gateway`.
- Content signal is the interaction text, submitted only for risk classification. Raw content is not stored unless a risk event is raised.

**Limitations:**
- Requires installation on each device. Not effective if child uses a non-managed device.
- Can be circumvented by a determined user via private browsing or device switching.
- Extension must request only minimal permissions (tabs, activeTab, webRequest where needed) to comply with browser store policies.

**Deployment Model:**
- Extension is distributed via Chrome Web Store and Firefox Add-ons under the Bhapi brand.
- Admin generates a setup link/code used to associate the extension with a specific group member.

### 7.2 Channel 2 — DNS-Layer Proxy / Network Monitoring

A family or school configures their network router or uses the Bhapi DNS resolver (similar in model to NextDNS or Circle) to route DNS queries through a Bhapi-managed resolver.

**Capabilities:**
- Logs DNS resolution events for monitored AI domains.
- Can optionally block AI platform DNS resolution (admin-controlled policy setting, see backlog for MVP status).
- Provides device-level usage attribution (by MAC address / device name configured by admin).

**Limitations:**
- DNS-layer monitoring shows that a service was accessed but cannot inspect HTTPS content (this is intentional and GDPR-compliant — content inspection is handled by the browser extension at the device level).
- Requires router configuration by admin. Simpler setup involves installing a Bhapi device agent (Phase 2).
- Mobile data bypasses home/school DNS.

**Deployment Model:**
- Bhapi provides a DNS resolver address (IPv4 and IPv6).
- Admin dashboard provides guided router setup instructions per common router model.
- For schools, automated DHCP/DNS configuration scripts provided for common network management platforms.

### 7.3 Channel 3 — LLM Provider API / Webhook Integration

Where supported by the LLM provider, the admin connects their organisation's API account to Bhapi, allowing direct query of usage and spend data.

**Supported integrations at MVP:**

| Provider | Spend Data | Usage Events | Content Access |
|---|---|---|---|
| OpenAI | ✅ Usage API | ✅ Logs API | ⛔ Not available |
| Google (Gemini API) | ✅ Cloud Billing | ✅ Audit Logs | ⛔ Not available |
| Microsoft (Azure OpenAI) | ✅ Azure Cost API | ✅ Azure Monitor | ⛔ Not available |
| Anthropic | ✅ Usage API | ✅ Usage logs | ⛔ Not available |
| xAI (Grok) | 🔄 API evolving | 🔄 API evolving | ⛔ Not available |

Note: No provider exposes content (prompt/response text) via their management APIs. Content-level risk monitoring is handled exclusively by the browser extension (Channel 1). Channel 3 provides spend and usage volume data only.

### 7.4 Channel Coverage Matrix

| Capability | Browser Extension | DNS Proxy | LLM API |
|---|---|---|---|
| Usage detection | ✅ | ✅ | ✅ |
| Content risk scanning | ✅ | ⛔ | ⛔ |
| Spend tracking | Estimated | ⛔ | ✅ Accurate |
| Mobile device coverage | ✅ (per browser) | Partial | ✅ |
| Works on unmanaged devices | ⛔ | ⛔ | ✅ |
| Works without internet config | ✅ | ⛔ | ✅ |

---

## 8. Risk & Safety Engine

The risk engine is a **new, standalone service** independent of Littledata. It draws on architectural learnings from Littledata's AI risk methodology but is implemented as a purpose-built consumer safety service with a different threat model (protecting children and families, not enterprise AI governance).

### 8.1 Architecture

The risk engine operates as an async consumer of the `raw_events` Pub/Sub topic. It applies a multi-layer classification pipeline:

**Layer 1 — PII Detection (Google Cloud DLP)**  
All content signals are passed through Cloud DLP to identify: names, email addresses, phone numbers, physical addresses, national identity numbers, financial account numbers, health/medical information, and age indicators. Detected PII is masked before any further processing or storage.

**Layer 2 — Safety Classification (Safety LLM)**  
A safety-tuned LLM (Google Gemini with safety settings, or a fine-tuned model via Vertex AI) classifies the interaction against the risk taxonomy. This model is prompted with the masked content and returns a structured risk assessment.

**Layer 3 — Rules Engine**  
A deterministic rules layer applies context-specific overrides: school-specific keyword watchlists, parent-configured alert preferences, age-band risk scaling (content risk assessment is stricter for younger members), and spend anomaly detection.

**Layer 4 — Risk Event Emission**  
If any layer produces a risk classification above the configured sensitivity threshold, a structured risk event is emitted to the `risk_events` Pub/Sub topic.

### 8.2 Risk Taxonomy

| Category | Severity | Description |
|---|---|---|
| `SELF_HARM` | Critical | Content related to self-harm, suicide, eating disorders |
| `VIOLENCE` | Critical | Threats, glorification of violence, weapons |
| `RADICALISATION` | Critical | Extremist content, recruitment patterns |
| `CSAM_ADJACENT` | Critical | Any content with sexual indicators involving minors |
| `ADULT_CONTENT` | High | Sexual or explicit content not involving minors |
| `SCAM_MANIPULATION` | High | Social engineering, phishing, manipulation patterns |
| `PII_EXPOSURE` | High | Personally identifiable information submitted to AI |
| `ACADEMIC_DISHONESTY` | Medium | Assignment completion, exam question patterns |
| `BULLYING_HARASSMENT` | Medium | Content targeting identifiable individuals |
| `SPEND_ANOMALY` | Medium | Usage or spend significantly exceeding baseline |
| `EXCESSIVE_USAGE` | Low | Usage duration anomaly |
| `UNKNOWN_PLATFORM` | Low | Access to an unmonitored AI platform detected |

### 8.3 Response Actions by Severity

| Severity | In-Portal Alert | Email to Admin | Re-notification if unacknowledged |
|---|---|---|---|
| Critical | ✅ Immediate | ✅ Immediate | After 15 minutes |
| High | ✅ Immediate | ✅ Immediate | After 30 minutes |
| Medium | ✅ Immediate | Digest (configurable) | No |
| Low | Dashboard feed | Digest (configurable) | No |

Note: Automated blocking of AI sessions is **not in scope for MVP** (see Section 14). Admins receive alerts and take manual action. The ability for admins to push a block signal to the browser extension is on the backlog.

### 8.4 Data Minimisation

- Raw prompt/response text is **never stored by default**.
- When a risk event is raised, the triggering content excerpt (minimum necessary to evidence the risk) is stored encrypted, with access restricted to the group admin and system admins.
- PII is masked before storage in all cases.
- Content excerpts associated with risk events are deleted after 12 months, or immediately upon member account deletion.

---

## 9. LLM Billing Management

This is a first-class feature of the portal, not an afterthought. Families, schools, and clubs increasingly hold paid LLM subscriptions or API accounts and have no tooling to manage costs across multiple users.

### 9.1 LLM Account Connection

Admins connect their LLM provider accounts via OAuth (where supported) or API key (with read-only scope). Bhapi requests the minimum scope necessary: usage data and billing data. Bhapi explicitly does not request the ability to generate content or manage model settings.

### 9.2 Spend Aggregation

Once connected, the `billing-service` polls provider APIs on a scheduled basis (minimum hourly, where provider API rate limits allow) and aggregates:

- Total spend for the current billing period.
- Spend per user (where the provider exposes user-level attribution — currently limited on most platforms; browser extension usage attribution is used as a proxy).
- Spend per day and trend vs. prior period.
- Token consumption by model (where available).
- Estimated cost per interaction.

### 9.3 Budget Thresholds & Alerts

Admins configure thresholds at group level and optionally at member level. Thresholds are set in the group's reporting currency (defaulting to the subscription currency).

- **Soft threshold (alert only):** Sends notification at 50%, 80%, and 100% of the configured limit.
- **Hard threshold (flag for action):** At 100%, sends a critical alert and flags the LLM account in the dashboard. Automated blocking of API spend is not in MVP scope; the admin must take action with the provider directly.

**School / Club budget envelopes:** School admins can define named budget envelopes (e.g. "Year 10 Computing", "Football First Team") and allocate members to those envelopes. Spend is tracked and alerted at envelope level as well as group level.

### 9.4 Reporting

- Spend reports are exportable as CSV and PDF.
- Reports can be scheduled (weekly, monthly) and emailed to designated recipients.
- Schools can generate reports structured for finance committee review or EdTech budget governance.

---

## 10. Compliance & Regulatory Framework

The portal processes data about children and families across multiple jurisdictions. Compliance is a foundation of the product, not a retrofit.

### 10.1 Regulations in Scope

| Regulation | Jurisdiction | Key Obligations |
|---|---|---|
| GDPR | EU / EEA | Lawful basis, data subject rights, DPO, data residency, breach notification (72hr) |
| UK GDPR + Children's Code | UK | Age-appropriate design, high privacy defaults for under-18s, geolocation off by default |
| COPPA | United States | Verifiable parental consent for under-13s, no targeted advertising, data minimisation |
| LGPD | Brazil | Similar to GDPR; explicit consent, data subject rights, DPA notification |
| Online Safety Act | Australia | Age assurance, harmful content obligations, platform duty of care |
| EU AI Act | EU | Risk classification for AI systems used with children; documentation and transparency obligations |

### 10.2 Age Assurance

- Account holders must declare their age at registration.
- For users under 16 (EU/UK), parental or guardian consent is required before account activation.
- For users under 13 (US), COPPA-compliant verifiable parental consent is required.
- Brazil: parental consent required for under-18s per LGPD guidance.
- Age assurance at MVP is declaration-based with additional verification (email or identity document) as a Phase 2 enhancement.

### 10.3 Data Residency

- EU member data must be stored and processed within the EU (Cloud SQL and Firestore configured with EU regions).
- Australian data must be stored within Australia.
- US data stored in US regions.
- Data transfer between regions must be governed by appropriate transfer mechanisms (Standard Contractual Clauses for EU-UK-AU transfers).

### 10.4 Privacy by Design Principles

- Data minimisation: only collect what is necessary for the stated purpose.
- Purpose limitation: monitoring data used only for safety and governance; not for advertising or profiling.
- Storage limitation: defined retention periods for all data categories.
- Transparency: clear privacy notice in all supported languages.
- No behavioural advertising in Bhapi products.

### 10.5 Documentation Requirements

- Data Protection Impact Assessment (DPIA) required before launch (GDPR Article 35, UK ICO guidance).
- Children's Code Children's Data Impact Assessment (CDIA).
- Record of Processing Activities (ROPA) maintained.
- EU AI Act: maintain technical documentation for the risk classification AI system as a high-risk system under Annex III (AI used in education, safety of persons).

---

## 11. Billing & Subscription

### 11.1 Subscription Model

**MVP: Single tier, monthly or annual billing.**

- Family plan: billed per family group (up to N members — number TBD in commercial planning).
- School plan: billed per school (up to N student members — education pricing).
- Club plan: billed per club group.

Payment processor: **Stripe**, using the existing Bhapi Stripe account with a new Product and Price configuration for this portal.

### 11.2 Billing Features

- Monthly and annual billing cycles with annual discount.
- Stripe Customer Portal enabled for self-service plan management, payment method updates, and invoice history.
- Automatic dunning management via Stripe for failed payments.
- Prorated billing for mid-cycle membership changes.
- Invoice generated per billing cycle; downloadable from the portal.
- VAT/GST handling via Stripe Tax (automatic tax calculation by jurisdiction).

### 11.3 Free Trial

A 14-day free trial is offered at sign-up with no credit card required. After 14 days, users are prompted to subscribe. Data is retained for 30 days post-trial expiry before deletion.

### 11.4 Pricing (TBD)

Specific pricing to be determined during commercial planning. The spec assumes a SaaS subscription model in the range consistent with Bhapi's existing pricing strategy. Tiers and volume pricing are backlog items.

---

## 12. Internationalisation

### 12.1 MVP Language

English only at launch.

### 12.2 Supported Languages (Phase 2)

The following languages must be supported in Phase 2 in order of regional user priority:

1. French (FR)
2. Spanish (ES)
3. German (DE)
4. Portuguese (PT — both PT-PT and PT-BR variants)
5. Italian (IT)

### 12.3 Technical Implementation

- All UI strings must be externalised into locale resource files (JSON) from day one. No hardcoded English strings in component code.
- Use of `next-intl` or equivalent library to handle locale routing (`bhapi.ai/en/`, `bhapi.ai/fr/` etc.) and string interpolation.
- Date, time, number, and currency formatting must use the user's locale via `Intl` API.
- Right-to-left (RTL) layout not required for MVP languages but architecture should not preclude it.
- Legal documents (Privacy Policy, Terms of Service) must be professionally translated and legally reviewed for each locale, not machine-translated.

### 12.4 Risk Engine Localisation

The risk classification engine must correctly handle content in all supported languages. The underlying safety LLM must have verified multilingual capability for each supported language before that language is enabled in production.

---

## 13. Security Requirements

### 13.1 Authentication & Access

- Passwords must meet minimum complexity requirements (12+ characters, mixed case, numbers).
- Multi-factor authentication (MFA) must be available and strongly encouraged at onboarding; mandatory for school and club admin roles.
- Session tokens expire after 24 hours of inactivity (configurable).
- All API endpoints must be authenticated. There are no public unauthenticated API endpoints beyond the auth handshake.

### 13.2 Encryption

- All data in transit: TLS 1.3 minimum.
- All data at rest: AES-256 encryption via GCP's managed encryption.
- PII and risk event content: field-level encryption using GCP Cloud KMS with separate key rings per data classification level.

### 13.3 API Security

- Browser extension communication with `capture-gateway` must use signed requests (HMAC or JWT) to prevent spoofing.
- LLM provider API credentials stored in GCP Secret Manager, never in environment variables or code.
- OAuth tokens for LLM provider connections stored encrypted, refreshed automatically.

### 13.4 Penetration Testing & Security Review

- An independent penetration test must be completed before public launch.
- OWASP Top 10 must be addressed in code review prior to launch.
- Dependency vulnerability scanning must be integrated into the CI/CD pipeline (e.g. Dependabot, Snyk).

### 13.5 AI-Specific Security

- The risk engine LLM must be hardened against prompt injection attacks. User-submitted content passed to the classifier must be escaped and wrapped in a structured classification prompt that prevents instruction following.
- The capture gateway must validate and sanitise all incoming events from the browser extension against an event schema before processing.

---

## 14. Scope Boundaries — MVP

### In Scope

- Web-responsive portal (mobile web supported, minimum 320px).
- Family, school, and club group account types.
- Monitoring of: ChatGPT, Gemini, Microsoft Copilot, Claude, Grok.
- Browser extension (Chrome and Firefox).
- DNS proxy monitoring channel.
- LLM API/webhook integration for spend and usage data.
- Risk & safety engine with PII detection and harmful content classification.
- Real-time alerts (in-portal and email).
- LLM spend tracking, budget thresholds, and alerts.
- Budget envelopes for schools and clubs.
- Stripe billing (monthly and annual plans, single tier).
- English language only.
- Compliance: GDPR, UK GDPR, COPPA, LGPD, Australian Online Safety Act, EU AI Act.
- Report exports (CSV and PDF).
- WCAG 2.1 AA accessibility.

### Out of Scope — MVP

- Native mobile application (iOS/Android).
- Additional languages beyond English.
- Automated blocking of AI sessions (alert and flag only).
- Tiered pricing and freemium model.
- SMS notifications.
- Device agent for router-free network monitoring.
- Direct LLM API key revocation or spend blocking via provider APIs.
- Third-party SIS (Student Information System) integrations for schools.
- Single sign-on federation with school identity providers (e.g. Google Workspace for Education, Microsoft Entra).
- Browser extension for Safari.
- Age verification beyond self-declaration.
- Advanced analytics and trend modelling.

---

## 15. Backlog & Future Phases

Items from the original backlog. Most have been implemented as part of the post-MVP roadmap (see `docs/bhapi-post-mvp-roadmap.md`).

### Implemented (v2.1.0)
- **Tiered pricing:** Family ($9.99/mo), School (per-seat), Enterprise tiers with Stripe plan management — `src/billing/plans.py`
- **Additional language support:** EN, FR, ES, DE, PT-BR, IT — `portal/messages/`
- **Automated AI session blocking:** Auto-block rules, time budgets, bedtime mode, parent approval flow — `src/blocking/`
- **SMS notifications:** Twilio with rate limiting (10/min/group) — `src/sms/`
- **School SIS integration:** Clever, ClassLink, Canvas, PowerSchool — `src/integrations/`
- **Federated SSO for schools:** Google Workspace and Microsoft Entra with auto-provisioning — `src/integrations/sso_provisioner.py`
- **Age verification:** Yoti integration with dev/test mode — `src/integrations/yoti.py`
- **AI usage coaching:** AI literacy assessment modules — `src/literacy/`
- **Report scheduling:** Cron-based with PDF/CSV export and email delivery — `src/reporting/`
- **Browser extension for Safari:** Xcode project with Swift bridge — `extension/safari/`
- **Vendor risk scoring:** A-F grading across 5 categories — `src/billing/vendor_risk.py`

### Remaining (Deferred)
- **Native mobile apps:** iOS and Android (React Native evaluation pending)
- **Mobile device agent:** Lightweight app to extend DNS proxy coverage to mobile data connections
- **API for third-party integration:** Public API for EdTech platforms (needs partner demand, rate limit tiers, API docs portal)
- **Community Safety Intelligence Network:** Anonymised threat intelligence aggregation (needs legal review, critical user mass)
- **Device agent for network monitoring:** Desktop app for families without router-level access

---

## 16. Open Questions & Assumptions

| # | Question | Assumption Made | Status |
|---|---|---|---|
| OQ-1 | What is the member cap per Family plan? | **5 members** — enforced in `add_member()` and `accept_invitation()` | **Resolved** |
| OQ-2 | What is the student cap per School plan? | No cap — per-seat billing via Stripe quantity | **Resolved** |
| OQ-3 | Will the portal share auth with Bhapi social platform via SSO, or separate login? | Separate login. Google Workspace + Microsoft Entra SSO for schools | **Resolved** |
| OQ-4 | Who is the Data Controller for school/club data — Bhapi or the school/club? | Bhapi as Data Processor, school/club as Controller | Legal review required |
| OQ-5 | Will xAI (Grok) API provide spend/usage data by MVP? | **Yes** — xAI spend tracking implemented (`src/billing/spend_sync.py`) | **Resolved** |
| OQ-6 | What is the browser extension content review timeline for Chrome Web Store? | Approximately 2–4 weeks; factor into launch plan | To schedule |
| OQ-7 | Is there a DPO appointed for the portal? | Must be confirmed prior to DPIA | Open |
| OQ-8 | Does the EU AI Act high-risk classification apply? | **Yes** — EU AI Act compliance module implemented (`src/compliance/`) | **Resolved** |
| OQ-9 | What is the backup/recovery RTO and RPO target? | RTO 4 hours, RPO 1 hour assumed | To confirm with engineering |
| OQ-10 | Will Bhapi act as a COPPA-certified operator? | COPPA certification readiness implemented (`src/compliance/coppa.py`). PRIVO/KidSAFE submission pending | **Partially resolved** |

---

## 17. Glossary

| Term | Definition |
|---|---|
| Bhapi | The parent brand and social safety platform for families, schools, and clubs |
| bhapi.ai | The domain under which both the core Bhapi platform and the AI Governance Portal are delivered |
| Capture Gateway | The ingestion service that receives monitoring signals from all three capture channels |
| COPPA | Children's Online Privacy Protection Act (United States, applies to under-13s) |
| CDIA | Children's Data Impact Assessment (UK ICO requirement) |
| DPIA | Data Protection Impact Assessment (GDPR Article 35 requirement) |
| DNS Proxy | Network-layer monitoring via a managed DNS resolver that logs resolution of AI platform domains |
| Group | A named collection of members (family, class, club) managed by an admin |
| Hard Threshold | A spend or usage limit that triggers a critical alert and admin action flag |
| LLM | Large Language Model (e.g. ChatGPT, Gemini, Copilot, Claude, Grok) |
| LGPD | Lei Geral de Proteção de Dados (Brazil's data protection law) |
| PII | Personally Identifiable Information |
| Risk Engine | The service responsible for classifying AI interactions against the risk taxonomy |
| Risk Event | A structured record produced when an interaction exceeds a risk threshold |
| ROPA | Record of Processing Activities (GDPR compliance documentation) |
| Soft Threshold | A spend or usage limit that triggers an informational alert only |
| SSO | Single Sign-On |
| System Admin | Internal Bhapi staff role with full platform access |

---

*End of Document — Version 2.1 (Updated March 2026)*
*MVP and Post-MVP roadmap substantially complete. See `bhapi-post-mvp-roadmap.md` for feature status.*
