# Bhapi Unified Platform — Design Specification

**Version:** 1.1
**Date:** March 19, 2026
**Status:** Draft (post-review revision)
**Based on:** Bhapi Gap Analysis Q2 2026, Platform Unification Plan (Mar 17), Brainstorming Session (Mar 19)

---

## 1. Vision & Positioning

**One-line positioning:** "The only platform where kids socialize safely AND parents monitor AI"

Bhapi unifies a safe social network for children (under 16) with an AI safety monitoring platform for parents and schools. No competitor offers both — GoGuardian/Gaggle monitor AI but have no social product; Bark monitors social media but has no AI depth; PopJam/Zigazoo offer safe social but no parental monitoring.

### Target Markets (Dual-Track)

| Market | Entry Strategy | Primary Product |
|--------|---------------|-----------------|
| **Families** | Child uses Bhapi Social (free) → Parent installs Bhapi Safety → Free tier → Paid conversion | Both apps |
| **Schools** | Compliance-led (Ohio AI mandate, Australian legislation) → Channel partnerships for scale | Safety + Governance |

### Regulatory Scope (Global from Day One)

- **US:** COPPA 2026 (done), Ohio AI Mandate (Jul 1), California AADC (2027 prep)
- **Australia:** Online Safety Act, Social Media Minimum Age Bill
- **EU:** EU AI Act full enforcement (Aug 2)
- **UK:** Age Appropriate Design Code (Dec 2026 review)
- **i18n:** 6 languages — English, Portuguese (BR), Spanish, French, German, Italian

---

## 2. Product Architecture

### 2.1 Client Applications

#### Bhapi Social (Child App)
- **Platform:** iOS + Android (Expo SDK 52+)
- **Bundle ID:** `com.bhapi.social`
- **Target users:** Children 5-15, three age tiers
- **Core experience:** Safe social feed + messaging + creative tools (incremental rollout)
- **Monetization:** Free (no ads, no in-app purchases)

#### Bhapi Safety (Parent App)
- **Platform:** iOS + Android (Expo SDK 52+)
- **Bundle ID:** `com.bhapi.safety`
- **Target users:** Parents, guardians
- **Core experience:** AI monitoring dashboard + Bhapi Social activity monitoring + alerts
- **Monetization:** Tiered subscriptions (Free / $9.99 / $14.99 / School / Enterprise)

#### Web Portal (Existing)
- **URL:** bhapi.ai
- **Platform:** Next.js 15 (static export)
- **Target users:** Parents, school admins, enterprise
- **Role:** Full dashboard, admin, school management, governance tools

#### Browser Extension (Existing)
- **Platform:** Chrome + Firefox + Safari (Manifest V3)
- **Role:** AI platform conversation capture (10 platforms)

### 2.2 Expo Monorepo Structure

```
bhapi-mobile/
├── apps/
│   ├── safety/                  # Bhapi Safety (parent app)
│   │   ├── app/                 # Expo Router screens
│   │   │   ├── (auth)/          # Login, register, magic link
│   │   │   ├── (dashboard)/     # Dashboard, alerts, activity
│   │   │   ├── (children)/      # Per-child views, contacts approval
│   │   │   ├── (settings)/      # Account, subscription, notifications
│   │   │   └── _layout.tsx      # Root layout with auth guard
│   │   ├── assets/
│   │   └── app.json
│   └── social/                  # Bhapi Social (child app)
│       ├── app/                 # Expo Router screens
│       │   ├── (auth)/          # Login, parent consent, age verify
│       │   ├── (feed)/          # Feed, post detail, create post
│       │   ├── (chat)/          # Conversations, messaging
│       │   ├── (profile)/       # Profile, followers, settings
│       │   ├── (creative)/      # AI art, story creation (Phase 3)
│       │   └── _layout.tsx      # Root layout with age-tier guard
│       ├── assets/
│       └── app.json
├── packages/
│   ├── shared-ui/               # Brand components, buttons, cards, inputs
│   │   ├── src/
│   │   │   ├── BhapiLogo.tsx
│   │   │   ├── Button.tsx       # Variants, sizes, isLoading
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── Avatar.tsx
│   │   │   ├── PostCard.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   └── ContactRequest.tsx
│   │   ├── __tests__/
│   │   └── package.json
│   ├── shared-auth/             # JWT, SecureStore, biometrics, session
│   │   ├── src/
│   │   │   ├── token-manager.ts
│   │   │   ├── secure-store.ts
│   │   │   ├── biometric.ts
│   │   │   └── session.ts
│   │   ├── __tests__/
│   │   └── package.json
│   ├── shared-api/              # REST + WebSocket client
│   │   ├── src/
│   │   │   ├── rest-client.ts   # Axios instance, interceptors, retry
│   │   │   ├── ws-client.ts     # WebSocket connection, reconnection
│   │   │   ├── offline-queue.ts # Queue requests when offline
│   │   │   └── endpoints/       # Typed API functions per module
│   │   ├── __tests__/
│   │   └── package.json
│   ├── shared-i18n/             # 6-language translations
│   │   ├── locales/
│   │   │   ├── en.json
│   │   │   ├── pt-BR.json
│   │   │   ├── es.json
│   │   │   ├── fr.json
│   │   │   ├── de.json
│   │   │   └── it.json
│   │   ├── src/
│   │   │   └── i18n.ts          # Locale detection, provider
│   │   └── package.json
│   ├── shared-config/           # Theme, constants, feature flags
│   │   ├── src/
│   │   │   ├── theme.ts         # Orange #FF6B35, Teal #0D9488, Inter
│   │   │   ├── constants.ts     # API URLs, age tiers, limits
│   │   │   └── feature-flags.ts # Tier-based feature gating
│   │   └── package.json
│   └── shared-types/            # TypeScript types from backend schemas
│       ├── src/
│       │   ├── auth.ts
│       │   ├── social.ts
│       │   ├── safety.ts
│       │   ├── moderation.ts
│       │   └── billing.ts
│       └── package.json
├── turbo.json                   # Turborepo config
├── package.json                 # Workspace root
└── tsconfig.base.json           # Shared TS config
```

**Mobile Accessibility Requirements (WCAG 2.1 AA):**
- All interactive elements: minimum 44pt tap targets
- VoiceOver (iOS) and TalkBack (Android) labels on all screens
- Dynamic type / font scaling support
- Sufficient color contrast (4.5:1 text, 3:1 large text)
- No color-only information (always include text/icon alongside color)
- Screen reader testing included in Maestro E2E suite
- Accessibility checks in mobile Definition of Done

### 2.3 Backend Architecture

#### FastAPI Monolith (Extended)

All modules served from single FastAPI app (`src/main.py`). Existing 19 modules plus 10 new modules:

| Module | Prefix | Purpose | Phase |
|--------|--------|---------|-------|
| **Existing modules** | | | |
| `auth/` | `/api/v1/auth` | Registration, login, JWT, API keys | — |
| `groups/` | `/api/v1/groups` | Groups, members, invitations, consent | — |
| `capture/` | `/api/v1/capture` | AI conversation ingestion | — |
| `risk/` | `/api/v1/risk` | Risk scoring, safety classification | — |
| `alerts/` | `/api/v1/alerts` | Notifications, escalation | — |
| `billing/` | `/api/v1/billing` | Stripe, spend tracking | — |
| `reporting/` | `/api/v1/reports` | Reports, PDF/CSV export | — |
| `portal/` | `/api/v1/portal` | Dashboard aggregation | — |
| `compliance/` | `/api/v1/compliance` | GDPR/COPPA/LGPD, EU AI Act | — |
| `integrations/` | `/api/v1/integrations` | Clever, ClassLink, Yoti, SSO | — |
| `blocking/` | `/api/v1/blocking` | Content blocking, time budgets | — |
| `analytics/` | `/api/v1/analytics` | Trends, anomaly detection | — |
| `sms/` | (internal) | Twilio SMS | — |
| `email/` | (internal) | SendGrid email | — |
| `literacy/` | `/api/v1/literacy` | AI literacy (deferred) | — |
| `groups/school_router` | `/api/v1/school` | School admin | — |
| `legal/` | `/legal` | Privacy policy, terms | — |
| `jobs/` | `/internal` | Background jobs | — |
| **New modules** | | | |
| `social/` | `/api/v1/social` | Feed, posts, comments, likes, hashtags, profiles, follow/unfollow | P1 |
| `messaging/` | `/api/v1/messages` | Conversations, messages (text/image/video), read receipts | P1 |
| `contacts/` | `/api/v1/contacts` | Contact requests, parent approval, blocking, social graph | P1 |
| `moderation/` | `/api/v1/moderation` | Pre-publish pipeline, post-publish takedown, queue, appeals | P1 |
| `age_tier/` | `/api/v1/age-tier` | Permission engine, tier rules, graduated unlocks, transitions | P1 |
| `media/` | `/api/v1/media` | Cloudflare R2 upload, Images resize, Stream transcode | P1 |
| `device_agent/` | `/api/v1/device` | Mobile agent ingestion, screen time, location, app usage | P2 |
| `governance/` | `/api/v1/governance` | AI policy generator, state compliance, audit trails | P1 |
| `intelligence/` | `/api/v1/intelligence` | Cross-product correlation, unified risk scores, baselines | P2-P3 |
| `creative/` | `/api/v1/creative` | AI art, story creation, templates, challenges | P3 |

