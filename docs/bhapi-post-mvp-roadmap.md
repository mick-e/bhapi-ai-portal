# BHAPI AI Safety Portal — Post-MVP Feature Roadmap

| Field | Value |
|-------|-------|
| **Document** | Post-MVP Roadmap v1.1 |
| **Product** | Bhapi Family AI Governance Portal |
| **Author** | Mike (Head of Technology) |
| **Date** | February 2026 (updated March 2026) |
| **Status** | Active — All phases substantially complete |
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

### 4.1 Tiered Pricing & Plan Management — ✅ COMPLETE

Three pricing tiers (Family, School, Enterprise) with Stripe-managed subscriptions, plan comparison, and public plans endpoint.

**Implemented:**
- 14-day trial system with status tracking and enforcement (`src/billing/trial.py`)
- Trial expiry reminder emails (`src/billing/trial_reminders.py`)
- Subscription enforcement middleware (`src/dependencies.py`)
- Spend sync scheduler for LLM providers (`src/billing/spend_sync.py`)
- Plan tiers with pricing, features, and limits (`src/billing/plans.py`)
- Public plans endpoint `GET /api/v1/billing/plans` (no auth required)
- Plan comparison grid on settings page (Family/School/Enterprise)
- React Query hook for plan data (`portal/src/hooks/use-plans.ts`)

### 4.2 AI Safety Score — ✅ COMPLETE

A composite safety score (0–100) per child summarising their AI usage risk profile.

**Implemented:**
- Risk classifier module with keyword and AI-based detection (`src/risk/classifier.py`)
- Enhanced risk event schemas with severity scoring
- Composite score algorithm with weighted severity, recency decay, logistic normalization (`src/risk/score.py`)
- Score endpoints: `GET /score` (per-member), `GET /score/group` (aggregate), `GET /score/history` (daily trend)
- Score schemas (`src/risk/schemas.py`): SafetyScoreResponse, GroupScoreResponse, ScoreHistoryResponse
- 35 tests (23 unit + 12 E2E)

### 4.3 Weekly Email Digest — ✅ COMPLETE

Automated weekly summary emails to parents/admins.

**Implemented:**
- `run_weekly_digest()` in `src/alerts/digest.py` (7-day window, same pattern as daily)
- Weekly digest job registered in job runner (`src/jobs/runner.py`)
- Digest frequency selector on settings page (immediate/hourly/daily/weekly)
- 5 E2E tests

### 4.4 Deepfake Detection Alerts — ✅ COMPLETE

Detection of AI-generated image/video content in monitored sessions.

**Implemented:**
- Provider abstraction with Hive and Sensity detectors (`src/risk/deepfake_detector.py`)
- `DEEPFAKE_CONTENT` risk category (severity: high) in taxonomy
- Deepfake keyword patterns in classifier
- Layer 1.5 in risk pipeline for media analysis (`src/risk/engine.py`)
- 21 tests (6 unit + 11 emotional dependency + 4 pipeline)

### 4.5 Onboarding Experience — ✅ COMPLETE

**Implemented:**
- Step-by-step onboarding wizard (`portal/src/components/OnboardingWizard.tsx`)
- Extension installation guidance page (`portal/src/app/(dashboard)/extension/page.tsx`)

### Phase 1 Priority Matrix

| Feature | Priority | Effort | Status |
|---------|----------|--------|--------|
| Tiered Pricing & Plans | P0 | 4 weeks | ✅ Complete |
| AI Safety Score | P0 | 3 weeks | ✅ Complete |
| Weekly Email Digest | P1 | 2 weeks | ✅ Complete |
| Deepfake Detection Alerts | P1 | 3 weeks | ✅ Complete |
| Onboarding Experience | P0 | 2 weeks | ✅ Complete |

---

## 5. Phase 2 — School Channel & Differentiation (3–6 Months)

Focus: Unlock the school/education revenue channel and build AI-specific features no competitor offers.

### 5.1 Companion Chatbot Monitoring — ✅ COMPLETE

Detection and monitoring of children forming emotional relationships with AI companions (Character.ai, Replika, Pi, Inflection).

