# Bhapi Platform — Phase 1 Hiring Plan

**Date:** March 19, 2026
**Target:** 5-7 engineers by May 2026
**Current team:** 2-3 engineers
**Hiring gap:** 3-4 new roles

---

## Context

Phase 1 (May–June 2026) is the foundational build for Bhapi's unified platform. The team will ship two Expo mobile apps (Bhapi Safety for parents, Bhapi Social for children ages 5–15) in a single monorepo, extend the FastAPI backend with 10 new modules, stand up a WebSocket real-time service, build a pre-publish content moderation pipeline (including CSAM detection), and execute school market entry with Chromebook deployment and Ohio AI governance compliance.

This document defines the 4 roles needed to bridge from the current team to Phase 1 delivery.

---

## Roles

---

### 1. Senior Mobile Engineer (Expo/React Native) — 2 positions

#### Responsibilities

- Build and maintain Bhapi Safety (parent-facing) and Bhapi Social (child-facing, ages 5–15) as separate Expo apps in a shared monorepo under `mobile/`
- Develop shared packages: auth, API client, UI component library, shared hooks
- Implement real-time messaging via WebSocket client with reconnection handling and offline queue
- Integrate push notifications (Expo Push, APNs, FCM) for alerts, moderation events, and activity summaries
- Design and implement age-tier UX (distinct interaction patterns and content for 5–9, 10–12, 13–15 cohorts)
- Write unit and integration tests; maintain high coverage on critical flows

#### Required Skills

- 3+ years of production React Native or Expo development
- Strong TypeScript — strict mode, discriminated unions, typed API layers
- Turborepo or comparable monorepo tooling (Nx, Yarn workspaces)
- End-to-end App Store and Google Play deployment including review cycle management
- Real-time messaging implementation (WebSocket, socket.io, or similar)
- Proficiency with Jest and React Native Testing Library

#### Nice to Have

- Prior experience building apps for children or regulated audiences
- COPPA, GDPR-K, or children's privacy awareness
- Accessibility: VoiceOver (iOS) and TalkBack (Android)
- Internationalization (i18n) with react-i18next or expo-localization
- Reanimated 3 and Gesture Handler for custom animation and interaction work

#### Compensation

- **Range:** $140,000–$175,000 USD base (dependent on experience and location)
- Equity considered for exceptional candidates
- Remote-first; US or Canada preferred for timezone overlap

#### Location & Start Date

- **Location:** Remote (US/Canada preferred; EU considered for strong fits)
- **Start date:** May 5, 2026 (or sooner)

---

### 2. Senior Backend Engineer (Python/FastAPI) — 1-2 positions

#### Responsibilities

- Build the Phase 1 social modules: feed, messaging, contacts, friend requests, and moderation queues
- Stand up and maintain the WebSocket real-time service for chat and live notifications
- Integrate Cloudflare R2 (media storage), Cloudflare Images (image transforms), and Cloudflare Stream (video) into the upload and delivery pipeline
- Author and review Alembic migrations; maintain schema quality on PostgreSQL
- Build the pre-publish content moderation pipeline: hook into message submission, run classifiers, enforce under-13 blocking rules
- Write comprehensive pytest coverage for all new modules; participate in code review

#### Required Skills

- 3+ years Python in production backend services
- FastAPI or comparable async Python framework (Starlette, Litestar)
- SQLAlchemy async with PostgreSQL
- WebSocket server development (native asyncio, or starlette WebSocket)
- REST API design: versioning, pagination, error contracts
- pytest with async fixtures

#### Nice to Have

- Prior work on content moderation or trust and safety systems
- Redis pub/sub for fan-out messaging
- Cloudflare Workers, R2, or Images/Stream API
- Experience building platforms for children or sensitive audiences
- COPPA compliance implementation

#### Compensation

- **Range:** $135,000–$170,000 USD base
- Equity considered for exceptional candidates

#### Location & Start Date

- **Location:** Remote (US/Canada preferred)
- **Start date:** May 5, 2026 (or sooner)

---

### 3. Safety/ML Engineer — 1 position

#### Responsibilities

