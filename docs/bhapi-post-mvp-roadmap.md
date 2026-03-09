# BHAPI AI Safety Portal — Post-MVP Feature Roadmap

| Field | Value |
|-------|-------|
| **Document** | Post-MVP Roadmap v1.1 |
| **Product** | Bhapi Family AI Governance Portal |
| **Author** | Mike (Head of Technology) |
| **Date** | February 2026 (updated March 2026) |
| **Status** | Active — Phase 1 in progress |
| **Classification** | Confidential |

---

## 1. Executive Summary

The Bhapi AI Safety Portal MVP is complete, delivering the full specification across all three monitoring channels (browser extension, DNS proxy, LLM API integration), the risk and safety engine with PII detection and content classification, LLM spend management, group administration for families and schools/clubs, Stripe billing, and a responsive web portal. This document outlines the prioritised next features across four phases, informed by three factors: the current regulatory acceleration in child online safety, the competitive gap between traditional parental controls and AI-specific governance, and the Bhapi fundraising narrative.

Bhapi occupies a unique position in the market. Existing parental control platforms like Bark, Qustodio, and Norton Family focus on traditional digital risks: social media monitoring, web filtering, screen time, and location tracking. None of them specifically address AI tool governance, which is the fastest-growing category of child-technology interaction. Research published for Safer Internet Day 2026 shows that 97% of young people aged 8 to 17 have used AI in some form, and 41% of teens feel their peers are relying heavily on AI for emotional support. This is the gap Bhapi fills.

---

## 2. MVP Delivered — Baseline

| Domain | Shipped Capability |
|--------|-------------------|
| Portal & Auth | Registration, login, family/school/club group management, member invitations, parental consent flows, role-based access |
| Browser Extension | Chrome and Firefox extension with DOM monitoring across ChatGPT, Gemini, Copilot, Claude, Grok |
| DNS Proxy | Bhapi DNS resolver logging AI platform access, device attribution, guided router setup |
| LLM API Integration | Provider API/webhook connections for usage and spend data from supported platforms |
| Risk Engine | Google Cloud DLP for PII detection, Vertex AI safety LLM for content classification, structured risk taxonomy |
| Alerting | Real-time admin notifications for flagged interactions with severity levels |
| Dashboard | Activity feed, risk event log, flagged content review with approve/escalate workflow |
| LLM Spend Management | Per-member and per-platform spend tracking, soft/hard thresholds, monthly budget caps |
| Billing | Stripe integration, single-tier monthly/annual, 14-day free trial, Stripe Customer Portal |
| Compliance | GDPR, COPPA, UK Online Safety Act, Australia Online Safety Act, Brazil LGPD foundations |

---

## 3. Strategic Context — Why These Features, Why Now

### 3.1 Regulatory Tailwinds

The regulatory environment for child online safety is intensifying rapidly across every jurisdiction Bhapi targets:

- **UK**: Duties under the Online Safety Act to assess and mitigate risks to minors became applicable in July 2025, with Ofcom's supercomplaint regime coming into force at the end of 2025.
- **US**: The Take It Down Act (May 2025) targets AI-generated deepfakes and non-consensual intimate imagery. California is advancing a Child AI Safety Audit Mandate requiring risk classification of AI products accessible to children.
- **Australia**: Under-16 social media ban creates immediate demand for age-appropriate AI governance tooling.
- **Brazil**: ECA Digital Law now requires age verification technology rather than self-declared ages.
- **EU**: AI Act classifies AI systems used in education and safety of persons as high-risk under Annex III, directly applicable to Bhapi's monitoring engine.

Every one of these regulatory developments creates a buying trigger for schools and families.

### 3.2 Competitive Gap

The major parental control platforms (Bark, Qustodio, Norton Family, Canopy) remain focused on traditional digital risks. None offer AI-specific governance capabilities: monitoring which LLMs children use, what they ask, whether they share PII with AI systems, how much they spend on AI subscriptions, or whether AI responses contain harmful content.

---

## 4. Phase 1 — Engagement & Conversion (0–3 Months)

Focus: Maximise free-to-paid conversion, deepen daily engagement, and build PR-worthy safety features.

### 4.1 Tiered Pricing & Plan Management — ✅ PARTIALLY COMPLETE

Three pricing tiers (Family, School Starter, School Pro) with Stripe-managed subscriptions, plan comparison page, and upgrade/downgrade flows.

