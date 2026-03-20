# Phase 2: Social Launch + Platform Expansion — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Launch the Bhapi Social app in beta (TestFlight + Android), submit Bhapi Safety to App Store, achieve Ohio AI governance compliance before Jul 1 deadline, EU AI Act compliance before Aug 2 deadline, and bring the content moderation pipeline to production readiness with live age-tier enforcement.

**Architecture:** Extends the Phase 1 backend modules (`social/`, `contacts/`, `moderation/`, `messaging/`, `media/`, `age_tier/`, `governance/`) with real-time messaging (WebSocket integration), device agent data collection, behavioral analysis, and multi-jurisdiction compliance. Mobile Social app screens transition from Phase 1 shells to fully functional screens with Expo SDK 52+ native features. Safety app gains Bhapi Social activity monitoring and device-level data. All new tables via Alembic migrations 033-040+.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy async / Alembic / PostgreSQL 16 | Expo SDK 52+ / React Native / TypeScript / Turborepo | Manifest V3 browser extension | Redis 7 | Cloudflare R2/Images/Stream | Expo Push Notifications | Maestro (mobile E2E)

**Spec:** `docs/superpowers/specs/2026-03-19-bhapi-unified-platform-design.md` (v1.2, Section 8 Phase 2)

**Duration:** Weeks 13-20 (Jun 9 — Aug 3, 2026)
**Team:** 8-10 engineers
**Budget:** 64-80 person-weeks (54.4-68.0 net after production overhead)
**Phase 1 exit:** 30/30 tasks complete, 3,125+ tests passing, v3.0.0 on master
**Regulatory deadlines:** Ohio AI Mandate (Jul 1), EU AI Act (Aug 2)

---

## Dependency Graph

```
TRACK A: SOCIAL APP BUILD (P2-S1 → P2-S12)
  P2-S1: Onboarding (Yoti + parent consent + profile) ─────┐
  P2-S6: Age-tier UX (feature vis, locks, unlock requests) ─┤
       │                                                      │
       ├──► P2-S2: Feed (create post, FlashList, like, comment) ─┐
       ├──► P2-S3: Profiles (view/edit, avatar, followers)       │
       ├──► P2-S5: Contacts (search, request, parent approve)   │
       │                                                         │
       P2-S7: Media (R2 upload, resize, transcode, cache) ──────┤
       │                                                         │
       ├──► P2-S4: Messaging (real-time WS, media, typing) ─────┤
       │                                                         │
       P2-S8: Push notifications ────────────────────────────────┤
       P2-S9: Reporting (report post/user/message) ─────────────┤
       P2-S10: Settings (privacy, notifs, language, theme) ─────┤
       P2-S11: Moderation UX (review hold, takedown, appeal) ──┘
       │
       └──► P2-S12: TestFlight + Android beta (≥50 users)

TRACK B: SAFETY APP v2 (P2-M1 → P2-M6)
  P2-M1: Bhapi Social activity monitoring ──────┐
  P2-M2: Device agent (app usage, screen time) ─┤
       │                                         │
       ├──► P2-M3: Cross-product alert view ─────┤
       ├──► P2-M4: Child profile (AI + social)  │
       ├──► P2-M5: Contact approval flow ────────┘
       │
       └──► P2-M6: App Store submission (iOS + Google Play)

TRACK C: COMPLIANCE (P2-C1 → P2-C6)
  P2-C1: Ohio governance final ◄── DEADLINE: Jul 1 ────┐
  P2-C2: EU AI Act conformity  ◄── DEADLINE: Aug 2 ────┤
  P2-C3: EU database registration ─────────────────────┤
  P2-C4: Australian compliance (eSafety, age verify) ──┤
  P2-C5: UK AADC gap analysis + privacy-by-default ────┤
  P2-C6: State compliance framework (CA/TX/FL/NY prep) ┘

TRACK D: SAFETY ENGINE (P2-E1 → P2-E8)
  P2-E1: Age-tier enforcement (all social endpoints) ──┐
  P2-E2: Social graph analysis ─────────────────────────┤
  P2-E3: Behavioral baselines ─────────────────────────┤
       │                                                │
       ├──► P2-E4: Pre-publish live (<2s p95) ──────────┤
       ├──► P2-E5: Post-publish live (<60s takedown) ──┤
       ├──► P2-E6: Moderation dashboard ────────────────┤
       ├──► P2-E7: Anti-abuse measures ─────────────────┤
       └──► P2-E8: Parental abuse safeguards ──────────┘
```

**Parallelization:** All four tracks can run concurrently. Within each track, foundation tasks (first listed) must complete before dependent tasks. P2-C1 (Ohio) is the earliest hard deadline (Jul 1) — start Week 13. P2-C2 (EU AI Act) deadline is Aug 2 — start no later than Week 15.

**Cross-track dependencies:**
- P2-S4 (messaging) depends on `src/realtime/` WebSocket service (Phase 1 complete)
- P2-M1 (social monitoring) depends on P2-S2 (feed) for social data to monitor
- P2-E4/E5 (live moderation) depend on P2-E1 (age-tier enforcement)
- P2-E7 (anti-abuse: account farming detection) depends on P2-M2 (device agent tables)
- P2-S12 (beta) depends on all P2-S1–S11 being functional
- P2-S8 (push notifications) is a soft dependency for P2-M1, P2-M5, P2-E4 (parent notifications degrade gracefully if push not yet deployed)
- **Serialization points:** Tasks modifying `src/main.py` and `alembic/env.py` (P2-M2, P2-E2) must not run in parallel — use worktrees or sequence them

---

## File Structure

### New Backend Modules

```
src/
├── device_agent/                   # NEW — Mobile device data collection
│   ├── __init__.py                 # Public interface
│   ├── router.py                   # /api/v1/device endpoints
│   ├── service.py                  # App usage, screen time, sync
│   ├── models.py                   # DeviceSession, AppUsageRecord, ScreenTimeRecord
│   └── schemas.py                  # Pydantic schemas
│
├── intelligence/                   # NEW — Cross-product correlation
│   ├── __init__.py                 # Public interface
│   ├── router.py                   # /api/v1/intelligence endpoints
│   ├── service.py                  # Unified risk scoring, correlation
│   ├── models.py                   # BehavioralBaseline, SocialGraphEdge, AbuseSignal
│   └── schemas.py                  # Pydantic schemas
│
├── governance/                     # EXTEND — Ohio final + EU AI Act
│   ├── ohio.py                     # NEW — Ohio-specific customization
│   ├── eu_ai_act.py                # NEW — Conformity assessment, tech docs
│   └── state_framework.py          # NEW — Extensible state compliance
│
├── compliance/                     # EXTEND — Australian, UK AADC
│   ├── australian.py               # NEW — eSafety, age verify enforcement
│   └── uk_aadc.py                  # NEW — AADC gap analysis, privacy-by-default
│
├── moderation/                     # EXTEND — Live pipeline, dashboard, anti-abuse
│   ├── dashboard_service.py        # NEW — Queue management, SLA tracking
│   ├── anti_abuse.py               # NEW — Age misrep, farming, harassment
│   └── parental_safeguards.py      # NEW — Trusted adult, custody, teen privacy
│
├── social/                         # EXTEND — Graph analysis, behavioral
│   ├── graph_analysis.py           # NEW — Contact patterns, isolation detection
│   └── behavioral.py               # NEW — Per-child baselines, deviation alerting
│
├── age_tier/                       # EXTEND — Middleware enforcement
│   └── middleware.py               # NEW — Feature gating middleware for all social
│
└── realtime/                       # EXTEND — Typing indicators, read receipts
    ├── typing.py                   # NEW — Typing indicator events
    └── receipts.py                 # NEW — Read receipt sync
```

### New Mobile Files

```
mobile/
├── apps/
│   ├── social/
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   │   ├── onboarding.tsx         # NEW — Age verify + parent consent + profile
│   │   │   │   └── age-verify.tsx         # NEW — Yoti integration screen
│   │   │   ├── (feed)/
│   │   │   │   ├── create-post.tsx        # NEW — Post creation with media
│   │   │   │   └── post-detail.tsx        # NEW — Post detail with comments
│   │   │   ├── (chat)/
│   │   │   │   └── conversation.tsx       # NEW — Real-time chat screen
│   │   │   ├── (contacts)/
│   │   │   │   ├── index.tsx              # NEW — Contact list + search
│   │   │   │   └── request.tsx            # NEW — Contact request detail
│   │   │   ├── (profile)/
│   │   │   │   └── edit.tsx               # NEW — Profile edit screen
│   │   │   └── (settings)/
│   │   │       ├── privacy.tsx            # NEW — Privacy settings
│   │   │       ├── notifications.tsx      # NEW — Notification prefs
│   │   │       └── trusted-adult.tsx      # NEW — Trusted adult escalation
│   │   └── __tests__/
│   │       ├── onboarding.test.ts         # NEW
│   │       ├── feed.test.ts              # NEW
│   │       ├── chat.test.ts             # NEW
│   │       ├── contacts.test.ts         # NEW
│   │       └── profile.test.ts          # NEW
│   │
│   └── safety/
│       ├── app/
│       │   ├── (dashboard)/
│       │   │   └── social-activity.tsx    # NEW — Bhapi Social monitoring
│       │   ├── (children)/
│       │   │   ├── child-profile.tsx      # NEW — Combined AI + social timeline
│       │   │   └── contact-approval.tsx   # NEW — Parent approve/deny contacts
│       │   └── (device)/
│       │       ├── index.tsx              # NEW — Device agent dashboard
│       │       └── screen-time.tsx        # NEW — Screen time details
│       └── __tests__/
│           ├── social-activity.test.ts    # NEW
│           ├── child-profile.test.ts     # NEW
│           └── device-agent.test.ts      # NEW
│
├── packages/
│   ├── shared-types/src/
│   │   ├── device.ts                      # NEW — Device agent types
│   │   ├── intelligence.ts                # NEW — Cross-product types
│   │   └── compliance.ts                  # NEW — Compliance types
│   ├── shared-ui/src/
│   │   ├── AgeTierGate.tsx                # NEW — Feature lock/unlock UI
│   │   ├── ModerationNotice.tsx           # NEW — "Post under review" banner
│   │   ├── ReportDialog.tsx               # NEW — Report content modal
│   │   └── TrustedAdultButton.tsx         # NEW — Trusted adult escalation
│   └── shared-api/src/
│       └── push-notifications.ts          # NEW — Expo push token registration
│
└── maestro/                               # NEW — E2E test flows
    ├── social-onboarding.yaml
    ├── social-feed.yaml
    ├── social-chat.yaml
    └── safety-monitoring.yaml
```

### New Alembic Migrations

```
alembic/versions/
├── 033_push_tokens.py                     # PushToken (P2-S8)
├── 034_device_agent_tables.py             # DeviceSession, AppUsageRecord, ScreenTimeRecord (P2-M2)
├── 035_ohio_governance_extensions.py      # District customization, import config, board report (P2-C1)
├── 036_eu_ai_act_tables.py                # ConformityAssessment, TechDoc, RiskManagement, BiasTest (P2-C2)
├── 037_australian_compliance.py           # AgeVerificationRecord, ESafetyReport, CyberbullyingCase (P2-C4)
├── 038_uk_aadc_tables.py                  # AadcAssessment, PrivacyDefault (P2-C5)
├── 039_moderation_dashboard.py            # ModeratorAssignment, SLAMetric, PatternDetection (P2-E6)
├── 040_parental_safeguards.py             # TrustedAdult, CustodyConfig, TeenPrivacyTier, GuardianRole (P2-E8)
├── 041_intelligence_tables.py             # SocialGraphEdge, AbuseSignal, BehavioralBaseline (P2-E2/E3)
```

---

## Track A: Social App Build

### Task 1 (P2-S1): Social Onboarding — Age Verification, Parent Consent, Profile Creation

**Files:**
- Create: `mobile/apps/social/app/(auth)/onboarding.tsx`
- Create: `mobile/apps/social/app/(auth)/age-verify.tsx`
- Modify: `mobile/apps/social/app/(auth)/login.tsx`
- Modify: `mobile/packages/shared-types/src/social.ts` (add onboarding types)
- Modify: `mobile/packages/shared-types/src/auth.ts` (add consent types)
- Create: `mobile/apps/social/__tests__/onboarding.test.ts`
- Create: `tests/e2e/test_social_onboarding.py`
- Test: `tests/unit/test_age_tier.py` (extend), `tests/e2e/test_social_onboarding.py`

**Tests Required:** Component ≥15, Integration ≥10, Security ≥10

- [ ] **Step 1: Write onboarding type definitions**

Add to `mobile/packages/shared-types/src/social.ts`:
```typescript
export interface OnboardingState {
  step: 'age_verify' | 'parent_consent' | 'profile_create' | 'complete';
  age_verified: boolean;
  parent_consent_given: boolean;
  profile_created: boolean;
}

export interface YotiVerificationRequest {
  session_id: string;
  redirect_url: string;
}

export interface YotiVerificationResult {
  verified: boolean;
  age_estimate: number | null;
  session_id: string;
}

export interface ParentConsentRequest {
  child_user_id: string;
  parent_email: string;
  consent_type: 'social_access';
}

export interface ProfileCreateRequest {
  display_name: string;
  avatar_url?: string;
  bio?: string;
  date_of_birth: string; // ISO date
}
```

- [ ] **Step 2: Write failing backend E2E tests for onboarding flow**