**Implemented:**
- Character.ai DOM adapter (`extension/src/content/platforms/characterai.ts`)
- Replika DOM adapter (`extension/src/content/platforms/replika.ts`)
- Pi by Inflection DOM adapter (`extension/src/content/platforms/pi.ts`)
- Extension manifest updated with content_scripts for all 3 platforms
- `EMOTIONAL_DEPENDENCY` risk category (severity: medium) in taxonomy
- Emotional dependency keyword patterns in classifier

### 5.2 School Admin Dashboard — ✅ COMPLETE

Dedicated school-specific dashboard views with class-level grouping, teacher alerts, and safeguarding lead reports.

**Implemented:**
- ClassGroup and ClassGroupMember models (`src/groups/models.py`)
- School router with 6 endpoints (`src/groups/school_router.py`): class CRUD, member management, risks, safeguarding report
- Alembic migration for class_groups tables (`alembic/versions/008_add_class_groups.py`)
- SIS section-to-class sync (`src/integrations/sis_sync.py`)
- School overview page (`portal/src/app/(dashboard)/school/page.tsx`)
- Class detail page (`portal/src/app/(dashboard)/school/class/page.tsx`)
- 15 E2E tests

### 5.3 Clever & ClassLink SIS Integration — ✅ COMPLETE

**Implemented:**
- Canvas LMS connector (`src/integrations/canvas.py`)
- PowerSchool SIS connector (`src/integrations/powerschool.py`)
- Clever OAuth framework (`src/integrations/clever.py`)
- ClassLink OneRoster framework (`src/integrations/classlink.py`)
- Automated roster provisioning (`src/integrations/sis_sync.py`)
- Enhanced integration router and schemas

### 5.4 Federated SSO (Google Workspace & Entra) — ✅ COMPLETE

**Implemented:**
- Google Workspace SSO framework (`src/integrations/sso_models.py`)
- Microsoft Entra SSO framework
- SSO config CRUD endpoints (POST/PATCH/DELETE /sso)
- Auto-provisioning on SSO login (`src/integrations/sso_provisioner.py`) — respects family cap of 5
- Directory sync from Google Admin SDK and Microsoft Graph API (`src/integrations/directory_sync.py`)
- Daily directory_sync job registered in runner
- 18 tests (8 E2E + 10 unit)

### 5.5 AI Literacy Assessment — ✅ COMPLETE

Educational content and assessment tools for schools.

**Implemented:**
- Full literacy module: models, service, router, schemas (`src/literacy/`)
- 5 seed modules: What is AI, AI Safety, Privacy, Critical Thinking, Responsible Use (`src/literacy/content.py`)
- Endpoints: GET /modules, GET /modules/{id}/questions, POST /assessments, GET /progress/{member_id}, POST /seed
- Alembic migration for 4 tables (`alembic/versions/009_add_literacy_tables.py`)
- Quiz interface page (`portal/src/app/(dashboard)/literacy/page.tsx`)
- React Query hooks (`portal/src/hooks/use-literacy.ts`)
- 18 E2E tests

### Phase 2 Priority Matrix

| Feature | Priority | Effort | Status |
|---------|----------|--------|--------|
| Companion Chatbot Monitoring | P0 | 6 weeks | ✅ Complete |
| School Admin Dashboard | P0 | 6 weeks | ✅ Complete |
| SIS Integration (Clever/ClassLink/Canvas/PowerSchool) | P1 | 4 weeks | ✅ Complete |
| Federated SSO | P1 | 3 weeks | ✅ Complete |
| AI Literacy Assessment | P2 | 4 weeks | ✅ Complete |

---

## 6. Phase 3 — Intelligence & Protection (6–9 Months)

Focus: Move from passive monitoring to active protection. Build the technology moat.

### 6.1 Behaviour Analytics & Patterns — ✅ COMPLETE

Longitudinal behavioural analysis: usage pattern anomaly detection, risk trajectory prediction, peer comparison baselines.