**Module Ownership Boundaries:**
- `moderation/` owns `moderation_queue` and `moderation_decisions` tables. It communicates with `social/`, `messaging/`, and `media/` via their public `__init__.py` interfaces to fetch content for classification and to update `moderation_status` on source records.
- `intelligence/` owns `intelligence_events` and `behavioral_baselines`. It reads from `risk/`, `social/`, `capture/`, and `device_agent/` via public interfaces to correlate signals.
- `governance/` is distinct from `compliance/`: governance handles **organizational policy management** (school AI policies, tool inventories, audit trails); compliance handles **regulatory data subject rights** (GDPR erasure, COPPA consent, EU AI Act conformity). They share no tables.
- All other modules follow the existing rule: each module only queries its own tables.

#### Real-Time WebSocket Service (New, Separate Process)

```
src/realtime/
├── main.py              # WebSocket FastAPI app (separate Render service)
├── chat.py              # Message delivery, typing indicators
├── presence.py          # Online/offline/last-seen via Redis
├── notifications.py     # Push notification relay (Expo push tokens)
├── feed.py              # Live feed updates (new post, like, comment)
├── moderation_gate.py   # Hold-and-release for pre-publish content
└── auth.py              # JWT validation (shared secret with monolith)
```

- Deployed as separate Render service
- Connects to same PostgreSQL + Redis
- Communicates with monolith via Redis pub/sub
- Scales independently (long-lived WebSocket connections don't impact REST API latency)

**Connection Pooling Strategy:** Multiple services sharing one PostgreSQL instance requires explicit pool management to avoid connection exhaustion (Render managed PostgreSQL limits: 25-100 connections depending on plan).

| Service | Pool Size | Strategy |
|---------|:---------:|---------|
| Monolith (FastAPI) | 20 | SQLAlchemy async pool (existing) |
| Jobs (cron) | 5 | SQLAlchemy async pool, smaller |
| WebSocket service | 10 | **Lazy acquisition** — acquire DB connection only when writing (message persistence, presence update), release immediately. No held connections during idle WebSocket sessions. |
| **Total** | **35** | Fits within Render Standard plan (50 connections). PgBouncer sidecar added if exceeding 80% utilization. |

This is documented as a constraint: the WebSocket service MUST NOT hold persistent DB connections per WebSocket session. Use Redis for all real-time state (presence, typing indicators); PostgreSQL only for durable writes.

### 2.4 Data Layer

#### Storage

| Data Type | Storage | CDN |
|-----------|---------|-----|
| Structured data (users, posts, messages, etc.) | PostgreSQL 16 | — |
| Session/cache/pub-sub | Redis 7 | — |
| Images (posts, avatars, media) | Cloudflare R2 + Cloudflare Images | Cloudflare edge |
| Videos (posts, messages) | Cloudflare R2 + Cloudflare Stream | Cloudflare edge |
| Encrypted content excerpts (AI monitoring) | PostgreSQL (Fernet encrypted) | — |

#### New Database Tables

**Phase 1 Migrations (032-037):**

| Table | Key Columns | Purpose |
|-------|------------|---------|
| `profiles` | user_id (FK), display_name, avatar_url, bio, age_tier, dob, visibility | Social profile (1:1 with users) |
| `age_tier_configs` | member_id (FK), tier (enum: 5-9/10-12/13-15), jurisdiction (country_code), min_age_override, feature_overrides (JSON), locked_features (JSON) | Per-member tier configuration with jurisdiction-specific age gates |
| `social_posts` | author_id, content, media_urls (JSON), post_type, moderation_status, hashtag_ids | Feed posts |
| `post_comments` | post_id (FK), author_id, content, moderation_status | Comments on posts |
| `post_likes` | post_id (FK), user_id, created_at | Likes (unique constraint) |
| `hashtags` | name (unique), post_count | Hashtag registry |
| `post_hashtags` | post_id (FK), hashtag_id (FK) | Many-to-many join |
| `follows` | follower_id, following_id, status (pending/accepted/blocked) | Follow relationships |
| `contacts` | requester_id, target_id, status, parent_approval_status | Contact requests with parent gate |
| `contact_approvals` | contact_id (FK), parent_user_id, decision, decided_at | Parent approval records |
| `conversations` | type (direct/group), created_by, title | Chat conversations |
| `conversation_members` | conversation_id (FK), user_id, last_read_at, role | Conversation membership |
| `messages` | conversation_id (FK), sender_id, content, message_type, moderation_status | Chat messages |
| `message_media` | message_id (FK), cloudflare_id, media_type, moderation_status | Message attachments |
| `moderation_queue` | content_type, content_id, pipeline, status, risk_scores (JSON), age_tier | Content moderation queue |
| `moderation_decisions` | queue_id (FK), moderator_id, action, reason, timestamp | Moderation audit trail |
| `content_reports` | reporter_id, target_type, target_id, reason, status | User reports |
| `media_assets` | cloudflare_r2_key, cloudflare_image_id, cloudflare_stream_id, media_type, moderation_status, owner_id, variants (JSON) | Media registry |
| `governance_policies` | school_id, state_code, policy_type, content (JSON), status, version | AI governance policies |
| `governance_audits` | policy_id (FK), action, actor_id, diff (JSON), timestamp | Governance audit trail |

**Phase 2 Migrations (038-040):**

| Table | Key Columns | Purpose |
|-------|------------|---------|
| `behavioral_baselines` | user_id, avg_posts_day, avg_messages_day, active_hours (JSON), deviation_threshold, updated_at | Per-child activity norms |
| `device_agent_data` | member_id (FK), app_usage (JSON), screen_time_minutes, location (JSON), timestamp | Mobile agent data |
| `intelligence_events` | child_id, signal_source, signal_type, correlation_id, severity, data (JSON), parent_alerted | Cross-product intelligence |

**Phase 3 Migrations (041):**

| Table | Key Columns | Purpose |
|-------|------------|---------|
| `creative_assets` | author_id, asset_type, content (JSON), moderation_status | AI-generated creative content |

#### Compound Indexes

```sql
-- Social feed (latency-critical)
ix_social_posts_feed ON social_posts(author_id, created_at DESC) WHERE deleted_at IS NULL
ix_social_posts_moderation ON social_posts(moderation_status, created_at) WHERE deleted_at IS NULL

-- Follow-based feed construction
ix_follows_active ON follows(follower_id, following_id) WHERE status = 'accepted'

-- Messaging (latency-critical)
ix_messages_conversation ON messages(conversation_id, created_at DESC)
ix_conversation_members_user ON conversation_members(user_id, last_read_at)

-- Moderation pipeline (latency-critical: <2s pre-publish)
ix_moderation_queue_pending ON moderation_queue(pipeline, status, created_at) WHERE status = 'pending'
ix_moderation_queue_content ON moderation_queue(content_type, content_id)

-- Contacts + parent approval
ix_contacts_status ON contacts(target_id, status) WHERE deleted_at IS NULL
ix_contact_approvals_pending ON contact_approvals(parent_user_id, decision) WHERE decision = 'pending'

-- Intelligence correlation
ix_intelligence_events_child ON intelligence_events(child_id, created_at DESC)
ix_intelligence_events_correlation ON intelligence_events(correlation_id)

-- Device agent queries
ix_device_agent_data_member ON device_agent_data(member_id, timestamp DESC)

-- Media moderation
ix_media_assets_moderation ON media_assets(moderation_status, created_at) WHERE moderation_status = 'pending'
```

---

## 3. Age Tier System

### Three Tiers

| Tier | Age | COPPA Status | Feature Set |
|------|-----|-------------|-------------|
| **Young** | 5-9 | Under 13 (COPPA applies) | Parent-curated, no DMs, no search, moderated creative tools only |
| **Pre-teen** | 10-12 | Under 13 (COPPA applies) | Social feed, moderated group messaging, creative tools, parent approval for new contacts |
| **Teen** | 13-15 | Over 13 (COPPA relaxed, but platform rules apply) | Full social features, DMs with AI moderation, AI creative tools, less parent gatekeeping but full monitoring |

### Feature Matrix by Tier

| Feature | 5-9 (Young) | 10-12 (Pre-teen) | 13-15 (Teen) |
|---------|:-----------:|:-----------------:|:-------------:|
| View feed | Curated only | Full (age-filtered) | Full |
| Create posts (text) | Parent-approved | Yes (pre-screened) | Yes |
| Create posts (image) | Disabled | Yes (pre-screened) | Yes (post-screened) |
| Create posts (video) | Disabled | Yes (pre-screened) | Yes (post-screened) |
| Comments | Positive reactions only | Yes (pre-screened) | Yes (post-screened) |
| Likes | Yes | Yes | Yes |
| Hashtags | No | View only | Create + view |
| Search users | No | School network only | Platform-wide |
| Follow/unfollow | Parent-approved | Parent-approved (non-school) | Self-managed |
| Direct messages | Disabled | Group only, parent-approved | Yes, AI-moderated |
| Group messaging | Disabled | Parent-approved groups | Yes |
| Contact requests | Parent handles | Parent approval required | Self-managed, flagged |
| Creative tools | Basic templates | Full (moderated) | Full (AI-powered) |
| Profile visibility | Not searchable | School network | Platform-wide |
| Location sharing | Blocked | Blocked | Optional (parent-visible) |
| Report content | Auto-report to parent | Report button + parent notify | Report button + optional parent |
| Moderation mode | **Pre-publish (all content)** | **Pre-publish (image/video)** | **Post-publish rapid takedown** |
| Content takedown SLA | Pre-publish block | <30 seconds | <60 seconds |

### Age Verification by Jurisdiction

```
Registration flow:
1. User enters date of birth
2. System determines age tier + jurisdiction (from locale/IP)
3. Jurisdiction-specific verification:

   US (age < 13):      Parent consent required (existing COPPA flow)
   US (age 13-15):     Self-register, parent notification
   Australia (age < 16): Yoti mandatory age verification + parent consent
   EU (age < 16):      Yoti or parent consent verification
   UK (age < 13):      Parent consent required
   UK (age 13-15):     Yoti or parent consent
   Default (age < 16): Parent consent required

4. Age tier assigned: 5-9 / 10-12 / 13-15
5. Feature permissions loaded from age_tier_configs
```

### Graduated Unlocks

Parents can override tier defaults:
- **Unlock features early:** Parent can enable DMs for a mature 11-year-old
- **Restrict features:** Parent can disable video posting for a 14-year-old
- **Override stored in:** `age_tier_configs.feature_overrides` (JSON)
- **Audit logged:** All parent overrides create an audit entry

### Profile Lifecycle

The `profiles` table (social identity) is separate from `users` (auth identity):

- **Created:** Automatically when a child completes Social app onboarding (age verification + parent consent). NOT created on Safety-only registration.
- **Safety-only users:** Parents who only use the Safety app have NO profile record. All Safety app queries are profile-independent.
- **Consistency:** Profile creation is transactional with the Social app onboarding flow. If onboarding fails, no orphan profile is created.
- **Deletion:** Profile soft-deleted when user account is deleted (existing `SoftDeleteMixin`). GDPR/COPPA erasure removes profile data.

### Offline Strategy (Mobile Apps)

**Safety app (parent):** Dashboard data cached locally. Alerts viewable offline (last sync). No write operations required offline.

**Social app (child):**
- **Feed:** Cached for offline viewing (last 50 posts). Pull-to-refresh when online.
- **Messages:** Cached conversation history viewable offline. New messages queued as "sending..." and delivered when reconnected.
- **Post creation (5-9 and 10-12 tiers):** **BLOCKED offline.** Pre-publish moderation requires network. UI shows "You need internet to post." Draft saved locally.
- **Post creation (13-15 tier):** Queued offline, submitted to post-publish moderation on reconnect. UI shows "Will post when you're back online."
- **Media upload:** Blocked offline (requires Cloudflare pipeline). Drafts with media show placeholder.
- **Notifications:** Delivered on reconnect via Expo push notification queue.

### Age Transitions

When a child's birthday crosses a tier boundary:
1. System detects DOB-based tier change on daily job
2. Parent notification: "Your child is now in the [Pre-teen/Teen] tier. New features are available."
3. 7-day grace period: new features visible but labeled "New! Ask your parent to review"
4. After 7 days or parent acknowledgment: features fully enabled
5. Parent can restrict any new feature during or after grace period

---

## 4. Content Moderation Architecture

### Pipeline Overview

```
Content submitted (post/comment/message/image/video)
         │
         ▼
┌──────────────────────────────┐
│  Age Tier Router              │
│  Determines pipeline:         │
│  5-9:  ALL pre-publish        │
│  10-12: text post-pub,        │
│         image/video pre-pub   │
│  13-15: ALL post-publish      │
└──────────┬───────────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
PRE-PUBLISH    POST-PUBLISH
     │              │
     ▼              ▼
┌─────────┐   ┌──────────┐
│ Hold in  │   │ Publish   │
│ queue    │   │ immediately│
└────┬────┘   └─────┬─────┘
     │              │
     ▼              ▼
┌──────────────────────────────┐
│  FAST PATH: Keyword Check     │
│  <100ms, configurable lists   │
│  per age tier                 │
│                               │
│  BLOCK → notify parent        │
│  ALLOW → continue             │
│  UNCERTAIN → AI classify      │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  AI CLASSIFICATION             │
│  Text: Vertex AI / keyword     │
│  Image: Hive/Sensity via CF    │
│  Video: Frame extract + Hive   │
│                               │
│  14-category risk taxonomy:    │
│  self-harm, violence,          │
│  sexual, bullying, grooming,   │
│  hate, drugs, weapons,         │
│  personal-info, academic-      │
│  dishonesty, emotional-dep,    │
│  deepfake, radicalization,     │
│  age-inappropriate             │
│                               │
│  Score 0-100 per category     │
└──────────┬───────────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
  APPROVE      REJECT/ESCALATE
     │              │
     ▼              ▼
Pre-pub:        Parent notified
release content Alert created
                Content removed/held
Post-pub:       Moderation queue entry
content already Appeal flow available
visible
```

### Moderation SLAs

| Tier | Pipeline | Target Latency | Severe Content |
|------|----------|---------------|----------------|
| 5-9 | Pre-publish | <2s p95 | Block + immediate parent alert |
| 10-12 | Pre-pub (image/video), post-pub (text) | <2s pre-pub, <30s takedown | Block + immediate parent alert |
| 13-15 | Post-publish | <60s takedown | Remove + parent alert + moderator review |

### Image/Video Pipeline (Cloudflare)

```
Upload request
     │
     ▼
┌────────────────────────┐
│ Client uploads to       │
│ Cloudflare R2 via       │
│ pre-signed URL          │
│ (media/ module provides)│
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐       ┌──────────────────────┐
│ Cloudflare Images       │       │ Cloudflare Stream     │
│ (for images)            │       │ (for video)           │
│                         │       │                       │
│ Auto-resize variants:   │       │ Auto-transcode:       │
│ - thumbnail (150px)     │       │ - 360p, 720p, 1080p   │
│ - medium (600px)        │       │ - HLS + DASH           │
│ - full (1200px)         │       │ - Thumbnail extraction │
└──────────┬─────────────┘       └──────────┬────────────┘
           │                                 │
           └──────────┬──────────────────────┘
                      │
                      ▼
              Webhook to backend
              /api/v1/media/webhook
                      │
                      ▼
              ┌───────────────┐
              │ Hive/Sensity   │
              │ classification │
              │ (existing      │
              │ integration)   │
              └───────┬───────┘
                      │
                ┌─────┴──────┐
                ▼            ▼
             APPROVE      REJECT
             Set status    Set status
             = approved    = rejected
             CDN serves    CDN blocks
             content       (returns 403)
```

### CSAM Detection & NCMEC Reporting (MANDATORY — Legal Obligation)

Under US federal law (18 U.S.C. 2258A), any electronic service provider that obtains knowledge of CSAM must report to NCMEC via CyberTipline. This is non-negotiable for a children's social platform.

**Pipeline integration (before Phase 2 Social launch):**

```
Image/video uploaded
     │
     ▼
┌─────────────────────────┐
│ CSAM Detection           │
│ (PhotoDNA or equivalent) │
│ Runs BEFORE any other    │
│ moderation step          │
└──────────┬──────────────┘
     ┌─────┴──────┐
     ▼            ▼
  CLEAN        MATCH
  Continue      │
  to normal     ▼
  moderation   ┌──────────────────────┐
               │ 1. Block content      │
               │ 2. Preserve evidence  │
               │    (hash + metadata,  │
               │    DO NOT delete)     │
               │ 3. Submit CyberTipline│
               │    report via API     │
               │ 4. Suspend account    │
               │ 5. Alert admin        │
               │ 6. Log for law        │
               │    enforcement        │
               └──────────────────────┘
```

**Requirements:**
- PhotoDNA integration (Microsoft provides free for qualifying services) or equivalent perceptual hash matching
- NCMEC CyberTipline API integration for automated reporting
- Evidence preservation: content must be retained (encrypted, access-restricted) for law enforcement even after platform removal
- Account suspension: automatic on CSAM match, no appeal flow
- Audit trail: immutable log of all CSAM detections and reports
- Staff training: documented process for handling CSAM reports

**Phase:** Must be production-ready before Phase 2 Social app beta launch. Added to Phase 1 AI Safety track as P1-A7.

### Social-Specific Risk Models (New)

| Model | What it detects | Training approach | Phase |
|-------|----------------|-------------------|-------|
| Grooming detection | Escalating intimacy in message threads (flattery → isolation → sexual content) | Sequence analysis on message history, NCMEC patterns | P1 |
| Cyberbullying detection | Repeated targeting of same user, severity escalation, group pile-on | Frequency + sentiment analysis per target, social graph signals | P1 |
| Sexting detection | Text + image correlation (suggestive text + image from same user) | Multi-modal classification, Hive nudity detection | P1 |
| Predator contact detection | Adult (or age-misrepresenting) user contacting children, behavioral patterns | Age-inappropriate contact graph analysis, message pattern analysis | P2 |
| Isolation pattern detection | Sudden drop in social connections, withdrawal from group chats | Behavioral baseline deviation | P2 |
| Self-harm correlation | Cross-signal: social content + AI chatbot usage + behavioral change | Intelligence engine cross-product correlation | P3 |

---

## 5. Pricing & Billing

### Tier Structure

| Tier | Price | Annual | Target | Key Features |
|------|-------|--------|--------|-------------|
| **Free** | $0 | — | Every parent of a Bhapi Social user | Social app (full), Safety app (24h summary, critical alerts only) |
| **Family** | $9.99/mo | $99/yr (save 17%) | Safety-conscious parents | Full AI monitoring (10+ platforms), Bhapi Social monitoring, all alerts, weekly reports, 5 members |
| **Family Plus** | $14.99/mo | $149/yr (save 17%) | Parents wanting full suite | Everything + screen time + location + mood analysis + cross-product intelligence, 10 members |
| **School** | $3-6/student/yr | Volume discount | Districts | AI governance + Chromebook deploy + teacher dashboard + compliance, unlimited members |
| **Enterprise** | Custom | Custom | Large districts, club chains | All features + API + SLA + dedicated support + SCIM |

### Conversion Funnel

```
Child installs Bhapi Social (free)
     │
     ▼
Parent prompted to install Bhapi Safety
     │
     ▼
Free tier auto-created (24h summary + critical alerts)
     │
     ├── Wants full AI monitoring + all alerts ──► FAMILY ($9.99/mo)
     ├── Wants screen time + location ────────────► FAMILY+ ($14.99/mo)
     └── School admin discovers platform ─────────► SCHOOL (per-seat)
                                                     └── District ──► ENTERPRISE
```

### Stripe Implementation

| Work Item | Detail |
|-----------|--------|
| Free tier | No Stripe session. Feature gating in middleware via `subscription.tier` check |
| Family Plus | New Stripe Price: $14.99/mo recurring, $149/yr recurring |
| Annual pricing | New annual Price objects for Family ($99/yr) and Family+ ($149/yr) |
| Tier upgrade | Stripe proration on mid-cycle upgrade (Family → Family+) |
| Cross-app entitlement | Safety app checks `subscription.tier` via API on launch, caches in SecureStore |
| Social app feature gate | Creative tools check tier via `shared-api` package |
| School governance add-on | Governance features as Stripe add-on to school per-seat plan |

---

## 6. School Go-To-Market

### Strategy: Compliance-Led → Channel Partnerships

#### Phase 1: Compliance-Led Entry

1. **Ohio AI Mandate (Jul 1, 2026):** Ship AI governance package — policy template generator, AI tool inventory, compliance dashboard, audit trail. Target Ohio's 610+ school districts.
2. **Australian legislation:** Position as compliant platform for schools affected by Social Media Minimum Age Bill.
3. **Chromebook deployment:** Google Admin Console integration, Chrome Web Store enterprise listing, mass extension deployment.
4. **Value proposition to schools:** "Bhapi is the AI governance compliance tool you need, AND it includes AI monitoring and a safe social platform for students."

#### Phase 2: Channel Partnerships

1. **Target partners:** EdTech distributors (CDW-G, SHI), ISTE members, state education technology associations
2. **Partner package:** Sales collateral, compliance documentation, ROI calculator, white-label deployment guide
3. **Revenue share:** Standard EdTech channel margins (15-25%)
4. **Support:** White-glove onboarding for first 10 school pilots

---

## 7. Regulatory Compliance

### Compliance Matrix

| Requirement | US COPPA | Ohio AI | EU AI Act | Australia | UK AADC | Phase |
|-------------|:--------:|:-------:|:---------:|:---------:|:-------:|:-----:|
| Parental consent (under 13) | **Done** | — | Req | Req | Req | P0 |
| Parental consent (under 16) | — | — | Req | **Req** | Req | P1 |
| Age verification (Yoti) | **Done** | — | Req | **Mandatory** | Req | P1 |
| Third-party consent itemized | **Done** | — | Req | — | — | P0 |
| Written security program | **Done** | Req | Req | Req | — | P0 |
| Data retention policy | **Done** | — | Req | Req | Req | P0 |
| AI transparency disclosures | — | Req | **Mandatory** | — | — | P1-P2 |
| Conformity self-assessment | — | — | **Mandatory** | — | — | P2 |
| Risk management system doc | — | — | **Mandatory** | — | — | P2 |
| Bias testing framework | — | — | **Mandatory** | — | — | P2 |
| AI governance policy generator | — | **Mandatory** | — | — | — | P1 |
| eSafety Commissioner reporting | — | — | — | **Mandatory** | — | P1 |
| 24h content takedown SLA | — | — | — | **Mandatory** | — | P1 |
| Privacy by default (children) | **Done** | — | Req | Req | **Mandatory** | P0 |
| No nudge techniques | — | — | — | — | **Mandatory** | P3 |
| DPIA | — | — | Req | — | **Mandatory** | P3 |
| Incident reporting (72h) | — | — | **Mandatory** | **Mandatory** | — | P2 |
| Right to erasure | **Done** | — | **Mandatory** | — | **Mandatory** | P0 |
| EU database registration | — | — | **Mandatory** | — | — | P2 |
| CSAM reporting (NCMEC CyberTipline) | **Mandatory** | — | Mandatory | **Mandatory** | — | P1 |

### Age Gate Logic by Jurisdiction

| Jurisdiction | Min Age (Social) | Verification Method | Parent Consent Under |
|-------------|:----------------:|--------------------:|:--------------------:|
| US | 13 | Parent consent (COPPA) | 13 |
| Australia | 16* | Yoti mandatory | 16 |
| EU | 16 | Yoti or parent consent | 16 |
| UK | 13 | Yoti or parent consent | 16 |
| Default | 13 | Parent consent | 16 |

*Note: Australian Social Media Minimum Age Bill bans under-16s from mainstream social media. Legal counsel must confirm in Phase 0 (P0-9) whether Bhapi Social qualifies for exemption as a safety-first platform. The `age_tier_configs.jurisdiction` column supports per-country minimum ages. **Fallback (if exemption denied):** AU Social app serves 16+ only via jurisdiction-based age gate; Safety app serves all ages regardless. This fallback is a first-class configuration, not an afterthought.

---

## 8. Implementation Roadmap

### Approach: "Safety Shell First with Social Head Start" (Approach 1.5)

Build outward from the strongest asset (AI Portal). Ship parent Safety app first, build social infrastructure in parallel, launch Social app once safety pipeline is proven on mobile.

### Production Support Overhead (All Phases)

Each phase reserves **15-20% of engineering capacity** for production support, bug fixes, incident response, and on-call duties for the existing v2.1.0 system. This is NOT included in deliverable effort estimates. Effective feature capacity per phase:

| Phase | Engineers | Gross PW | Production Overhead (15%) | Net Feature PW |
|-------|:---------:|:--------:|:-------------------------:|:--------------:|
| Phase 0 | 2-3 | 10-15 | 1.5-2.3 | 8.5-12.7 |
| Phase 1 | 5-7 | 35-49 | 5.3-7.4 | 29.7-41.6 |
| Phase 2 | 8-10 | 64-80 | 9.6-12.0 | 54.4-68.0 |
| Phase 3 | 10-13 | 60-78 | 9.0-11.7 | 51.0-66.3 |

### Phase 0: Emergency Stabilization (Weeks 1-5, Mar 17 — Apr 22)

**Team:** 2-3 engineers
**Budget:** 10-15 person-weeks (8.5-12.7 net after production overhead)
**Regulatory deadline:** COPPA 2026 — April 22

| ID | Deliverable | Effort | Owner | Tests Required |
|----|------------|--------|-------|---------------|
| P0-1 | COPPA 2026 enforcement | — | Backend | **DONE** |
| P0-2 | Legacy repo audit: document all bhapi-inc features as reference | 1-2 pw | Full-stack | — |
| P0-3 | Archive legacy repos (README → bhapi-ai-portal, set read-only). **Clean-break decision:** No MongoDB data migration. Legacy app data is not migrated — negligible active users, different data model, security risks of importing unvalidated data into a children's platform. Document this decision in ADR-010. | 0.5 pw | DevOps | — |
| P0-4 | ADR-006: Two-app mobile strategy (Safety + Social) | 0.5 pw | Architecture | — |
| P0-5 | ADR-007: Cloudflare R2/Images/Stream for media | 0.5 pw | Architecture | — |
| P0-6 | ADR-008: Real-time WebSocket as separate service | 0.5 pw | Architecture | — |
| P0-7 | ADR-009: Age-tier permission model (5-9, 10-12, 13-15) | 0.5 pw | Architecture | — |
| P0-8 | Expo monorepo scaffold with Turborepo + shared packages (stubs) | 2-3 pw | Mobile | Shared pkg unit tests (≥20) |
| P0-9 | Australian compliance legal analysis: determine Social Media Minimum Age Bill exemption status for Bhapi Social. **If denied, design 16+ AU fallback as first-class configuration.** Document jurisdiction-specific age gates. | 1-2 pw | Legal | — |
| P0-10 | Pre-publish moderation architecture design doc | 1 pw | Backend | — |
| P0-11 | Hiring: post 3-4 roles (mobile, backend, safety/ML) | Ongoing | Management | — |

**Exit criteria:**
- [ ] COPPA 2026 compliant (done)
- [ ] 3/3 legacy repos archived
- [ ] ADR-006 through ADR-009 accepted
- [ ] Monorepo compiles with empty app shells, CI green
- [ ] Australian compliance requirements documented
- [ ] Moderation architecture designed and reviewed
- [ ] Hiring pipeline active with first interviews
- [ ] Test count: ≥1,739 (current + shared pkg tests)

---

### Phase 1: Moat Defense + Safety Foundation (Weeks 6-12, Apr 23 — Jun 8)

**Team:** 5-7 engineers
**Budget:** 35-49 person-weeks

#### Track A: School Market (2 engineers)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P1-S1 | Google Admin Console integration for mass extension deployment | 3-4 pw | Unit ≥30, E2E ≥20, Security ≥10 |
| P1-S2 | School IT admin dashboard (device inventory, deployment status, policy management) | 2-3 pw | Unit ≥20, E2E ≥15, Security ≥10 |
| P1-S3 | Ohio AI governance: policy template generator, AI tool inventory, risk assessment, compliance dashboard | 3-4 pw | Unit ≥40, E2E ≥25, Security ≥10 |
| P1-S4 | Chromebook-optimized extension with offline capability | 2 pw | Unit ≥15, E2E ≥10 |
| P1-S5 | Compliance reporting: school board PDF export | 1-2 pw | Unit ≥10, E2E ≥5 |
| P1-S6 | Chrome Web Store enterprise listing submission | 1 pw | — |
| P1-S7 | First school pilot identified and onboarding started | Ongoing | — |

#### Track B: Safety App MVP (2 engineers)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P1-M1 | `shared-auth`: JWT tokens, SecureStore, biometric unlock, session refresh | 2 pw | Unit ≥25 |
| P1-M2 | `shared-api`: REST client, WebSocket client, offline queue, retry logic | 2 pw | Unit ≥25 |
| P1-M3 | `shared-i18n`: 6 languages, locale detection | 1 pw | Unit ≥10 |
| P1-M4 | `shared-ui`: BhapiLogo, Button, Card, Input, Badge, Toast, Avatar | 2 pw | Component ≥30 |
| P1-M5 | Safety app — Auth screens: login, register, magic link, email verification | 2 pw | Component ≥15, Integration ≥10 |
| P1-M6 | Safety app — Dashboard: activity summary, risk overview, recent alerts, platform breakdown | 3 pw | Component ≥20, Integration ≥15 |
| P1-M7 | Safety app — Alerts: list, detail, snooze, escalation | 2 pw | Component ≥15, Integration ≥10 |
| P1-M8 | Safety app — Group management: members, invitations, consent | 2 pw | Component ≥15, Integration ≥10 |
| P1-M9 | Safety app — Push notifications (Expo Notifications) | 1-2 pw | Unit ≥10, Integration ≥5 |
| P1-M10 | Safety app — TestFlight + Android internal testing | 1 pw | Maestro E2E ≥10 |

#### Track C: AI Safety & Moderation (1-2 engineers)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P1-A1 | Image moderation pipeline: CF Images webhook → Hive/Sensity → approve/reject | 3 pw | Unit ≥30, E2E ≥20, Security ≥10 |
| P1-A2 | Video moderation pipeline: CF Stream → frame extract → classify → approve/reject | 2-3 pw | Unit ≥25, E2E ≥15, Security ≥10 |
| P1-A3 | Fast-path text classifier: keyword <100ms, hold-and-release queue, async AI | 2-3 pw | Unit ≥30, E2E ≥20, Security ≥5, Perf ≥5 |
| P1-A4 | Social risk models v1: grooming, cyberbullying, sexting detection | 3-4 pw | Unit ≥40, E2E ≥20 |
| P1-A5 | Australian safety: Yoti AU flow, eSafety reporting pipeline, 24h takedown SLA | 2-3 pw | Unit ≥20, E2E ≥15, Security ≥10 |
| P1-A6 | `src/moderation/` module: pipeline, takedown, queue CRUD, dashboard API | 3 pw | Unit ≥35, E2E ≥25, Security ≥15 |
| P1-A7 | CSAM detection + NCMEC reporting: PhotoDNA integration, CyberTipline API, evidence preservation, account suspension, audit trail | 2-3 pw | Unit ≥20, E2E ≥10, Security ≥10 |

#### Track D: Real-Time Service (1 engineer, partial)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P1-R1 | WebSocket service: FastAPI app, JWT auth, connection management, heartbeat | 2 pw | Unit ≥20, WS E2E ≥15, Security ≥10 |
| P1-R2 | Redis pub/sub: event bridge between monolith and real-time service | 1-2 pw | Unit ≥15, Integration ≥10 |
| P1-R3 | Push notification relay: Expo push token registration, delivery | 1-2 pw | Unit ≥10, E2E ≥10 |
| P1-R4 | Presence system: online/offline/last-seen via Redis | 1 pw | Unit ≥10 |

#### Track E: Social Head Start (1-2 engineers, weeks 8-12)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P1-H1 | Social DB models + Alembic migrations 032-037 | 2-3 pw | Unit ≥20, Migration ≥10 |
| P1-H2 | `src/social/` module: feed CRUD, profile CRUD, follow/unfollow | 2-3 pw | Unit ≥40, E2E ≥30, Security ≥15 |
| P1-H3 | `src/contacts/` module: requests, parent approval, block | 1-2 pw | Unit ≥20, E2E ≥15, Security ≥10 |
| P1-H4 | `src/age_tier/` module: permission engine, tier assignment, rule matrix | 1-2 pw | Unit ≥25, E2E ≥15, Security ≥10 |
| P1-H5 | Social app screen shells: feed, profile, chat, settings, onboarding (nav wired) | 2-3 pw | Component ≥20 |
| P1-H6 | `shared-ui` social components: PostCard, CommentThread, MessageBubble, ContactRequest | 1-2 pw | Component ≥15 |

**Phase 1 exit criteria:**
- [ ] Chrome Web Store enterprise listing live
- [ ] Ohio governance MVP deployed and demo-ready
- [ ] ≥1 school pilot onboarding
- [ ] Safety app in TestFlight + Android internal testing
- [ ] Pre-publish moderation pipeline: <2s p95, image pipeline functional
- [ ] All social backend APIs functional with full test coverage
- [ ] Social app screen shells navigable with shared-ui components
- [ ] eSafety reporting pipeline live (Australian compliance)
- [ ] WebSocket service deployed with presence working
- [ ] Test count: ≥2,499
- [ ] Security test coverage: 100% of new endpoints have auth/RBAC/age-tier tests
- [ ] All Alembic migrations committed and pushed

---

### Phase 2: Social Launch + Platform Expansion (Weeks 13-20, Jun 9 — Aug 3)

**Team:** 8-10 engineers
**Budget:** 64-80 person-weeks
**Regulatory deadlines:** Ohio AI Mandate (Jul 1), EU AI Act (Aug 2)

#### Track A: Social App Build (3-4 engineers)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P2-S1 | Onboarding: age verification (Yoti), parent consent, profile creation, tier assignment | 3 pw | Comp ≥15, Integ ≥10, Security ≥10 |
| P2-S2 | Feed: create post, timeline (FlashList), like, comment, hashtags | 4-5 pw | Comp ≥25, Integ ≥20, Backend E2E ≥20 |
| P2-S3 | Profiles: view/edit, avatar upload, followers, post history | 2-3 pw | Comp ≥15, Integ ≥10 |
| P2-S4 | Messaging: conversation list, real-time chat (WS), media messages, typing, read receipts | 4-5 pw | Comp ≥20, Integ ≥15, WS E2E ≥15 |
| P2-S5 | Contacts: search, request, accept/reject, parent approval (5-12), block/report | 2-3 pw | Comp ≥15, Integ ≥10, Security ≥10 |
| P2-S6 | Age-tier UX: feature visibility, locked explanations, unlock requests | 2-3 pw | Comp ≥15, Integ ≥10 |
| P2-S7 | Media: CF R2 upload, CF Images resize, CF Stream transcode, caching | 3 pw | Integ ≥15, Backend E2E ≥15 |
| P2-S8 | Push notifications: messages, likes, comments, contacts, moderation | 2 pw | Comp ≥10, Integ ≥5 |
| P2-S9 | Reporting: report post/user/message, reasons, status | 1-2 pw | Comp ≥10, Backend E2E ≥10 |
| P2-S10 | Settings: privacy, notifications, language, theme, account | 1-2 pw | Comp ≥10 |
| P2-S11 | Moderation UX: pre-publish hold ("Your post is being reviewed"), takedown notice, appeal | 2-3 pw | Comp ≥15, Integ ≥10 |
| P2-S12 | TestFlight + Android beta, ≥50 beta users | 1-2 pw | Maestro E2E ≥20 |

#### Track B: Safety App v2 (2 engineers)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P2-M1 | Bhapi Social activity monitoring: posts, messages, contacts, time, flags | 3-4 pw | Comp ≥20, Integ ≥15, Security ≥10 |
| P2-M2 | Device agent: app usage, screen time, background sync | 4-5 pw | Unit ≥30, E2E ≥20, Security ≥10 |
| P2-M3 | Cross-product alert view: unified AI + social feed, severity, drill-down | 2-3 pw | Comp ≥15, Integ ≥10 |
| P2-M4 | Child profile: combined AI + social timeline, risk trend, platform breakdown | 2 pw | Comp ≥10, Integ ≥10 |
| P2-M5 | Contact approval: parent notification, requester profile, approve/deny | 1-2 pw | Comp ≥10, Integ ≥5, Security ≥5 |
| P2-M6 | App Store submission (iOS + Google Play) | 1-2 pw | — |

#### Track C: Compliance (1-2 engineers)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P2-C1 | Ohio governance final: district customization, AI tool import, audit trail, board report | 2-3 pw | Unit ≥25, E2E ≥15, Security ≥10 |
| P2-C2 | EU AI Act: conformity assessment, tech docs portal, risk management, bias testing, benchmarks | 6-8 pw | Unit ≥40, E2E ≥30, Security ≥15 |
| P2-C3 | EU database registration submission | 1 pw | E2E ≥5 |
| P2-C4 | Australian: age verification enforcement, eSafety live, 24h SLA monitoring, cyberbullying workflow | 2-3 pw | Unit ≥20, E2E ≥15, Security ≥10 |
| P2-C5 | UK AADC: gap analysis + privacy-by-default implementation | 2 pw | Unit ≥15, E2E ≥10 |
| P2-C6 | State compliance framework: extensible for CA, TX, FL, NY (2027 prep) | 1-2 pw | Unit ≥10 |

#### Track D: Safety Engine (1-2 engineers)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P2-E1 | Age-tier enforcement: permission checks on all social endpoints, feature gating middleware | 2-3 pw | Unit ≥25, Security ≥20 |
| P2-E2 | Social graph analysis: age-inappropriate contacts, isolation detection, influence mapping | 3-4 pw | Unit ≥30, E2E ≥20 |
| P2-E3 | Behavioral baselines: per-child norms, deviation alerting | 2-3 pw | Unit ≥20, E2E ≥15 |
| P2-E4 | Pre-publish live: 5-9 and 10-12 tiers, <2s p95, parent notification on blocks | 2-3 pw | Unit ≥20, E2E ≥15, Perf ≥10 |
| P2-E5 | Post-publish live: 13-15 tier, <60s takedown, flagging, auto-escalation | 2 pw | Unit ≥15, E2E ≥10 |
| P2-E6 | Moderation dashboard: queue, bulk actions, pattern detection, SLA tracking | 2-3 pw | Unit ≥20, E2E ≥15 |

**Phase 2 exit criteria:**
- [ ] Social app in beta (TestFlight + Android), ≥50 beta users
- [ ] Safety app submitted to App Store (iOS + Google Play)
- [ ] Ohio governance deployed before Jul 1 deadline
- [ ] EU AI Act compliant before Aug 2 deadline
- [ ] Australian age verification + eSafety reporting live
- [ ] UK AADC gap analysis complete, privacy-by-default implemented
- [ ] Pre-publish moderation operational for under-13: <2s p95, <0.1% false negative on severe
- [ ] Post-publish takedown: <60s p95 for 13-15 tier
- [ ] Age-tier enforcement: all social endpoints gated (verified by security tests)
- [ ] Behavioral baselines computing for all active child accounts
- [ ] ≥5 school deployments active
- [ ] Test count: ≥3,689
- [ ] Mobile test coverage: ≥80% screen coverage
- [ ] All new Alembic migrations committed and pushed
- [ ] 0 open critical/high security findings

---

### Phase 3: Competitive Parity + Market Launch (Weeks 21-26, Aug 4 — Sep 17)

**Team:** 10-13 engineers
**Budget:** 60-78 person-weeks

#### Track A: Public Launch (2-3 engineers)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P3-L1 | Bhapi Social — App Store + Google Play public release | 1-2 pw | Maestro E2E ≥15 |
| P3-L2 | Bhapi Safety — App Store + Google Play public release | 1-2 pw | Maestro E2E ≥15 |
| P3-L3 | App Store optimization: screenshots, descriptions, keywords (6 languages) | 1-2 pw | — |
| P3-L4 | Landing page: bhapi.ai unified messaging, download links, school/family CTAs | 1-2 pw | Portal vitest ≥10 |
| P3-L5 | Onboarding: Safety → invite child to Social, Social → prompt parent for Safety | 2 pw | Comp ≥15, Integ ≥10 |

#### Track B: Cross-Product Intelligence (2 engineers)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P3-I1 | `src/intelligence/` module: event bus, correlation rules per risk category | 3-4 pw | Unit ≥40, E2E ≥25, Security ≥15 |
| P3-I2 | Unified risk scoring: weighted AI + social signals, confidence, trends | 2-3 pw | Unit ≥25, E2E ≥15 |
| P3-I3 | Parent alert enrichment: "X in AI usage AND Y in social activity" | 2 pw | Unit ≥15, E2E ≥10 |
| P3-I4 | Behavioral anomaly correlation: AI spike + social withdrawal, evasion detection | 2-3 pw | Unit ≥20, E2E ≥15 |

#### Track C: Feature Expansion (3-4 engineers)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P3-F1 | Creative tools: AI art (moderated), story templates, drawing (react-native-skia), stickers | 4-5 pw | Comp ≥20, Backend Unit ≥30, E2E ≥15, Security ≥10 |
| P3-F2 | Screen time: per-app limits, schedules, extension requests, reports | 3-4 pw | Unit ≥25, E2E ≥20, Comp ≥15, Security ≥10 |
| P3-F3 | Location: real-time map, geofencing, history, check-in from panic button | 3-4 pw | Unit ≥25, E2E ≥20, Comp ≥15, Security ≥10 |
| P3-F4 | Unified parent dashboard: combined Social + AI view, risk summary, action center | 3-4 pw | Comp ≥20, Integ ≥15, Portal vitest ≥15 |

#### Track D: Business (2 engineers)

| ID | Deliverable | Effort | Tests |
|----|------------|--------|-------|
| P3-B1 | Bundle pricing: Free/Family/Family+/School/Enterprise, Stripe, annual discount | 2-3 pw | Unit ≥20, E2E ≥15, Security ≥10 |
| P3-B2 | Channel partnership package: collateral, compliance docs, ROI calculator, deployment guide | 2-3 pw | — |
| P3-B3 | Public API beta: OAuth 2.0, rate limiting tiers, webhooks, interactive docs | 3-4 pw | Unit ≥30, E2E ≥20, Security ≥15 |
| P3-B4 | SOC 2 Type II audit initiation: evidence collection, policy docs | 2 pw | — |

**Phase 3 exit criteria:**
- [ ] Both apps publicly available on iOS + Android App Stores
- [ ] ≥500 family signups
- [ ] ≥10 school deployments
- [ ] App Store rating ≥4.0 (both apps)
- [ ] Bundle conversion ≥10% free → paid
- [ ] Cross-product intelligence engine live, generating correlated alerts
- [ ] Screen time + location live for Family Plus tier
- [ ] Creative tools live (AI art + story creation) with moderation
- [ ] ≥2 channel partners signed
- [ ] Public API beta with ≥3 external integrations
- [ ] SOC 2 audit initiated
- [ ] Test count: ≥4,469
- [ ] Prod E2E: ≥195 tests, all passing post-deploy
- [ ] Security incidents: 0 data breaches, 0 regulatory violations
- [ ] All Alembic migrations committed and pushed

---

## 9. Testing & Quality Strategy

### Test Pyramid

```
                    ┌──────────┐
                    │  Prod E2E │  Per-release smoke (195 target)
                   ┌┴──────────┴┐
                   │  Security   │  Per-endpoint auth/RBAC/injection (520 target)
                  ┌┴────────────┴┐
                  │    E2E        │  Per-feature full flow (1,400 target)
                 ┌┴──────────────┴┐
                 │     Unit        │  Per-function logic (1,530 target)
                ┌┴────────────────┴┐
                │   Mobile          │  Per-screen component + integration (824 target)
                └──────────────────┘
```

### Test Counts by Phase

Per-deliverable test targets are the source of truth. Phase-level totals are aggregated from deliverable requirements.

| Phase | Backend (unit+E2E+security) | Mobile (component+integration+E2E) | Prod E2E | Total |
|-------|:--------------------------:|:-----------------------------------:|:--------:|:-----:|
| Current (v2.1.0) | 1,578 | 174 (portal) | 95 | ~1,847 |
| Phase 0 exit | +20 | +20 | — | ~1,887 |
| Phase 1 exit | +875 | +200 | +30 | ~2,992 |
| Phase 2 exit | +900 | +350 | +40 | ~4,282 |
| Phase 3 exit | +550 | +250 | +30 | ~5,112 |

**Note:** Backend count from CLAUDE.md (1,578 passed = ~580 unit + ~700 E2E + ~170 security + ~128 other). Phase increments are summed from per-deliverable targets in Section 8. Production overhead buffer: 15-20% of engineering capacity per phase is reserved for production support, bug fixes, and incident response (not counted in deliverable effort).

### Mandatory Security Tests Per Endpoint

Every API endpoint must have tests for:
1. Unauthenticated access returns 401
2. Wrong role/permission returns 403
3. Cross-tenant isolation (user A can't access user B's data)
4. Age-tier enforcement (child can't access parent endpoints, 5-9 can't access 13-15 features)
5. COPPA consent gates (third-party calls blocked without consent)
6. Input validation (SQL injection, XSS, path traversal)
7. Rate limiting enforced
8. RBAC per role (parent, child, school-admin, moderator, support, super-admin)
9. Sensitive data not leaked in error responses
10. Soft-deleted records not accessible

### Mandatory E2E Tests Per Feature

1. Happy path (complete flow)
2. Auth required (401)
3. Forbidden (403)
4. Validation errors (422)
5. Not found (404)
6. Pagination correctness
7. Edge cases (empty state, max limits, boundaries)
8. Idempotency
9. i18n (localized error messages)

### Content Moderation Testing

| Category | Tests | Method |
|----------|-------|--------|
| True positive | Known harmful content blocked | Synthetic test corpus |
| True negative | Innocent content allowed | Normal child content samples |
| False positive | Innocent content wrongly blocked | Edge cases: gaming slang, dark humor |
| False negative | Harmful content missed | Obfuscation, leetspeak, Unicode tricks |
| Latency | Pre-publish <2s p95 | Performance test suite |
| Age-tier routing | Correct pipeline per tier | Parametrized tests across tiers |
| Escalation | Severe content → immediate alert | Severity corpus, verify notification SLA |

### CI/CD Pipeline

```
On PR:
  1. Ruff lint (backend)
  2. ESLint + tsc --noEmit (frontend + mobile)
  3. pytest tests/unit/
  4. pytest tests/e2e/
  5. pytest tests/security/
  6. vitest (portal)
  7. jest (mobile shared packages)
  8. Coverage ≥80% on new code
  ALL MUST PASS

On merge to master:
  1. Full test suite
  2. Docker build
  3. Deploy to Render
  4. Prod E2E smoke tests
  5. Alert on failure

On mobile release:
  1. Shared package tests
  2. App component tests
  3. tsc --noEmit
  4. EAS Build (iOS + Android)
  5. Maestro E2E
  6. Submit to TestFlight / Internal
  7. Prod E2E after store release
```

### Definition of Done (Every Deliverable)

- [ ] Unit tests written and passing
- [ ] E2E tests written and passing
- [ ] Security tests written and passing (every endpoint)
- [ ] Mobile tests written and passing (every screen)
- [ ] `tsc --noEmit` passes
- [ ] CI green
- [ ] CLAUDE.md updated (if new module/routes)
- [ ] Alembic migration created AND committed (if model changes)
- [ ] i18n strings in all 6 language files
- [ ] Code reviewed
- [ ] Prod E2E updated for new endpoints

---

## 10. Success Metrics

### Phase 0 Exit (Apr 22)

| Metric | Target |
|--------|--------|
| COPPA compliance | 100% |
| Legacy repos archived | 3/3 |
| ADRs accepted | 006-009 |
| Monorepo compiles | CI green |
| Test count | ≥1,739 |

### Phase 1 Exit (Jun 8)

| Metric | Target |
|--------|--------|
| Chrome Web Store listing | Live |
| Ohio governance | Deployed, demo-ready |
| School pilots | ≥1 onboarding |
| Safety app | TestFlight + Android internal |
| Moderation pipeline | Pre-publish <2s p95 |
| Social backend APIs | All CRUD tested |
| WebSocket service | Deployed, presence working |
| eSafety reporting | Pipeline live |
| Test count | ≥2,549 |
| Security coverage | 100% new endpoints |

### Phase 2 Exit (Aug 3)

| Metric | Target |
|--------|--------|
| Social app | Beta, ≥50 users |
| Safety app | App Store submitted |
| Ohio governance | Live before Jul 1 |
| EU AI Act | Compliant before Aug 2 |
| AU compliance | Age verify + eSafety live |
| Pre-publish moderation | <2s p95, <0.1% FN on severe |
| Post-publish takedown | <60s p95 |
| School deployments | ≥5 |
| Test count | ≥3,739 |
| Mobile coverage | ≥80% screens |

### Phase 3 Exit (Sep 17)

| Metric | Target |
|--------|--------|
| Both apps | Public on iOS + Android |
| Family signups | ≥500 |
| School deployments | ≥10 |
| App Store rating | ≥4.0 |
| Free → paid conversion | ≥10% |
| Intelligence engine | Live, generating alerts |
| Screen time + location | Live (Family+) |
| Channel partners | ≥2 signed |
| Public API | Beta, ≥3 integrations |
| SOC 2 | Audit initiated |
| Test count | ≥4,519 |
| Prod E2E | ≥195, all passing |
| Security incidents | 0 |

---

## 11. Risk Register

| ID | Risk | Prob | Impact | Phase | Mitigation |
|----|------|:----:|:------:|:-----:|-----------|
| R1 | App Store rejects Safety app (MDM concerns) | Med | High | P1-P2 | Study Apple MDM policies Phase 0. Engage developer relations. Web-only fallback. |
| R2 | App Store rejects Social app (children's content) | Med | High | P2 | Pre-submit Apple consultation. Over-document moderation. COPPA evidence. |
| R3 | Pre-publish moderation latency >2s at scale | Med | Med | P2 | Fast-path keyword first (<100ms). AI only for uncertain. Cache common patterns. |
| R4 | Harmful content reaches child (false negative) | Low | Critical | P2-P3 | Defense in depth: keyword + AI + image + behavioral. Human escalation. <60s takedown. Community reporting. |
| R5 | GoGuardian adds 10+ AI platforms by Q3 | High | High | P1-P2 | Compete on governance + family market + cross-product intelligence (all unique). |
| R6 | Australian exemption denied for Social app | Med | High | P1 | Design 16+ AU fallback. Safety app serves all ages. Engage AU legal. |
| R7 | Hiring 2+ months delayed | High | High | P1-P2 | P0-P1 scoped for 2-3 eng. Contract bridge. Prioritize safety over social if understaffed. |
| R8 | WebSocket scaling under load | Med | Med | P2-P3 | Locust load test Phase 1. Horizontal scale via Redis pub/sub. Per-user connection limits. |
| R9 | Cloudflare integration complexity | Low | Med | P2 | Prototype Phase 1. S3 fallback if needed. |
| R10 | EU AI Act unclear for social moderation | Med | High | P2 | Over-comply. EU legal counsel. Auditable conformity assessment. |
| R11 | Moderation queue backlog | Med | Med | P2-P3 | Automation-first (95%+ AI). Human review edge cases only. Severity-based priority. |
| R12 | Cross-product intelligence false alert flood | Med | Med | P3 | Conservative thresholds at launch. Tune on data. Parent feedback. Configurable sensitivity. |
| R13 | Social app no traction (no network effect) | Med | High | P3+ | School pilots seed users. Family referrals. Creative tools as standalone value. |
| R14 | Competitor launches social + safety combo | Low | Critical | All | Execute fast. 6-month head start. IP protection for cross-product intelligence. |
| R15 | Data breach (children's PII) | Low | Critical | P2+ | Fernet encryption. Pen testing Phase 2. Bug bounty Phase 3. Incident response plan Phase 0. |

---

## 12. Deferred to Post-V1 (Q4 2026+)

| Feature | Reason | Estimated Phase |
|---------|--------|----------------|
| Social media monitoring (30+ platforms) | Too large (14-20 pw), Bark has 10yr head start, mobile agent needed first | Q4 2026 |
| VR/metaverse monitoring | Market too early, Qustodio only competitor | Q1 2027 |
| Gaming safety (200+ games) | Aura well ahead, partnership better than build | Q1 2027 |
| Identity theft protection | Business development timeline, partnership not build | Q4 2026 |
| Community safety intelligence | Needs critical mass of users first | Q1 2027 |
| AI literacy integration in Social app | Core platform must stabilize first | Q4 2026 |
| Stories/Reels equivalent | Foundation must be solid first | Q4 2026 |
| Educational content partnerships | Partnership-dependent | Q1 2027 |

---

## 13. Architecture Decision Records

**Storage:** All ADRs stored at `docs/adrs/ADR-00X-title.md`. Phase 0 includes writing ADR-001 through ADR-005 as formal documents (currently implicit in unification plan).

### Accepted (Existing)

| ADR | Decision | Status |
|-----|----------|--------|
| ADR-001 | Unified JWT auth (Portal's system) | Accepted |
| ADR-002 | Social features as FastAPI modules | Accepted |
| ADR-003 | Single PostgreSQL database | Accepted |
| ADR-004 | Greenfield mobile on Expo | Accepted |
| ADR-005 | Archive legacy repos | Accepted |

### New (Phase 0)

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-006 | Two mobile apps (Safety + Social) | Separate audiences (parent vs child), separate app store listings, separate review processes, different UX paradigms |
| ADR-007 | Cloudflare R2/Images/Stream for media | Zero egress fees, automatic resize/transcode, global CDN, webhook pipeline for moderation |
| ADR-008 | Separate WebSocket service | Long-lived WS connections have different scaling profile than REST. Separate process avoids resource contention. Redis pub/sub bridges events. |
| ADR-009 | Three age tiers (5-9, 10-12, 13-15) | Aligned with COPPA boundary (13), developmental stages, Australian under-16 focus. Graduated permissions with parent overrides. |

---

## Appendix A: Competitive Positioning Summary

| Capability | Bhapi (target) | Bark | GoGuardian | Qustodio | Aura |
|------------|:-------------:|:----:|:----------:|:--------:|:----:|
| Safe social network | **Yes** | No | No | No | No |
| AI monitoring (10+ platforms) | **Yes** | No | 3 | No | No |
| Cross-product intelligence | **Yes** | No | No | No | No |
| Mobile safety app | **Yes** | Yes | No | Yes | Yes |
| School governance tools | **Yes** | No | No | No | No |
| Age-tiered social | **Yes** | No | No | No | No |
| Screen time | **Yes** | Yes | No | Yes | Yes |
| Location | **Yes** | Yes | No | Yes | Yes |
| Free social app | **Yes** | No | No | Free (1 device) | No |
| Under-16 compliant (AU) | **Yes** | Unknown | No | Unknown | Unknown |
| 6-language i18n | **Yes** | No | No | Yes | No |
| COPPA 2026 compliant | **Yes** | Yes | Unknown | Yes | Unknown |
| EU AI Act compliant | **Yes** | No | No | Partial | No |

**Unique moat:** No competitor combines a safe social network with AI safety monitoring and cross-product intelligence. This is Bhapi's defensible position.