- Own the content moderation ML pipeline: train, evaluate, and deploy text classifiers for grooming detection, cyberbullying, sexting, and manipulation patterns
- Integrate CSAM detection via PhotoDNA or equivalent perceptual hashing; maintain NCMEC reporting workflow
- Build social-specific risk models that extend the existing 14-category taxonomy with social interaction signals (contact patterns, escalation velocity, sentiment drift)
- Optimize the keyword classifier: maintain category dictionaries, tune thresholds, reduce false positive rates on age-appropriate content
- Analyze false positive and false negative rates; build dashboards for moderation SLA monitoring
- Coordinate with the backend team on pipeline hooks and latency budgets

#### Required Skills

- 3+ years in ML/NLP with production model deployment
- Text classification: fine-tuning, transformer models, evaluation methodology
- Image classification experience (CNNs, vision transformers, or API-based)
- Python (PyTorch or TensorFlow; scikit-learn for classical methods)
- Prior work in content moderation, trust and safety, or online harm prevention

#### Nice to Have

- PhotoDNA or perceptual hashing (pHash, FAISS-based similarity search)
- Children's safety domain knowledge
- Hive Moderation or Sensity API integration experience
- Google Cloud Vision AI or AWS Rekognition
- Adversarial testing and red-teaming for safety classifiers

#### Compensation

- **Range:** $145,000–$185,000 USD base (safety/ML roles carry a market premium)
- Equity package

#### Location & Start Date

- **Location:** Remote (global; strong US/EU candidate pool expected)
- **Start date:** May 5, 2026 (can flex to April for an exceptional fit)

---

### 4. DevOps/Security Engineer — 1 position (can be fractional or contract)

#### Responsibilities

- Design and maintain CI/CD for the full monorepo: backend (pytest, Docker), mobile (Expo EAS Build), and portal (Next.js)
- Optimize Render deployment configuration: zero-downtime deploys, cron job reliability, environment promotion
- Security hardening: dependency scanning, secret rotation, OWASP top-10 audit, penetration testing coordination
- Build and maintain CSAM evidence preservation infrastructure: encrypted storage, chain-of-custody logs, NCMEC submission pipeline
- Set up monitoring and alerting: moderation SLA dashboards, uptime, error rate thresholds, WebSocket connection health

#### Required Skills

- 2+ years DevOps or platform engineering
- GitHub Actions: matrix builds, reusable workflows, secrets management
- Docker: multi-stage builds, image hardening
- Security best practices: OWASP, CVE triage, least-privilege IAM
- Monitoring and alerting setup (Datadog, Grafana, or similar)

#### Nice to Have

- Render platform expertise
- Expo EAS Build and submit pipelines
- Cloudflare: WAF rules, R2 lifecycle policies, Workers deployment
- SOC 2 Type II preparation
- Children's platform compliance (COPPA, CIPA)

#### Compensation

- **Range:** $120,000–$155,000 USD base (full-time) or $85–$120/hour (contract)
- Contract engagement minimum 3 months with full-time conversion path

#### Location & Start Date

- **Location:** Remote (US preferred for compliance/legal timezone overlap)
- **Start date:** April 21, 2026 (earlier than other roles to prepare CI/CD before mobile/backend engineers join)

---

## Interview Process

All roles follow a four-stage process targeting a two-week cycle from first contact to offer.

### Stage 1 — Technical Screen (45 min, async-first option)

- 30 min conversation with a founding engineer
- Assess communication clarity, system-level thinking, and baseline technical fit
- For Safety/ML: discuss a past moderation or classification project in depth
- For Mobile: discuss a challenging real-time or performance problem they solved
- Pass/fail decision within 24 hours

### Stage 2 — Take-Home Assignment (3–4 hours)

- Mobile: extend a small Expo monorepo with a shared component and a WebSocket hook; write tests
- Backend: implement a FastAPI endpoint with async SQLAlchemy, a WebSocket handler, and pytest coverage
- Safety/ML: analyze a provided dataset of synthetic messages; propose a classifier approach; document false positive tradeoffs
- DevOps: write a GitHub Actions workflow for the monorepo; identify a security misconfiguration in a provided Dockerfile
- Reviewed by two engineers; written feedback provided to every candidate regardless of outcome