**Implemented:**
- Stddev-based anomaly detection (`src/analytics/service.py`: `detect_anomalies()`)
- Peer comparison with percentile ranks (`get_peer_comparison()`)
- Anomaly and peer comparison endpoints (`src/analytics/router.py`)
- Anomaly alerts and peer comparison tabs on analytics page
- Daily anomaly_check job registered in runner
- 21 tests (11 unit + 10 E2E)

### 6.2 Real-Time Content Blocking — ✅ PARTIALLY COMPLETE

**Implemented:**
- Auto-blocking rules engine with CRUD endpoints (`src/blocking/`)
- Block rules: keyword, category, platform, time-of-day based
- Extension polling endpoint for block list sync
- Blocked page HTML served to users (`extension/src/blocked-page.html`)
- Extension-side blocking script (`extension/src/blocking.js`)
- Comprehensive E2E tests for blocking flows

**Now also implemented:**
- DNS-level blocking with NXDOMAIN + 60s TTL cache (`dns-proxy/src/resolver.py`)
- Parent approval flow: request/approve/deny endpoints (`src/blocking/approval.py`)
- BlockApproval model + migration (`alembic/versions/007_add_block_approvals.py`)
- Block effectiveness analytics (`src/blocking/service.py`: `get_block_effectiveness()`)
- Approval queue and effectiveness UI on blocking page
- 10 E2E tests

### 6.3 Age Verification Integration — ✅ COMPLETE

**Implemented:**
- Yoti age verification integration (`src/integrations/yoti.py`)
- Age verification flow (`src/integrations/age_verification.py`)
- Start/callback endpoints on integrations router
- Dev/test mode support

### 6.4 Mobile Device Agent

Native iOS/Android agent for monitoring AI app usage outside the browser.

**Status:** Not started.

### 6.5 Vendor Risk Scoring — ✅ COMPLETE

AI platform safety ratings based on data retention, content moderation, child safety features, and compliance status.

**Implemented:**
- Static vendor profiles for 5 providers (`src/billing/vendor_profiles.json`)
- Vendor risk scoring with 5 weighted categories, grade A-F system (`src/billing/vendor_risk.py`)
- Public endpoints: `GET /api/v1/billing/vendor-risk`, `GET /api/v1/billing/vendor-risk/{provider}`
- 13 tests (10 unit + 3 E2E)

### Phase 3 Priority Matrix

| Feature | Priority | Effort | Status |
|---------|----------|--------|--------|
| Behaviour Analytics & Patterns | P0 | 8 weeks | ✅ Complete |
| Real-Time Content Blocking | P1 | 6 weeks | ✅ Complete |
| Age Verification Integration | P1 | 3 weeks | ✅ Complete |
| Mobile Device Agent | P0 | 8 weeks | ⬜ Not started (deferred) |
| Vendor Risk Scoring | P2 | 4 weeks | ✅ Complete |

---

## 7. Phase 4 — Scale & Platform (9–12 Months)

Focus: International expansion, platform ecosystem, and positioning for Series A.

### 7.1 Multi-Language Launch — ✅ COMPLETE

Full localisation across 6 languages: English, French, Spanish, German, Portuguese (PT-BR), and Italian.

**Implemented:**
- i18n infrastructure with `useTranslations()` hook
- All 6 translation files complete (`portal/messages/`: en.json, fr.json, es.json, de.json, pt-br.json, it.json)
- Client-side `LocaleContext` with dynamic JSON imports
- `LocaleMiddleware` for server-side locale detection

### 7.2 API for Third-Party Integration

Public API allowing EdTech platforms, school management systems, and child safety tools to consume Bhapi's risk signals.

**Status:** Not started. Internal API well-structured for future exposure.

### 7.3 Safari Browser Extension — ✅ COMPLETE

Extension support for Safari on macOS and iOS.

**Implemented:**
- Xcode project structure (`extension/safari/SafariBhapiExtension/`)
- Swift bridge handler (`SafariWebExtensionHandler.swift`)
- Safari browser API polyfill (`extension/safari/browser-polyfill.js`)
- DeclarativeNetRequest rules (`extension/safari/declarativeNetRequest/rules.json`)
- Build script using `xcrun safari-web-extension-converter` (`extension/safari/convert.sh`)
- `build:safari` npm script