**Implemented:**
- 14-day trial system with status tracking and enforcement (`src/billing/trial.py`)
- Trial expiry reminder emails (`src/billing/trial_reminders.py`)
- Subscription enforcement middleware (`src/dependencies.py`)
- Spend sync scheduler for LLM providers (`src/billing/spend_sync.py`)

**Remaining:**
- Plan comparison landing page
- Upgrade/downgrade self-service flows
- Annual discount implementation

### 4.2 AI Safety Score — ✅ PARTIALLY COMPLETE

A composite safety score (0–100) per child summarising their AI usage risk profile.

**Implemented:**
- Risk classifier module with keyword and AI-based detection (`src/risk/classifier.py`)
- Enhanced risk event schemas with severity scoring

**Remaining:**
- Composite score calculation algorithm
- Score display on dashboard and member profiles
- Score trend tracking over time

### 4.3 Weekly Email Digest

Automated weekly summary emails to parents/admins.

**Status:** Email templates infrastructure ready (`src/email/templates.py` enhanced). Scheduling logic needed.

### 4.4 Deepfake Detection Alerts

Detection of AI-generated image/video content in monitored sessions.

**Status:** Not started. Requires integration with deepfake detection API (e.g., Sensity, Hive Moderation).

### 4.5 Onboarding Experience — ✅ COMPLETE

**Implemented:**
- Step-by-step onboarding wizard (`portal/src/components/OnboardingWizard.tsx`)
- Extension installation guidance page (`portal/src/app/(dashboard)/extension/page.tsx`)

### Phase 1 Priority Matrix

| Feature | Priority | Effort | Status |
|---------|----------|--------|--------|
| Tiered Pricing & Plans | P0 | 4 weeks | 🟡 Partial |
| AI Safety Score | P0 | 3 weeks | 🟡 Partial |
| Weekly Email Digest | P1 | 2 weeks | ⬜ Not started |
| Deepfake Detection Alerts | P1 | 3 weeks | ⬜ Not started |
| Onboarding Experience | P0 | 2 weeks | ✅ Complete |

---

## 5. Phase 2 — School Channel & Differentiation (3–6 Months)

Focus: Unlock the school/education revenue channel and build AI-specific features no competitor offers.

### 5.1 Companion Chatbot Monitoring

Detection and monitoring of children forming emotional relationships with AI companions (Character.ai, Replika, Pi, Inflection).

**Status:** Not started.

### 5.2 School Admin Dashboard

Dedicated school-specific dashboard views with class-level grouping, teacher alerts, and safeguarding lead reports.

**Status:** Not started.

### 5.3 Clever & ClassLink SIS Integration — ✅ PARTIALLY COMPLETE

**Implemented:**
- Canvas LMS connector (`src/integrations/canvas.py`)
- PowerSchool SIS connector (`src/integrations/powerschool.py`)
- Enhanced integration router and schemas

**Remaining:**
- Clever OAuth flow (framework ready, credentials needed)
- ClassLink OneRoster sync
- Automated roster provisioning

### 5.4 Federated SSO (Google Workspace & Entra)

**Status:** Framework ready in auth module. Requires OAuth credentials.

### 5.5 AI Literacy Assessment

Educational content and assessment tools for schools.

**Status:** Not started.

### Phase 2 Priority Matrix

| Feature | Priority | Effort | Status |
|---------|----------|--------|--------|
| Companion Chatbot Monitoring | P0 | 6 weeks | ⬜ Not started |
| School Admin Dashboard | P0 | 6 weeks | ⬜ Not started |
| SIS Integration (Clever/ClassLink/Canvas/PowerSchool) | P1 | 4 weeks | 🟡 Partial |
| Federated SSO | P1 | 3 weeks | 🟡 Framework ready |
| AI Literacy Assessment | P2 | 4 weeks | ⬜ Not started |

---

## 6. Phase 3 — Intelligence & Protection (6–9 Months)

Focus: Move from passive monitoring to active protection. Build the technology moat.

### 6.1 Behaviour Analytics & Patterns

Longitudinal behavioural analysis: usage pattern anomaly detection, risk trajectory prediction, peer comparison baselines.

**Status:** Analytics module exists with basic trends (`src/analytics/`). Advanced ML pipeline not started.

### 6.2 Real-Time Content Blocking — ✅ PARTIALLY COMPLETE

**Implemented:**
- Auto-blocking rules engine with CRUD endpoints (`src/blocking/`)
- Block rules: keyword, category, platform, time-of-day based
- Extension polling endpoint for block list sync
- Blocked page HTML served to users (`extension/src/blocked-page.html`)
- Extension-side blocking script (`extension/src/blocking.js`)
- Comprehensive E2E tests for blocking flows

