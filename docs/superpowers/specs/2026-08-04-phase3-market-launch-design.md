# Phase 3: Competitive Parity + Market Launch — Design Specification

> **Version:** 1.0
> **Date:** 2026-03-22
> **Status:** Draft
> **Timeline:** Weeks 21-26 (Aug 4 — Sep 17, 2026)
> **Team:** 10-13 engineers
> **Budget:** 60-78 person-weeks
> **Prerequisite:** Phase 2 exit criteria met (v3.0.0+, 3,854+ backend tests passing)

## 1. Goal

Bring both Bhapi apps to public release on iOS and Android, ship the cross-product intelligence engine that no competitor can replicate, add location tracking and screen time management for the Family+ tier, launch creative tools for children, open a B2B API for school and EdTech partners, and establish bundle pricing with a conversion-optimized free tier. Initiate SOC 2 Type II audit process.

## 2. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | Full spec — all 17 deliverables | Maximize competitive position before GoGuardian closes AI monitoring gap in Q4 2026 |
| Execution approach | Foundation → Features → Launch (3 layers) | Backend foundations first, features build on them, launch is final polish. Compatible with subagent-driven development |
| Location tracking | Tiered visibility — parent full + school check-in | Competitive parity with Life360/Bark + school attendance value. Kill switch, audit log, opt-in per school |
| Creative tools | Full suite — AI art, stories, drawing, stickers | Differentiation for kids — no competitor has moderated creative tools in a safety app |
| Free tier | Minimal — 1 child, extension only, weekly email | "Awareness only" — shows AI usage exists, upsells detail. No dashboard, no alerts, no apps |
| API pricing | B2B only — no free tier | School (included), Partner ($99/mo), Enterprise (custom). Supports partnership channel, not playground |
| API target | Schools + EdTech platforms | Maximize partnership opportunity — MDM vendors, LMS providers, resellers |
| Onboarding | Three paths | Parent-initiated, child-initiated, school-initiated — all converge to same family group state |

## 3. Execution Layers

### Layer 1: Foundation (Weeks 21-23)
Backend-heavy infrastructure that doesn't need public apps.

| ID | Deliverable | Layer |
|----|------------|-------|
| P3-I1 | Intelligence module: event bus + correlation rules | Foundation |
| P3-I2 | Unified risk scoring: weighted signals, confidence, trends | Foundation |
| P3-B1 | Bundle pricing: Free/Family/Family+/School/Enterprise | Foundation |
| P3-B3 | Public API: OAuth 2.0, tiers, webhook delivery, docs | Foundation |
| P3-F3 | Location infrastructure: tracking, geofencing, school check-in | Foundation |
| P3-F2 | Screen time: per-app limits, schedules, extension requests | Foundation |

### Layer 2: Features (Weeks 24-25)
Features built on foundation layer, user-facing but not yet public.

| ID | Deliverable | Layer |
|----|------------|-------|
| P3-F1 | Creative tools: AI art, stories, drawing, stickers | Features |
| P3-F4 | Unified parent dashboard: combined AI + social + location + screen time | Features |
| P3-I3 | Alert enrichment: correlated cross-product context | Features |
| P3-I4 | Behavioral anomaly correlation: evasion detection | Features |
| P3-B2 | Channel partnership package: collateral, ROI calculator, deployment guide | Features |
| P3-B4 | SOC 2 Type II audit initiation: policy docs, evidence collection | Features |

### Layer 3: Launch (Week 26)
Everything built and tested before going public.

| ID | Deliverable | Layer |
|----|------------|-------|
| P3-L1 | Bhapi Social — App Store + Google Play public release | Launch |
| P3-L2 | Bhapi Safety — App Store + Google Play public release | Launch |
| P3-L3 | App Store optimization: screenshots, descriptions, keywords (6 languages) | Launch |
| P3-L4 | Landing page: unified marketing at bhapi.ai | Launch |
| P3-L5 | Cross-app onboarding: 3 paths (parent, child, school initiated) | Launch |

## 4. Dependency Graph

```
LAYER 1: FOUNDATION (Weeks 21-23)
  P3-I1: Intelligence event bus + correlation rules ────────┐
  P3-I2: Unified risk scoring ──────────────────────────────┤
  P3-B1: Bundle pricing + feature gating ───────────────────┤
  P3-B3: Public API (OAuth, tiers, webhooks) ───────────────┤
  P3-F3: Location (tracking, geofencing, school check-in) ─┤
  P3-F2: Screen time (limits, schedules, enforcement) ─────┘
       │
       ▼
LAYER 2: FEATURES (Weeks 24-25)
  P3-F1: Creative tools (art, stories, drawing, stickers) ─┐
  P3-F4: Unified dashboard (depends on I1, I2, F2, F3) ────┤
  P3-I3: Alert enrichment (depends on I1, I2) ─────────────┤
  P3-I4: Anomaly correlation (depends on I1, I2) ──────────┤
  P3-B2: Channel partnership package ──────────────────────┤
  P3-B4: SOC 2 audit initiation ──────────────────────────┘
       │
       ▼
LAYER 3: LAUNCH (Week 26)
  P3-L1: Social app public release ────────────────────────┐
  P3-L2: Safety app public release ────────────────────────┤
  P3-L3: App Store optimization ───────────────────────────┤
  P3-L4: Landing page redesign ────────────────────────────┤
  P3-L5: Cross-app onboarding (depends on L1, L2) ────────┘
```