### Stage 3 — System Design Interview (60 min, live)

- Mobile: design the age-tier content feed architecture across Safety and Social apps
- Backend: design the pre-publish moderation pipeline for under-13 messages at scale
- Safety/ML: design a grooming detection system with latency, recall, and privacy constraints
- DevOps: design the CSAM evidence preservation and reporting infrastructure
- Evaluated on: problem decomposition, tradeoff articulation, safety and privacy awareness

### Stage 4 — Culture Fit & Mission Alignment (30 min)

- Conversation with a founder or team lead
- Discuss motivation for working on children's safety
- Explore working style, async communication preference, and how they handle ambiguity
- No trick questions; genuine two-way conversation

---

## Hiring Timeline

| Week | Activity |
|------|----------|
| Week 1 (Mar 23) | Finalize job descriptions; open roles on all platforms |
| Week 2 (Mar 30) | Begin technical screens for first applicants |
| Week 3 (Apr 6) | Send take-home assignments; complete screens for backlog |
| Week 4 (Apr 13) | System design interviews; culture fit calls begin |
| Week 5 (Apr 20) | Extend offers; begin reference checks |
| Week 6 (Apr 27) | Offers accepted; hardware/access provisioning starts |
| Week 7 (May 5) | Day 1 for all Phase 1 hires |

DevOps/Security role is posted and screened one week earlier (week 0) to hit the April 21 start date.

---

## Onboarding Plan

### Day 1

- CLAUDE.md orientation: project conventions, code style, commit message format, test expectations
- Environment setup: clone repos, configure `.env`, run backend tests (`pytest`), run portal (`npm run dev`)
- Meet the team: async intro, Slack workspace tour, GitHub org access

### Days 2–3 — Codebase Tour

- Backend: walk through `src/main.py` router structure, module layout, auth flow, database patterns
- Mobile (when `mobile/` exists): monorepo structure, shared packages, Expo config, EAS setup
- Safety/ML: risk pipeline, consent-gated flow, keyword classifier, existing moderation integrations
- DevOps: `render.yaml`, GitHub Actions workflows, Docker builds, environment promotion

### Day 3 — First PR

- Every new hire ships a meaningful first PR within 72 hours of day 1
- Suggested first tasks are pre-scoped and documented in the onboarding issue template
- Reviewed same-day with constructive written feedback
- Merged before end of week 1

### Week 2 — Ramp

- Attend first architecture sync; contribute to Phase 1 planning board
- Take ownership of one module or component with a defined deliverable for week 3
- Shadow one moderation review session (Safety/ML and Backend roles)

---

## Where to Post

| Channel | Roles | Notes |
|---------|-------|-------|
| LinkedIn Jobs | All | Sponsored posts for Senior Mobile and Safety/ML |
| Hacker News — Who's Hiring (Apr 1 thread) | Backend, DevOps, Safety/ML | Plain-text post; link to full JD |
| React Native Community (Discord, GitHub Discussions) | Mobile | Direct outreach to active contributors |
| Python Discord / FastAPI GitHub Discussions | Backend | Post in `#jobs` channels |
| Hugging Face Jobs | Safety/ML | Strong ML/NLP audience |
| Trust & Safety Professional Association (TSPA) | Safety/ML | Niche but highly qualified pool |
| Expo Discord | Mobile | Target engineers shipping production Expo apps |
| Wellfound (AngelList) | All | Startup-focused; highlight mission and equity |
| Refer.me / internal referrals | All | $2,000 referral bonus for successful 90-day hires |

---

## Notes for Reviewers

- Compensation ranges reflect US market rates for 2026; adjust for EU/Canada candidates based on local benchmarks
- All roles are remote-first; the team operates async with two weekly syncs (Tuesday architecture + Thursday demo)
- Children's safety mission is a meaningful filter — candidates who are drawn to the problem space perform better and retain longer; assess genuine motivation in Stage 4
- The Safety/ML role is the highest-risk hire (specialized domain + small candidate pool); consider parallel outreach to ML contractors as a fallback if the search extends past week 4