**Remaining:**
- DNS-level blocking integration
- Block override with parent approval flow
- Block effectiveness analytics

### 6.3 Age Verification Integration

**Status:** Yoti integration framework exists. Credentials needed.

### 6.4 Mobile Device Agent

Native iOS/Android agent for monitoring AI app usage outside the browser.

**Status:** Not started.

### 6.5 Vendor Risk Scoring

AI platform safety ratings based on data retention, content moderation, child safety features, and compliance status.

**Status:** Not started. Could leverage Littledata AI risk methodology.

### Phase 3 Priority Matrix

| Feature | Priority | Effort | Status |
|---------|----------|--------|--------|
| Behaviour Analytics & Patterns | P0 | 8 weeks | 🟡 Basic analytics exists |
| Real-Time Content Blocking | P1 | 6 weeks | 🟡 Partial (rules + extension done) |
| Age Verification Integration | P1 | 3 weeks | 🟡 Framework ready |
| Mobile Device Agent | P0 | 8 weeks | ⬜ Not started |
| Vendor Risk Scoring | P2 | 4 weeks | ⬜ Not started |

---

## 7. Phase 4 — Scale & Platform (9–12 Months)

Focus: International expansion, platform ecosystem, and positioning for Series A.

### 7.1 Multi-Language Launch

Full localisation across 6 languages: French, Spanish, German, Portuguese (PT-PT and PT-BR), and Italian.

**Status:** i18n infrastructure complete (6 language files in `portal/messages/`). Translation content needed.

### 7.2 API for Third-Party Integration

Public API allowing EdTech platforms, school management systems, and child safety tools to consume Bhapi's risk signals.

**Status:** Not started. Internal API well-structured for future exposure.

### 7.3 Safari Browser Extension

Extension support for Safari on macOS and iOS.

**Status:** Safari scaffold exists in `extension/`. Requires Apple Developer entitlements.

### 7.4 Report Scheduling & Compliance Export

Automated scheduled reports for safeguarding leads, governors, and regulatory submissions.

**Status:** Reporting module exists with PDF/CSV generation. Scheduling not implemented.

### 7.5 Community Safety Intelligence Network

Opt-in anonymised threat intelligence network aggregating risk signals across users.

**Status:** Not started.

### Phase 4 Priority Matrix

| Feature | Priority | Effort | Status |
|---------|----------|--------|--------|
| Multi-Language Launch (6 langs) | P0 | 8 weeks | 🟡 Infrastructure ready |
| Third-Party API | P1 | 6 weeks | ⬜ Not started |
| Safari Extension | P0 | 4 weeks | 🟡 Scaffold exists |
| Report Scheduling & Export | P1 | 3 weeks | 🟡 PDF/CSV generation done |
| Community Safety Network | P2 | 8 weeks | ⬜ Not started |

---

## 8. Competitive Feature Matrix — Post-Roadmap

| Capability | Bhapi (Post-Roadmap) | Bark | Qustodio | Norton Family |
|-----------|---------------------|------|----------|---------------|
| AI/LLM usage monitoring | ✅ | ❌ | ❌ | ❌ |
| AI content classification | ✅ | ❌ | ❌ | ❌ |
| LLM spend management | ✅ | ❌ | ❌ | ❌ |
| PII leak detection | ✅ | ❌ | ❌ | ❌ |
| Real-time AI blocking | ✅ | ❌ | ❌ | ❌ |
| Deepfake detection | ✅ | ❌ | ❌ | ❌ |
| Companion chatbot monitoring | ✅ | ❌ | ❌ | ❌ |
| AI Safety Score | ✅ | ❌ | ❌ | ❌ |
| Behaviour analytics | ✅ | Partial | Partial | ❌ |
| School admin dashboard | ✅ | ✅ | ✅ | ❌ |
| SIS integration | ✅ | ✅ | ❌ | ❌ |
| Web filtering | ❌ | ✅ | ✅ | ✅ |
| Social media monitoring | ❌ | ✅ | ❌ | ❌ |
| Screen time management | ❌ | ✅ | ✅ | ✅ |
| Location tracking | ❌ | ✅ | ✅ | ✅ |
| Multi-language | ✅ (6) | 2 | 8 | 4 |

---

## 9. Feature Dependency Map