**Cross-layer dependencies:**
- P3-F4 (unified dashboard) depends on P3-I1/I2 (intelligence), P3-F2 (screen time), P3-F3 (location)
- P3-I3/I4 (alert enrichment, anomaly) depend on P3-I1/I2 (event bus, scoring)
- P3-L5 (onboarding) depends on P3-L1/L2 (apps being submittable)
- P3-F1 (creative tools) depends on P3-B1 (feature gating for Family+ tier)
- P3-B3 (API) is independent — can be built in parallel with all Layer 1 tasks

**Serialization points:**
- Tasks creating new modules (location, screen_time, creative, api_platform) each modify `src/main.py` and `alembic/env.py` — must be sequenced or use worktrees
- P3-B1 (pricing) modifies `src/billing/` which is shared — serialize with other billing changes

## 5. Architecture

### 5.1 New Backend Modules

#### `src/location/` — Location Tracking + Geofencing

```
src/location/
  __init__.py          # Public interface
  router.py            # /api/v1/location endpoints
  service.py           # Tracking, geofencing, school check-in, kill switch
  models.py            # LocationRecord, Geofence, GeofenceEvent, SchoolCheckIn,
                       #   LocationSharingConsent, LocationKillSwitch, LocationAuditLog
  schemas.py           # Pydantic schemas
```

**Endpoints:**
- `POST /api/v1/location/report` — Device agent reports location (batch, signed)
- `GET /api/v1/location/{child_id}/current` — Parent: latest location
- `GET /api/v1/location/{child_id}/history` — Parent: 30-day history (paginated)
- `POST /api/v1/location/geofences` — Parent: create geofence (max 10 per child)
- `GET /api/v1/location/geofences` — Parent: list geofences
- `DELETE /api/v1/location/geofences/{id}` — Parent: remove geofence
- `GET /api/v1/location/{child_id}/checkins` — School admin: check-in/check-out records
- `POST /api/v1/location/{child_id}/kill-switch` — Parent: disable all tracking immediately
- `DELETE /api/v1/location/{child_id}/history` — Parent: purge all location data
- `GET /api/v1/location/{child_id}/audit-log` — Parent: who accessed location data

**Privacy model:**
- Kill switch: `LocationKillSwitch` table — when active, device agent stops collecting, API returns 204 No Content for location queries, existing data remains until explicit delete
- Audit log: every read of location data (parent or school admin) creates a `LocationAuditLog` entry with accessor_id, data_type, timestamp
- School consent: `LocationSharingConsent` — per-child, per-school opt-in. Parent creates in Safety app. Revocable anytime. School admin cannot request — parent must initiate
- COPPA: children <13 require existing FamilyAgreement + explicit `location_consent` field (separate checkbox)
- GDPR erasure: `DELETE /api/v1/location/{child_id}/history` purges all records including school check-ins within 24h
- Encryption: all LocationRecord lat/lng encrypted at rest via `encrypt_credential()`. Decrypted on read for authorized users only
- Retention: 30-day rolling window. Daily cron purges records older than 30 days. School check-in records retained per school's data retention policy (configurable, max 1 year)

#### `src/screen_time/` — Screen Time Management

```
src/screen_time/
  __init__.py          # Public interface
  router.py            # /api/v1/screen-time endpoints
  service.py           # Rules, schedules, enforcement, extension requests
  models.py            # ScreenTimeRule, ScreenTimeSchedule, ExtensionRequest
  schemas.py           # Pydantic schemas
```

**Endpoints:**
- `POST /api/v1/screen-time/rules` — Parent: create per-app or per-category limit
- `GET /api/v1/screen-time/rules/{child_id}` — Parent/device: get active rules
- `PUT /api/v1/screen-time/rules/{id}` — Parent: update rule
- `DELETE /api/v1/screen-time/rules/{id}` — Parent: remove rule
- `POST /api/v1/screen-time/schedules` — Parent: create weekday/weekend schedule
- `GET /api/v1/screen-time/schedules/{child_id}` — Parent/device: get schedules
- `POST /api/v1/screen-time/extension-request` — Child: request more time
- `PUT /api/v1/screen-time/extension-request/{id}` — Parent: approve/deny
- `GET /api/v1/screen-time/{child_id}/report` — Parent: weekly screen time summary