Create `tests/e2e/test_social_onboarding.py`:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_onboarding_age_verify_creates_tier(client: AsyncClient, auth_headers: dict):
    """Child registers → Yoti verifies age → tier assigned automatically."""
    resp = await client.post("/api/v1/age-tier/assign", json={
        "member_id": "test-member-id",
        "date_of_birth": "2018-06-15",  # 8 years old → young tier
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tier"] == "young"
    assert data["permissions"]["moderation_mode"] == "pre_publish"

@pytest.mark.asyncio
async def test_onboarding_parent_consent_required_under_13(client: AsyncClient, auth_headers: dict):
    """Under-13 onboarding requires parent consent before social access."""
    resp = await client.post("/api/v1/social/profiles", json={
        "display_name": "TestKid",
        "date_of_birth": "2017-01-01",
    }, headers=auth_headers)
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["age_tier"] in ["young", "preteen"]

@pytest.mark.asyncio
async def test_onboarding_profile_creation_enforces_age_range(client: AsyncClient, auth_headers: dict):
    """Profile creation rejects users outside 5-15 age range."""
    resp = await client.post("/api/v1/social/profiles", json={
        "display_name": "TooOld",
        "date_of_birth": "2005-01-01",  # 21 years old
    }, headers=auth_headers)
    assert resp.status_code == 422
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/e2e/test_social_onboarding.py -v`
Expected: Tests reference existing endpoints but may need fixture setup

- [ ] **Step 4: Write onboarding screen (age verification)**

Create `mobile/apps/social/app/(auth)/age-verify.tsx` — Yoti WebView integration with callback URL handling, age result display, and redirect to parent consent if under 13.

- [ ] **Step 5: Write onboarding screen (profile creation)**

Create `mobile/apps/social/app/(auth)/onboarding.tsx` — Multi-step wizard: age verify → parent consent (if <13) → display name + avatar + bio → tier assignment confirmation.

- [ ] **Step 6: Update login to redirect new users to onboarding**

Modify `mobile/apps/social/app/(auth)/login.tsx` — After successful login, check if user has a Profile. If not, redirect to onboarding screen.

- [ ] **Step 7: Write component tests**

Create `mobile/apps/social/__tests__/onboarding.test.ts` — Test all onboarding states, age verification result handling, parent consent flow, profile form validation, tier display.

- [ ] **Step 8: Write security tests**

Create `tests/security/test_social_onboarding_security.py` — Test age spoofing prevention, parent consent bypass attempts, profile creation without verification, rate limiting on verification requests.

- [ ] **Step 9: Run all tests**

Run: `pytest tests/e2e/test_social_onboarding.py tests/security/test_social_onboarding_security.py -v`
Run: `cd mobile && npx turbo run test`
Expected: All pass

- [ ] **Step 10: Commit**

```bash
git add tests/e2e/test_social_onboarding.py tests/security/test_social_onboarding_security.py
git add mobile/apps/social/app/(auth)/onboarding.tsx mobile/apps/social/app/(auth)/age-verify.tsx
git add mobile/apps/social/app/(auth)/login.tsx mobile/packages/shared-types/src/social.ts
git add mobile/apps/social/__tests__/onboarding.test.ts
git commit -m "feat(P2-S1): social onboarding — age verification, parent consent, profile creation"
```

---

### Task 2 (P2-S2): Social Feed — Create Post, Timeline, Like, Comment, Hashtags

**Files:**
- Create: `mobile/apps/social/app/(feed)/create-post.tsx`
- Create: `mobile/apps/social/app/(feed)/post-detail.tsx`
- Modify: `mobile/apps/social/app/(feed)/index.tsx` (upgrade from shell to full FlashList)
- Modify: `mobile/packages/shared-ui/src/PostCard.tsx` (add interaction callbacks)
- Modify: `mobile/packages/shared-types/src/social.ts` (add post creation types)
- Create: `mobile/apps/social/__tests__/feed.test.ts`
- Create: `tests/e2e/test_social_feed_flow.py`
- Test: `tests/unit/test_social.py` (extend), `tests/e2e/test_social_feed_flow.py`

**Tests Required:** Component ≥25, Integration ≥20, Backend E2E ≥20

- [ ] **Step 1: Write post creation types**

Add to `mobile/packages/shared-types/src/social.ts`:
```typescript
export interface CreatePostRequest {
  content: string;
  media_ids?: string[];
  visibility?: PostVisibility;
  hashtags?: string[];
}

export interface CreatePostResponse {
  id: string;
  moderation_status: ModerationStatus;
  message: string; // "Your post is being reviewed" for pre-publish
}

export interface PostDetailResponse extends SocialPost {
  author: Pick<Profile, 'id' | 'display_name' | 'avatar_url' | 'is_verified'>;
  comments: CommentResponse[];
  comment_count: number;
}

export interface CommentResponse {
  id: string;
  author_id: string;
  author_name: string;
  author_avatar: string | null;
  content: string;
  created_at: string;
}

export interface CreateCommentRequest {
  content: string;
}
```

- [ ] **Step 2: Write failing backend E2E tests**

Create `tests/e2e/test_social_feed_flow.py` — Test full flow: create profile → create post → post appears in feed → like post → add comment → hashtag extraction → trending hashtags. Test pagination, age-tier content length limits, moderation status filtering.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/e2e/test_social_feed_flow.py -v`
Expected: FAIL (tests exercise existing API, may pass if endpoints already work)

- [ ] **Step 4: Upgrade feed screen to FlashList with real data**

Modify `mobile/apps/social/app/(feed)/index.tsx` — Replace FlatList with FlashList (from `@shopify/flash-list`). Connect to `GET /api/v1/social/feed` via shared-api. Add pull-to-refresh, infinite scroll pagination, empty state ("Follow people to see posts here"), loading skeleton.

- [ ] **Step 5: Write create post screen**

Create `mobile/apps/social/app/(feed)/create-post.tsx` — Text input with character counter (respects age-tier max_post_length), media attachment (camera + gallery via expo-image-picker), hashtag extraction preview, submit → show moderation status ("Your post is being reviewed" for pre-publish tiers).

- [ ] **Step 6: Write post detail screen**

Create `mobile/apps/social/app/(feed)/post-detail.tsx` — Full post content, author info, like button with count, comment list, add comment input, share button (age-tier gated), report button.

- [ ] **Step 7: Write component tests**

Create `mobile/apps/social/__tests__/feed.test.ts` — Test feed rendering with mock data, create post form validation, character limit enforcement per tier, media attachment UI, comment list rendering, like toggle, empty states, loading states.

- [ ] **Step 8: Run all tests**

Run: `pytest tests/e2e/test_social_feed_flow.py -v`
Run: `cd mobile && npx turbo run test`
Expected: All pass

- [ ] **Step 9: Commit**

```bash
git add mobile/apps/social/app/(feed)/ mobile/apps/social/__tests__/feed.test.ts
git add mobile/packages/shared-types/src/social.ts mobile/packages/shared-ui/src/PostCard.tsx
git add tests/e2e/test_social_feed_flow.py
git commit -m "feat(P2-S2): social feed — create post, FlashList timeline, like, comment, hashtags"
```

---

### Task 3 (P2-S3): Profiles — View/Edit, Avatar Upload, Followers, Post History

**Files:**
- Create: `mobile/apps/social/app/(profile)/edit.tsx`
- Modify: `mobile/apps/social/app/(profile)/index.tsx` (upgrade from shell)
- Modify: `mobile/packages/shared-ui/src/Avatar.tsx` (add upload capability)
- Create: `mobile/apps/social/__tests__/profile.test.ts`
- Test: `tests/e2e/test_social_profiles.py` (extend)

**Tests Required:** Component ≥15, Integration ≥10

- [ ] **Step 1: Write failing tests for profile edit flow**

Create `tests/e2e/test_social_profiles_extended.py` — Test profile update (display_name, bio, avatar_url), follower/following list pagination, post history for a profile, visibility settings (friends_only, public, private).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/e2e/test_social_profiles_extended.py -v`

- [ ] **Step 3: Upgrade profile screen**

Modify `mobile/apps/social/app/(profile)/index.tsx` — Full profile view: avatar, display name, bio, age tier badge, follower/following counts (tappable → list), post grid/list toggle, "Edit Profile" button for own profile.

- [ ] **Step 4: Write profile edit screen**

Create `mobile/apps/social/app/(profile)/edit.tsx` — Edit display name, bio, avatar (camera/gallery via expo-image-picker → upload to media API → set avatar_url), visibility selector.

- [ ] **Step 5: Write component tests**

Create `mobile/apps/social/__tests__/profile.test.ts` — Test profile display, edit form validation, avatar upload flow, follower list rendering, visibility toggle.

- [ ] **Step 6: Run all tests and commit**

Run: `pytest tests/e2e/test_social_profiles_extended.py -v && cd mobile && npx turbo run test`

```bash
git add mobile/apps/social/app/(profile)/ mobile/apps/social/__tests__/profile.test.ts
git add mobile/packages/shared-ui/src/Avatar.tsx tests/e2e/test_social_profiles_extended.py
git commit -m "feat(P2-S3): profiles — view/edit, avatar upload, followers, post history"
```

---

### Task 4 (P2-S4): Real-Time Messaging — WebSocket Chat, Media Messages, Typing, Read Receipts

**Files:**
- Create: `mobile/apps/social/app/(chat)/conversation.tsx`
- Modify: `mobile/apps/social/app/(chat)/index.tsx` (upgrade from shell)
- Create: `src/realtime/typing.py`
- Create: `src/realtime/receipts.py`
- Modify: `src/messaging/service.py` (add real-time hooks, media message support)
- Modify: `src/messaging/router.py` (add typing, read receipt endpoints)
- Modify: `mobile/packages/shared-api/src/ws-client.ts` (add typing/receipt events)
- Create: `mobile/apps/social/__tests__/chat.test.ts`
- Create: `tests/e2e/test_messaging_realtime.py`
- Create: `tests/unit/test_realtime_typing.py`
- Create: `tests/unit/test_realtime_receipts.py`

**Tests Required:** Component ≥20, Integration ≥15, WebSocket E2E ≥15

- [ ] **Step 1: Write failing tests for typing indicators**

Create `tests/unit/test_realtime_typing.py`:
```python
import pytest
from src.realtime.typing import TypingManager

@pytest.mark.asyncio
async def test_typing_start_publishes_event():
    manager = TypingManager()
    event = await manager.start_typing("conv-1", "user-1")
    assert event["type"] == "typing_start"
    assert event["conversation_id"] == "conv-1"
    assert event["user_id"] == "user-1"

@pytest.mark.asyncio
async def test_typing_auto_expires_after_timeout():
    manager = TypingManager(timeout_seconds=3)
    await manager.start_typing("conv-1", "user-1")
    # After timeout, typing state should clear
    assert not manager.is_typing("conv-1", "user-1")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_realtime_typing.py -v`
Expected: FAIL — `src.realtime.typing` does not exist

- [ ] **Step 3: Implement typing indicator module**

Create `src/realtime/typing.py`:
```python
import asyncio
from datetime import datetime, timezone

class TypingManager:
    def __init__(self, timeout_seconds: int = 5):
        self.timeout_seconds = timeout_seconds
        self._typing: dict[str, dict[str, datetime]] = {}  # conv_id → {user_id → started_at}

    async def start_typing(self, conversation_id: str, user_id: str) -> dict:
        if conversation_id not in self._typing:
            self._typing[conversation_id] = {}
        self._typing[conversation_id][user_id] = datetime.now(timezone.utc)
        return {
            "type": "typing_start",
            "conversation_id": conversation_id,
            "user_id": user_id,
        }

    async def stop_typing(self, conversation_id: str, user_id: str) -> dict:
        if conversation_id in self._typing:
            self._typing[conversation_id].pop(user_id, None)
        return {
            "type": "typing_stop",
            "conversation_id": conversation_id,
            "user_id": user_id,
        }

    def is_typing(self, conversation_id: str, user_id: str) -> bool:
        if conversation_id not in self._typing:
            return False
        started = self._typing[conversation_id].get(user_id)
        if not started:
            return False
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        if elapsed > self.timeout_seconds:
            self._typing[conversation_id].pop(user_id, None)
            return False
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_realtime_typing.py -v`
Expected: PASS

- [ ] **Step 5: Write failing tests for read receipts**

Create `tests/unit/test_realtime_receipts.py` — Test mark_read creates receipt event, batch read for catching up, receipt timestamp accuracy.

- [ ] **Step 6: Implement read receipts module**

Create `src/realtime/receipts.py` — `ReadReceiptManager` with `mark_read(conversation_id, user_id, message_id)` → publishes receipt event via Redis pub/sub.

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/unit/test_realtime_receipts.py -v`
Expected: PASS

- [ ] **Step 8: Write messaging E2E tests**

Create `tests/e2e/test_messaging_realtime.py` — Test full flow: create conversation → send message → message appears in list → send media message → mark read → typing indicator.

- [ ] **Step 9: Extend messaging service with real-time hooks**

Modify `src/messaging/service.py` — After `send_message()`, publish event to Redis channel `conversation:{id}`. Add `send_media_message()` that creates MessageMedia + submits to moderation. Modify `list_conversations()` to order by last message timestamp.

- [ ] **Step 10: Upgrade chat list screen**

Modify `mobile/apps/social/app/(chat)/index.tsx` — Real conversation data, last message preview, unread count badges, pull-to-refresh, WebSocket connection for live updates.

- [ ] **Step 11: Write conversation screen**

Create `mobile/apps/social/app/(chat)/conversation.tsx` — Real-time chat with WebSocket, message list (FlashList inverted), text input, media attach, typing indicator display, read receipts (double check marks), auto-scroll on new messages.

- [ ] **Step 12: Write component tests**

Create `mobile/apps/social/__tests__/chat.test.ts` — Test conversation rendering, message sending, typing indicator display, read receipt marks, media message display, WebSocket connection states.

- [ ] **Step 13: Run all tests and commit**

Run: `pytest tests/unit/test_realtime_typing.py tests/unit/test_realtime_receipts.py tests/e2e/test_messaging_realtime.py -v`
Run: `cd mobile && npx turbo run test`

```bash
git add src/realtime/typing.py src/realtime/receipts.py
git add src/messaging/service.py src/messaging/router.py
git add mobile/apps/social/app/(chat)/ mobile/apps/social/__tests__/chat.test.ts
git add mobile/packages/shared-api/src/ws-client.ts
git add tests/unit/test_realtime_typing.py tests/unit/test_realtime_receipts.py tests/e2e/test_messaging_realtime.py
git commit -m "feat(P2-S4): real-time messaging — WebSocket chat, media messages, typing indicators, read receipts"
```

---

### Task 5 (P2-S5): Contacts — Search, Request, Accept/Reject, Parent Approval, Block/Report

**Files:**
- Create: `mobile/apps/social/app/(contacts)/index.tsx`
- Create: `mobile/apps/social/app/(contacts)/request.tsx`
- Modify: `mobile/packages/shared-ui/src/ContactRequest.tsx` (add search result variant)
- Create: `mobile/apps/social/__tests__/contacts.test.ts`
- Create: `tests/e2e/test_contacts_flow.py`
- Create: `tests/security/test_contacts_security.py`

**Tests Required:** Component ≥15, Integration ≥10, Security ≥10

- [ ] **Step 1: Write failing E2E tests for contact flow**

Create `tests/e2e/test_contacts_flow.py` — Test: search users by display_name → send request → target receives request → target accepts → both see each other in contacts list. Test parent approval gate for under-13. Test blocking prevents future requests.

- [ ] **Step 2: Write security tests**

Create `tests/security/test_contacts_security.py` — Test: rate limiting on contact requests (max per age tier), cannot send request to blocked user, cannot bypass parent approval, cannot view contact list of other users.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/e2e/test_contacts_flow.py tests/security/test_contacts_security.py -v`

- [ ] **Step 4: Add user search endpoint to social router**

Modify `src/social/router.py` — Add `GET /api/v1/social/search?q=<query>` endpoint. Searches profiles by display_name (case-insensitive `ilike`). Excludes blocked users. Respects visibility settings. Paginated.

Modify `src/social/service.py` — Add `search_profiles(db, query, requester_id, page, page_size)`.

- [ ] **Step 5: Write contacts list screen**

Create `mobile/apps/social/app/(contacts)/index.tsx` — Tabs: My Contacts | Pending | Search. Search bar → API search → result list with ContactRequest component (send request variant). My Contacts list with message/block actions. Pending tab shows incoming requests with accept/reject.

- [ ] **Step 6: Write contact request detail screen**

Create `mobile/apps/social/app/(contacts)/request.tsx` — Requester profile preview, mutual contacts count, accept/reject buttons, "Waiting for parent approval" badge for under-13 requests.

- [ ] **Step 7: Write component tests**

Create `mobile/apps/social/__tests__/contacts.test.ts`

- [ ] **Step 8: Run all tests and commit**

Run: `pytest tests/e2e/test_contacts_flow.py tests/security/test_contacts_security.py -v`
Run: `cd mobile && npx turbo run test`

```bash
git add src/social/router.py src/social/service.py
git add mobile/apps/social/app/(contacts)/ mobile/apps/social/__tests__/contacts.test.ts
git add mobile/packages/shared-ui/src/ContactRequest.tsx
git add tests/e2e/test_contacts_flow.py tests/security/test_contacts_security.py
git commit -m "feat(P2-S5): contacts — search, request, accept/reject, parent approval, block/report"
```

---

### Task 6 (P2-S6): Age-Tier UX — Feature Visibility, Locked Explanations, Unlock Requests

**Files:**
- Create: `mobile/packages/shared-ui/src/AgeTierGate.tsx`
- Modify: `mobile/packages/shared-config/src/constants.ts` (add feature descriptions)
- Modify: `mobile/apps/social/app/(feed)/index.tsx` (wrap features in AgeTierGate)
- Modify: `mobile/apps/social/app/(chat)/index.tsx` (gate messaging for young tier)
- Create: `mobile/packages/shared-ui/__tests__/AgeTierGate.test.ts`
- Create: `tests/e2e/test_age_tier_ux.py`

**Tests Required:** Component ≥15, Integration ≥10

- [ ] **Step 1: Write failing tests for AgeTierGate component**

Create `mobile/packages/shared-ui/__tests__/AgeTierGate.test.ts`:
```typescript
import { AgeTierGate } from '../src/AgeTierGate';

describe('AgeTierGate', () => {
  it('renders children when permission is granted', () => {
    // age_tier: teen, permission: can_message → show content
  });

  it('renders lock explanation when permission denied', () => {
    // age_tier: young, permission: can_message → show "Messaging unlocks at age 10"
  });

  it('renders unlock request button for preteen features locked for young', () => {
    // age_tier: young, permission: can_upload_video → show lock + "Ask parent to unlock"
  });
});
```

- [ ] **Step 2: Implement AgeTierGate component**

Create `mobile/packages/shared-ui/src/AgeTierGate.tsx` — Checks permission for current user's age tier. If granted, renders children. If denied, renders a friendly lock message with age-appropriate explanation ("You'll be able to do this when you're older!") and optional "Ask parent" button.

- [ ] **Step 3: Add feature descriptions to config**

Modify `mobile/packages/shared-config/src/constants.ts` — Add `FEATURE_DESCRIPTIONS` mapping permissions to child-friendly explanations and unlock ages.

- [ ] **Step 4: Integrate AgeTierGate into social screens**

Modify feed (video upload), chat (messaging for young), contacts (search for young), profile (group chat creation). Wrap gated features with `<AgeTierGate permission="can_message" ageTier={user.age_tier}>`.

- [ ] **Step 5: Write backend E2E tests**

Create `tests/e2e/test_age_tier_ux.py` — Test: young user cannot access messaging endpoint (403), preteen can access messaging but not video upload, teen can access all features. Test unlock request endpoint.

- [ ] **Step 6: Run all tests and commit**

```bash
git add mobile/packages/shared-ui/src/AgeTierGate.tsx mobile/packages/shared-ui/__tests__/AgeTierGate.test.ts
git add mobile/packages/shared-config/src/constants.ts
git add mobile/apps/social/app/(feed)/index.tsx mobile/apps/social/app/(chat)/index.tsx
git add tests/e2e/test_age_tier_ux.py
git commit -m "feat(P2-S6): age-tier UX — feature visibility, lock explanations, unlock requests"
```

---

### Task 7 (P2-S7): Media — Cloudflare R2 Upload, Images Resize, Stream Transcode, Caching

**Files:**
- Modify: `src/media/service.py` (add caching layer, batch upload, progress)
- Modify: `src/media/router.py` (add batch endpoint, cache headers)
- Create: `mobile/packages/shared-api/src/media-upload.ts`
- Create: `tests/e2e/test_media_flow.py`
- Create: `tests/unit/test_media_cache.py`

**Tests Required:** Integration ≥15, Backend E2E ≥15

- [ ] **Step 1: Write failing tests for media caching**

Create `tests/unit/test_media_cache.py` — Test: cached variant URL returned on repeat request, cache invalidation on re-process, cache TTL expiry.

- [ ] **Step 2: Write media E2E tests**

Create `tests/e2e/test_media_flow.py` — Test full flow: request upload URL → simulate upload complete → webhook triggers processing → variants available → cached variant URL. Test image resize variants (thumbnail, medium, large). Test video transcode status polling.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/test_media_cache.py tests/e2e/test_media_flow.py -v`

- [ ] **Step 4: Add caching to media service**

Modify `src/media/service.py` — Add in-memory LRU cache for variant URLs (keyed by media_id + variant). Add `get_cached_variants()` that checks cache before DB. Add batch upload URL generation (`create_batch_upload_urls()`).

- [ ] **Step 5: Add cache headers to media router**

Modify `src/media/router.py` — Add `Cache-Control: public, max-age=86400` on variant responses. Add `POST /api/v1/media/upload/batch` for multi-file upload.

- [ ] **Step 6: Write mobile media upload helper**

Create `mobile/packages/shared-api/src/media-upload.ts` — `uploadMedia(file, type)` → calls presigned URL API → uploads to R2 → returns media_id. Progress callback support. Retry on failure.

- [ ] **Step 7: Run all tests and commit**

```bash
git add src/media/service.py src/media/router.py
git add mobile/packages/shared-api/src/media-upload.ts
git add tests/unit/test_media_cache.py tests/e2e/test_media_flow.py
git commit -m "feat(P2-S7): media — R2 upload, resize, transcode, caching, batch upload"
```

---

### Task 8 (P2-S8): Push Notifications — Messages, Likes, Comments, Contacts, Moderation

**Files:**
- Create: `mobile/packages/shared-api/src/push-notifications.ts`
- Modify: `src/alerts/service.py` (add push notification delivery channel)
- Create: `src/alerts/push.py` (Expo push notification sender)
- Modify: `src/auth/models.py` (add push_token field to Session or new PushToken model)
- Create: `alembic/versions/033_push_tokens.py`
- Create: `tests/unit/test_push_notifications.py`
- Create: `tests/e2e/test_push_delivery.py`

**Tests Required:** Component ≥10, Integration ≥5

- [ ] **Step 1: Write failing tests for push token registration**

Create `tests/unit/test_push_notifications.py`:
```python
import pytest
from src.alerts.push import ExpoPushService

@pytest.mark.asyncio
async def test_register_push_token(test_session):
    service = ExpoPushService()
    result = await service.register_token(
        db=test_session,
        user_id="user-1",
        token="ExponentPushToken[xxxxxx]",
        device_type="ios",
    )
    assert result.token == "ExponentPushToken[xxxxxx]"
    assert result.device_type == "ios"

@pytest.mark.asyncio
async def test_send_push_notification(test_session):
    service = ExpoPushService()
    sent = await service.send_notification(
        user_id="user-1",
        title="New message",
        body="Alice sent you a message",
        data={"type": "message", "conversation_id": "conv-1"},
        db=test_session,
    )
    assert sent is True  # or mock response
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_push_notifications.py -v`
Expected: FAIL — `src.alerts.push` does not exist

- [ ] **Step 3: Create push token migration**

Create `alembic/versions/033_push_tokens.py` — `push_tokens` table: `id` (UUID), `user_id` (FK users), `token` (unique), `device_type` (ios|android), `created_at`, `updated_at`.

- [ ] **Step 4: Implement push notification service**

Create `src/alerts/push.py`:
```python
import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

class ExpoPushService:
    async def register_token(self, db: AsyncSession, user_id: str, token: str, device_type: str):
        # Upsert push token for user
        ...

    async def send_notification(self, user_id: str, title: str, body: str, data: dict, db: AsyncSession) -> bool:
        # Lookup user's push tokens, send via Expo Push API
        tokens = await self._get_tokens(db, user_id)
        if not tokens:
            return False
        messages = [{"to": t.token, "title": title, "body": body, "data": data} for t in tokens]
        async with httpx.AsyncClient() as client:
            resp = await client.post(EXPO_PUSH_URL, json=messages)
            return resp.status_code == 200
```

- [ ] **Step 5: Add push token registration endpoint**

Add to auth router or create dedicated endpoint: `POST /api/v1/auth/push-token` — registers push token for current user.

- [ ] **Step 6: Integrate push with social events**

Modify `src/social/service.py` — After like/comment on a post, call push service to notify post author. Modify `src/contacts/service.py` — On new contact request, push to target. Modify `src/messaging/service.py` — On new message, push to conversation members.

- [ ] **Step 7: Write mobile push registration**

Create `mobile/packages/shared-api/src/push-notifications.ts` — `registerForPushNotifications()` → request Expo push token → POST to API. Handle notification taps (deep link to relevant screen).

- [ ] **Step 8: Run all tests and commit**

```bash
git add src/alerts/push.py alembic/versions/033_push_tokens.py
git add src/social/service.py src/contacts/service.py src/messaging/service.py
git add mobile/packages/shared-api/src/push-notifications.ts
git add tests/unit/test_push_notifications.py tests/e2e/test_push_delivery.py
git commit -m "feat(P2-S8): push notifications — messages, likes, comments, contacts, moderation events"
```

**IMPORTANT:** Verify migration file tracked: `git status` must show `alembic/versions/033_push_tokens.py` staged.

---

### Task 9 (P2-S9): Content Reporting — Report Post/User/Message, Reasons, Status

**Files:**
- Modify: `src/moderation/router.py` (extend report endpoints)
- Modify: `src/moderation/service.py` (add report reason taxonomy, status workflow)
- Create: `mobile/packages/shared-ui/src/ReportDialog.tsx`
- Create: `mobile/packages/shared-ui/__tests__/ReportDialog.test.ts`
- Create: `tests/e2e/test_content_reporting.py`

**Tests Required:** Component ≥10, Backend E2E ≥10

- [ ] **Step 1: Write failing E2E tests**

Create `tests/e2e/test_content_reporting.py` — Test: report post (select reason) → report appears in moderation queue → moderator reviews → status updated. Test duplicate report prevention. Test self-report prevention. Test report reasons taxonomy.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Extend moderation service with report reasons**

Modify `src/moderation/service.py` — Add report reason enum: `inappropriate`, `bullying`, `spam`, `impersonation`, `self_harm`, `adult_content`, `other`. Add `create_content_report()` with deduplication (same reporter + same target = 409).

- [ ] **Step 4: Write ReportDialog component**

Create `mobile/packages/shared-ui/src/ReportDialog.tsx` — Modal with reason selection (radio buttons), optional description text, submit button. Age-appropriate reason labels.

- [ ] **Step 5: Integrate report into PostCard and conversation**

Add report button to PostCard long-press menu. Add report to chat message long-press.

- [ ] **Step 6: Write component tests and commit**

```bash
git add src/moderation/router.py src/moderation/service.py
git add mobile/packages/shared-ui/src/ReportDialog.tsx mobile/packages/shared-ui/__tests__/ReportDialog.test.ts
git add tests/e2e/test_content_reporting.py
git commit -m "feat(P2-S9): content reporting — report post/user/message with reasons and status tracking"
```

---

### Task 10 (P2-S10): Settings — Privacy, Notifications, Language, Theme, Account

**Files:**
- Modify: `mobile/apps/social/app/(settings)/index.tsx` (upgrade from shell)
- Create: `mobile/apps/social/app/(settings)/privacy.tsx`
- Create: `mobile/apps/social/app/(settings)/notifications.tsx`
- Create: `tests/e2e/test_social_settings.py`

**Tests Required:** Component ≥10

- [ ] **Step 1: Write settings E2E tests**

Create `tests/e2e/test_social_settings.py` — Test: update privacy (who sees profile, who can message), notification preferences (push on/off per category), language change persists.

- [ ] **Step 2: Upgrade settings screen**

Modify `mobile/apps/social/app/(settings)/index.tsx` — Section list: Privacy, Notifications, Language, Theme (light/dark), Account (logout, delete). Each links to sub-screen.

- [ ] **Step 3: Write privacy settings screen**

Create `mobile/apps/social/app/(settings)/privacy.tsx` — Who can see my profile (everyone/friends/nobody), who can message me (friends/nobody), who can see my online status.

- [ ] **Step 4: Write notification preferences screen**

Create `mobile/apps/social/app/(settings)/notifications.tsx` — Toggle switches for: new messages, likes, comments, contact requests, moderation decisions, weekly digest.

- [ ] **Step 5: Run tests and commit**

```bash
git add mobile/apps/social/app/(settings)/ tests/e2e/test_social_settings.py
git commit -m "feat(P2-S10): settings — privacy, notifications, language, theme, account"
```

---

### Task 11 (P2-S11): Moderation UX — Pre-Publish Hold, Takedown Notice, Appeal

**Files:**
- Create: `mobile/packages/shared-ui/src/ModerationNotice.tsx`
- Create: `mobile/packages/shared-ui/__tests__/ModerationNotice.test.ts`
- Modify: `mobile/packages/shared-ui/src/PostCard.tsx` (show moderation status)
- Modify: `mobile/apps/social/app/(feed)/create-post.tsx` (show review message)
- Create: `tests/e2e/test_moderation_ux.py`

**Tests Required:** Component ≥15, Integration ≥10

- [ ] **Step 1: Write failing tests for ModerationNotice**

Create `mobile/packages/shared-ui/__tests__/ModerationNotice.test.ts` — Test: pending state shows "Your post is being reviewed", rejected shows reason + appeal button, removed shows "This post was removed" with reason.

- [ ] **Step 2: Implement ModerationNotice component**

Create `mobile/packages/shared-ui/src/ModerationNotice.tsx` — Banner component with states: `pending` (yellow, clock icon, "Being reviewed"), `rejected` (red, reason text, "Appeal" button), `removed` (gray, "Removed by moderator", reason). Age-appropriate language.

- [ ] **Step 3: Integrate into feed and post creation**

Modify PostCard to show ModerationNotice for own posts that are pending/rejected. Modify create-post to show confirmation with ModerationNotice after submission.

- [ ] **Step 4: Add appeal endpoint**

Modify `src/moderation/router.py` — Add `POST /api/v1/moderation/queue/{queue_id}/appeal` — user can appeal rejected content (once per item). Creates new queue entry with status `escalated`.

- [ ] **Step 5: Write E2E tests and commit**

Create `tests/e2e/test_moderation_ux.py` — Test appeal flow, re-submission after appeal approval, appeal rate limiting (1 per item).

```bash
git add mobile/packages/shared-ui/src/ModerationNotice.tsx mobile/packages/shared-ui/__tests__/ModerationNotice.test.ts
git add mobile/packages/shared-ui/src/PostCard.tsx mobile/apps/social/app/(feed)/create-post.tsx
git add src/moderation/router.py tests/e2e/test_moderation_ux.py
git commit -m "feat(P2-S11): moderation UX — pre-publish hold, takedown notice, appeal flow"
```

---

### Task 12 (P2-S12): TestFlight + Android Beta — ≥50 Beta Users

**Files:**
- Modify: `mobile/apps/social/app.json` (production config: bundle ID, version, icons)
- Modify: `mobile/apps/safety/app.json` (production config)
- Create: `mobile/maestro/social-onboarding.yaml`
- Create: `mobile/maestro/social-feed.yaml`
- Create: `mobile/maestro/social-chat.yaml`
- Create: `mobile/maestro/safety-monitoring.yaml`
- Create: `mobile/eas.json` (Expo Application Services config)

**Tests Required:** Maestro E2E ≥20

- [ ] **Step 1: Configure EAS Build**

Create `mobile/eas.json`:
```json
{
  "cli": { "version": ">= 10.0.0" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal",
      "ios": { "simulator": false },
      "android": { "buildType": "apk" }
    },
    "production": {
      "ios": { "autoIncrement": true },
      "android": { "autoIncrement": true }
    }
  },
  "submit": {
    "production": {
      "ios": { "appleId": "developer@bhapi.ai", "ascAppId": "TBD" },
      "android": { "serviceAccountKeyPath": "./google-service-account.json" }
    }
  }
}
```

- [ ] **Step 2: Configure app.json for both apps**

Update Social `app.json`: bundle ID `com.bhapi.social`, version `1.0.0`, splash screen, icons, permissions (camera, photo library, notifications).
Update Safety `app.json`: bundle ID `com.bhapi.safety`, version `1.0.0`.

- [ ] **Step 3: Write Maestro E2E test flows**

Create `mobile/maestro/social-onboarding.yaml` — Launch → login → onboarding → age verify → profile creation → land on feed.
Create `mobile/maestro/social-feed.yaml` — Create post → see in feed → like → comment → see hashtag.
Create `mobile/maestro/social-chat.yaml` — Open chat → select conversation → send message → see delivery.
Create `mobile/maestro/safety-monitoring.yaml` — Login → dashboard → view alerts → view child profile → contact approval.

- [ ] **Step 4: Run Maestro tests**

Run: `cd mobile && maestro test maestro/`
Expected: ≥20 test assertions pass

- [ ] **Step 5: Build preview for TestFlight + Android internal**

Run: `cd mobile/apps/social && eas build --platform ios --profile preview`
Run: `cd mobile/apps/social && eas build --platform android --profile preview`

- [ ] **Step 6: Submit to TestFlight + distribute Android APK**

Upload iOS build to TestFlight. Distribute Android APK internally. Set up beta testing group (target: ≥50 users).

- [ ] **Step 7: Commit**

```bash
git add mobile/eas.json mobile/apps/social/app.json mobile/apps/safety/app.json
git add mobile/maestro/
git commit -m "feat(P2-S12): TestFlight + Android beta build configuration, Maestro E2E tests"
```

---

## Track B: Safety App v2

### Task 13 (P2-M1): Bhapi Social Activity Monitoring — Posts, Messages, Contacts, Time, Flags

**Files:**
- Create: `mobile/apps/safety/app/(dashboard)/social-activity.tsx`
- Modify: `src/portal/service.py` (add social activity aggregation)
- Modify: `src/portal/router.py` (add social activity endpoint)
- Create: `tests/e2e/test_social_monitoring.py`
- Create: `tests/security/test_social_monitoring_security.py`
- Create: `mobile/apps/safety/__tests__/social-activity.test.ts`

**Tests Required:** Component ≥20, Integration ≥15, Security ≥10

- [ ] **Step 1: Write failing backend tests**

Create `tests/e2e/test_social_monitoring.py`:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_social_activity_summary_for_child(client: AsyncClient, auth_headers: dict):
    """Parent can see aggregated social activity for their child."""
    resp = await client.get(
        "/api/v1/portal/social-activity?member_id=child-1",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "post_count" in data
    assert "message_count" in data
    assert "contact_count" in data
    assert "flagged_content" in data
    assert "time_spent_minutes" in data

@pytest.mark.asyncio
async def test_social_activity_requires_parent_role(client: AsyncClient, child_headers: dict):
    """Child cannot access monitoring endpoints."""
    resp = await client.get(
        "/api/v1/portal/social-activity?member_id=child-1",
        headers=child_headers,
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/e2e/test_social_monitoring.py -v`

- [ ] **Step 3: Implement social activity aggregation service**

Modify `src/portal/service.py` — Add `get_social_activity(db, member_id, auth)`:
- Count posts by member in last 7/30 days
- Count messages sent in last 7/30 days
- Count accepted contacts
- List flagged/moderated content (rejected posts, escalated items)
- Estimate time spent (from session data)

- [ ] **Step 4: Add social activity endpoint**

Modify `src/portal/router.py` — Add `GET /api/v1/portal/social-activity?member_id=<id>` — requires parent role for the member's group.

- [ ] **Step 5: Write social activity monitoring screen**

Create `mobile/apps/safety/app/(dashboard)/social-activity.tsx` — Per-child social overview: post count (7d/30d chart), message count, contact list, flagged content list with severity, time spent bar chart by day. Pull-to-refresh.

- [ ] **Step 6: Write security tests**

Create `tests/security/test_social_monitoring_security.py` — Parent can only see own children's data. Cannot access other families' data. Rate limiting on queries.

- [ ] **Step 7: Write component tests and commit**

```bash
git add src/portal/service.py src/portal/router.py
git add mobile/apps/safety/app/(dashboard)/social-activity.tsx
git add mobile/apps/safety/__tests__/social-activity.test.ts
git add tests/e2e/test_social_monitoring.py tests/security/test_social_monitoring_security.py
git commit -m "feat(P2-M1): social activity monitoring — posts, messages, contacts, time, flags"
```

---

### Task 14 (P2-M2): Device Agent — App Usage, Screen Time, Background Sync

**Files:**
- Create: `src/device_agent/__init__.py`
- Create: `src/device_agent/router.py`
- Create: `src/device_agent/service.py`
- Create: `src/device_agent/models.py`
- Create: `src/device_agent/schemas.py`
- Create: `alembic/versions/034_device_agent_tables.py`
- Modify: `src/main.py` (register device agent router)
- Modify: `alembic/env.py` (import device agent models)
- Create: `mobile/apps/safety/app/(device)/index.tsx`
- Create: `mobile/apps/safety/app/(device)/screen-time.tsx`
- Create: `tests/unit/test_device_agent.py`
- Create: `tests/e2e/test_device_agent.py`
- Create: `tests/security/test_device_agent_security.py`

**Tests Required:** Unit ≥30, E2E ≥20, Security ≥10

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/test_device_agent.py`:
```python
import pytest
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_record_app_usage_session(test_session):
    from src.device_agent.service import record_app_usage
    result = await record_app_usage(
        db=test_session,
        member_id="member-1",
        app_name="YouTube",
        bundle_id="com.google.ios.youtube",
        started_at=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 6, 15, 10, 30, tzinfo=timezone.utc),
        foreground_minutes=25,
    )
    assert result.app_name == "YouTube"
    assert result.foreground_minutes == 25

@pytest.mark.asyncio
async def test_get_screen_time_summary(test_session):
    from src.device_agent.service import get_screen_time_summary
    summary = await get_screen_time_summary(
        db=test_session,
        member_id="member-1",
        date=datetime(2026, 6, 15, tzinfo=timezone.utc).date(),
    )
    assert "total_minutes" in summary
    assert "app_breakdown" in summary
    assert "category_breakdown" in summary
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_device_agent.py -v`
Expected: FAIL — `src.device_agent` does not exist

- [ ] **Step 3: Create device agent models**

Create `src/device_agent/models.py`:
```python
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON
from src.database import Base
from src.models_mixins import UUIDMixin, TimestampMixin

class DeviceSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "device_sessions"
    member_id = Column(String, ForeignKey("group_members.id"), nullable=False, index=True)
    device_id = Column(String, nullable=False)
    device_type = Column(String, nullable=False)  # ios, android
    os_version = Column(String)
    app_version = Column(String)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    battery_level = Column(Float)

class AppUsageRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "app_usage_records"
    member_id = Column(String, ForeignKey("group_members.id"), nullable=False, index=True)
    session_id = Column(String, ForeignKey("device_sessions.id"))
    app_name = Column(String, nullable=False)
    bundle_id = Column(String)
    category = Column(String)  # social, education, entertainment, gaming, productivity
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True))
    foreground_minutes = Column(Integer, default=0)

class ScreenTimeRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "screen_time_records"
    member_id = Column(String, ForeignKey("group_members.id"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False)
    total_minutes = Column(Integer, default=0)
    app_breakdown = Column(JSON, default=dict)  # {app_name: minutes}
    category_breakdown = Column(JSON, default=dict)  # {category: minutes}
    pickups = Column(Integer, default=0)
```

- [ ] **Step 4: Create migration**

Run: `alembic revision --autogenerate -m "device agent tables"`
Verify: `git status` shows `alembic/versions/034_device_agent_tables.py`

- [ ] **Step 5: Implement device agent service**

Create `src/device_agent/service.py` — `record_app_usage()`, `record_device_session()`, `get_screen_time_summary()`, `get_app_usage_history()`, `sync_device_data()` (batch endpoint for background sync).

- [ ] **Step 6: Implement device agent router**

Create `src/device_agent/router.py`:
- `POST /api/v1/device/sessions` — record device session
- `POST /api/v1/device/usage` — record app usage
- `POST /api/v1/device/sync` — batch sync (multiple records)
- `GET /api/v1/device/screen-time?member_id=<id>&date=<date>` — get screen time summary
- `GET /api/v1/device/usage?member_id=<id>&date=<date>` — get app usage

- [ ] **Step 7: Register router in main.py**

Modify `src/main.py` — Add `from src.device_agent.router import router as device_agent_router` and mount at `/api/v1/device`.
Modify `alembic/env.py` — Add `from src.device_agent.models import *`.

- [ ] **Step 8: Write E2E and security tests**

Create `tests/e2e/test_device_agent.py` — Full sync flow, screen time aggregation, multi-day queries.
Create `tests/security/test_device_agent_security.py` — Parent-only access, cannot see other families, rate limiting on sync.

- [ ] **Step 9: Write Safety app device screens**

Create `mobile/apps/safety/app/(device)/index.tsx` — Device overview: connected devices, last sync time, screen time today vs budget.
Create `mobile/apps/safety/app/(device)/screen-time.tsx` — Daily/weekly screen time chart, app breakdown pie chart, category bars.

- [ ] **Step 10: Run all tests and commit**

Run: `pytest tests/unit/test_device_agent.py tests/e2e/test_device_agent.py tests/security/test_device_agent_security.py -v`

```bash
git add src/device_agent/ alembic/versions/034_device_agent_tables.py
git add src/main.py alembic/env.py
git add mobile/apps/safety/app/(device)/
git add tests/unit/test_device_agent.py tests/e2e/test_device_agent.py tests/security/test_device_agent_security.py
git commit -m "feat(P2-M2): device agent — app usage, screen time, background sync"
```

---

### Task 15 (P2-M3): Cross-Product Alert View — Unified AI + Social Feed

**Files:**
- Modify: `src/alerts/service.py` (add social alert generation)
- Modify: `src/alerts/router.py` (add unified feed endpoint)
- Modify: `mobile/apps/safety/app/(dashboard)/alerts.tsx` (unified view)
- Create: `tests/e2e/test_unified_alerts.py`

**Tests Required:** Component ≥15, Integration ≥10

- [ ] **Step 1: Write failing tests for unified alert feed**

Create `tests/e2e/test_unified_alerts.py` — Test: AI alert and social alert both appear in unified feed, sorted by severity then timestamp. Test severity drill-down. Test filter by source (ai|social|device).

- [ ] **Step 2: Extend alert service**

Modify `src/alerts/service.py` — Add `get_unified_alerts(db, group_id, member_id, source_filter, page, page_size)` — queries alerts table with optional source filter. Add social alert generation: when moderation rejects content, create alert for parent.

- [ ] **Step 3: Add unified endpoint**

Modify `src/alerts/router.py` — Add `GET /api/v1/alerts/unified?member_id=<id>&source=<ai|social|device>` — paginated, filterable.

- [ ] **Step 4: Upgrade Safety app alerts screen**

Modify `mobile/apps/safety/app/(dashboard)/alerts.tsx` — Add source tabs (All | AI | Social | Device), severity badges, drill-down to alert detail with context (AI: capture event, Social: post/message, Device: app usage).

- [ ] **Step 5: Run tests and commit**

```bash
git add src/alerts/service.py src/alerts/router.py
git add mobile/apps/safety/app/(dashboard)/alerts.tsx
git add tests/e2e/test_unified_alerts.py
git commit -m "feat(P2-M3): cross-product alert view — unified AI + social + device feed"
```

---

### Task 16 (P2-M4): Child Profile — Combined AI + Social Timeline, Risk Trend

**Files:**
- Create: `mobile/apps/safety/app/(children)/child-profile.tsx`
- Modify: `src/portal/service.py` (add child profile aggregation)
- Create: `tests/e2e/test_child_profile.py`

**Tests Required:** Component ≥10, Integration ≥10

- [ ] **Step 1: Write failing tests**

Create `tests/e2e/test_child_profile.py` — Test: get combined child profile with AI activity + social activity + risk trend. Test platform breakdown. Test timeline ordering.

- [ ] **Step 2: Implement child profile aggregation**

Modify `src/portal/service.py` — Add `get_child_profile(db, member_id, auth)` — combines: recent AI captures, social posts/messages, risk events, device usage, moderation decisions. Returns unified timeline sorted by timestamp.

- [ ] **Step 3: Write child profile screen**

Create `mobile/apps/safety/app/(children)/child-profile.tsx` — Header: child name + avatar + age tier + risk score. Timeline: mixed AI and social events. Risk trend chart (7/30 day). Platform breakdown pie chart. Quick actions: view contacts, view screen time, adjust settings.

- [ ] **Step 4: Run tests and commit**

```bash
git add src/portal/service.py
git add mobile/apps/safety/app/(children)/child-profile.tsx
git add tests/e2e/test_child_profile.py
git commit -m "feat(P2-M4): child profile — combined AI + social timeline, risk trend, platform breakdown"
```

---

### Task 17 (P2-M5): Contact Approval — Parent Notification, Requester Profile, Approve/Deny

**Files:**
- Create: `mobile/apps/safety/app/(children)/contact-approval.tsx`
- Modify: `src/contacts/service.py` (add parent notification on new request)
- Create: `tests/e2e/test_contact_approval.py`
- Create: `tests/security/test_contact_approval_security.py`

**Tests Required:** Component ≥10, Integration ≥5, Security ≥5

- [ ] **Step 1: Write failing tests**

Create `tests/e2e/test_contact_approval.py` — Test: child sends contact request → parent receives notification → parent views requester profile → parent approves/denies → contact status updated. Test batch approval.

- [ ] **Step 2: Extend contacts service**

Modify `src/contacts/service.py` — After creating a contact request that requires parent approval, trigger push notification to parent. Add `get_pending_with_profiles(db, parent_user_id)` that joins requester profile data.

- [ ] **Step 3: Write contact approval screen**

Create `mobile/apps/safety/app/(children)/contact-approval.tsx` — List of pending contact requests for parent's children. Each shows: requester name + avatar + age tier, child's name, request date, mutual contacts count. Approve / Deny buttons. Batch approve/deny.

- [ ] **Step 4: Write security tests and commit**

Create `tests/security/test_contact_approval_security.py` — Only parent of the child can approve. Cannot approve on behalf of other families.

```bash
git add src/contacts/service.py
git add mobile/apps/safety/app/(children)/contact-approval.tsx
git add tests/e2e/test_contact_approval.py tests/security/test_contact_approval_security.py
git commit -m "feat(P2-M5): contact approval — parent notification, requester profile, approve/deny"
```

---

### Task 18 (P2-M6): App Store Submission — iOS + Google Play

**Files:**
- Modify: `mobile/eas.json` (production build profiles)
- Create: `mobile/apps/safety/store-listing.md` (App Store metadata)
- Create: `mobile/apps/social/store-listing.md` (App Store metadata)

**No automated tests — manual QA submission process.**

- [ ] **Step 1: Prepare Safety app store listing**

Create `mobile/apps/safety/store-listing.md` — App name, subtitle, description, keywords, screenshots spec, privacy policy URL (bhapi.ai/legal/privacy), age rating (4+), review notes.

- [ ] **Step 2: Prepare Social app store listing**

Create `mobile/apps/social/store-listing.md` — Same structure. Note: Social app targets children, requires specific App Store Review guidelines compliance (guideline 1.3, kids category).

- [ ] **Step 3: Build production binaries**

Run: `cd mobile/apps/safety && eas build --platform all --profile production`
Run: `cd mobile/apps/social && eas build --platform all --profile production`

- [ ] **Step 4: Submit to App Store Connect + Google Play Console**

Run: `cd mobile/apps/safety && eas submit --platform ios --profile production`
Run: `cd mobile/apps/safety && eas submit --platform android --profile production`

- [ ] **Step 5: Commit**

```bash
git add mobile/eas.json mobile/apps/safety/store-listing.md mobile/apps/social/store-listing.md
git commit -m "feat(P2-M6): App Store submission preparation — Safety app iOS + Google Play"
```

---

## Track C: Compliance

### Task 19 (P2-C1): Ohio Governance Final — District Customization, AI Tool Import, Audit Trail, Board Report

**DEADLINE: July 1, 2026 — START WEEK 13**

**Files:**
- Create: `src/governance/ohio.py`
- Modify: `src/governance/service.py` (extend for district customization)
- Modify: `src/governance/router.py` (add Ohio-specific endpoints)
- Create: `alembic/versions/035_ohio_governance_extensions.py`
- Modify: `alembic/env.py` (import new models if any)
- Create: `tests/unit/test_ohio_governance.py`
- Create: `tests/e2e/test_ohio_governance.py`
- Create: `tests/security/test_ohio_governance_security.py`

**Tests Required:** Unit ≥25, E2E ≥15, Security ≥10

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/test_ohio_governance.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_ohio_district_customization(test_session):
    """District can customize Ohio policy template with local requirements."""
    from src.governance.ohio import customize_ohio_policy
    policy = await customize_ohio_policy(
        db=test_session,
        school_id="school-1",
        district_name="Columbus City Schools",
        additional_requirements=["Require parental opt-in for AI tools"],
        approved_tools=["Google Classroom AI", "Khan Academy"],
    )
    assert policy["state_code"] == "OH"
    assert "Columbus City Schools" in policy["content"]["district_name"]
    assert len(policy["content"]["approved_tools"]) == 2

@pytest.mark.asyncio
async def test_ohio_ai_tool_import_csv(test_session):
    """District can bulk import AI tools from CSV."""
    from src.governance.ohio import import_tools_csv
    csv_data = "tool_name,vendor,risk_level,approval_status\nChatGPT,OpenAI,high,pending\nGrammarly,Grammarly Inc,low,approved"
    result = await import_tools_csv(test_session, "school-1", csv_data)
    assert result["imported"] == 2
    assert result["errors"] == []

@pytest.mark.asyncio
async def test_ohio_board_report_generation(test_session):
    """Generate board-ready PDF report of AI governance compliance."""
    from src.governance.ohio import generate_board_report
    report = await generate_board_report(test_session, "school-1")
    assert report["format"] == "pdf"
    assert "compliance_score" in report
    assert "tool_inventory_count" in report
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_ohio_governance.py -v`

- [ ] **Step 3: Create Ohio governance extensions migration**

Create `alembic/versions/035_ohio_governance_extensions.py` — Add columns to GovernancePolicy: `district_name`, `district_customizations` (JSON). Add `GovernanceImportLog` table for CSV import tracking.

- [ ] **Step 4: Implement Ohio governance module**

Create `src/governance/ohio.py`:
- `customize_ohio_policy()` — Takes base Ohio template, applies district-specific customizations
- `import_tools_csv()` — Parse CSV, validate, bulk create tool inventory entries
- `generate_board_report()` — Aggregate compliance data into PDF-ready structure
- `get_ohio_compliance_status()` — Check all required policies exist and are active

- [ ] **Step 5: Add Ohio-specific endpoints**

Modify `src/governance/router.py`:
- `POST /api/v1/governance/ohio/customize` — district customization
- `POST /api/v1/governance/ohio/import-tools` — CSV tool import
- `GET /api/v1/governance/ohio/board-report` — generate board report
- `GET /api/v1/governance/ohio/status` — compliance status check

- [ ] **Step 6: Write E2E and security tests**

Create `tests/e2e/test_ohio_governance.py` — Full flow: create school → customize Ohio policy → import tools → check compliance → generate board report.
Create `tests/security/test_ohio_governance_security.py` — Only school admins can customize, import requires admin role, board report respects school isolation.

- [ ] **Step 7: Run all tests and commit**

Run: `pytest tests/unit/test_ohio_governance.py tests/e2e/test_ohio_governance.py tests/security/test_ohio_governance_security.py -v`

```bash
git add src/governance/ohio.py src/governance/service.py src/governance/router.py
git add alembic/versions/035_ohio_governance_extensions.py alembic/env.py
git add tests/unit/test_ohio_governance.py tests/e2e/test_ohio_governance.py tests/security/test_ohio_governance_security.py
git commit -m "feat(P2-C1): Ohio governance final — district customization, AI tool import, audit trail, board report"
```

**Important:** All new sub-modules (`ohio.py`, `eu_ai_act.py`, `state_framework.py`) must expose their public interfaces through `src/governance/__init__.py` per module communication rules. Same applies to `src/compliance/australian.py` and `src/compliance/uk_aadc.py` → expose via `src/compliance/__init__.py`.

---

### Task 20 (P2-C2): EU AI Act — Conformity Assessment, Tech Docs, Risk Management, Bias Testing

**DEADLINE: August 2, 2026 — START NO LATER THAN WEEK 15**

**Files:**
- Create: `src/governance/eu_ai_act.py`
- Create: `alembic/versions/036_eu_ai_act_tables.py`
- Modify: `src/governance/router.py` (add EU AI Act endpoints)
- Modify: `alembic/env.py`
- Create: `tests/unit/test_eu_ai_act.py`
- Create: `tests/e2e/test_eu_ai_act.py`
- Create: `tests/security/test_eu_ai_act_security.py`

**Tests Required:** Unit ≥40, E2E ≥30, Security ≥15

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/test_eu_ai_act.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_conformity_assessment_structure(test_session):
    """Conformity assessment covers all required EU AI Act articles."""
    from src.governance.eu_ai_act import create_conformity_assessment
    assessment = await create_conformity_assessment(test_session, group_id="org-1")
    required_articles = ["Article 9", "Article 10", "Article 11", "Article 12",
                         "Article 13", "Article 14", "Article 15"]
    for article in required_articles:
        assert article in assessment["sections"], f"Missing {article}"

@pytest.mark.asyncio
async def test_technical_documentation_generation(test_session):
    """Tech docs include all Annex IV required elements."""
    from src.governance.eu_ai_act import generate_tech_documentation
    docs = await generate_tech_documentation(test_session, group_id="org-1")
    annex_iv = ["general_description", "design_specifications", "development_process",
                "monitoring_functioning", "risk_management", "data_governance",
                "human_oversight", "accuracy_robustness"]
    for section in annex_iv:
        assert section in docs["sections"]

@pytest.mark.asyncio
async def test_bias_testing_framework(test_session):
    """Bias testing covers protected characteristics per EU AI Act."""
    from src.governance.eu_ai_act import run_bias_test
    result = await run_bias_test(
        test_session,
        group_id="org-1",
        model_id="safety-classifier",
        test_data=[
            {"text": "Sample content", "demographic": "age_5_9"},
            {"text": "Sample content", "demographic": "age_10_12"},
            {"text": "Sample content", "demographic": "age_13_15"},
        ],
    )
    assert "overall_bias_score" in result
    assert "demographic_breakdown" in result
    assert result["overall_bias_score"] >= 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_eu_ai_act.py -v`

- [ ] **Step 3: Create EU AI Act migration**

Create `alembic/versions/036_eu_ai_act_tables.py`:
- `ConformityAssessment`: `group_id`, `version`, `status` (draft|submitted|approved), `sections` (JSON), `assessor`, `assessed_at`
- `TechnicalDocumentation`: `group_id`, `version`, `sections` (JSON), `generated_at`
- `RiskManagementRecord`: `group_id`, `risk_type`, `severity`, `likelihood`, `mitigation`, `residual_risk`, `reviewed_at`
- `BiasTestResult`: `group_id`, `model_id`, `test_data_hash`, `results` (JSON), `overall_score`, `tested_at`

- [ ] **Step 4: Implement EU AI Act module**

Create `src/governance/eu_ai_act.py`:
- `create_conformity_assessment()` — Structured assessment per Articles 9-15
- `generate_tech_documentation()` — Annex IV compliant tech docs
- `run_risk_management_assessment()` — Article 9 risk management system
- `run_bias_test()` — Article 10 data governance + bias testing
- `get_compliance_status()` — Overall EU AI Act readiness score

- [ ] **Step 5: Add EU AI Act endpoints**

Modify `src/governance/router.py`:
- `POST /api/v1/governance/eu-ai-act/assessment` — create/update conformity assessment
- `GET /api/v1/governance/eu-ai-act/assessment` — get current assessment
- `POST /api/v1/governance/eu-ai-act/tech-docs` — generate tech documentation
- `POST /api/v1/governance/eu-ai-act/risk-management` — risk management assessment
- `POST /api/v1/governance/eu-ai-act/bias-test` — run bias test
- `GET /api/v1/governance/eu-ai-act/status` — overall compliance status

- [ ] **Step 6: Write E2E and security tests**

Create `tests/e2e/test_eu_ai_act.py` — Full compliance workflow: assessment → tech docs → risk management → bias test → status check.
Create `tests/security/test_eu_ai_act_security.py` — Admin-only access, multi-tenant isolation, assessment versioning integrity.

- [ ] **Step 7: Run all tests and commit**

```bash
git add src/governance/eu_ai_act.py alembic/versions/036_eu_ai_act_tables.py alembic/env.py
git add src/governance/router.py
git add tests/unit/test_eu_ai_act.py tests/e2e/test_eu_ai_act.py tests/security/test_eu_ai_act_security.py
git commit -m "feat(P2-C2): EU AI Act — conformity assessment, tech docs, risk management, bias testing"
```

---

### Task 21 (P2-C3): EU Database Registration Submission

**Files:**
- Modify: `src/governance/eu_ai_act.py` (add registration submission)
- Create: `tests/e2e/test_eu_registration.py`

**Tests Required:** E2E ≥5

- [ ] **Step 1: Write failing tests**

Create `tests/e2e/test_eu_registration.py` — Test: generate registration payload → validate all required fields → submit (mock) → track submission status.

- [ ] **Step 2: Implement registration submission**

Add to `src/governance/eu_ai_act.py`:
- `generate_registration_payload()` — EU database required fields
- `submit_registration()` — Mock submission (real integration when API available)
- `get_registration_status()` — Track submission state

- [ ] **Step 3: Run tests and commit**

```bash
git add src/governance/eu_ai_act.py tests/e2e/test_eu_registration.py
git commit -m "feat(P2-C3): EU database registration submission"
```

---

### Task 22 (P2-C4): Australian Compliance — Age Verification Enforcement, eSafety Live, Cyberbullying

**Files:**
- Create: `src/compliance/australian.py`
- Create: `alembic/versions/037_australian_compliance.py`
- Modify: `src/compliance/router.py` (add Australian endpoints)
- Modify: `alembic/env.py`
- Create: `tests/unit/test_australian_compliance.py`
- Create: `tests/e2e/test_australian_compliance.py`
- Create: `tests/security/test_australian_compliance_security.py`

**Tests Required:** Unit ≥20, E2E ≥15, Security ≥10

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/test_australian_compliance.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_australian_age_verification_enforcement(test_session):
    """Australian users must verify age before social access."""
    from src.compliance.australian import check_au_age_requirement
    result = await check_au_age_requirement(
        db=test_session,
        user_id="user-1",
        country_code="AU",
    )
    assert result["verification_required"] is True
    assert result["method"] == "yoti"  # or gov-issued ID

@pytest.mark.asyncio
async def test_esafety_24h_sla_monitoring(test_session):
    """eSafety complaints must be actioned within 24 hours."""
    from src.compliance.australian import check_esafety_sla
    result = await check_esafety_sla(test_session)
    assert "pending_count" in result
    assert "overdue_count" in result
    assert "average_response_hours" in result

@pytest.mark.asyncio
async def test_cyberbullying_workflow(test_session):
    """Cyberbullying reports follow structured workflow."""
    from src.compliance.australian import create_cyberbullying_case
    case = await create_cyberbullying_case(
        db=test_session,
        reporter_id="user-1",
        target_id="user-2",
        evidence_ids=["post-1", "message-1"],
        severity="high",
    )
    assert case["status"] == "open"
    assert case["workflow_steps"] is not None
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Create Australian compliance migration**

Create `alembic/versions/037_australian_compliance.py`:
- `AgeVerificationRecord`: `user_id`, `country_code`, `method`, `verified`, `verified_at`, `verification_data` (JSON encrypted)
- `ESafetyReport`: `content_id`, `content_type`, `reported_at`, `actioned_at`, `sla_hours`, `status`
- `CyberbullyingCase`: `reporter_id`, `target_id`, `evidence_ids` (JSON), `severity`, `status`, `workflow_steps` (JSON)

- [ ] **Step 4: Implement Australian compliance module**

Create `src/compliance/australian.py` — Age verification enforcement, eSafety SLA monitoring (24h), cyberbullying workflow (detect → document → notify parent → escalate to eSafety if needed).

- [ ] **Step 5: Add endpoints and write E2E/security tests**

- [ ] **Step 6: Run all tests and commit**

```bash
git add src/compliance/australian.py alembic/versions/037_australian_compliance.py alembic/env.py
git add src/compliance/router.py
git add tests/unit/test_australian_compliance.py tests/e2e/test_australian_compliance.py tests/security/test_australian_compliance_security.py
git commit -m "feat(P2-C4): Australian compliance — age verification enforcement, eSafety live, cyberbullying workflow"
```

---

### Task 23 (P2-C5): UK AADC — Gap Analysis + Privacy-by-Default Implementation

**Files:**
- Create: `src/compliance/uk_aadc.py`
- Create: `alembic/versions/038_uk_aadc_tables.py`
- Modify: `alembic/env.py`
- Create: `tests/unit/test_uk_aadc.py`
- Create: `tests/e2e/test_uk_aadc.py`

**Tests Required:** Unit ≥15, E2E ≥10

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_uk_aadc.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_aadc_gap_analysis(test_session):
    """Gap analysis identifies AADC non-compliant settings."""
    from src.compliance.uk_aadc import run_gap_analysis
    gaps = await run_gap_analysis(test_session, group_id="org-1")
    assert "standards" in gaps  # 15 AADC standards
    assert all(s["status"] in ["compliant", "partial", "non_compliant"] for s in gaps["standards"])

@pytest.mark.asyncio
async def test_privacy_by_default_enforcement(test_session):
    """New child accounts have maximum privacy by default."""
    from src.compliance.uk_aadc import get_default_privacy_settings
    settings = await get_default_privacy_settings(age_tier="young")
    assert settings["profile_visibility"] == "private"
    assert settings["geolocation_enabled"] is False
    assert settings["profiling_enabled"] is False
    assert settings["data_sharing_enabled"] is False
```

- [ ] **Step 2: Create migration, implement module, write tests, commit**

```bash
git add src/compliance/uk_aadc.py alembic/versions/038_uk_aadc_tables.py alembic/env.py
git add tests/unit/test_uk_aadc.py tests/e2e/test_uk_aadc.py
git commit -m "feat(P2-C5): UK AADC — gap analysis + privacy-by-default implementation"
```

---

### Task 24 (P2-C6): State Compliance Framework — Extensible for CA, TX, FL, NY

**Files:**
- Create: `src/governance/state_framework.py`
- Create: `tests/unit/test_state_framework.py`

**Tests Required:** Unit ≥10

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_state_framework.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_register_state_regulation(test_session):
    """Framework supports registering new state regulations."""
    from src.governance.state_framework import StateComplianceFramework
    framework = StateComplianceFramework()
    framework.register_state("CA", {
        "name": "California AADC",
        "effective_date": "2027-07-01",
        "requirements": ["age_verification", "data_minimization", "opt_out_profiling"],
    })
    assert "CA" in framework.get_registered_states()

@pytest.mark.asyncio
async def test_check_multi_state_compliance(test_session):
    """Check compliance across multiple states simultaneously."""
    from src.governance.state_framework import StateComplianceFramework
    framework = StateComplianceFramework()
    # Register OH (already done) + CA
    result = framework.check_compliance(["OH", "CA"])
    assert "OH" in result
    assert "CA" in result
    assert all(s["status"] in ["compliant", "partial", "non_compliant"] for s in result.values())
```

- [ ] **Step 2: Implement state framework**

Create `src/governance/state_framework.py` — Extensible registry pattern. Each state has required policies, deadlines, and compliance checks. `check_compliance()` runs all applicable checks. Supports: OH (active), CA/TX/FL/NY (2027 prep).

- [ ] **Step 3: Run tests and commit**

```bash
git add src/governance/state_framework.py tests/unit/test_state_framework.py
git commit -m "feat(P2-C6): state compliance framework — extensible for CA, TX, FL, NY 2027 prep"
```

---

## Track D: Safety Engine

### Task 25 (P2-E1): Age-Tier Enforcement — Permission Checks on All Social Endpoints

**Files:**
- Create: `src/age_tier/middleware.py`
- Modify: `src/social/router.py` (add middleware dependency)
- Modify: `src/contacts/router.py` (add middleware dependency)
- Modify: `src/messaging/router.py` (add middleware dependency)
- Modify: `src/media/router.py` (add middleware dependency)
- Create: `tests/unit/test_age_tier_enforcement.py`
- Create: `tests/security/test_age_tier_enforcement_security.py`

**Tests Required:** Unit ≥25, Security ≥20

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/test_age_tier_enforcement.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_young_user_cannot_message(test_session, young_user_headers):
    """Young tier (5-9) cannot access messaging endpoints."""
    from httpx import AsyncClient
    # POST /api/v1/messages/conversations should return 403

@pytest.mark.asyncio
async def test_young_user_cannot_search(test_session, young_user_headers):
    """Young tier (5-9) cannot search users."""
    # GET /api/v1/social/search should return 403

@pytest.mark.asyncio
async def test_preteen_user_can_message(test_session, preteen_user_headers):
    """Preteen tier (10-12) can access messaging."""
    # POST /api/v1/messages/conversations should return 200

@pytest.mark.asyncio
async def test_teen_user_can_upload_video(test_session, teen_user_headers):
    """Teen tier (13-15) can upload video."""
    # POST /api/v1/media/upload with video should return 200

@pytest.mark.asyncio
async def test_enforcement_middleware_checks_all_endpoints():
    """Every social endpoint has age-tier enforcement."""
    from src.age_tier.middleware import PROTECTED_ENDPOINTS
    from src.social.router import router as social_router
    from src.contacts.router import router as contacts_router
    from src.messaging.router import router as messaging_router
    # Verify all routes are in PROTECTED_ENDPOINTS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_age_tier_enforcement.py -v`

- [ ] **Step 3: Implement age-tier enforcement middleware**

Create `src/age_tier/middleware.py`:
```python
from fastapi import Depends, Request
from src.dependencies import AuthContext
from src.age_tier import check_permission, get_tier_for_age
from src.exceptions import ForbiddenError

ENDPOINT_PERMISSIONS = {
    "POST /api/v1/social/posts": "can_post",
    "POST /api/v1/social/posts/{post_id}/comments": "can_comment",
    "POST /api/v1/messages/conversations": "can_message",
    "POST /api/v1/messages/conversations/{conversation_id}/messages": "can_message",
    "GET /api/v1/social/search": "can_search_users",
    "POST /api/v1/contacts/request/{user_id}": "can_add_contacts",
    "POST /api/v1/media/upload": "can_upload_image",  # video checked separately
    # ... all social endpoints
}

async def enforce_age_tier(request: Request, auth: AuthContext = Depends()):
    """Middleware dependency that checks age-tier permissions for social endpoints."""
    endpoint_key = f"{request.method} {request.url.path}"
    permission = _match_endpoint(endpoint_key)
    if permission is None:
        return  # Not a gated endpoint
    tier = _get_user_tier(auth)
    if tier is None:
        return  # Not a child user
    if not check_permission(tier, permission):
        raise ForbiddenError(
            detail=f"This feature is not available for your age group",
            code="AGE_TIER_RESTRICTED",
        )
```

- [ ] **Step 4: Add middleware to all social routers**

Modify `src/social/router.py`, `src/contacts/router.py`, `src/messaging/router.py`, `src/media/router.py` — Add `dependencies=[Depends(enforce_age_tier)]` to router instantiation.

- [ ] **Step 5: Write security tests**

Create `tests/security/test_age_tier_enforcement_security.py` — Comprehensive tests for every social endpoint × every age tier. Verify no endpoint is unprotected. Test permission bypass attempts.

- [ ] **Step 6: Run all tests and commit**

```bash
git add src/age_tier/middleware.py
git add src/social/router.py src/contacts/router.py src/messaging/router.py src/media/router.py
git add tests/unit/test_age_tier_enforcement.py tests/security/test_age_tier_enforcement_security.py
git commit -m "feat(P2-E1): age-tier enforcement — permission checks on all social endpoints, feature gating middleware"
```

---

### Task 26 (P2-E2): Social Graph Analysis — Age-Inappropriate Contacts, Isolation, Influence

**Files:**
- Create: `src/social/graph_analysis.py`
- Create: `src/intelligence/__init__.py`
- Create: `src/intelligence/models.py`
- Create: `src/intelligence/service.py`
- Create: `src/intelligence/router.py`
- Create: `src/intelligence/schemas.py`
- Create: `alembic/versions/041_intelligence_tables.py`
- Modify: `src/main.py` (register intelligence router)
- Modify: `alembic/env.py`
- Create: `tests/unit/test_graph_analysis.py`
- Create: `tests/e2e/test_graph_analysis.py`

**Tests Required:** Unit ≥30, E2E ≥20

**Note:** Migration numbering may need adjustment if Task 8 (push tokens) used 033. Use next available number.

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/test_graph_analysis.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_detect_age_inappropriate_contact(test_session):
    """Detect when contact age gap exceeds threshold for tier."""
    from src.social.graph_analysis import analyze_contacts
    result = await analyze_contacts(test_session, member_id="child-1")
    assert "age_gap_flags" in result
    # If a 15yo contacts a 7yo, flag it

@pytest.mark.asyncio
async def test_detect_isolation(test_session):
    """Detect socially isolated children (few/no contacts, no interaction)."""
    from src.social.graph_analysis import detect_isolation
    result = await detect_isolation(test_session, member_id="child-1")
    assert "isolation_score" in result  # 0-100
    assert "indicators" in result

@pytest.mark.asyncio
async def test_influence_mapping(test_session):
    """Map influence patterns in child's social graph."""
    from src.social.graph_analysis import map_influence
    result = await map_influence(test_session, member_id="child-1")
    assert "influencers" in result  # Users who most affect this child
    assert "influence_score" in result
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Create intelligence models and migration**

Create `src/intelligence/models.py`:
```python
class SocialGraphEdge(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "social_graph_edges"
    source_id = Column(String, ForeignKey("group_members.id"), nullable=False, index=True)
    target_id = Column(String, ForeignKey("group_members.id"), nullable=False, index=True)
    edge_type = Column(String, nullable=False)  # contact, follow, message, mention
    weight = Column(Float, default=1.0)  # Interaction frequency
    last_interaction = Column(DateTime(timezone=True))

class AbuseSignal(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "abuse_signals"
    member_id = Column(String, ForeignKey("group_members.id"), nullable=False, index=True)
    signal_type = Column(String, nullable=False)  # age_gap, isolation, influence, farming
    severity = Column(String, nullable=False)  # low, medium, high, critical
    details = Column(JSON, default=dict)
    resolved = Column(Boolean, default=False)
```

- [ ] **Step 4: Implement graph analysis**

Create `src/social/graph_analysis.py`:
- `analyze_contacts()` — Check age gaps, flag suspicious contact patterns
- `detect_isolation()` — Score based on contact count, interaction frequency, response rate
- `map_influence()` — Identify high-influence users in child's network
- `detect_age_inappropriate_pattern()` — Flag contacts where age tier mismatch is concerning

- [ ] **Step 5: Create intelligence service and router**

Implement `src/intelligence/service.py` and `src/intelligence/router.py` — Endpoints for graph analysis results, abuse signals, isolation alerts.

- [ ] **Step 6: Register router, write E2E tests, commit**

```bash
git add src/social/graph_analysis.py src/intelligence/
git add alembic/versions/041_intelligence_tables.py alembic/env.py src/main.py
git add tests/unit/test_graph_analysis.py tests/e2e/test_graph_analysis.py
git commit -m "feat(P2-E2): social graph analysis — age-inappropriate contacts, isolation detection, influence mapping"
```

---

### Task 27 (P2-E3): Behavioral Baselines — Per-Child Norms, Deviation Alerting

**Files:**
- Create: `src/social/behavioral.py`
- Modify: `src/intelligence/models.py` (add BehavioralBaseline)
- Modify: `src/intelligence/service.py` (add baseline computation)
- Create: `tests/unit/test_behavioral_baselines.py`
- Create: `tests/e2e/test_behavioral_baselines.py`

**Tests Required:** Unit ≥20, E2E ≥15

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/test_behavioral_baselines.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_compute_baseline(test_session):
    """Compute behavioral baseline from 14 days of activity."""
    from src.social.behavioral import compute_baseline
    baseline = await compute_baseline(test_session, member_id="child-1", window_days=14)
    assert "avg_posts_per_day" in baseline
    assert "avg_messages_per_day" in baseline
    assert "avg_session_duration" in baseline
    assert "active_hours" in baseline  # Typical hours of activity
    assert "content_sentiment_avg" in baseline

@pytest.mark.asyncio
async def test_detect_deviation(test_session):
    """Alert when behavior deviates >2 std from baseline."""
    from src.social.behavioral import detect_deviation
    deviations = await detect_deviation(test_session, member_id="child-1")
    # Returns list of deviations with type and magnitude
    for d in deviations:
        assert "metric" in d
        assert "current_value" in d
        assert "baseline_value" in d
        assert "std_deviations" in d
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Add BehavioralBaseline model**

Add to `src/intelligence/models.py`:
```python
class BehavioralBaseline(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "behavioral_baselines"
    member_id = Column(String, ForeignKey("group_members.id"), nullable=False, index=True)
    window_days = Column(Integer, default=14)
    metrics = Column(JSON, nullable=False)  # avg_posts, avg_messages, avg_session, etc.
    computed_at = Column(DateTime(timezone=True), nullable=False)
    sample_count = Column(Integer, default=0)
```

- [ ] **Step 4: Implement behavioral analysis**

Create `src/social/behavioral.py`:
- `compute_baseline()` — Aggregate activity over window, compute mean + std for each metric
- `detect_deviation()` — Compare current activity against baseline, flag >2 std deviations
- `update_baselines_batch()` — Scheduled job to recompute baselines for all active children
- `get_baseline_summary()` — Return human-readable baseline for parent dashboard

- [ ] **Step 5: Write E2E tests and commit**

```bash
git add src/social/behavioral.py src/intelligence/models.py src/intelligence/service.py
git add tests/unit/test_behavioral_baselines.py tests/e2e/test_behavioral_baselines.py
git commit -m "feat(P2-E3): behavioral baselines — per-child norms, deviation alerting"
```

---

### Task 28 (P2-E4): Pre-Publish Moderation Live — 5-9 and 10-12 Tiers, <2s p95

**Files:**
- Modify: `src/moderation/service.py` (optimize pipeline for <2s)
- Modify: `src/moderation/keyword_filter.py` (performance tuning)
- Create: `tests/unit/test_moderation_performance.py`
- Create: `tests/e2e/test_prepublish_live.py`

**Tests Required:** Unit ≥20, E2E ≥15, Performance ≥10

- [ ] **Step 1: Write failing performance tests**

Create `tests/unit/test_moderation_performance.py`:
```python
import pytest
import time

@pytest.mark.asyncio
async def test_prepublish_latency_under_2s(test_session):
    """Pre-publish moderation must complete in <2s."""
    from src.moderation import submit_for_moderation
    start = time.monotonic()
    result = await submit_for_moderation(
        db=test_session,
        content_type="post",
        content_id="test-post-1",
        author_age_tier="young",
        content_text="Hello friends! I made a drawing today.",
        media_ids=[],
    )
    elapsed = time.monotonic() - start
    assert elapsed < 2.0, f"Pre-publish took {elapsed:.2f}s (limit: 2.0s)"
    assert result.status in ["approved", "rejected", "escalated"]

@pytest.mark.asyncio
async def test_prepublish_false_negative_rate(test_session):
    """<0.1% false negative on severe content for pre-publish."""
    from src.moderation import submit_for_moderation
    severe_content = [
        "I want to hurt myself",
        "Meet me at [address] and don't tell your parents",
        "Send me a picture without clothes",
    ]
    detected = 0
    for content in severe_content:
        result = await submit_for_moderation(
            db=test_session,
            content_type="post",
            content_id=f"test-{hash(content)}",
            author_age_tier="young",
            content_text=content,
            media_ids=[],
        )
        if result.status in ["rejected", "escalated"]:
            detected += 1
    assert detected == len(severe_content), "Severe content must always be caught"
```

- [ ] **Step 2: Run tests to verify performance**

Run: `pytest tests/unit/test_moderation_performance.py -v`

- [ ] **Step 3: Optimize pre-publish pipeline**

Modify `src/moderation/service.py`:
- Fast-path: keyword filter first (<100ms). If keyword match → reject immediately.
- Parallel: run social risk + image classification concurrently.
- Cache: cache keyword lists in memory (refresh every 5 min).
- Short-circuit: if CSAM detected, skip all other checks.

Modify `src/moderation/keyword_filter.py` — Use Aho-Corasick for multi-pattern matching. Pre-compile patterns on startup.

- [ ] **Step 4: Add parent notification on blocks**

When pre-publish rejects content for under-13, create alert for parent and send push notification.

- [ ] **Step 5: Write E2E tests and commit**

Create `tests/e2e/test_prepublish_live.py` — Test full pipeline for young and preteen tiers. Verify auto-approve for safe content, auto-reject for severe, escalate for ambiguous.

```bash
git add src/moderation/service.py src/moderation/keyword_filter.py
git add tests/unit/test_moderation_performance.py tests/e2e/test_prepublish_live.py
git commit -m "feat(P2-E4): pre-publish moderation live — 5-9 and 10-12 tiers, <2s p95, parent notification"
```

---

### Task 29 (P2-E5): Post-Publish Moderation Live — 13-15 Tier, <60s Takedown

**Files:**
- Modify: `src/moderation/service.py` (add async post-publish pipeline)
- Create: `tests/unit/test_postpublish.py`
- Create: `tests/e2e/test_postpublish_live.py`

**Tests Required:** Unit ≥15, E2E ≥10

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_postpublish.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_postpublish_content_published_immediately(test_session):
    """Teen content publishes immediately, moderation runs async."""
    from src.moderation import submit_for_moderation
    result = await submit_for_moderation(
        db=test_session,
        content_type="post",
        content_id="teen-post-1",
        author_age_tier="teen",
        content_text="Just finished my science project!",
        media_ids=[],
    )
    assert result.status == "approved"  # Published immediately
    assert result.pipeline == "post_publish"

@pytest.mark.asyncio
async def test_postpublish_takedown_under_60s(test_session):
    """Flagged teen content taken down within 60s."""
    from src.moderation import submit_for_moderation, takedown_content
    result = await submit_for_moderation(
        db=test_session,
        content_type="post",
        content_id="teen-post-2",
        author_age_tier="teen",
        content_text="Harmful content that should be caught",
        media_ids=[],
    )
    # Post-publish pipeline should flag and auto-takedown
    assert result.pipeline == "post_publish"
```

- [ ] **Step 2: Implement post-publish pipeline**

Modify `src/moderation/service.py` — For teen tier: immediately approve (published), then run async background moderation. If flagged → auto-takedown + create alert for parent + notification to author.

- [ ] **Step 3: Add auto-escalation**

When post-publish detects severe content: immediate takedown, parent alert, potential account restriction pending review.

- [ ] **Step 4: Write E2E tests and commit**

```bash
git add src/moderation/service.py
git add tests/unit/test_postpublish.py tests/e2e/test_postpublish_live.py
git commit -m "feat(P2-E5): post-publish moderation live — 13-15 tier, <60s takedown, auto-escalation"
```

---

### Task 30 (P2-E6): Moderation Dashboard — Queue, Bulk Actions, Pattern Detection, SLA Tracking

**Files:**
- Create: `src/moderation/dashboard_service.py`
- Create: `alembic/versions/039_moderation_dashboard.py`
- Modify: `src/moderation/router.py` (add dashboard endpoints)
- Modify: `alembic/env.py`
- Create: `tests/unit/test_moderation_dashboard.py`
- Create: `tests/e2e/test_moderation_dashboard.py`

**Tests Required:** Unit ≥20, E2E ≥15

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_moderation_dashboard.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_queue_assignment(test_session):
    """Moderators can be assigned queue items."""
    from src.moderation.dashboard_service import assign_moderator
    result = await assign_moderator(test_session, queue_id="q-1", moderator_id="mod-1")
    assert result.assigned_to == "mod-1"

@pytest.mark.asyncio
async def test_bulk_action(test_session):
    """Moderators can bulk approve/reject items."""
    from src.moderation.dashboard_service import bulk_action
    result = await bulk_action(
        db=test_session,
        queue_ids=["q-1", "q-2", "q-3"],
        action="approve",
        moderator_id="mod-1",
    )
    assert result["processed"] == 3
    assert result["errors"] == []

@pytest.mark.asyncio
async def test_sla_tracking(test_session):
    """SLA metrics tracked for pre-publish and post-publish."""
    from src.moderation.dashboard_service import get_sla_metrics
    metrics = await get_sla_metrics(test_session)
    assert "pre_publish_p95_ms" in metrics
    assert "post_publish_p95_ms" in metrics
    assert "items_in_sla" in metrics
    assert "items_breached_sla" in metrics

@pytest.mark.asyncio
async def test_pattern_detection(test_session):
    """Detect emerging content patterns (e.g., new slang, trends)."""
    from src.moderation.dashboard_service import detect_patterns
    patterns = await detect_patterns(test_session, window_hours=24)
    assert isinstance(patterns, list)
```

- [ ] **Step 2: Create migration and implement dashboard service**

- [ ] **Step 3: Add endpoints**

Modify `src/moderation/router.py`:
- `POST /api/v1/moderation/queue/{queue_id}/assign` — assign moderator
- `POST /api/v1/moderation/bulk-action` — bulk approve/reject
- `GET /api/v1/moderation/sla` — SLA metrics
- `GET /api/v1/moderation/patterns` — detected patterns

- [ ] **Step 4: Write E2E tests and commit**

```bash
git add src/moderation/dashboard_service.py alembic/versions/039_moderation_dashboard.py alembic/env.py
git add src/moderation/router.py
git add tests/unit/test_moderation_dashboard.py tests/e2e/test_moderation_dashboard.py
git commit -m "feat(P2-E6): moderation dashboard — queue assignment, bulk actions, pattern detection, SLA tracking"
```

---

### Task 31 (P2-E7): Anti-Abuse Measures — Age Misrepresentation, Account Farming, Harassment Detection

**Files:**
- Create: `src/moderation/anti_abuse.py`
- Modify: `src/intelligence/models.py` (extend AbuseSignal)
- Create: `tests/unit/test_anti_abuse.py`
- Create: `tests/e2e/test_anti_abuse.py`
- Create: `tests/security/test_anti_abuse_security.py`

**Tests Required:** Unit ≥30, E2E ≥20, Security ≥10

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/test_anti_abuse.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_detect_age_misrepresentation(test_session):
    """Flag users whose behavior diverges from claimed age tier."""
    from src.moderation.anti_abuse import detect_age_misrepresentation
    signals = await detect_age_misrepresentation(test_session, member_id="member-1")
    assert "vocabulary_complexity_z" in signals
    assert "posting_time_z" in signals
    assert "flagged" in signals

@pytest.mark.asyncio
async def test_detect_account_farming(test_session):
    """Detect multiple accounts from same device."""
    from src.moderation.anti_abuse import detect_account_farming
    result = await detect_account_farming(
        test_session,
        device_fingerprint="abc123",
        ip_address="1.2.3.4",
    )
    assert "accounts_from_device" in result
    assert "flagged" in result

@pytest.mark.asyncio
async def test_detect_coordinated_harassment(test_session):
    """Detect when multiple accounts target same user."""
    from src.moderation.anti_abuse import detect_coordinated_harassment
    result = await detect_coordinated_harassment(test_session, target_id="victim-1")
    assert "report_count_24h" in result
    assert "unique_reporters" in result
    assert "flagged" in result

@pytest.mark.asyncio
async def test_serial_false_reporter_detection(test_session):
    """Flag users who submit many reports with low confirmation rate."""
    from src.moderation.anti_abuse import detect_report_abuse
    result = await detect_report_abuse(test_session, reporter_id="reporter-1")
    assert "total_reports" in result
    assert "confirmed_rate" in result
    assert "trust_score" in result

@pytest.mark.asyncio
async def test_invitation_spam_rate_limiting(test_session):
    """Rate limit contact requests per day per age tier."""
    from src.moderation.anti_abuse import check_invitation_rate
    result = await check_invitation_rate(
        test_session, member_id="member-1", age_tier="young",
    )
    assert "requests_today" in result
    assert "limit" in result  # 3 for young, 10 for preteen, 10 for teen
    assert "allowed" in result
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement anti-abuse module**

Create `src/moderation/anti_abuse.py`:
- `detect_age_misrepresentation()` — Analyze vocabulary complexity (avg word length, unique words), posting times (late night for young tier), contact patterns vs age-tier norms. Flag if >2 std deviations.
- `detect_account_farming()` — Query device sessions for fingerprint matches. Flag if >2 accounts per device.
- `detect_coordinated_harassment()` — Count reports/blocks against target in 24h window. Auto-escalate if ≥3 unique reporters.
- `detect_report_abuse()` — Track reporter accuracy. Deprioritize if confirmation rate <20% with >10 reports.
- `check_invitation_rate()` — Enforce daily limits per tier (young=3, preteen=10, teen=10).
- `check_content_manipulation()` — Normalize Unicode/leetspeak before keyword check.

- [ ] **Step 4: Write E2E and security tests**

- [ ] **Step 5: Run all tests and commit**

```bash
git add src/moderation/anti_abuse.py src/intelligence/models.py
git add tests/unit/test_anti_abuse.py tests/e2e/test_anti_abuse.py tests/security/test_anti_abuse_security.py
git commit -m "feat(P2-E7): anti-abuse — age misrepresentation, account farming, coordinated harassment, report abuse, invitation spam"
```

---

### Task 32 (P2-E8): Parental Abuse Safeguards — Trusted Adult, Custody Model, Teen Privacy

**Files:**
- Create: `src/moderation/parental_safeguards.py`
- Create: `alembic/versions/040_parental_safeguards.py`
- Modify: `alembic/env.py`
- Create: `mobile/packages/shared-ui/src/TrustedAdultButton.tsx`
- Create: `mobile/apps/social/app/(settings)/trusted-adult.tsx`
- Create: `tests/unit/test_parental_safeguards.py`
- Create: `tests/e2e/test_parental_safeguards.py`
- Create: `tests/security/test_parental_safeguards_security.py`

**Tests Required:** Unit ≥20, E2E ≥15, Security ≥10

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/test_parental_safeguards.py`:
```python
import pytest

@pytest.mark.asyncio
async def test_trusted_adult_request_not_visible_to_parent(test_session):
    """Trusted adult escalation is NOT visible to the parent."""
    from src.moderation.parental_safeguards import request_trusted_adult
    result = await request_trusted_adult(
        db=test_session,
        child_id="child-1",
        escalation_type="school_counselor",
    )
    assert result["logged"] is True
    assert result["parent_notified"] is False

@pytest.mark.asyncio
async def test_custody_aware_access(test_session):
    """Multiple guardians have separate dashboards."""
    from src.moderation.parental_safeguards import get_guardian_access
    access = await get_guardian_access(test_session, child_id="child-1", guardian_id="parent-1")
    assert access["role"] in ["primary", "secondary"]
    assert "permissions" in access

@pytest.mark.asyncio
async def test_teen_privacy_tiers(test_session):
    """Parent sees different data based on child's age tier."""
    from src.moderation.parental_safeguards import get_parent_visible_data
    # Young (5-9): everything
    young_data = await get_parent_visible_data(test_session, child_id="young-child", parent_id="parent-1")
    assert young_data["can_see_messages"] is True
    assert young_data["can_see_posts"] is True

    # Preteen (10-12): posts + contacts but not message content (unless flagged)
    preteen_data = await get_parent_visible_data(test_session, child_id="preteen-child", parent_id="parent-1")
    assert preteen_data["can_see_messages"] is False
    assert preteen_data["can_see_posts"] is True
    assert preteen_data["can_see_flagged_messages"] is True

    # Teen (13-15): activity summary + flagged only
    teen_data = await get_parent_visible_data(test_session, child_id="teen-child", parent_id="parent-1")
    assert teen_data["can_see_messages"] is False
    assert teen_data["can_see_posts"] is False
    assert teen_data["can_see_flagged_content"] is True
    assert teen_data["can_see_activity_summary"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Create parental safeguards migration**

Create `alembic/versions/040_parental_safeguards.py`:
- `TrustedAdultRequest`: `child_id`, `escalation_type` (school_counselor|helpline|designated_adult), `contact_info`, `created_at`, `resolved_at`
- `CustodyConfig`: `child_id`, `guardian_id`, `role` (primary|secondary|institutional), `permissions` (JSON), `custody_dispute` (bool), `legal_doc_reference`
- `TeenPrivacyConfig`: `age_tier`, `parent_can_see` (JSON — maps data types to visibility)
- `GuardianRole`: `group_id`, `user_id`, `role_type`, `granted_by`, `granted_at`

- [ ] **Step 4: Implement parental safeguards module**

Create `src/moderation/parental_safeguards.py`:
- `request_trusted_adult()` — Log request, do NOT notify parent. Provide helpline numbers based on country. Options: school counselor (if school account), helpline (Kids Helpline AU, Childhelp US, Childline UK), designated adult.
- `get_guardian_access()` — Return guardian's role and permissions for specific child.
- `get_parent_visible_data()` — Apply teen privacy tiers (spec Section 14.4).
- `set_custody_dispute()` — Admin-only: freeze guardian changes.
- `add_secondary_guardian()` — Primary guardian or admin can add.

- [ ] **Step 5: Write TrustedAdultButton component**

Create `mobile/packages/shared-ui/src/TrustedAdultButton.tsx` — Subtle but accessible button in settings. Tapping opens trusted adult screen. **NOT visible to parent** (does not appear in parent's view of child settings).

- [ ] **Step 6: Write trusted adult screen**

Create `mobile/apps/social/app/(settings)/trusted-adult.tsx` — "Talk to a trusted adult" with options: school counselor (if available), helpline (country-specific numbers), designated trusted adult. Reassuring, child-friendly language. "This is private — your parent won't be notified."

- [ ] **Step 7: Write E2E and security tests**

Create `tests/e2e/test_parental_safeguards.py` — Full flow: teen requests trusted adult → logged but parent not notified → custody model with dual guardians → teen privacy filtering.
Create `tests/security/test_parental_safeguards_security.py` — Parent cannot see trusted adult requests via API. Secondary guardian cannot escalate to primary. Custody dispute freezes changes.

- [ ] **Step 8: Run all tests and commit**

```bash
git add src/moderation/parental_safeguards.py alembic/versions/040_parental_safeguards.py alembic/env.py
git add mobile/packages/shared-ui/src/TrustedAdultButton.tsx
git add mobile/apps/social/app/(settings)/trusted-adult.tsx
git add tests/unit/test_parental_safeguards.py tests/e2e/test_parental_safeguards.py tests/security/test_parental_safeguards_security.py
git commit -m "feat(P2-E8): parental abuse safeguards — trusted adult escalation, custody model, teen privacy tiers"
```

---

## Exit Criteria

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
- [ ] Anti-abuse measures live (age misrepresentation, account farming, harassment detection)
- [ ] Parental abuse safeguards designed (trusted adult, custody model, teen privacy tiers)
- [ ] FERPA documentation complete, SDPA template ready
- [ ] **Test count: ≥3,689 (backend + mobile)**
- [ ] **Mobile test coverage: ≥80% screen coverage**
- [ ] **All new Alembic migrations committed and pushed**
- [ ] **0 open critical/high security findings**

### Test Count Targets (Phase 2 Increments)

| Category | Phase 1 Exit | Phase 2 Target | Increment |
|----------|-------------|----------------|-----------|
| Backend (unit + e2e + security) | ~3,125 | ~4,025 | +900 |
| Mobile (component + integration) | 213 | ~563 | +350 |
| Prod E2E | 82 | ~122 | +40 |
| Frontend (portal) | 174 | 174 | — |
| Extension | 43 | 43 | — |
| **Total** | **~3,637** | **≥3,689** | **+1,290** |

### Migration Tracking

| Number | Table | Task |
|--------|-------|------|
| 033 | `push_tokens` | P2-S8 |
| 034 | `device_sessions`, `app_usage_records`, `screen_time_records` | P2-M2 |
| 035 | Ohio governance extensions | P2-C1 |
| 036 | `conformity_assessments`, `tech_docs`, `risk_management`, `bias_tests` | P2-C2 |
| 037 | `age_verification_records`, `esafety_reports`, `cyberbullying_cases` | P2-C4 |
| 038 | `aadc_assessments`, `privacy_defaults` | P2-C5 |
| 039 | `moderator_assignments`, `sla_metrics`, `pattern_detections` | P2-E6 |
| 040 | `trusted_adults`, `custody_configs`, `teen_privacy_configs`, `guardian_roles` | P2-E8 |
| 041 | `social_graph_edges`, `abuse_signals`, `behavioral_baselines` | P2-E2/E3 |

**Serialization note:** Tasks 14 (P2-M2) and 26 (P2-E2) both modify `src/main.py` and `alembic/env.py`. If running in parallel via subagents, one must complete before the other starts — or use worktrees and merge sequentially.

### Scheduling Priorities

1. **Week 13 (Jun 9):** Start P2-C1 (Ohio — Jul 1 deadline) + P2-C2 (EU AI Act — Aug 2 deadline, needs early start for 6-8 pw effort) + P2-E1 (age-tier enforcement, foundation for all social)
2. **Week 13-14:** Start P2-S1 (onboarding) + P2-S6 (age-tier UX) — foundation for all social app work
3. **Week 14-15:** EU AI Act should have 2 dedicated engineers given the Aug 2 hard deadline and 6-8 pw effort
4. **Week 15-18:** Social app features (P2-S2 through P2-S11) + Safety app v2 (P2-M1 through P2-M5)
5. **Week 18-19:** P2-E4/E5 (live moderation) + P2-E7 (anti-abuse) + P2-E8 (parental safeguards)
6. **Week 19-20:** P2-S12 (beta) + P2-M6 (App Store) + final compliance tasks