| # | Feature | Phase | Effort | Depends On | Status |
|---|---------|-------|--------|------------|--------|
| 1 | Tiered Pricing | Phase 1 | 4 weeks | — | 🟡 Partial |
| 2 | AI Safety Score | Phase 1 | 3 weeks | — | 🟡 Partial |
| 3 | Weekly Email Digest | Phase 1 | 2 weeks | — | ⬜ |
| 4 | Deepfake Detection | Phase 1 | 3 weeks | — | ⬜ |
| 5 | Onboarding Experience | Phase 1 | 2 weeks | — | ✅ Complete |
| 6 | Companion Chatbot Monitoring | Phase 2 | 6 weeks | — | ⬜ |
| 7 | School Admin Dashboard | Phase 2 | 6 weeks | — | ⬜ |
| 8 | Clever & ClassLink SIS | Phase 2 | 4 weeks | School Dashboard | 🟡 Partial |
| 9 | Federated SSO | Phase 2 | 3 weeks | — | 🟡 Framework |
| 10 | AI Literacy Assessment | Phase 2 | 4 weeks | School Dashboard | ⬜ |
| 11 | Mobile Device Agent | Phase 3 | 8 weeks | — | ⬜ |
| 12 | Behaviour Analytics | Phase 3 | 8 weeks | 6+ months data | 🟡 Basic |
| 13 | Real-Time Content Blocking | Phase 3 | 6 weeks | — | 🟡 Partial |
| 14 | Age Verification | Phase 3 | 3 weeks | — | 🟡 Framework |
| 15 | Vendor Risk Scoring | Phase 3 | 4 weeks | — | ⬜ |
| 16 | Multi-Language Launch | Phase 4 | 8 weeks | — | 🟡 Infra ready |
| 17 | Safari Extension | Phase 4 | 4 weeks | — | 🟡 Scaffold |
| 18 | Third-Party API | Phase 4 | 6 weeks | — | ⬜ |
| 19 | Report Scheduling | Phase 4 | 3 weeks | School Dashboard | 🟡 PDF/CSV done |
| 20 | Community Safety Network | Phase 4 | 8 weeks | Behaviour Analytics | ⬜ |

---

## 10. Success Metrics by Phase

| Phase | Timeline | Key Metrics | Target |
|-------|----------|-------------|--------|
| Phase 1 | 0–3 months | DAU/MAU ratio, free-to-paid conversion, weekly digest open rate, AI Safety Score adoption | DAU/MAU > 25%, conversion > 5% |
| Phase 2 | 3–6 months | Schools onboarded, students per school, school plan ARPU, companion chatbot detection rate | 50+ schools, avg 300 students |
| Phase 3 | 6–9 months | Mobile coverage %, prediction accuracy, blocking policy adoption, age verification rate | Mobile coverage > 60% |
| Phase 4 | 9–12 months | Non-English users %, API partners, threat intel contributions, NPS by market | Non-English > 30% of users |

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Browser extension store rejection delays | Delays Phase 1 deepfake detection and Phase 4 Safari launch | Submit early, maintain minimal permissions, build relationship with Chrome/Apple review teams |
| LLM platforms change DOM structure | Breaks browser extension monitoring | Automated DOM change detection, rapid hotfix pipeline, abstract monitoring layer |
| School procurement cycles (6–12 months) | Slow Phase 2 revenue recognition | Target pilot programmes, free tier for teachers, build case studies during trial |
| Age verification provider costs | Increases per-user cost and onboarding friction | Negotiate volume pricing, make verification optional until regulation mandates it |
| Regulatory fragmentation across jurisdictions | Increases compliance engineering burden | Modular compliance engine with per-jurisdiction rule sets |
| Competitor entry into AI monitoring | Bark or Qustodio add basic AI monitoring | First-mover depth advantage: longitudinal analytics and safety intelligence network cannot be replicated quickly |

---

## 12. Conclusion & Recommendation

The Bhapi AI Safety Portal MVP has established a strong technical foundation across monitoring, risk classification, and governance. Post-MVP development has already begun with progress on auto-blocking rules, trial billing, risk classification, SIS integrations (Canvas/PowerSchool), onboarding, and SSE alert streaming.

**Immediate priorities:**
1. Complete Phase 1 tiered pricing (plan comparison page, upgrade/downgrade flows)
2. Finish AI Safety Score (composite algorithm, dashboard display)
3. Ship weekly email digest
4. Complete content blocking (DNS integration, parent approval override)

The competitive window is now. No major parental control platform has moved into AI governance. Every month of delay is a month that Bark, Qustodio, or a new entrant could announce an AI monitoring feature. First-mover advantage in this category is substantial because the data flywheel (more users, more threat intelligence, better detection) compounds over time.

---

*End of Document — v1.1 (Updated March 2026)*