**Age-tier enforcement:**
- Young (5-9): Hard block when limit reached. No extension requests. Parent-only configuration.
- Pre-teen (10-12): Warning at 80% of limit, hard block at 100%. Extension requests allowed (max 2/day).
- Teen (13-15): Warning at 80%, soft block at 100% (dismissible with acknowledgment, parent notified). Extension requests allowed (max 5/day). Auto-deny if parent doesn't respond within 15 minutes.

**Integration with device agent:**
- `src/device_agent/` is fully implemented with three models: `DeviceSession` (agent sessions with device_id, os_version, battery_level), `AppUsageRecord` (per-app usage with bundle_id, category, foreground_minutes), and `ScreenTimeRecord` (daily summaries with app_breakdown JSON, category_breakdown JSON, pickups count). All indexed on `(member_id, started_at)` and `(member_id, category)`.
- Screen time rules are evaluated against `AppUsageRecord` data from the device agent.
- Device agent polls `/api/v1/screen-time/rules/{child_id}` every 60 seconds for active rules.
- Enforcement is local on device (notification + optional block). Server-side is the source of truth for rules.

#### `src/creative/` — Creative Tools

```
src/creative/
  __init__.py          # Public interface
  router.py            # /api/v1/creative endpoints
  service.py           # AI art, stories, stickers, drawing management
  models.py            # ArtGeneration, StoryTemplate, StoryCreation,
                       #   StickerPack, Sticker, DrawingAsset
  schemas.py           # Pydantic schemas
```

**Endpoints:**
- `POST /api/v1/creative/art/generate` — Child: generate AI art from prompt
- `GET /api/v1/creative/art/{child_id}` — Child/parent: list generated art
- `GET /api/v1/creative/stories/templates` — Child: list story templates (age-filtered)
- `POST /api/v1/creative/stories` — Child: create story from template or free-write
- `GET /api/v1/creative/stories/{child_id}` — Child/parent: list stories
- `GET /api/v1/creative/stickers/packs` — Child: list available sticker packs
- `POST /api/v1/creative/stickers/custom` — Child: save custom sticker
- `GET /api/v1/creative/stickers/{child_id}` — Child: personal sticker library
- `POST /api/v1/creative/drawings` — Child: save drawing as PNG
- `GET /api/v1/creative/drawings/{child_id}` — Child/parent: list drawings

**AI art generation flow:**
1. Child submits text prompt
2. Prompt screened by keyword filter (block age-inappropriate terms)
3. If prompt passes: call OpenAI Images API (DALL-E 3, 1024x1024)
4. Generated image saved to Cloudflare R2 via `src/media/`
5. Image enters moderation pipeline (pre-publish for <13, post-publish for teens)
6. If moderation passes: image available in child's gallery and postable to Social feed
7. Generation tracked in `ArtGeneration` table (prompt, model, cost, moderation_status)

**Rate limits per age tier:**
- Young (5-9): 10 generations/day
- Pre-teen (10-12): 25 generations/day
- Teen (13-15): 50 generations/day
- Monthly cap per family: 100 included in Family+ tier, $0.02 each additional

**Story templates:**
- 20+ templates organized by theme: adventure, friendship, mystery, science, fantasy, humor
- Age-tier filtering: young (5-9) gets fill-in-the-blank (Mad Libs style), pre-teen and teen get free-write option
- Stories moderated same as social posts (keyword + AI classification)
- Stories can be posted to Social feed or kept private

**Drawing canvas (mobile only):**
- `react-native-skia` integration in Social app
- Tools: freehand brush, color palette (20 colors), 3 brush sizes, eraser, undo/redo (10 levels)
- Export: PNG to Cloudflare R2 via `src/media/`
- Drawings enter moderation pipeline before posting
- Drawings usable as profile backgrounds or Social feed posts

**Sticker system:**
- Curated packs: Bhapi-branded (safety mascot), seasonal (holiday themes), educational (science, math)
- Curated packs are pre-approved — no moderation needed
- User-created stickers: child draws (canvas) or generates (AI art), saves to personal library
- User-created stickers enter moderation pipeline before usable in chat/comments
- Sticker format: 256x256 PNG with transparency, stored in R2

#### `src/api_platform/` — Public API for Partners

```
src/api_platform/
  __init__.py          # Public interface
  router.py            # /api/v1/platform endpoints (registration, keys, webhooks)
  oauth.py             # OAuth 2.0 authorization server
  service.py           # API key management, usage metering, tier enforcement
  webhooks.py          # Webhook delivery, retry, signature
  models.py            # OAuthClient, OAuthToken, APIKeyTier, WebhookEndpoint,
                       #   WebhookDelivery, APIUsageRecord
  schemas.py           # Pydantic schemas
```