**Note:** Requires macOS + Apple Developer account for testing/signing.

### 7.4 Report Scheduling & Compliance Export — ✅ COMPLETE

Automated scheduled reports for safeguarding leads, governors, and regulatory submissions.

**Implemented:**
- ReportSchedule model with cron expressions
- Scheduled report generation job in job runner
- PDF and CSV export generators (`src/reporting/generators/`)
- Email delivery of scheduled reports
- Report CRUD endpoints with scheduling support

### 7.5 Community Safety Intelligence Network

Opt-in anonymised threat intelligence network aggregating risk signals across users.

**Status:** Not started.

### Phase 4 Priority Matrix

| Feature | Priority | Effort | Status |
|---------|----------|--------|--------|
| Multi-Language Launch (6 langs) | P0 | 8 weeks | ✅ Complete |
| Third-Party API | P1 | 6 weeks | ⬜ Not started (deferred) |
| Safari Extension | P0 | 4 weeks | ✅ Complete |
| Report Scheduling & Export | P1 | 3 weeks | ✅ Complete |
| Community Safety Network | P2 | 8 weeks | ⬜ Not started (deferred) |

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
| 1 | Tiered Pricing | Phase 1 | 4 weeks | — | ✅ Complete |
| 2 | AI Safety Score | Phase 1 | 3 weeks | — | ✅ Complete |
| 3 | Weekly Email Digest | Phase 1 | 2 weeks | — | ✅ Complete |
| 4 | Deepfake Detection | Phase 1 | 3 weeks | — | ✅ Complete |
| 5 | Onboarding Experience | Phase 1 | 2 weeks | — | ✅ Complete |
| 6 | Companion Chatbot Monitoring | Phase 2 | 6 weeks | — | ✅ Complete |
| 7 | School Admin Dashboard | Phase 2 | 6 weeks | — | ✅ Complete |
| 8 | Clever & ClassLink SIS | Phase 2 | 4 weeks | School Dashboard | ✅ Complete |
| 9 | Federated SSO | Phase 2 | 3 weeks | — | ✅ Complete |
| 10 | AI Literacy Assessment | Phase 2 | 4 weeks | School Dashboard | ✅ Complete |
| 11 | Mobile Device Agent | Phase 3 | 8 weeks | — | ⬜ Deferred |
| 12 | Behaviour Analytics | Phase 3 | 8 weeks | 6+ months data | ✅ Complete |
| 13 | Real-Time Content Blocking | Phase 3 | 6 weeks | — | ✅ Complete |
| 14 | Age Verification | Phase 3 | 3 weeks | — | ✅ Complete |
| 15 | Vendor Risk Scoring | Phase 3 | 4 weeks | — | ✅ Complete |
| 16 | Multi-Language Launch | Phase 4 | 8 weeks | — | ✅ Complete |
| 17 | Safari Extension | Phase 4 | 4 weeks | — | ✅ Complete |
| 18 | Third-Party API | Phase 4 | 6 weeks | — | ⬜ Deferred |
| 19 | Report Scheduling | Phase 4 | 3 weeks | School Dashboard | ✅ Complete |
| 20 | Community Safety Network | Phase 4 | 8 weeks | Behaviour Analytics | ⬜ Deferred |

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

**Status as of March 2026:** 17 of 20 roadmap features are now complete. The 3 deferred items (Mobile Device Agent, Third-Party API, Community Safety Network) require separate product efforts or partner demand and are planned for future phases.

**Remaining priorities:**
1. Mobile Device Agent — requires native iOS/Android development (React Native evaluation pending)
2. Third-Party Public API — needs partner demand, separate rate limit tiers, API docs portal
3. Community Safety Network — needs anonymization infrastructure, legal review, critical user mass

The platform now offers comprehensive AI governance capabilities that no competitor matches, with 1,469 passing tests across the full stack (1,314 backend + 60 frontend + 95 production E2E).

---

*End of Document — v1.2 (Updated March 2026)*