**OAuth 2.0 provider:**
- Authorization code flow with PKCE
- Scopes: `read:alerts`, `read:compliance`, `read:activity`, `write:webhooks`, `read:risk_scores`, `read:checkins`, `read:screen_time`
- Token lifetime: access 1h, refresh 30 days
- School admins authorize apps for their school's data. Parents authorize for their family's data.
- Consent screen shows requested scopes in plain language

**API tiers (B2B only, no free tier):**

| Tier | Price | Rate Limit | Webhooks | Access |
|------|-------|------------|----------|--------|
| School | Included in School/Enterprise plan | 1,000 req/hr | 10 endpoints | Read-only school data |
| Partner | $99/mo | 5,000 req/hr | 50 endpoints | Read/write, SDK, sandbox |
| Enterprise API | Custom | 10,000+ req/hr | Unlimited | Full access, SLA, priority support |

**Registration:** Not self-serve. Partner applies via `/developers/apply` form. Bhapi admin reviews and approves. On approval: API credentials generated, welcome email with docs link.

**Webhook delivery:**
- Events: `alert.created`, `risk_score.changed`, `compliance.report_ready`, `checkin.event`, `screen_time.limit_reached`
- Delivery: POST to registered URL with JSON payload
- Signature: HMAC-SHA256 in `X-Bhapi-Signature` header (same pattern as Stripe webhook handler)
- Retry: 3 attempts with exponential backoff (10s, 60s, 300s)
- Delivery log: `WebhookDelivery` table tracks attempt count, status code, response time

**Interactive docs:**
- FastAPI auto-generates OpenAPI spec at `/api/docs` (existing Swagger UI)
- Enhanced with: authentication guide, per-endpoint examples, error code reference, webhook payload schemas
- Code samples: Python, TypeScript, curl for each endpoint

**SDK generation:**
- Auto-generate from OpenAPI spec using `openapi-generator-cli`
- `bhapi-sdk` for Python (PyPI) and `@bhapi/sdk` for TypeScript (npm)
- SDKs include typed models, auth helpers, webhook signature verification

**Developer portal pages (Next.js):**
- `/developers` — Overview, apply for access
- `/developers/dashboard` — API key management, usage metrics, webhook config
- `/developers/docs` — Interactive documentation
- `/developers/webhooks` — Webhook endpoint management, delivery log, test sender

### 5.2 Extended Modules

#### `src/intelligence/` — Event Bus + Correlation Engine

Extends existing module (SocialGraphEdge, AbuseSignal, BehavioralBaseline from Phase 2).

**New components:**
- `event_bus.py` — Redis pub/sub event bus. Channels: `ai_session`, `social_activity`, `device_event`, `location_event`. Each module publishes structured events. Intelligence subscribes to all channels.
- `correlation.py` — Rule engine. Rules stored in `CorrelationRule` table (condition JSON, action, severity, age_tier_filter). Evaluated on each incoming event against rolling 48h window. Matches create `EnrichedAlert`.
- `scoring.py` — Unified risk score calculator. Inputs: AI risk events, social behavioral scores, device usage patterns, location anomalies. Output: 0-100 score per child with confidence (low/medium/high) and trend (increasing/stable/decreasing).
- `anomaly.py` — Multi-signal anomaly detection. Per-child baselines (from Phase 2). Deviation scoring across signal types. Deterministic thresholds (>2 standard deviations = alert), not ML.

**New models:**
- `CorrelationRule`: `id`, `name`, `description`, `condition` (JSON — signal types, thresholds, time window), `action` (alert_severity, notification_type), `age_tier_filter`, `enabled`, `created_at`
- `EnrichedAlert`: `id`, `alert_id` (FK to Alert), `correlation_context` (text — human-readable explanation), `contributing_signals` (JSON — list of signal references), `unified_risk_score`, `confidence`
**Note on BehavioralBaseline:** The existing `BehavioralBaseline` model (Phase 2) stores per-child baselines with a `metrics` JSON field, `sample_count`, and `window_days`. Phase 3 does NOT create a separate `AnomalyModel` table — instead, the `anomaly.py` service computes multi-signal deviation scores at runtime by reading from `BehavioralBaseline` (social/device baselines) combined with AI risk event history and location patterns. No new baseline table is needed; the existing model's `metrics` JSON is flexible enough to store per-signal-type means and standard deviations.

**Default correlation rules (14 categories):**
1. AI dependency + social withdrawal → emotional_dependency (HIGH)
2. AI usage spike + attendance drop → academic_risk (MEDIUM)
3. Harmful AI content + self-harm social posts → self_harm (CRITICAL)
4. Evasion (monitored AI drop + high screen time) → evasion (MEDIUM)
5. New AI platform + sudden social contacts → grooming_risk (HIGH)
6. PII in AI + PII in social posts → privacy_violation (HIGH)
7. AI-generated content shared socially → academic_integrity (MEDIUM)
8. Location anomaly + social silence → safety_concern (HIGH)
9. Deepfake detection + social sharing → deepfake_risk (HIGH)
10. Budget overrun + dependency signals → financial_risk (MEDIUM)
11. Night-time AI usage + bedtime mode bypass → sleep_disruption (MEDIUM)
12. Multiple platform blocks bypassed → evasion_escalation (HIGH)
13. Social isolation score increasing + AI chatbot reliance → dependency_escalation (HIGH)
14. Sudden contact pattern change + location change → stranger_danger (CRITICAL)

**Unified risk score weights (configurable per age tier):**

| Signal Source | Young (5-9) | Pre-teen (10-12) | Teen (13-15) |
|--------------|-------------|------------------|--------------|
| AI monitoring | 0.40 | 0.30 | 0.25 |
| Social behavior | 0.20 | 0.30 | 0.35 |
| Device usage | 0.20 | 0.20 | 0.20 |
| Location | 0.20 | 0.20 | 0.20 |

**Trend tracking:**
- Rolling 7-day and 30-day averages stored per child in `BehavioralBaseline` (existing model, `metrics` JSON extended with per-signal-type means and standard deviations)
- Dashboard shows trend direction (arrow up/down/stable) and magnitude (see P3-F4 unified dashboard)
- Trend reversal (risk decreasing after period of increase) triggers positive notification to parent

#### `src/billing/` — Bundle Pricing Extension

**New tier definitions:**

| Tier | Stripe Product | Price | Features |
|------|---------------|-------|----------|
| Free | — (no Stripe) | $0 | 1 child, 1 parent, extension only, weekly email summary |
| Family | `prod_family` (existing) | $9.99/mo | 5 children, Safety app, alerts, blocking, reports, Social access |
| Family+ | `prod_family_plus` (NEW) | $14.99/mo | Family + location, screen time, creative tools (100 AI art/mo) |
| School | `prod_school` (existing) | $4.99/seat/mo | Admin dashboard, compliance, SIS, check-in/check-out, governance, API |
| Enterprise | `prod_enterprise` (existing) | Custom | SSO, SLA, API, multi-district, dedicated support |

**New models:**
- `FeatureGate`: `id`, `feature_key` (e.g., `location_tracking`, `screen_time`, `creative_tools`, `api_access`), `required_tier` (enum), `created_at`
- Feature gating middleware: `check_feature_gate(feature_key)` dependency — returns 403 with `{"upgrade_url": "/pricing", "required_tier": "family_plus"}` if user's tier is insufficient

**Annual discount:**
- 20% off for Family and Family+ (annual billing)
- Family annual: $95.90/yr (vs $119.88 monthly)
- Family+ annual: $143.90/yr (vs $179.88 monthly)
- Stripe handles billing cycle switching

**Free tier implementation:**
- No Stripe subscription — user exists in DB with `subscription_tier = "free"`
- Weekly email cron job: queries capture events for free-tier users, generates summary email
- Email includes: platform usage counts (no detail), "You missed X HIGH risk alerts this week" teaser, upgrade CTA
- Feature gating blocks all non-free features (dashboard, alerts, apps, blocking, reports)
- Free users can upgrade to any paid tier via self-serve Stripe checkout

**Upgrade/downgrade:**
- Self-serve via Stripe customer portal
- Upgrade: immediate access to new features
- Downgrade: gated features disabled at next billing cycle. Data retained 30 days. Re-upgrade restores access.
- Free → paid: Stripe checkout with plan preselection (existing pattern from Phase 1)

#### `src/alerts/` — Enriched Alerts

- Existing `Alert` model extended with optional `enriched_alert_id` FK to `EnrichedAlert`
- Alert creation flow: when intelligence engine creates a correlated alert, it also creates an `EnrichedAlert` with `correlation_context` and attaches it to the `Alert`
- Alert detail endpoints return enrichment data when present
- Safety app and portal show enrichment context: "This alert was triggered because [AI signal] combined with [social signal]"
- Push notification for enriched alerts includes correlation summary in the body

#### `src/moderation/` — Creative Content Moderation

- Existing pre-publish and post-publish pipelines handle creative content
- AI art prompts: keyword filter before API call (block sexual, violent, hateful prompts)
- AI art images: run through image classification (existing Hive/Sensity pipeline)
- Drawings: image classification on PNG export
- Stories: text moderation (existing keyword + AI classification pipeline)
- Stickers: image classification on 256x256 PNG
- User-created stickers quarantined until moderation passes

#### `src/portal/` — Unified Dashboard + Developer Portal + Landing Pages

**Unified dashboard (`/unified`):**
- Single page combining: risk summary (intelligence), AI activity (capture), social activity (social), screen time (screen_time), location map (location)
- Risk summary card: unified score, trend, confidence, top factors
- Action center: pending contact approvals, extension requests, unread alerts
- Child selector: switch between children. Comparison view for multi-child families.
- Data from existing + new endpoints via React Query hooks

**Developer portal (`/developers/*`):**
- `/developers` — Landing: API overview, partnership benefits, apply CTA
- `/developers/apply` — Application form (company, use case, expected volume)
- `/developers/dashboard` — API key display, usage chart (calls/day), tier info, upgrade
- `/developers/webhooks` — Endpoint management (add/edit/delete), delivery log, test sender
- `/developers/docs` — Embedded Swagger UI with enhanced examples

**Landing page redesign (`/`):**
- Hero: "Safe AI. Safe Social. One Platform." + App Store badges + "Start Free" CTA
- Audience tabs: Families / Schools / Partners — each with tailored messaging
- Feature highlights: AI monitoring, social safety, location, screen time, creative tools
- Social proof: school count, family count, compliance badges
- Pricing section: tier comparison table with "Start Free" and "Contact Sales" CTAs
- Footer: legal links, privacy policy, terms, contact

**Additional pages:**
- `/families` — Family-focused features + pricing
- `/schools` — School-focused features + compliance + pricing
- `/partners` — Partnership program + apply CTA + co-branded resources
- `/pricing` — Full tier comparison with feature matrix

### 5.3 New Mobile Screens

#### Safety App (Parent)

| Screen | Path | Purpose |
|--------|------|---------|
| Location map | `(dashboard)/location.tsx` | Real-time child location, geofence list, history playback |
| Geofence management | `(dashboard)/geofences.tsx` | Create/edit/delete geofences, radius picker |
| Screen time dashboard | `(dashboard)/screen-time.tsx` | Per-child screen time rules, schedules, usage chart |
| Extension request | `(dashboard)/extension-request.tsx` | Approve/deny child's time extension request |
| Unified dashboard | `(dashboard)/unified.tsx` | Combined AI + social + location + screen time view |
| Creative content review | `(children)/creative-review.tsx` | Review child's AI art, stories, drawings |
| Location settings | `(settings)/location-settings.tsx` | Kill switch, school consent, retention preferences |

#### Social App (Child)

| Screen | Path | Purpose |
|--------|------|---------|
| Art studio | `(creative)/art-studio.tsx` | AI art generation with prompt input |
| Story creator | `(creative)/story-creator.tsx` | Template browser + writing screen |
| Drawing canvas | `(creative)/drawing.tsx` | react-native-skia canvas with tools |
| Sticker picker | `(creative)/stickers.tsx` | Browse packs + personal library |
| Location share | `(settings)/share-location.tsx` | One-tap location share + panic button |
| Screen time status | `(settings)/screen-time.tsx` | Current usage, limits, request extension |

#### Shared UI Components (new)

| Component | Package | Purpose |
|-----------|---------|---------|
| `LocationMap` | `@bhapi/shared-ui` | MapView wrapper with child marker + geofences |
| `ScreenTimeBar` | `@bhapi/shared-ui` | Usage progress bar with limit indicator |
| `RiskScoreCard` | `@bhapi/shared-ui` | Unified score display with trend arrow + confidence |
| `CreativeToolbar` | `@bhapi/shared-ui` | Drawing tools (brush, color, size, eraser, undo) |
| `StickerGrid` | `@bhapi/shared-ui` | Grid layout for sticker browsing/selection |
| `FeatureGateBanner` | `@bhapi/shared-ui` | "Upgrade to Family+" banner for gated features |
| `AudienceTab` | `@bhapi/shared-ui` | Tab component for landing page audience sections |

### 5.4 New Alembic Migrations

| Number | Tables | Task |
|--------|--------|------|
| 045 | `location_records`, `geofences`, `geofence_events`, `school_checkins`, `location_sharing_consents`, `location_kill_switches`, `location_audit_logs` | P3-F3 |
| 046 | `screen_time_rules`, `screen_time_schedules`, `extension_requests` | P3-F2 |
| 047 | `art_generations`, `story_templates`, `story_creations`, `sticker_packs`, `stickers`, `drawing_assets` | P3-F1 |
| 048 | `oauth_clients`, `oauth_tokens`, `api_key_tiers`, `webhook_endpoints`, `webhook_deliveries`, `api_usage_records` | P3-B3 |
| 049 | `feature_gates` + seed data for tier-feature mappings | P3-B1 |
| 050 | `correlation_rules`, `enriched_alerts` + seed 14 default correlation rules | P3-I1/I2 |
| 051 | `audit_policies`, `evidence_collections`, `compliance_controls` | P3-B4 |

**Migration notes:**
- Latest existing migration is 044 (`parental_safeguards`). The Phase 2 plan defined 033-041, but implementation added 3 additional migrations: 042 (`alert_source_column`), 043 (`moderation_dashboard`), 044 (`parental_safeguards`). Phase 3 starts at **045**.
- Migrations 045-051 each modify `alembic/env.py` (model imports) — must be sequenced, not parallel
- All migrations must be committed and pushed (lesson from 2026-03-12 outage)
- Location records use compound index on `(child_id, timestamp)` for efficient range queries
- Geofence uses PostGIS-style lat/lng + radius (no PostGIS dependency — Haversine distance in Python)

### 5.5 Cross-App Onboarding (P3-L5)

Three paths, one destination:

#### Path 1: Parent-Initiated (Primary)
1. Parent installs Bhapi Safety
2. Creates account (email + password or SSO)
3. Creates family group
4. Adds children: name, date of birth, email (optional for young tier)
5. Age tier auto-assigned from date of birth
6. For each child: "Invite to Bhapi Social?" → generates invite code
7. Child installs Bhapi Social, enters invite code
8. Child linked to family group, age tier enforced, parent consent recorded
9. If child <13: FamilyAgreement signing flow triggered for parent

#### Path 2: Child-Initiated
1. Child installs Bhapi Social (via school recommendation or friend)
2. Yoti age verification runs during onboarding
3. If under 16: "A parent needs to approve your account"
4. Child enters parent's email address
5. Parent receives email + SMS (if phone provided) with link
6. Link opens: Safety app (if installed) or web approval page (portal)
7. Parent creates account (if new) or logs in
8. Parent reviews child's profile, approves account
9. Family group created (or child added to existing group)
10. Parent prompted to install Safety app if using web flow

#### Path 3: School-Initiated
1. School admin creates school group in portal
2. SIS sync imports student roster (Clever/ClassLink)
3. Student accounts created with school email
4. Access codes generated per student
5. Students enter access code in Bhapi Social during onboarding
6. Parents receive notification: "[School Name] has enrolled [Child] in Bhapi"
7. Parent installs Safety app, links to child's school-provisioned account
8. Parent can add additional children (personal, non-school)

**Deep links:**
- `bhapi://invite/{code}` — Social app: join family group
- `bhapi://approve/{token}` — Safety app: approve child account
- `https://bhapi.ai/approve/{token}` — Web fallback for parents without Safety app
- Expo Linking handles both iOS universal links and Android app links

### 5.6 Landing Page Design

**Route structure (all static export compatible):**

| Route | Purpose | Audience |
|-------|---------|----------|
| `/` | Hero + overview + CTAs | All |
| `/families` | Family features + Family/Family+ pricing | Parents |
| `/schools` | School features + compliance + per-seat pricing | School admins |
| `/partners` | Partnership program + apply | EdTech, resellers |
| `/pricing` | Full tier comparison matrix | All |
| `/developers` | API overview + apply | Technical partners |

**Hero section:**
- Headline: "Safe AI. Safe Social. One Platform."
- Subheadline: "The only app where kids socialize safely AND parents monitor AI usage across 10 platforms."
- CTAs: "Start Free" (→ /register) and "Book a Demo" (→ /contact)
- App Store badges: iOS + Android for both Safety and Social
- Background: existing `hero-bg.svg` pattern (orange/beige)

**Social proof bar:**
- "[X] schools" | "[X] families" | "COPPA 2026 Compliant" | "EU AI Act Compliant" | "SOC 2 In Progress"
- Numbers pulled from DB via lightweight API endpoint (cached 1h)

## 6. Testing Strategy

### Test Count Targets

| Category | Phase 2 Exit | Phase 3 Target | Increment |
|----------|-------------|----------------|-----------|
| Backend (unit + e2e + security) | ~3,854 | ~4,650 | +796 |
| Mobile (component + integration) | 213 | ~500 | +287 |
| Prod E2E | 82 | ~130 | +48 |
| Frontend (portal) | 225 | ~300 | +75 |
| Extension | 43 | 43 | — |
| **Total** | **~4,417** | **~5,623** | **+1,206** |

### Per-Deliverable Test Requirements

| ID | Unit | E2E | Security | Mobile/Frontend |
|----|------|-----|----------|-----------------|
| P3-I1 | ≥40 | ≥25 | ≥15 | — |
| P3-I2 | ≥25 | ≥15 | — | — |
| P3-I3 | ≥15 | ≥10 | — | — |
| P3-I4 | ≥20 | ≥15 | — | — |
| P3-F1 | ≥30 | ≥15 | ≥10 | Comp ≥20 |
| P3-F2 | ≥25 | ≥20 | ≥10 | Comp ≥15 |
| P3-F3 | ≥30 | ≥25 | ≥15 | Comp ≥15 |
| P3-F4 | — | — | — | Comp ≥20, Portal ≥15 |
| P3-B1 | ≥20 | ≥15 | ≥10 | — |
| P3-B2 | — | — | — | — (documentation only, unless ROI calculator is a web tool) |
| P3-B3 | ≥30 | ≥20 | ≥15 | Portal ≥10 |
| P3-B4 | ≥10 | ≥5 | — | — |
| P3-L1/L2 | — | — | — | Maestro ≥15 each |
| P3-L3 | — | — | — | — |
| P3-L4 | — | — | — | Portal ≥10 |
| P3-L5 | ≥15 | ≥10 | ≥10 | Comp ≥15 |

### Security Test Focus Areas

- Location data: encryption at rest verification, audit log completeness, kill switch effectiveness, school consent enforcement
- API platform: OAuth token validation, scope enforcement, rate limiting per tier, webhook signature verification
- Feature gating: tier enforcement on all gated endpoints, upgrade bypass prevention
- Creative tools: prompt injection prevention, moderation pipeline coverage, rate limit enforcement
- Screen time: rule bypass prevention, extension request authentication, age-tier enforcement

## 7. Exit Criteria

- [ ] Both apps publicly available on iOS App Store + Google Play Store
- [ ] ≥500 family signups (organic + school referral)
- [ ] ≥10 school deployments active
- [ ] App Store rating ≥4.0 (both apps)
- [ ] Bundle conversion ≥10% free → paid (tracked in analytics)
- [ ] Cross-product intelligence engine live, generating correlated alerts
- [ ] Screen time + location tracking live for Family+ tier
- [ ] Location kill switch functional, audit log recording all access
- [ ] School check-in/check-out live with parent opt-in consent
- [ ] Creative tools live (AI art + stories + drawing + stickers) with moderation
- [ ] Public API beta live with ≥3 approved partner integrations
- [ ] Channel partnership package complete (collateral, ROI calculator, deployment guide)
- [ ] SOC 2 Type II audit engagement signed, evidence collection automated
- [ ] Landing page live with audience-specific messaging (families, schools, partners)
- [ ] Cross-app onboarding functional (all 3 paths: parent, child, school)
- [ ] Free tier operational with weekly email summary + upgrade CTA
- [ ] Feature gating enforced on all tier-restricted endpoints
- [ ] **Test count: ≥5,623 total**
- [ ] **Mobile test coverage: ≥80% screen coverage**
- [ ] **All Alembic migrations (045-051) committed and pushed**
- [ ] **0 open critical/high security findings**
- [ ] **Prod E2E: ≥130 tests, all passing post-deploy**

## 8. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Apple rejects background location | Delays Safety app launch | Pre-submission consultation with Apple, detailed privacy justification, fallback to foreground-only |
| Google background location form rejected | Delays Safety app on Android | Submit form early in Layer 1, allow 2 weeks for review cycle |
| OpenAI Images API cost overrun | Budget impact | Rate limits per tier, monthly caps, cost tracking in billing module |
| SOC 2 auditor availability | Delays audit initiation | Start RFP in Layer 1, target engagement by Layer 2 |
| App Store review time | Delays public launch | Submit apps at start of Week 26, not end. Allow 1 week buffer |
| Intelligence false positives | Parent alert fatigue | Conservative thresholds (>2 std dev), confidence levels, "snooze" option on correlated alerts |
| Location data breach | Catastrophic trust loss | Encryption at rest, audit logging, minimal retention, kill switch, penetration testing pre-launch |

## 9. Compatibility

### Existing Module Contracts

No breaking changes to existing module public interfaces. All new functionality is additive:

- `src/intelligence/` — New files added alongside existing models.py (SocialGraphEdge, AbuseSignal, BehavioralBaseline unchanged)
- `src/billing/` — New tier definitions added via migration seed data. Existing Family/School/Enterprise products unchanged in Stripe
- `src/alerts/` — `enriched_alert_id` is nullable FK — existing alerts unaffected
- `src/moderation/` — Creative content uses existing pipeline (no changes to pre-publish/post-publish flow)
- `src/device_agent/` — Screen time enforcement is a new polling endpoint, not a change to existing data flow

### Database Compatibility

- All new migrations are additive (CREATE TABLE, ADD COLUMN)
- No ALTER or DROP on existing tables
- Existing queries unaffected
- Feature gate enforcement is opt-in via new middleware dependency — existing endpoints unchanged unless explicitly gated
