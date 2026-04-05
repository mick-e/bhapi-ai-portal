# Launch Excellence Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gap between "feature-complete" and "market-leader" — fix operational blockers, harden infrastructure, build missing UI components, redesign the dashboard/alerts/onboarding for "Calm Safety" UX philosophy, and prepare both mobile apps for public App Store release.

**Architecture:** No new backend modules. This plan modifies existing portal pages (Next.js 15), mobile screens (Expo/React Native), Render infrastructure config, and adds 5 new shared UI components to the portal. Mobile API stubs are wired to real endpoints. Dashboard, alerts, onboarding, and settings pages are redesigned for simplicity.

**Tech Stack:** Next.js 15 (static export) / TypeScript / Tailwind / React Query | Expo SDK 52+ / React Native / Turborepo | Render (render.yaml) | Sentry | EAS Build/Submit

**Spec:** `docs/superpowers/specs/2026-04-05-unified-roadmap-closeout-and-excellence.md` (v1.0)

**Navigation file:** `portal/src/app/(dashboard)/layout.tsx` (NOT `components/Layout.tsx` — that file does not exist)

---

## Track Overview

```
Track A: Store Submission Pipeline    (A1-A4, sequential)
Track B: Infrastructure               (B1-B3, parallel with A)
Track C: Pre-Launch Quality            (C1-C4, parallel with A & B)
Track D: UX Excellence                 (D1-D10, D1 first, then parallel)

All tracks must complete before public release (A5).
```

## Dependency Graph

```
A1 (EAS IDs) ──→ A2 (Sentry) ──→ A3 (TestFlight + Play Store) ──→ A4 (Screenshots + Listing)
                                                                           │
B1 (Redis) ──→ B2 (WebSocket deploy) ──→ B3 (Pool verify)                 │
                                                                           │
C1 (Mod SLA), C2 (Reduced motion), C3 (High contrast), C4 (Dyslexia font) │
                                                                           │
D1 (Components) ──→ D2 (Dashboard), D3 (Onboarding), D4 (Alerts), D6 (Settings) ──→ D9 (Trust), D10 (Calm lang)
D5 (Role nav) ─────────────────────────────────────────────────────────────│
D7 (Mobile API) ──→ D8 (Empty states + Dark mode)                         │
                                                                           ▼
                                                                    A5: PUBLIC RELEASE
```

---

## Track A: Store Submission Pipeline

### Task A1: Replace EAS Project IDs

**Files:**
- Modify: `mobile/apps/safety/eas.json`
- Modify: `mobile/apps/social/eas.json`
- Modify: `mobile/apps/safety/app.json`
- Modify: `mobile/apps/social/app.json`

**Context:** Both `eas.json` files have placeholder values (`SAFETY_ASC_APP_ID`, `SOCIAL_ASC_APP_ID`, `BHAPI_TEAM_ID`). These must be replaced with real Expo/Apple/Google project IDs before any build submission.

- [ ] **Step 1: Initialize EAS for Safety app**

```bash
cd mobile/apps/safety
npx eas init
```

This will prompt for Expo account login and create/link a project. It updates `app.json` with a real `extra.eas.projectId`.

- [ ] **Step 2: Initialize EAS for Social app**

```bash
cd mobile/apps/social
npx eas init
```

- [ ] **Step 3: Update Safety eas.json with real Apple credentials**

Replace the placeholder values in `mobile/apps/safety/eas.json`:

```json
{
  "build": {
    "development": { "developmentClient": true, "distribution": "internal" },
    "preview": { "distribution": "internal" },
    "production": {}
  },
  "submit": {
    "production": {
      "ios": {
        "appleId": "<YOUR_APPLE_ID>",
        "ascAppId": "<REAL_ASC_APP_ID_FROM_APP_STORE_CONNECT>",
        "appleTeamId": "<REAL_TEAM_ID_FROM_APPLE_DEVELOPER>"
      },
      "android": {
        "track": "internal",
        "rollout": 0.1
      }
    }
  }
}
```

Replace `<YOUR_APPLE_ID>`, `<REAL_ASC_APP_ID_FROM_APP_STORE_CONNECT>`, and `<REAL_TEAM_ID_FROM_APPLE_DEVELOPER>` with actual values from Apple Developer account.

- [ ] **Step 4: Update Social eas.json with real Apple credentials**

Same replacement for `mobile/apps/social/eas.json` with the Social app's App Store Connect ID.

- [ ] **Step 5: Verify both apps build**

```bash
cd mobile
npx turbo run typecheck
npx turbo run test
```

Expected: All type checks and tests pass.

- [ ] **Step 6: Commit**

```bash
git add mobile/apps/safety/eas.json mobile/apps/social/eas.json mobile/apps/safety/app.json mobile/apps/social/app.json
git commit -m "chore: replace EAS placeholder project IDs with real credentials"
```

---

### Task A2: Sentry Crash Reporting

**Files:**
- Modify: `mobile/apps/safety/app.json`
- Modify: `mobile/apps/social/app.json`
- Modify: `mobile/apps/safety/app/_layout.tsx`
- Modify: `mobile/apps/social/app/_layout.tsx`
- Modify: `mobile/package.json`

**Context:** Both mobile apps have no crash reporting. Sentry is required before public release. Use `@sentry/react-native` with Expo integration. COPPA-compliant: no PII in crash reports for the Social app (directed to children).

- [ ] **Step 1: Install Sentry in the monorepo**

```bash
cd mobile
npm install @sentry/react-native --save
cd apps/safety && npx expo install @sentry/react-native
cd ../social && npx expo install @sentry/react-native
```

- [ ] **Step 2: Add Sentry DSN to both app.json files**

In `mobile/apps/safety/app.json`, add to `expo.plugins`:

```json
["@sentry/react-native/expo", {
  "organization": "bhapi",
  "project": "bhapi-safety",
  "url": "https://sentry.io/"
}]
```

In `mobile/apps/social/app.json`, add to `expo.plugins`:

```json
["@sentry/react-native/expo", {
  "organization": "bhapi",
  "project": "bhapi-social",
  "url": "https://sentry.io/"
}]
```

- [ ] **Step 3: Initialize Sentry in Safety app root layout**

In `mobile/apps/safety/app/_layout.tsx`, add Sentry initialization at the top of the file after imports:

```typescript
import * as Sentry from '@sentry/react-native';

Sentry.init({
  dsn: process.env.EXPO_PUBLIC_SENTRY_DSN_SAFETY || '',
  tracesSampleRate: 0.2,
  environment: __DEV__ ? 'development' : 'production',
  enabled: !__DEV__,
});
```

Wrap the default export with `Sentry.wrap()`:

```typescript
export default Sentry.wrap(RootLayout);
```

- [ ] **Step 4: Initialize Sentry in Social app root layout (COPPA-compliant)**

In `mobile/apps/social/app/_layout.tsx`, add Sentry initialization with PII scrubbing:

```typescript
import * as Sentry from '@sentry/react-native';

Sentry.init({
  dsn: process.env.EXPO_PUBLIC_SENTRY_DSN_SOCIAL || '',
  tracesSampleRate: 0.2,
  environment: __DEV__ ? 'development' : 'production',
  enabled: !__DEV__,
  beforeSend(event) {
    // COPPA: strip PII from crash reports for child-directed app
    if (event.user) {
      delete event.user.email;
      delete event.user.ip_address;
      delete event.user.username;
    }
    return event;
  },
});
```

Wrap the default export with `Sentry.wrap()`:

```typescript
export default Sentry.wrap(RootLayout);
```

- [ ] **Step 5: Run tests to verify no regressions**

```bash
cd mobile && npx turbo run test
```

Expected: All 213+ tests pass (Sentry is disabled in test/dev mode via `enabled: !__DEV__`).

- [ ] **Step 6: Commit**

```bash
git add mobile/apps/safety/app.json mobile/apps/social/app.json mobile/apps/safety/app/_layout.tsx mobile/apps/social/app/_layout.tsx mobile/package.json
git commit -m "feat: add Sentry crash reporting to both mobile apps (COPPA-compliant)"
```

---

### Task A3: TestFlight + Google Play Internal Submission

**Files:**
- No code changes — uses EAS CLI commands

**Context:** Build and submit both apps to TestFlight (iOS) and Google Play internal track (Android). Requires Apple Developer and Google Play Console accounts configured.

- [ ] **Step 1: Build Safety app for iOS production**

```bash
cd mobile/apps/safety
npx eas build --platform ios --profile production
```

Wait for build to complete on Expo servers. Note the build URL.

- [ ] **Step 2: Submit Safety app to TestFlight**

```bash
npx eas submit --platform ios --profile production --latest
```

This uploads the latest build to App Store Connect TestFlight.

- [ ] **Step 3: Build Safety app for Android production**

```bash
cd mobile/apps/safety
npx eas build --platform android --profile production
```

- [ ] **Step 4: Submit Safety app to Google Play internal track**

```bash
npx eas submit --platform android --profile production --latest
```

- [ ] **Step 5: Repeat for Social app (iOS)**

```bash
cd mobile/apps/social
npx eas build --platform ios --profile production
npx eas submit --platform ios --profile production --latest
```

- [ ] **Step 6: Repeat for Social app (Android)**

```bash
cd mobile/apps/social
npx eas build --platform android --profile production
npx eas submit --platform android --profile production --latest
```

- [ ] **Step 7: Verify submissions in App Store Connect and Google Play Console**

Check that both apps appear in TestFlight (iOS) and internal testing track (Android). Note any review feedback.

---

### Task A4: App Store Screenshots + Listing Optimization

**Files:**
- Create: `mobile/store-assets/screenshots/safety/` (screenshot images)
- Create: `mobile/store-assets/screenshots/social/` (screenshot images)
- Modify: `mobile/store-assets/screenshots/README.md` (update status)

**Context:** Screenshots are required for App Store and Google Play listings. Need 6 key screens per app, 3 device sizes, 6 languages. The README at `mobile/store-assets/screenshots/README.md` already documents the spec.

- [ ] **Step 1: Capture Safety app screenshots on iOS simulator**

Launch Safety app on iPhone 15 Pro Max simulator. Capture these 6 screens:
1. Dashboard (with sample data from demo mode)
2. Alerts list (with 2-3 sample alerts)
3. Child profile detail
4. Activity timeline
5. Settings/Safety rules
6. AI usage report

Save to `mobile/store-assets/screenshots/safety/en/iphone-15-pro-max/`.

- [ ] **Step 2: Capture Social app screenshots on iOS simulator**

Launch Social app on iPhone 15 Pro Max simulator. Capture these 6 screens:
1. Feed with sample posts
2. Create post screen
3. Chat conversation
4. Profile page
5. Creative tools (art studio)
6. Age-tier welcome screen

Save to `mobile/store-assets/screenshots/social/en/iphone-15-pro-max/`.

- [ ] **Step 3: Capture screenshots for remaining device sizes**

Repeat for iPhone SE (375pt) and iPad Pro 12.9" (1024pt) for iOS. Repeat for Pixel 8 Pro and 7" tablet for Android.

- [ ] **Step 4: Generate localized screenshots for 5 additional languages**

For each language (FR, ES, DE, PT-BR, IT), either:
- Re-capture with the app set to that locale, OR
- Add localized text overlays to English screenshots using a screenshot framing tool

Save to `mobile/store-assets/screenshots/{app}/{locale}/{device}/`.

- [ ] **Step 5: Write App Store descriptions (6 languages)**

Create `mobile/store-assets/metadata/safety/en.txt` and `mobile/store-assets/metadata/social/en.txt` with:
- App name (30 chars max)
- Subtitle (30 chars max)
- Description (4000 chars max)
- Keywords (100 chars max, comma-separated)
- What's New text

Safety app example:
```
Name: Bhapi Safety
Subtitle: AI Monitoring for Families
Keywords: parental controls, AI safety, child monitoring, screen time, family safety
```

Social app example:
```
Name: Bhapi Social
Subtitle: Safe Social for Kids
Keywords: kids social media, safe social, children chat, moderated social, family safe
```

- [ ] **Step 6: Upload screenshots and metadata to App Store Connect + Google Play Console**

Use the store management dashboards to upload all screenshots, descriptions, and metadata for both apps in all 6 languages.

- [ ] **Step 7: Commit screenshot assets**

```bash
git add mobile/store-assets/
git commit -m "chore: add App Store screenshots and listing metadata (6 languages)"
```

---

## Track B: Infrastructure

### Task B1: Provision Redis on Render

**Files:**
- Modify: `render.yaml`

**Context:** The app currently uses in-memory rate limiter fallback because Redis is not provisioned. Redis is required for WebSocket pub/sub, real-time presence, and proper rate limiting.

- [ ] **Step 1: Add Redis service to render.yaml**

Add this block after the `databases:` section in `render.yaml`:

```yaml
  # Redis 7 — required for WebSocket pub/sub, rate limiting, presence
  - name: bhapi-redis
    type: redis
    plan: starter
    region: frankfurt
    maxmemoryPolicy: allkeys-lru
    ipAllowList: [] # Only allow connections from Render services
```

- [ ] **Step 2: Add REDIS_URL env var to core-api service**

In the `bhapi-core-api` service envVars section, add:

```yaml
      - key: REDIS_URL
        fromService:
          name: bhapi-redis
          type: redis
          property: connectionString
```

- [ ] **Step 3: Add REDIS_URL env var to jobs service**

In the `bhapi-jobs` service envVars section, add the same:

```yaml
      - key: REDIS_URL
        fromService:
          name: bhapi-redis
          type: redis
          property: connectionString
```

- [ ] **Step 4: Commit**

```bash
git add render.yaml
git commit -m "infra: provision Redis 7 on Render for WebSocket pub/sub and rate limiting"
```

---

### Task B2: Deploy WebSocket Service

**Files:**
- Modify: `render.yaml`

**Context:** The WebSocket real-time service exists at `src/realtime/main.py` but is not deployed as a separate Render service. It needs its own web service with Redis and PostgreSQL access. Per ADR-008, connection pooling: monolith=20, jobs=5, WebSocket=10 (total 35).

- [ ] **Step 1: Add WebSocket service to render.yaml**

Add this block in the `services:` section of `render.yaml`, after `bhapi-jobs`:

```yaml
  # Real-time WebSocket service (JWT auth, presence, messaging, pub/sub)
  # ADR-008: Separate process for long-lived WebSocket connections
  - type: web
    name: bhapi-realtime
    runtime: docker
    plan: starter
    region: frankfurt
    dockerfilePath: ./Dockerfile.realtime
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: bhapi-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: bhapi-redis
          type: redis
          property: connectionString
      - key: SECRET_KEY
        sync: false
      - key: ENVIRONMENT
        value: production
      - key: DB_POOL_SIZE
        value: "10"
```

- [ ] **Step 2: Create Dockerfile.realtime**

Create `Dockerfile.realtime` at the repo root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "src.realtime.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

One worker because WebSocket connections are long-lived and uvicorn handles async concurrency within a single worker. Multiple workers would break connection state.

- [ ] **Step 3: Verify the realtime app starts locally**

```bash
ENVIRONMENT=development uvicorn src.realtime.main:app --port 8001
```

Expected: App starts, `/health` returns 200.

- [ ] **Step 4: Commit**

```bash
git add render.yaml Dockerfile.realtime
git commit -m "infra: deploy WebSocket real-time service as separate Render web service"
```

---

### Task B3: Verify Connection Pooling

**Files:**
- Modify: `src/database.py` (if pool size not configurable)
- Modify: `src/realtime/main.py` (if pool size not configurable)

**Context:** Three services share one PostgreSQL instance. Render Starter plan allows 50 connections. Target: monolith=20, jobs=5, WebSocket=10 = 35 total.

- [ ] **Step 1: Verify core-api pool size**

Read `src/database.py` and check the `create_async_engine()` call. Confirm `pool_size` is set (should be 20 for production). If it reads from env var `DB_POOL_SIZE`, verify `render.yaml` sets it to `20` for `bhapi-core-api`.

- [ ] **Step 2: Verify jobs pool size**

Check that `bhapi-jobs` in `render.yaml` has `DB_POOL_SIZE=5` or that the jobs runner creates a smaller pool.

- [ ] **Step 3: Verify WebSocket pool size**

Check `src/realtime/main.py` creates its own engine with `pool_size=10` or reads from `DB_POOL_SIZE` env var (set to `10` in render.yaml above).

- [ ] **Step 4: Add pool size env vars if missing**

If any service hardcodes pool size instead of reading from env, add `DB_POOL_SIZE` to render.yaml and modify the engine creation to use `int(os.getenv("DB_POOL_SIZE", "20"))`.

- [ ] **Step 5: Commit if changes were needed**

```bash
git add src/database.py src/realtime/main.py render.yaml
git commit -m "infra: configure per-service DB connection pool sizes (20+5+10=35)"
```

---

## Track C: Pre-Launch Quality

### Task C1: Moderation SLA Dashboard

**Files:**
- Create: `src/moderation/sla_service.py`
- Create: `src/moderation/sla_schemas.py`
- Modify: `src/moderation/router.py`
- Create: `tests/unit/test_moderation_sla.py`
- Create: `portal/src/app/(dashboard)/moderation/page.tsx`
- Create: `portal/src/hooks/use-moderation-sla.ts`

**Context:** The spec requires a moderation SLA dashboard before children use the platform. The existing `src/moderation/dashboard_service.py` handles moderator queues but not SLA metrics. We need p50/p95 latency tracking, queue depth, and queue age metrics. The `_LATENCY_BUDGET_MS = 2000` constant exists in `src/moderation/service.py`.

- [ ] **Step 1: Write failing test for SLA metrics**

```python
# tests/unit/test_moderation_sla.py
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from src.moderation.sla_service import get_sla_metrics
from src.moderation.sla_schemas import SLAMetrics


class TestSLAMetrics:
    """Moderation SLA dashboard metrics."""

    @pytest.mark.asyncio
    async def test_sla_metrics_returns_expected_shape(self, test_session):
        """SLA metrics must include latency percentiles, queue depth, and queue age."""
        metrics = await get_sla_metrics(test_session)
        assert isinstance(metrics, SLAMetrics)
        assert hasattr(metrics, "pre_publish_p50_ms")
        assert hasattr(metrics, "pre_publish_p95_ms")
        assert hasattr(metrics, "post_publish_p50_ms")
        assert hasattr(metrics, "post_publish_p95_ms")
        assert hasattr(metrics, "queue_depth")
        assert hasattr(metrics, "oldest_pending_age_seconds")
        assert hasattr(metrics, "sla_breach_count_24h")
        assert hasattr(metrics, "total_reviewed_24h")

    @pytest.mark.asyncio
    async def test_sla_metrics_empty_queue(self, test_session):
        """Empty queue should return zero metrics, not errors."""
        metrics = await get_sla_metrics(test_session)
        assert metrics.queue_depth == 0
        assert metrics.oldest_pending_age_seconds == 0
        assert metrics.pre_publish_p50_ms == 0.0
        assert metrics.pre_publish_p95_ms == 0.0
        assert metrics.sla_breach_count_24h == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_moderation_sla.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.moderation.sla_service'`

- [ ] **Step 3: Create SLA schemas**

```python
# src/moderation/sla_schemas.py
from pydantic import BaseModel


class SLAMetrics(BaseModel):
    """Moderation pipeline SLA metrics for the dashboard."""
    pre_publish_p50_ms: float = 0.0
    pre_publish_p95_ms: float = 0.0
    post_publish_p50_ms: float = 0.0
    post_publish_p95_ms: float = 0.0
    queue_depth: int = 0
    oldest_pending_age_seconds: int = 0
    sla_breach_count_24h: int = 0
    total_reviewed_24h: int = 0
```

- [ ] **Step 4: Implement SLA service**

```python
# src/moderation/sla_service.py
"""Moderation SLA metrics for the pre-launch quality dashboard."""
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import select, func, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.moderation.models import ModerationQueue, ModerationDecision
from src.moderation.sla_schemas import SLAMetrics

logger = structlog.get_logger()

_PRE_PUBLISH_SLA_MS = 2000
_POST_PUBLISH_SLA_MS = 60000


async def get_sla_metrics(db: AsyncSession) -> SLAMetrics:
    """Compute SLA metrics from moderation queue and decision history."""
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)

    # Queue depth: pending items
    depth_result = await db.execute(
        select(func.count()).select_from(ModerationQueue).where(
            ModerationQueue.status == "pending"
        )
    )
    queue_depth = depth_result.scalar() or 0

    # Oldest pending item age
    oldest_result = await db.execute(
        select(func.min(ModerationQueue.created_at)).where(
            ModerationQueue.status == "pending"
        )
    )
    oldest_created = oldest_result.scalar()
    oldest_age_seconds = 0
    if oldest_created:
        oldest_age_seconds = int((now - oldest_created).total_seconds())

    # Decisions in last 24h for latency percentiles
    decisions_query = (
        select(ModerationDecision.latency_ms, ModerationDecision.pipeline)
        .where(ModerationDecision.created_at >= since_24h)
        .order_by(ModerationDecision.latency_ms)
    )
    decisions_result = await db.execute(decisions_query)
    rows = decisions_result.all()

    pre_latencies = [r.latency_ms for r in rows if r.pipeline == "pre_publish" and r.latency_ms is not None]
    post_latencies = [r.latency_ms for r in rows if r.pipeline == "post_publish" and r.latency_ms is not None]

    def percentile(values: list[float], pct: float) -> float:
        if not values:
            return 0.0
        k = (len(values) - 1) * (pct / 100.0)
        f = int(k)
        c = f + 1 if f + 1 < len(values) else f
        return values[f] + (k - f) * (values[c] - values[f])

    # SLA breaches: pre-publish > 2000ms or post-publish > 60000ms
    breach_count = sum(1 for v in pre_latencies if v > _PRE_PUBLISH_SLA_MS)
    breach_count += sum(1 for v in post_latencies if v > _POST_PUBLISH_SLA_MS)

    return SLAMetrics(
        pre_publish_p50_ms=percentile(pre_latencies, 50),
        pre_publish_p95_ms=percentile(pre_latencies, 95),
        post_publish_p50_ms=percentile(post_latencies, 50),
        post_publish_p95_ms=percentile(post_latencies, 95),
        queue_depth=queue_depth,
        oldest_pending_age_seconds=oldest_age_seconds,
        sla_breach_count_24h=breach_count,
        total_reviewed_24h=len(rows),
    )
```

- [ ] **Step 5: Add SLA endpoint to moderation router**

Add to `src/moderation/router.py`:

```python
from src.moderation.sla_service import get_sla_metrics
from src.moderation.sla_schemas import SLAMetrics

@router.get("/sla", response_model=SLAMetrics)
async def get_moderation_sla(
    auth: AuthContext,
    db: DbSession,
) -> SLAMetrics:
    """Get moderation pipeline SLA metrics for the dashboard."""
    return await get_sla_metrics(db)
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/unit/test_moderation_sla.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 7: Create React Query hook**

```typescript
// portal/src/hooks/use-moderation-sla.ts
"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface SLAMetrics {
  pre_publish_p50_ms: number;
  pre_publish_p95_ms: number;
  post_publish_p50_ms: number;
  post_publish_p95_ms: number;
  queue_depth: number;
  oldest_pending_age_seconds: number;
  sla_breach_count_24h: number;
  total_reviewed_24h: number;
}

export function useModerationSLA() {
  return useQuery<SLAMetrics>({
    queryKey: ["moderation-sla"],
    queryFn: () => apiClient.get("/moderation/sla").then((r) => r.data),
    refetchInterval: 10_000, // Refresh every 10 seconds for live dashboard
  });
}
```

- [ ] **Step 8: Create Moderation SLA dashboard page**

```tsx
// portal/src/app/(dashboard)/moderation/page.tsx
"use client";
import { useModerationSLA } from "@/hooks/use-moderation-sla";
import { Card } from "@/components/ui/Card";

function MetricCard({ label, value, unit, warning }: { label: string; value: number; unit: string; warning?: boolean }) {
  return (
    <div className={`rounded-lg p-4 ${warning ? "bg-amber-50 ring-1 ring-amber-200" : "bg-white ring-1 ring-gray-200"}`}>
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`text-2xl font-semibold ${warning ? "text-amber-700" : "text-gray-900"}`}>
        {value.toFixed(0)}{unit}
      </p>
    </div>
  );
}

export default function ModerationSLAPage() {
  const { data, isLoading, error } = useModerationSLA();

  if (isLoading) return <div className="p-6"><p className="text-gray-500">Loading SLA metrics...</p></div>;
  if (error || !data) return <div className="p-6"><p className="text-red-600">Failed to load SLA metrics.</p></div>;

  const prePublishBreached = data.pre_publish_p95_ms > 2000;
  const postPublishBreached = data.post_publish_p95_ms > 60000;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Content Moderation SLA</h1>
        <p className="text-sm text-gray-500">Live pipeline performance metrics. Pre-publish target: &lt;2s. Post-publish target: &lt;60s.</p>
      </div>

      <Card title="Pre-Publish Pipeline (Under-13 Content)">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <MetricCard label="p50 Latency" value={data.pre_publish_p50_ms} unit="ms" />
          <MetricCard label="p95 Latency" value={data.pre_publish_p95_ms} unit="ms" warning={prePublishBreached} />
          <MetricCard label="Queue Depth" value={data.queue_depth} unit="" warning={data.queue_depth > 50} />
          <MetricCard label="Oldest Pending" value={data.oldest_pending_age_seconds} unit="s" warning={data.oldest_pending_age_seconds > 30} />
        </div>
      </Card>

      <Card title="Post-Publish Pipeline (Teen Content)">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <MetricCard label="p50 Latency" value={data.post_publish_p50_ms} unit="ms" />
          <MetricCard label="p95 Latency" value={data.post_publish_p95_ms} unit="ms" warning={postPublishBreached} />
          <MetricCard label="SLA Breaches (24h)" value={data.sla_breach_count_24h} unit="" warning={data.sla_breach_count_24h > 0} />
          <MetricCard label="Reviews (24h)" value={data.total_reviewed_24h} unit="" />
        </div>
      </Card>

      {(prePublishBreached || postPublishBreached) && (
        <div className="rounded-lg bg-amber-50 p-4 ring-1 ring-amber-200">
          <p className="text-sm font-medium text-amber-800">
            SLA breach detected. Review moderation pipeline capacity.
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 9: Run frontend type check**

```bash
cd portal && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 10: Commit**

```bash
git add src/moderation/sla_service.py src/moderation/sla_schemas.py src/moderation/router.py tests/unit/test_moderation_sla.py portal/src/hooks/use-moderation-sla.ts portal/src/app/\(dashboard\)/moderation/page.tsx
git commit -m "feat: add moderation SLA dashboard with live latency metrics"
```

---

### Task C2: Reduced Motion Mode (Both Mobile Apps)

**Files:**
- Modify: `mobile/packages/shared-config/src/theme.ts`
- Modify: `mobile/apps/safety/app/_layout.tsx`
- Modify: `mobile/apps/social/app/_layout.tsx`
- Create: `mobile/packages/shared-ui/src/MotionProvider.tsx`
- Create: `mobile/packages/shared-ui/src/__tests__/MotionProvider.test.tsx`

**Context:** Respect `AccessibilityInfo.isReduceMotionEnabled()` from React Native. When enabled, disable all `Animated` transitions and use instant layout changes.

- [ ] **Step 1: Write failing test**

```tsx
// mobile/packages/shared-ui/src/__tests__/MotionProvider.test.tsx
import React from 'react';
import { render } from '@testing-library/react-native';
import { MotionProvider, useReducedMotion } from '../MotionProvider';
import { Text } from 'react-native';

function TestConsumer() {
  const reduced = useReducedMotion();
  return <Text testID="motion">{reduced ? 'reduced' : 'full'}</Text>;
}

describe('MotionProvider', () => {
  it('provides reduced motion state', () => {
    const { getByTestId } = render(
      <MotionProvider>
        <TestConsumer />
      </MotionProvider>
    );
    // Default is false (full motion) in test environment
    expect(getByTestId('motion').props.children).toBe('full');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mobile && npx turbo run test -- --testPathPattern=MotionProvider
```

Expected: FAIL with `Cannot find module '../MotionProvider'`

- [ ] **Step 3: Implement MotionProvider**

```tsx
// mobile/packages/shared-ui/src/MotionProvider.tsx
import React, { createContext, useContext, useEffect, useState } from 'react';
import { AccessibilityInfo } from 'react-native';

const MotionContext = createContext(false);

export function useReducedMotion(): boolean {
  return useContext(MotionContext);
}

export function MotionProvider({ children }: { children: React.ReactNode }) {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduced);
    const subscription = AccessibilityInfo.addEventListener(
      'reduceMotionChanged',
      setReduced,
    );
    return () => subscription.remove();
  }, []);

  return (
    <MotionContext.Provider value={reduced}>
      {children}
    </MotionContext.Provider>
  );
}
```

- [ ] **Step 4: Export from shared-ui index**

Add to `mobile/packages/shared-ui/src/index.ts`:

```typescript
export { MotionProvider, useReducedMotion } from './MotionProvider';
```

- [ ] **Step 5: Wrap both app layouts with MotionProvider**

In both `mobile/apps/safety/app/_layout.tsx` and `mobile/apps/social/app/_layout.tsx`, import and wrap:

```typescript
import { MotionProvider } from '@bhapi/ui';

// In the component return, wrap the outermost element:
return (
  <MotionProvider>
    {/* existing layout content */}
  </MotionProvider>
);
```

- [ ] **Step 6: Run tests**

```bash
cd mobile && npx turbo run test
```

Expected: All tests pass including the new MotionProvider test.

- [ ] **Step 7: Commit**

```bash
git add mobile/packages/shared-ui/src/MotionProvider.tsx mobile/packages/shared-ui/src/__tests__/MotionProvider.test.tsx mobile/packages/shared-ui/src/index.ts mobile/apps/safety/app/_layout.tsx mobile/apps/social/app/_layout.tsx
git commit -m "feat: add reduced motion mode respecting OS accessibility preference"
```

---

### Task C3: High Contrast Mode (Both Mobile Apps)

**Files:**
- Modify: `mobile/packages/shared-config/src/theme.ts`
- Create: `mobile/packages/shared-ui/src/ContrastProvider.tsx`
- Create: `mobile/packages/shared-ui/src/__tests__/ContrastProvider.test.tsx`
- Modify: `mobile/apps/safety/app/_layout.tsx`
- Modify: `mobile/apps/social/app/_layout.tsx`

**Context:** Provide a `useHighContrast()` hook that reads the OS high contrast setting. When enabled, swap the color palette to WCAG AAA-compliant values (7:1 contrast ratio for normal text).

- [ ] **Step 1: Write failing test**

```tsx
// mobile/packages/shared-ui/src/__tests__/ContrastProvider.test.tsx
import React from 'react';
import { render } from '@testing-library/react-native';
import { ContrastProvider, useHighContrast } from '../ContrastProvider';
import { Text } from 'react-native';

function TestConsumer() {
  const { isHighContrast } = useHighContrast();
  return <Text testID="contrast">{isHighContrast ? 'high' : 'normal'}</Text>;
}

describe('ContrastProvider', () => {
  it('defaults to normal contrast', () => {
    const { getByTestId } = render(
      <ContrastProvider>
        <TestConsumer />
      </ContrastProvider>
    );
    expect(getByTestId('contrast').props.children).toBe('normal');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mobile && npx turbo run test -- --testPathPattern=ContrastProvider
```

Expected: FAIL

- [ ] **Step 3: Implement ContrastProvider**

```tsx
// mobile/packages/shared-ui/src/ContrastProvider.tsx
import React, { createContext, useContext, useEffect, useState } from 'react';
import { AccessibilityInfo, Platform } from 'react-native';

interface ContrastState {
  isHighContrast: boolean;
}

const ContrastContext = createContext<ContrastState>({ isHighContrast: false });

export function useHighContrast(): ContrastState {
  return useContext(ContrastContext);
}

export function ContrastProvider({ children }: { children: React.ReactNode }) {
  const [isHighContrast, setHighContrast] = useState(false);

  useEffect(() => {
    // Android supports isAccessibilityServiceEnabled for high contrast detection
    // iOS uses Bold Text as a proxy (closest equivalent)
    if (Platform.OS === 'android') {
      AccessibilityInfo.isAccessibilityServiceEnabled?.().then(setHighContrast);
    } else {
      AccessibilityInfo.isBoldTextEnabled().then(setHighContrast);
      const sub = AccessibilityInfo.addEventListener('boldTextChanged', setHighContrast);
      return () => sub.remove();
    }
  }, []);

  return (
    <ContrastContext.Provider value={{ isHighContrast }}>
      {children}
    </ContrastContext.Provider>
  );
}
```

- [ ] **Step 4: Add high contrast color overrides to theme**

In `mobile/packages/shared-config/src/theme.ts`, add a `highContrastColors` export:

```typescript
export const highContrastColors = {
  primary: { 600: '#CC4400', 700: '#993300' },  // Darker orange for AAA on white
  accent: { 500: '#0A7A70', 600: '#065F58' },   // Darker teal
  text: { primary: '#000000', secondary: '#1A1A1A' },
  background: { primary: '#FFFFFF', secondary: '#F5F5F5' },
  border: '#000000',
} as const;
```

- [ ] **Step 5: Export from shared-ui and wrap layouts**

Add to `mobile/packages/shared-ui/src/index.ts`:

```typescript
export { ContrastProvider, useHighContrast } from './ContrastProvider';
```

Wrap both app layouts (same pattern as MotionProvider — nest inside MotionProvider):

```typescript
import { MotionProvider, ContrastProvider } from '@bhapi/ui';

return (
  <MotionProvider>
    <ContrastProvider>
      {/* existing layout content */}
    </ContrastProvider>
  </MotionProvider>
);
```

- [ ] **Step 6: Run tests**

```bash
cd mobile && npx turbo run test
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add mobile/packages/shared-ui/src/ContrastProvider.tsx mobile/packages/shared-ui/src/__tests__/ContrastProvider.test.tsx mobile/packages/shared-ui/src/index.ts mobile/packages/shared-config/src/theme.ts mobile/apps/safety/app/_layout.tsx mobile/apps/social/app/_layout.tsx
git commit -m "feat: add high contrast mode using OS accessibility preferences"
```

---

### Task C4: Dyslexia-Friendly Font Toggle

**Files:**
- Create: `mobile/packages/shared-ui/src/FontProvider.tsx`
- Create: `mobile/packages/shared-ui/src/__tests__/FontProvider.test.tsx`
- Modify: `mobile/apps/social/app/(settings)/index.tsx`
- Modify: `mobile/packages/shared-ui/src/index.ts`

**Context:** Add an in-app toggle (Social app settings) for OpenDyslexic font. Uses AsyncStorage to persist preference. The Social app is child-facing, so this is where it matters most. Safety app (parent-facing) gets it for free via the shared provider.

- [ ] **Step 1: Write failing test**

```tsx
// mobile/packages/shared-ui/src/__tests__/FontProvider.test.tsx
import React from 'react';
import { render } from '@testing-library/react-native';
import { FontProvider, useDyslexiaFont } from '../FontProvider';
import { Text } from 'react-native';

function TestConsumer() {
  const { isDyslexic, fontFamily } = useDyslexiaFont();
  return <Text testID="font">{fontFamily}</Text>;
}

describe('FontProvider', () => {
  it('defaults to system font', () => {
    const { getByTestId } = render(
      <FontProvider>
        <TestConsumer />
      </FontProvider>
    );
    expect(getByTestId('font').props.children).toBe('System');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mobile && npx turbo run test -- --testPathPattern=FontProvider
```

Expected: FAIL

- [ ] **Step 3: Implement FontProvider**

```tsx
// mobile/packages/shared-ui/src/FontProvider.tsx
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'bhapi_dyslexia_font';

interface FontState {
  isDyslexic: boolean;
  fontFamily: string;
  toggleDyslexiaFont: () => void;
}

const FontContext = createContext<FontState>({
  isDyslexic: false,
  fontFamily: 'System',
  toggleDyslexiaFont: () => {},
});

export function useDyslexiaFont(): FontState {
  return useContext(FontContext);
}

export function FontProvider({ children }: { children: React.ReactNode }) {
  const [isDyslexic, setDyslexic] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((val) => {
      if (val === 'true') setDyslexic(true);
    });
  }, []);

  const toggleDyslexiaFont = useCallback(() => {
    setDyslexic((prev) => {
      const next = !prev;
      AsyncStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  const fontFamily = isDyslexic ? 'OpenDyslexic' : 'System';

  return (
    <FontContext.Provider value={{ isDyslexic, fontFamily, toggleDyslexiaFont }}>
      {children}
    </FontContext.Provider>
  );
}
```

- [ ] **Step 4: Add OpenDyslexic font asset to both apps**

Download OpenDyslexic-Regular.otf and place it in:
- `mobile/apps/safety/assets/fonts/OpenDyslexic-Regular.otf`
- `mobile/apps/social/assets/fonts/OpenDyslexic-Regular.otf`

In both `app.json` files, add to `expo.fonts`:

```json
"fonts": ["./assets/fonts/OpenDyslexic-Regular.otf"]
```

- [ ] **Step 5: Export from shared-ui and wrap layouts**

Add to `mobile/packages/shared-ui/src/index.ts`:

```typescript
export { FontProvider, useDyslexiaFont } from './FontProvider';
```

Wrap both app layouts (innermost provider):

```typescript
import { MotionProvider, ContrastProvider, FontProvider } from '@bhapi/ui';

return (
  <MotionProvider>
    <ContrastProvider>
      <FontProvider>
        {/* existing layout content */}
      </FontProvider>
    </ContrastProvider>
  </MotionProvider>
);
```

- [ ] **Step 6: Add toggle to Social app settings**

In `mobile/apps/social/app/(settings)/index.tsx`, add a toggle row:

```tsx
import { useDyslexiaFont } from '@bhapi/ui';

// Inside the settings component:
const { isDyslexic, toggleDyslexiaFont } = useDyslexiaFont();

// In the render, add a toggle row:
<View style={styles.settingRow}>
  <Text style={styles.settingLabel}>Dyslexia-friendly font</Text>
  <Switch value={isDyslexic} onValueChange={toggleDyslexiaFont} />
</View>
```

- [ ] **Step 7: Run tests**

```bash
cd mobile && npx turbo run test
```

Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
git add mobile/packages/shared-ui/src/FontProvider.tsx mobile/packages/shared-ui/src/__tests__/FontProvider.test.tsx mobile/packages/shared-ui/src/index.ts mobile/apps/safety/app/_layout.tsx mobile/apps/social/app/_layout.tsx mobile/apps/social/app/\(settings\)/index.tsx mobile/apps/safety/assets/fonts/ mobile/apps/social/assets/fonts/ mobile/apps/safety/app.json mobile/apps/social/app.json
git commit -m "feat: add dyslexia-friendly font toggle (OpenDyslexic) with persistent preference"
```

---

## Track D: UX Excellence

### Task D1: Portal Component Library (Select, Modal, Tabs, EmptyState, Badge)

**Files:**
- Create: `portal/src/components/ui/Select.tsx`
- Create: `portal/src/components/ui/Modal.tsx`
- Create: `portal/src/components/ui/Tabs.tsx`
- Create: `portal/src/components/ui/EmptyState.tsx`
- Create: `portal/src/components/ui/Badge.tsx`
- Create: `portal/src/components/ui/__tests__/Select.test.tsx`
- Create: `portal/src/components/ui/__tests__/Modal.test.tsx`
- Create: `portal/src/components/ui/__tests__/Tabs.test.tsx`
- Create: `portal/src/components/ui/__tests__/EmptyState.test.tsx`
- Create: `portal/src/components/ui/__tests__/Badge.test.tsx`

**Context:** The portal has only 3 UI components (Button, Card, Input). Pages reinvent modals (5+ custom implementations), tabs (conditional rendering), and selects (raw `<select>`). This task creates 5 reusable components matching the existing design system (Orange `#FF6B35`, Teal `#0D9488`, Inter font, Tailwind).

This task is large so it should be implemented as 5 sub-steps, one per component. Each component follows: write test → implement → verify.

- [ ] **Step 1: Write Select test**

```tsx
// portal/src/components/ui/__tests__/Select.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { Select } from "../Select";

describe("Select", () => {
  const options = [
    { value: "a", label: "Option A" },
    { value: "b", label: "Option B" },
  ];

  it("renders label and options", () => {
    render(<Select label="Pick one" options={options} value="a" onChange={() => {}} />);
    expect(screen.getByLabelText("Pick one")).toBeInTheDocument();
    expect(screen.getAllByRole("option")).toHaveLength(2);
  });

  it("shows error state", () => {
    render(<Select label="Pick" options={options} value="" onChange={() => {}} error="Required" />);
    expect(screen.getByText("Required")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Implement Select**

```tsx
// portal/src/components/ui/Select.tsx
"use client";
import React from "react";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  label?: string;
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  error?: string;
  placeholder?: string;
  className?: string;
}

export function Select({ label, options, value, onChange, error, placeholder, className }: SelectProps) {
  const id = label ? label.toLowerCase().replace(/\s+/g, "-") : undefined;
  return (
    <div className={className}>
      {label && (
        <label htmlFor={id} className="mb-1 block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
        className={`block w-full rounded-lg border px-3 py-2 text-sm shadow-sm transition focus:outline-none focus:ring-2 ${
          error
            ? "border-red-300 focus:border-red-500 focus:ring-red-500/20"
            : "border-gray-300 focus:border-primary-500 focus:ring-primary-500/20"
        }`}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && (
        <p id={`${id}-error`} role="alert" className="mt-1 text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Write Modal test**

```tsx
// portal/src/components/ui/__tests__/Modal.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { Modal } from "../Modal";

describe("Modal", () => {
  it("renders children when open", () => {
    render(<Modal open onClose={() => {}} title="Test"><p>Content</p></Modal>);
    expect(screen.getByText("Content")).toBeInTheDocument();
    expect(screen.getByText("Test")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    render(<Modal open={false} onClose={() => {}} title="Test"><p>Content</p></Modal>);
    expect(screen.queryByText("Content")).not.toBeInTheDocument();
  });

  it("calls onClose when backdrop clicked", () => {
    const onClose = jest.fn();
    render(<Modal open onClose={onClose} title="Test"><p>Content</p></Modal>);
    fireEvent.click(screen.getByTestId("modal-backdrop"));
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 4: Implement Modal**

```tsx
// portal/src/components/ui/Modal.tsx
"use client";
import React, { useEffect, useRef } from "react";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg";
}

const sizes = { sm: "max-w-sm", md: "max-w-lg", lg: "max-w-2xl" };

export function Modal({ open, onClose, title, children, size = "md" }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleEsc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div data-testid="modal-backdrop" className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-label={title}
        className={`relative mx-4 w-full ${sizes[size]} rounded-xl bg-white shadow-xl`}>
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600" aria-label="Close">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <div className="px-6 py-4">{children}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Write Tabs test**

```tsx
// portal/src/components/ui/__tests__/Tabs.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { Tabs } from "../Tabs";

describe("Tabs", () => {
  const tabs = [
    { key: "a", label: "Tab A" },
    { key: "b", label: "Tab B" },
  ];

  it("renders tab labels", () => {
    render(<Tabs tabs={tabs} active="a" onChange={() => {}} />);
    expect(screen.getByText("Tab A")).toBeInTheDocument();
    expect(screen.getByText("Tab B")).toBeInTheDocument();
  });

  it("calls onChange on tab click", () => {
    const onChange = jest.fn();
    render(<Tabs tabs={tabs} active="a" onChange={onChange} />);
    fireEvent.click(screen.getByText("Tab B"));
    expect(onChange).toHaveBeenCalledWith("b");
  });

  it("marks active tab", () => {
    render(<Tabs tabs={tabs} active="a" onChange={() => {}} />);
    expect(screen.getByText("Tab A").closest("button")).toHaveClass("border-primary-600");
  });
});
```

- [ ] **Step 6: Implement Tabs**

```tsx
// portal/src/components/ui/Tabs.tsx
"use client";
import React from "react";

export interface TabItem {
  key: string;
  label: string;
  count?: number;
}

export interface TabsProps {
  tabs: TabItem[];
  active: string;
  onChange: (key: string) => void;
  className?: string;
}

export function Tabs({ tabs, active, onChange, className }: TabsProps) {
  return (
    <div className={`flex gap-1 border-b border-gray-200 ${className ?? ""}`} role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          role="tab"
          aria-selected={active === tab.key}
          onClick={() => onChange(tab.key)}
          className={`px-4 py-2 text-sm font-medium transition ${
            active === tab.key
              ? "border-b-2 border-primary-600 text-primary-700"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {tab.label}
          {tab.count !== undefined && (
            <span className="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{tab.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 7: Write EmptyState test**

```tsx
// portal/src/components/ui/__tests__/EmptyState.test.tsx
import { render, screen } from "@testing-library/react";
import { EmptyState } from "../EmptyState";

describe("EmptyState", () => {
  it("renders message and optional action", () => {
    render(<EmptyState title="No alerts" message="Your family is safe." actionLabel="View settings" onAction={() => {}} />);
    expect(screen.getByText("No alerts")).toBeInTheDocument();
    expect(screen.getByText("Your family is safe.")).toBeInTheDocument();
    expect(screen.getByText("View settings")).toBeInTheDocument();
  });

  it("renders without action", () => {
    render(<EmptyState title="Nothing here" message="Check back later." />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 8: Implement EmptyState**

```tsx
// portal/src/components/ui/EmptyState.tsx
"use client";
import React from "react";
import { Button } from "./Button";

export interface EmptyStateProps {
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export function EmptyState({ title, message, actionLabel, onAction, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {icon && <div className="mb-4 text-gray-300">{icon}</div>}
      <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      <p className="mt-1 text-sm text-gray-500">{message}</p>
      {actionLabel && onAction && (
        <div className="mt-4">
          <Button variant="primary" size="sm" onClick={onAction}>{actionLabel}</Button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 9: Write Badge test**

```tsx
// portal/src/components/ui/__tests__/Badge.test.tsx
import { render, screen } from "@testing-library/react";
import { Badge } from "../Badge";

describe("Badge", () => {
  it("renders with variant", () => {
    render(<Badge variant="success">Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Active")).toHaveClass("bg-green-50");
  });

  it("renders warning variant", () => {
    render(<Badge variant="warning">Pending</Badge>);
    expect(screen.getByText("Pending")).toHaveClass("bg-amber-50");
  });
});
```

- [ ] **Step 10: Implement Badge**

```tsx
// portal/src/components/ui/Badge.tsx
"use client";
import React from "react";

export type BadgeVariant = "info" | "success" | "warning" | "error" | "neutral";

export interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  info: "bg-blue-50 text-blue-700 ring-blue-600/20",
  success: "bg-green-50 text-green-700 ring-green-600/20",
  warning: "bg-amber-50 text-amber-700 ring-amber-600/20",
  error: "bg-red-50 text-red-700 ring-red-600/20",
  neutral: "bg-gray-50 text-gray-700 ring-gray-600/20",
};

export function Badge({ variant = "neutral", children, className }: BadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${variantStyles[variant]} ${className ?? ""}`}>
      {children}
    </span>
  );
}
```

- [ ] **Step 11: Run all component tests**

```bash
cd portal && npx vitest run src/components/ui/__tests__/
```

Expected: All 10 tests pass (2 per component x 5 components).

- [ ] **Step 12: Run type check**

```bash
cd portal && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 13: Commit**

```bash
git add portal/src/components/ui/Select.tsx portal/src/components/ui/Modal.tsx portal/src/components/ui/Tabs.tsx portal/src/components/ui/EmptyState.tsx portal/src/components/ui/Badge.tsx portal/src/components/ui/__tests__/
git commit -m "feat: add 5 portal UI components (Select, Modal, Tabs, EmptyState, Badge)"
```

---

### Task D2: Dashboard Redesign — "Calm Dashboard"

**Files:**
- Modify: `portal/src/app/(dashboard)/dashboard/page.tsx`
- Create: `portal/src/hooks/use-safety-score.ts`
- Create: `portal/src/components/SafetyScoreCard.tsx`
- Create: `portal/src/components/ActionsNeeded.tsx`
- Create: `portal/src/components/WeeklySummary.tsx`

**Context:** Replace the 6-section dashboard with a 3-zone "Calm Dashboard": (1) Family Safety Score at top, (2) Actions Needed (only if alerts exist), (3) This Week summary with 3 compact cards. The safety score reuses `compute_unified_score()` from `src/intelligence/scoring.py` via a new portal BFF endpoint.

- [ ] **Step 1: Create safety score hook**

```typescript
// portal/src/hooks/use-safety-score.ts
"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface SafetyScore {
  score: number;          // 0-100 (100 = safest)
  confidence: string;     // low | medium | high
  trend: string;          // increasing | stable | decreasing
  children_monitored: number;
  active_alerts: number;
}

export function useSafetyScore() {
  return useQuery<SafetyScore>({
    queryKey: ["safety-score"],
    queryFn: () => apiClient.get("/portal/safety-score").then((r) => r.data),
    refetchInterval: 60_000, // Refresh every minute
  });
}
```

- [ ] **Step 2: Add safety score endpoint to portal BFF**

Add to `src/portal/router.py`:

```python
from src.intelligence.scoring import compute_unified_score, get_score_trend

@router.get("/safety-score")
async def get_safety_score(auth: AuthContext, db: DbSession):
    """Aggregated family safety score for the calm dashboard."""
    members = await get_group_members(db, auth.group_id)
    if not members:
        return {"score": 100, "confidence": "low", "trend": "stable", "children_monitored": 0, "active_alerts": 0}

    scores = []
    for member in members:
        if member.role != "child":
            continue
        score = await compute_unified_score(db, member.id)
        scores.append(score)

    # Invert: scoring.py returns risk (high=bad), dashboard shows safety (high=good)
    avg_risk = sum(s.score for s in scores) / len(scores) if scores else 0
    safety_score = max(0, 100 - avg_risk)

    alert_count = await count_active_alerts(db, auth.group_id)

    return {
        "score": round(safety_score),
        "confidence": scores[0].confidence if scores else "low",
        "trend": "stable",
        "children_monitored": len(scores),
        "active_alerts": alert_count,
    }
```

- [ ] **Step 3: Create SafetyScoreCard component**

```tsx
// portal/src/components/SafetyScoreCard.tsx
"use client";
import React from "react";
import type { SafetyScore } from "@/hooks/use-safety-score";

function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 50) return "text-amber-600";
  return "text-red-600";
}

function scoreMessage(score: number, alerts: number): string {
  if (alerts === 0) return "Your family is safe — no alerts this week";
  if (alerts === 1) return "1 item needs your attention";
  return `${alerts} items need your attention`;
}

function scoreBg(score: number): string {
  if (score >= 80) return "bg-green-50 ring-green-200";
  if (score >= 50) return "bg-amber-50 ring-amber-200";
  return "bg-red-50 ring-red-200";
}

export function SafetyScoreCard({ data }: { data: SafetyScore }) {
  return (
    <div className={`rounded-xl p-6 ring-1 ${scoreBg(data.score)}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">Family Safety</p>
          <p className="mt-1 text-lg font-medium text-gray-900">
            {scoreMessage(data.score, data.active_alerts)}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {data.children_monitored} {data.children_monitored === 1 ? "child" : "children"} monitored
          </p>
        </div>
        <div className={`text-4xl font-bold ${scoreColor(data.score)}`}>
          {data.score}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create ActionsNeeded component**

```tsx
// portal/src/components/ActionsNeeded.tsx
"use client";
import React from "react";
import { useRouter } from "next/navigation";
import { useAlerts } from "@/hooks/use-alerts";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export function ActionsNeeded() {
  const router = useRouter();
  const { data } = useAlerts({ status: "pending", pageSize: 5 });

  if (!data?.items?.length) return null; // Progressive disclosure: hide when no actions

  return (
    <div className="rounded-xl bg-white p-4 ring-1 ring-gray-200">
      <h2 className="mb-3 text-sm font-semibold text-gray-900">Actions needed</h2>
      <div className="space-y-2">
        {data.items.map((alert: any) => (
          <div key={alert.id} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2">
            <div className="flex items-center gap-2">
              <Badge variant={alert.severity === "critical" ? "error" : alert.severity === "high" ? "warning" : "info"}>
                {alert.severity}
              </Badge>
              <span className="text-sm text-gray-700">{alert.title}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => router.push(`/alerts?id=${alert.id}`)}>
              View
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create WeeklySummary component**

```tsx
// portal/src/components/WeeklySummary.tsx
"use client";
import React from "react";
import { useRouter } from "next/navigation";
import { useDashboardSummary } from "@/hooks/use-dashboard";

function SummaryCard({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div className="rounded-lg bg-white p-4 ring-1 ring-gray-200">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-gray-900">
        {value}{unit && <span className="text-sm font-normal text-gray-400"> {unit}</span>}
      </p>
    </div>
  );
}

export function WeeklySummary() {
  const router = useRouter();
  const { data } = useDashboardSummary();

  if (!data) return null;

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">This week</h2>
        <button onClick={() => router.push("/analytics")} className="text-sm text-primary-600 hover:text-primary-700">
          View detailed analytics
        </button>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <SummaryCard label="AI Usage" value={data.activity?.total_events ?? 0} unit="sessions" />
        <SummaryCard label="Social Activity" value={data.social?.total_posts ?? 0} unit="posts" />
        <SummaryCard label="Screen Time" value={data.screen_time?.avg_daily_hours ?? "—"} unit="hrs/day" />
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Rewrite dashboard page with 3-zone layout**

Replace the contents of `portal/src/app/(dashboard)/dashboard/page.tsx` with:

```tsx
"use client";
import React from "react";
import { useSafetyScore } from "@/hooks/use-safety-score";
import { SafetyScoreCard } from "@/components/SafetyScoreCard";
import { ActionsNeeded } from "@/components/ActionsNeeded";
import { WeeklySummary } from "@/components/WeeklySummary";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAuth } from "@/hooks/use-auth";

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: score, isLoading } = useSafetyScore();

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <div className="h-24 animate-pulse rounded-xl bg-gray-100" />
        <div className="h-32 animate-pulse rounded-xl bg-gray-100" />
        <div className="h-24 animate-pulse rounded-xl bg-gray-100" />
      </div>
    );
  }

  if (!score || score.children_monitored === 0) {
    return (
      <div className="p-6">
        <EmptyState
          title="Welcome to Bhapi"
          message="Add your first child to start monitoring AI usage and keep your family safe."
          actionLabel="Add a child"
          onAction={() => window.location.href = "/members"}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Zone 1: Family Safety Score */}
      <SafetyScoreCard data={score} />

      {/* Zone 2: Actions Needed (progressive disclosure — hidden when empty) */}
      <ActionsNeeded />

      {/* Zone 3: This Week */}
      <WeeklySummary />
    </div>
  );
}
```

- [ ] **Step 7: Run type check and frontend tests**

```bash
cd portal && npx tsc --noEmit && npx vitest run
```

Expected: No type errors, all tests pass.

- [ ] **Step 8: Commit**

```bash
git add portal/src/app/\(dashboard\)/dashboard/page.tsx portal/src/hooks/use-safety-score.ts portal/src/components/SafetyScoreCard.tsx portal/src/components/ActionsNeeded.tsx portal/src/components/WeeklySummary.tsx src/portal/router.py
git commit -m "feat: redesign dashboard to 3-zone Calm Dashboard (safety score, actions, weekly summary)"
```

---

### Task D3: Onboarding Overhaul — "Instant Value"

**Files:**
- Modify: `portal/src/components/OnboardingWizard.tsx`
- Modify: `portal/src/app/(dashboard)/dashboard/page.tsx`
- Modify: `portal/src/app/(auth)/register/page.tsx`

**Context:** Current onboarding is a 4-step wizard that blocks dashboard access. New approach: register → land on dashboard immediately with demo data visible → contextual prompts to add children and install extension. The existing demo service (`src/portal/demo.py`) generates sample data we can reuse.

- [ ] **Step 1: Simplify OnboardingWizard to contextual cards**

Replace the 4-step modal wizard in `portal/src/components/OnboardingWizard.tsx` with non-blocking contextual cards that appear inline on the dashboard:

```tsx
// portal/src/components/OnboardingWizard.tsx
"use client";
import React, { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface OnboardingWizardProps {
  hasGroup: boolean;
  memberCount: number;
  hasExtension: boolean;
  hasAlerts: boolean;
  onDismiss: () => void;
}

export default function OnboardingWizard({ hasGroup, memberCount, hasExtension, hasAlerts, onDismiss }: OnboardingWizardProps) {
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && localStorage.getItem("bhapi_onboarding_complete") === "true") {
      setDismissed(true);
    }
  }, []);

  if (dismissed || (memberCount > 0 && hasExtension)) return null;

  const steps = [
    { done: memberCount > 0, label: "Add your first child", action: "/members", cta: "Add child" },
    { done: hasExtension, label: "Install the browser extension", action: "https://chrome.google.com/webstore/detail/bhapi", cta: "Install extension" },
  ].filter((s) => !s.done);

  if (steps.length === 0) {
    localStorage.setItem("bhapi_onboarding_complete", "true");
    return null;
  }

  return (
    <Card title="Get started" footer={
      <button onClick={() => { localStorage.setItem("bhapi_onboarding_complete", "true"); onDismiss(); }}
        className="text-sm text-gray-400 hover:text-gray-600">
        Dismiss
      </button>
    }>
      <div className="space-y-3">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-3">
            <span className="text-sm text-gray-700">{step.label}</span>
            <Button variant="primary" size="sm" onClick={() => window.location.href = step.action}>
              {step.cta}
            </Button>
          </div>
        ))}
      </div>
    </Card>
  );
}
```

- [ ] **Step 2: Update dashboard to show onboarding cards inline (not as modal)**

In `portal/src/app/(dashboard)/dashboard/page.tsx`, ensure OnboardingWizard renders as a regular section between the safety score and actions (not as a modal overlay). The current dashboard code from Task D2 already handles the empty state. Add the OnboardingWizard between Zone 1 and Zone 2:

```tsx
// After SafetyScoreCard, before ActionsNeeded:
<OnboardingWizard
  hasGroup={true}
  memberCount={score.children_monitored}
  hasExtension={false}  // TODO: detect from extension ping
  hasAlerts={score.active_alerts > 0}
  onDismiss={() => {}}
/>
```

- [ ] **Step 3: Pre-check privacy notice on registration page**

In `portal/src/app/(auth)/register/page.tsx`, change the privacy notice checkbox to be pre-checked with an expandable disclosure:

Find the privacy notice checkbox and change `checked` default from `false` to `true`:

```tsx
const [privacyAccepted, setPrivacyAccepted] = useState(true);
```

Add an expandable "What this means" section below the checkbox:

```tsx
<details className="mt-1 text-xs text-gray-500">
  <summary className="cursor-pointer text-primary-600 hover:text-primary-700">What this means</summary>
  <p className="mt-1">We collect data to monitor AI safety for your family. You can review and delete data at any time in Settings &gt; Privacy. Full details in our <a href="/legal/privacy" className="underline">privacy policy</a>.</p>
</details>
```

- [ ] **Step 4: Run type check**

```bash
cd portal && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 5: Commit**

```bash
git add portal/src/components/OnboardingWizard.tsx portal/src/app/\(dashboard\)/dashboard/page.tsx portal/src/app/\(auth\)/register/page.tsx
git commit -m "feat: overhaul onboarding to non-blocking contextual cards (instant value)"
```

---

### Task D4: Alert System Redesign — "Calm Alerts"

**Files:**
- Modify: `portal/src/app/(dashboard)/alerts/page.tsx`

**Context:** Replace flat severity-based alert list with child-grouped alerts using calm language. Two tabs: "Active" and "Handled" (not severity-based). Alerts show suggested actions per type.

- [ ] **Step 1: Define calm alert language map**

Create a constant map of alert types to calm language at the top of the alerts page:

```typescript
const CALM_MESSAGES: Record<string, (memberName: string, platform?: string) => string> = {
  pii_exposure: (name, platform) => `We noticed ${name} shared personal information${platform ? ` in ${platform}` : ""}`,
  deepfake: (name, platform) => `A suspicious image was found${platform ? ` in ${name}'s ${platform} session` : ""}`,
  safety_concern: (name) => `${name} may have encountered concerning content`,
  unusual_usage: (name) => `${name}'s AI usage changed significantly this week`,
  academic_integrity: (name) => `${name} may have used AI for schoolwork`,
  emotional_dependency: (name) => `${name} may be developing an emotional attachment to an AI`,
  default: (name) => `Something needs your attention regarding ${name}`,
};

const SUGGESTED_ACTIONS: Record<string, string> = {
  pii_exposure: "Talk to your child about sharing personal information online",
  deepfake: "Review the content and discuss image safety",
  safety_concern: "Have a calm conversation about what they saw",
  unusual_usage: "Check in about their AI usage habits",
  academic_integrity: "Discuss responsible AI use for schoolwork",
  emotional_dependency: "Encourage offline social activities",
  default: "Review the details and talk with your child",
};
```

- [ ] **Step 2: Rewrite alerts page with child grouping and Active/Handled tabs**

Replace the contents of `portal/src/app/(dashboard)/alerts/page.tsx`:

```tsx
"use client";
import React, { useState } from "react";
import { useAlerts } from "@/hooks/use-alerts";
import { useMarkAlertActioned, useSnoozeAlert } from "@/hooks/use-alerts";
import { Tabs } from "@/components/ui/Tabs";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";

// ... CALM_MESSAGES and SUGGESTED_ACTIONS from Step 1 ...

type AlertTab = "active" | "handled";

export default function AlertsPage() {
  const [tab, setTab] = useState<AlertTab>("active");
  const { data, isLoading } = useAlerts({ status: tab === "active" ? "pending" : "actioned" });
  const markActioned = useMarkAlertActioned();
  const snooze = useSnoozeAlert();

  const tabs = [
    { key: "active" as const, label: "Active", count: data?.items?.filter((a: any) => !a.actioned).length },
    { key: "handled" as const, label: "Handled" },
  ];

  // Group alerts by member_name
  const grouped: Record<string, any[]> = {};
  for (const alert of data?.items ?? []) {
    const name = alert.member_name || "Unknown";
    if (!grouped[name]) grouped[name] = [];
    grouped[name].push(alert);
  }

  if (isLoading) return <div className="p-6"><p className="text-gray-500">Loading alerts...</p></div>;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Alerts</h1>
        <p className="text-sm text-gray-500">Things that may need your attention</p>
      </div>

      <Tabs tabs={tabs} active={tab} onChange={(k) => setTab(k as AlertTab)} />

      {Object.keys(grouped).length === 0 ? (
        <EmptyState
          title={tab === "active" ? "All clear" : "No handled alerts yet"}
          message={tab === "active" ? "Your family is safe — no items need attention right now." : "Alerts you handle will appear here."}
        />
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([memberName, alerts]) => (
            <div key={memberName} className="rounded-xl bg-white ring-1 ring-gray-200">
              <div className="flex items-center justify-between border-b px-4 py-3">
                <h3 className="text-sm font-semibold text-gray-900">{memberName}</h3>
                <Badge variant={alerts.some((a: any) => a.severity === "critical") ? "error" : "info"}>
                  {alerts.length} {alerts.length === 1 ? "alert" : "alerts"}
                </Badge>
              </div>
              <div className="divide-y">
                {alerts.map((alert: any) => {
                  const calmMsg = (CALM_MESSAGES[alert.alert_type] || CALM_MESSAGES.default)(memberName, alert.platform);
                  const suggestion = SUGGESTED_ACTIONS[alert.alert_type] || SUGGESTED_ACTIONS.default;

                  return (
                    <div key={alert.id} className="px-4 py-3">
                      <p className="text-sm text-gray-900">{calmMsg}</p>
                      <p className="mt-1 text-xs text-gray-500">Suggestion: {suggestion}</p>
                      <div className="mt-2 flex gap-2">
                        {!alert.actioned && (
                          <>
                            <Button variant="primary" size="sm" onClick={() => markActioned.mutate(alert.id)}>
                              Mark as handled
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => snooze.mutate({ id: alert.id, hours: 24 })}>
                              Snooze 24h
                            </Button>
                          </>
                        )}
                        <Button variant="ghost" size="sm" onClick={() => window.location.href = `/activity?alert=${alert.id}`}>
                          View details
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Run type check**

```bash
cd portal && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 4: Commit**

```bash
git add portal/src/app/\(dashboard\)/alerts/page.tsx
git commit -m "feat: redesign alerts with child grouping, calm language, and suggested actions"
```

---

### Task D5: Role-Based Navigation

**Files:**
- Modify: `portal/src/app/(dashboard)/layout.tsx`

**Context:** The sidebar shows 12 navigation items to all users. Family parents see governance tools, school admins see emergency contacts. Filter nav items based on `user.account_type` (already available via `useAuth()`). Three profiles: family, school, club.

- [ ] **Step 1: Define navigation profiles**

At the top of `portal/src/app/(dashboard)/layout.tsx`, replace the flat `navItems` array with role-filtered items:

```typescript
type AccountType = "family" | "school" | "club";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: AccountType[];
}

const navItems: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, roles: ["family", "school", "club"] },
  { href: "/members", label: "Children", icon: Users, roles: ["family"] },
  { href: "/members", label: "Students", icon: Users, roles: ["school"] },
  { href: "/members", label: "Members", icon: Users, roles: ["club"] },
  { href: "/activity", label: "Activity", icon: Activity, roles: ["family", "school", "club"] },
  { href: "/alerts", label: "Alerts", icon: Bell, roles: ["family", "school", "club"] },
  { href: "/safety", label: "Safety", icon: ShieldAlert, roles: ["family"] },
  { href: "/school", label: "Classes", icon: GraduationCap, roles: ["school"] },
  { href: "/governance", label: "Compliance", icon: ShieldCheck, roles: ["school"] },
  { href: "/spend", label: "Spend", icon: CreditCard, roles: ["family", "school"] },
  { href: "/analytics", label: "Analytics", icon: BarChart3, roles: ["family", "school", "club"] },
  { href: "/reports", label: "Reports", icon: FileBarChart, roles: ["family", "school", "club"] },
  { href: "/integrations", label: "Integrations", icon: Plug, roles: ["school"] },
  { href: "/settings", label: "Settings", icon: Settings, roles: ["family", "school", "club"] },
];
```

- [ ] **Step 2: Filter nav items by account type in the sidebar render**

In the sidebar rendering section, filter items:

```typescript
const accountType = (user?.account_type || "family") as AccountType;
const visibleItems = navItems.filter((item) => item.roles.includes(accountType));
```

Then render `visibleItems` instead of `navItems` in the sidebar map.

- [ ] **Step 3: Run type check**

```bash
cd portal && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 4: Commit**

```bash
git add portal/src/app/\(dashboard\)/layout.tsx
git commit -m "feat: role-based navigation — family/school/club see different sidebar items"
```

---

### Task D6: Settings Simplification

**Files:**
- Modify: `portal/src/app/(dashboard)/settings/page.tsx`
- Create: `portal/src/app/(dashboard)/safety/page.tsx`

**Context:** Split 7-tab settings into 3 pages: `/settings` (Profile + Notifications + Language), `/safety` (Safety Rules + Emergency Contacts), and existing `/billing`. API Keys already live at `/developers`. Privacy stays at `/settings/privacy`.

- [ ] **Step 1: Create dedicated Safety page**

```tsx
// portal/src/app/(dashboard)/safety/page.tsx
"use client";
import React from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { useGroupSettings, useUpdateGroupSettings } from "@/hooks/use-settings";
import { useEmergencyContacts, useAddEmergencyContact, useRemoveEmergencyContact } from "@/hooks/use-emergency-contacts";
import { Input } from "@/components/ui/Input";

export default function SafetyPage() {
  const { data: settings } = useGroupSettings();
  const updateSettings = useUpdateGroupSettings();
  const { data: contacts } = useEmergencyContacts();
  const addContact = useAddEmergencyContact();
  const removeContact = useRemoveEmergencyContact();

  const [newContactName, setNewContactName] = React.useState("");
  const [newContactPhone, setNewContactPhone] = React.useState("");

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Safety Settings</h1>
        <p className="text-sm text-gray-500">Configure monitoring rules and emergency contacts</p>
      </div>

      <Card title="Safety Rules">
        <div className="space-y-4">
          <Select
            label="Safety level"
            options={[
              { value: "strict", label: "Strict — All content reviewed before child sees it" },
              { value: "moderate", label: "Moderate — Flag risky content, allow most through" },
              { value: "permissive", label: "Permissive — Alert on high-risk only" },
            ]}
            value={settings?.safety_level || "moderate"}
            onChange={(val) => updateSettings.mutate({ safety_level: val })}
          />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700">Auto-block critical content</p>
              <p className="text-xs text-gray-500">Automatically block sessions flagged as critical risk</p>
            </div>
            <input
              type="checkbox"
              checked={settings?.auto_block_critical ?? true}
              onChange={(e) => updateSettings.mutate({ auto_block_critical: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-primary-600"
            />
          </div>
        </div>
      </Card>

      <Card title="Emergency Contacts">
        <div className="space-y-3">
          {contacts?.map((contact: any) => (
            <div key={contact.id} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2">
              <div>
                <p className="text-sm font-medium text-gray-900">{contact.name}</p>
                <p className="text-xs text-gray-500">{contact.phone}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => removeContact.mutate(contact.id)}>Remove</Button>
            </div>
          ))}
          <div className="flex gap-2">
            <Input placeholder="Name" value={newContactName} onChange={(e) => setNewContactName(e.target.value)} />
            <Input placeholder="Phone" value={newContactPhone} onChange={(e) => setNewContactPhone(e.target.value)} />
            <Button variant="secondary" size="sm" onClick={() => {
              if (newContactName && newContactPhone) {
                addContact.mutate({ name: newContactName, phone: newContactPhone });
                setNewContactName("");
                setNewContactPhone("");
              }
            }}>Add</Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Simplify settings page to Profile + Notifications only**

In `portal/src/app/(dashboard)/settings/page.tsx`, remove the tabs for "safety", "billing", "emergency-contacts", and "api-keys". Keep only "profile" and "notifications" as inline sections (no tabs needed for just 2 sections):

Replace the tab structure with a simple stacked layout showing Profile section and Notifications section, both visible without tabs.

- [ ] **Step 3: Run type check**

```bash
cd portal && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 4: Commit**

```bash
git add portal/src/app/\(dashboard\)/settings/page.tsx portal/src/app/\(dashboard\)/safety/page.tsx
git commit -m "feat: simplify settings (profile+notifications) and create dedicated safety page"
```

---

### Task D7: Mobile API Wiring

**Files:**
- Modify: `mobile/apps/safety/app/(dashboard)/index.tsx`
- Modify: `mobile/apps/safety/app/(dashboard)/alerts.tsx`
- Modify: `mobile/apps/social/app/(feed)/index.tsx`
- Modify: `mobile/apps/social/app/(feed)/create-post.tsx`
- Modify: various other mobile screen files with stubbed API calls

**Context:** Mobile app screens have API calls as comments (stubbed). They need to be connected to real endpoints via `@bhapi/api` rest client. The shared-api package has a `rest-client.ts` with Axios instance and interceptors.

This is a large task. The pattern for each screen is:
1. Find commented-out API calls
2. Import the API client from `@bhapi/api`
3. Replace mock data with real API calls
4. Handle loading/error states

- [ ] **Step 1: Wire Safety app dashboard**

In `mobile/apps/safety/app/(dashboard)/index.tsx`, replace the mock data loading with:

```typescript
import { apiClient } from '@bhapi/api';

async function fetchDashboard(): Promise<DashboardData> {
  const response = await apiClient.get('/portal/dashboard');
  return response.data;
}

// In the useEffect or data loading function:
const data = await fetchDashboard();
```

Replace similar stubs in `alerts.tsx`, `alert-detail.tsx`, `unified.tsx`, `social-activity.tsx`.

- [ ] **Step 2: Wire Social app feed**

In `mobile/apps/social/app/(feed)/index.tsx`, replace the empty items array with:

```typescript
import { apiClient } from '@bhapi/api';

async function fetchFeed(page: number): Promise<{ items: FeedItem[]; total: number }> {
  const response = await apiClient.get(`/social/feed?page=${page}&page_size=${PAGE_SIZE}`);
  return response.data;
}
```

Replace similar stubs in `create-post.tsx`, `post-detail.tsx`.

- [ ] **Step 3: Wire Social app messaging**

In `mobile/apps/social/app/(chat)/index.tsx` and `conversation.tsx`, wire the messaging API:

```typescript
import { apiClient } from '@bhapi/api';

async function fetchConversations(): Promise<Conversation[]> {
  const response = await apiClient.get('/messages/conversations');
  return response.data.items;
}

async function fetchMessages(conversationId: string, page: number): Promise<Message[]> {
  const response = await apiClient.get(`/messages/conversations/${conversationId}/messages?page=${page}`);
  return response.data.items;
}

async function sendMessage(conversationId: string, content: string): Promise<Message> {
  const response = await apiClient.post(`/messages/conversations/${conversationId}/messages`, { content });
  return response.data;
}
```

- [ ] **Step 4: Wire remaining screens**

Apply the same pattern to:
- `mobile/apps/social/app/(contacts)/index.tsx` — `GET /contacts`
- `mobile/apps/social/app/(profile)/index.tsx` — `GET /social/profiles/me`
- `mobile/apps/social/app/(profile)/edit.tsx` — `PUT /social/profiles/me`
- `mobile/apps/safety/app/(children)/child-profile.tsx` — `GET /portal/children/{id}`
- `mobile/apps/safety/app/(children)/contact-approval.tsx` — `GET /contacts/pending-approvals`

- [ ] **Step 5: Run mobile tests**

```bash
cd mobile && npx turbo run test
```

Expected: All tests pass (API calls are mocked in test environment via `@bhapi/api` test utilities).

- [ ] **Step 6: Commit**

```bash
git add mobile/apps/safety/ mobile/apps/social/
git commit -m "feat: wire all mobile screens to real API endpoints (remove stubs)"
```

---

### Task D8: Mobile Empty States + Dark Mode

**Files:**
- Modify: `mobile/packages/shared-config/src/theme.ts`
- Create: `mobile/packages/shared-ui/src/MobileEmptyState.tsx`
- Modify: `mobile/apps/safety/app/(dashboard)/index.tsx`
- Modify: `mobile/apps/safety/app/(dashboard)/alerts.tsx`
- Modify: `mobile/apps/social/app/(feed)/index.tsx`
- Modify: `mobile/apps/social/app/(chat)/index.tsx`
- Modify: `mobile/apps/safety/app/_layout.tsx`
- Modify: `mobile/apps/social/app/_layout.tsx`

**Context:** Empty states currently show nothing. Add friendly messages. Dark mode uses React Native `useColorScheme()`.

- [ ] **Step 1: Create MobileEmptyState component**

```tsx
// mobile/packages/shared-ui/src/MobileEmptyState.tsx
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, typography } from '@bhapi/config';
import { Button } from './Button';

interface MobileEmptyStateProps {
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function MobileEmptyState({ title, message, actionLabel, onAction }: MobileEmptyStateProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{message}</Text>
      {actionLabel && onAction && (
        <View style={styles.action}>
          <Button title={actionLabel} onPress={onAction} variant="primary" size="sm" />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.xl },
  title: { fontSize: typography.fontSize.lg, fontWeight: '600', color: colors.gray[900], textAlign: 'center' },
  message: { fontSize: typography.fontSize.sm, color: colors.gray[500], textAlign: 'center', marginTop: spacing.sm },
  action: { marginTop: spacing.lg },
});
```

- [ ] **Step 2: Add empty states to key screens**

In Safety dashboard (`index.tsx`), when data has no alerts:
```tsx
<MobileEmptyState title="All clear" message="Your family is safe — no alerts this week." />
```

In Safety alerts (`alerts.tsx`), when no alerts:
```tsx
<MobileEmptyState title="No alerts" message="We'll notify you if something needs your attention." />
```

In Social feed (`index.tsx`), when empty:
```tsx
<MobileEmptyState title="Your feed is empty" message="Follow someone to see their posts here!" actionLabel="Find friends" onAction={() => router.push('/contacts')} />
```

In Social chat (`index.tsx`), when no conversations:
```tsx
<MobileEmptyState title="No messages yet" message="Start a conversation with a friend." />
```

- [ ] **Step 3: Add dark mode colors to theme**

In `mobile/packages/shared-config/src/theme.ts`, add dark color scheme:

```typescript
export const darkColors = {
  background: { primary: '#111827', secondary: '#1F2937', tertiary: '#374151' },
  text: { primary: '#F9FAFB', secondary: '#D1D5DB', tertiary: '#9CA3AF' },
  border: '#4B5563',
  primary: colors.primary,   // Orange stays the same
  accent: colors.accent,     // Teal stays the same
} as const;
```

- [ ] **Step 4: Add dark mode provider to both app layouts**

In both `_layout.tsx` files, add `useColorScheme()` detection:

```typescript
import { useColorScheme } from 'react-native';

// Inside the component:
const colorScheme = useColorScheme();
const isDark = colorScheme === 'dark';

// Pass isDark to a ThemeProvider context (or use it directly in styles)
```

- [ ] **Step 5: Export MobileEmptyState from shared-ui**

Add to `mobile/packages/shared-ui/src/index.ts`:

```typescript
export { MobileEmptyState } from './MobileEmptyState';
```

- [ ] **Step 6: Run tests**

```bash
cd mobile && npx turbo run test
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add mobile/packages/shared-ui/src/MobileEmptyState.tsx mobile/packages/shared-ui/src/index.ts mobile/packages/shared-config/src/theme.ts mobile/apps/safety/ mobile/apps/social/
git commit -m "feat: add mobile empty states with friendly messages and dark mode support"
```

---

### Task D9: Trust Signals

**Files:**
- Modify: `portal/src/app/page.tsx` (landing page)
- Create: `portal/public/coppa-badge.png` (static asset)
- Modify: `portal/src/app/(dashboard)/dashboard/page.tsx`
- Modify: `portal/src/app/(dashboard)/settings/privacy/page.tsx`

**Context:** Add visible trust signals: COPPA certification badge on landing page, transparency card on dashboard, and data deletion counter on privacy settings. The safe harbor certificate already exists at `/api/v1/compliance/coppa/safe-harbor-certificate`.

- [ ] **Step 1: Add COPPA badge and moderation SLA to landing page**

In `portal/src/app/page.tsx`, add a trust bar below the hero section:

```tsx
{/* Trust Signals Bar */}
<div className="border-y bg-gray-50 py-4">
  <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-8 px-4">
    <div className="flex items-center gap-2">
      <img src="/coppa-badge.png" alt="COPPA Compliant" className="h-8 w-8" />
      <span className="text-sm text-gray-600">COPPA 2026 Compliant</span>
    </div>
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-600">GDPR &amp; EU AI Act Ready</span>
    </div>
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-600">Content reviewed in &lt;2 seconds</span>
    </div>
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-600">End-to-end encrypted</span>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Add transparency card to dashboard**

In `portal/src/app/(dashboard)/dashboard/page.tsx`, add after the WeeklySummary component:

```tsx
{/* Trust: What we collect */}
<div className="rounded-lg bg-blue-50 px-4 py-3 ring-1 ring-blue-100">
  <p className="text-sm font-medium text-blue-800">What we monitor</p>
  <p className="mt-1 text-xs text-blue-600">
    AI conversation metadata (platforms, duration, risk signals). We never read message content unless flagged for safety.
    <a href="/settings/privacy" className="ml-1 underline">Manage privacy settings</a>
  </p>
</div>
```

- [ ] **Step 3: Add data deletion counter to privacy settings**

In `portal/src/app/(dashboard)/settings/privacy/page.tsx`, add a deletion counter section that queries the retention stats:

```tsx
// Add hook call:
const { data: retentionStats } = useQuery({
  queryKey: ["retention-stats"],
  queryFn: () => apiClient.get("/compliance/coppa/retention").then(r => r.data),
});

// Add to the page:
{retentionStats && (
  <div className="rounded-lg bg-green-50 p-4 ring-1 ring-green-100">
    <p className="text-sm font-medium text-green-800">Data auto-cleanup active</p>
    <p className="text-xs text-green-600">
      {retentionStats.records_deleted_this_month || 0} expired records auto-deleted this month.
      Your data retention policies are enforced automatically.
    </p>
  </div>
)}
```

- [ ] **Step 4: Run type check**

```bash
cd portal && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 5: Commit**

```bash
git add portal/src/app/page.tsx portal/src/app/\(dashboard\)/dashboard/page.tsx portal/src/app/\(dashboard\)/settings/privacy/page.tsx
git commit -m "feat: add trust signals — COPPA badge, transparency card, data deletion counter"
```

---

### Task D10: Calm Alert Language (Backend Templates)

**Files:**
- Create: `src/alerts/calm_templates.py`
- Modify: `src/alerts/service.py`
- Create: `tests/unit/test_calm_templates.py`

**Context:** Backend alert creation uses technical titles like "PII_EXPOSURE". Add a template layer that generates calm, parent-friendly messages. The frontend (Task D4) already has a client-side fallback, but generating calm text server-side ensures email digests and push notifications also use friendly language.

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_calm_templates.py
import pytest
from src.alerts.calm_templates import calm_message, suggested_action


class TestCalmTemplates:
    def test_pii_exposure_message(self):
        msg = calm_message("pii_exposure", member_name="Sam", platform="ChatGPT")
        assert "Sam" in msg
        assert "personal information" in msg
        assert "ChatGPT" in msg

    def test_unknown_type_has_default(self):
        msg = calm_message("unknown_new_type", member_name="Alex")
        assert "Alex" in msg
        assert "attention" in msg

    def test_suggested_action_exists_for_all_types(self):
        for alert_type in ["pii_exposure", "deepfake", "safety_concern", "unusual_usage",
                           "academic_integrity", "emotional_dependency"]:
            action = suggested_action(alert_type)
            assert len(action) > 10, f"No action for {alert_type}"

    def test_suggested_action_default(self):
        action = suggested_action("unknown_type")
        assert "Review" in action or "review" in action
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_calm_templates.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement calm templates**

```python
# src/alerts/calm_templates.py
"""Parent-friendly alert message templates.

"Calm Safety" principle: lead with what happened in plain language,
not technical severity labels. Parents respond better to
"Sam shared personal information" than "CRITICAL: PII_EXPOSURE".
"""

_CALM_MESSAGES: dict[str, str] = {
    "pii_exposure": "We noticed {member_name} shared personal information{platform_suffix}",
    "deepfake": "A suspicious image was found{platform_suffix} in {member_name}'s session",
    "safety_concern": "{member_name} may have encountered concerning content{platform_suffix}",
    "unusual_usage": "{member_name}'s AI usage changed significantly this week",
    "academic_integrity": "{member_name} may have used AI for schoolwork{platform_suffix}",
    "emotional_dependency": "{member_name} may be developing an emotional attachment to an AI{platform_suffix}",
    "grooming_risk": "We detected a potentially unsafe interaction involving {member_name}",
    "self_harm": "We noticed content that may indicate {member_name} is struggling",
    "privacy_violation": "{member_name}'s privacy settings may have been bypassed{platform_suffix}",
    "evasion": "{member_name} may be trying to avoid monitoring",
}

_SUGGESTED_ACTIONS: dict[str, str] = {
    "pii_exposure": "Talk to your child about sharing personal information online",
    "deepfake": "Review the content and discuss image safety with your child",
    "safety_concern": "Have a calm conversation about what they saw",
    "unusual_usage": "Check in about their AI usage habits this week",
    "academic_integrity": "Discuss responsible AI use for schoolwork",
    "emotional_dependency": "Encourage offline social activities and friendships",
    "grooming_risk": "Review the interaction details and consider contacting support",
    "self_harm": "Talk to your child with care and consider professional support",
    "privacy_violation": "Review your child's privacy settings together",
    "evasion": "Have an open conversation about monitoring and trust",
}

_DEFAULT_MESSAGE = "Something needs your attention regarding {member_name}"
_DEFAULT_ACTION = "Review the details and talk with your child"


def calm_message(alert_type: str, member_name: str, platform: str | None = None) -> str:
    """Generate a calm, parent-friendly alert message."""
    template = _CALM_MESSAGES.get(alert_type, _DEFAULT_MESSAGE)
    platform_suffix = f" in {platform}" if platform else ""
    return template.format(member_name=member_name, platform_suffix=platform_suffix)


def suggested_action(alert_type: str) -> str:
    """Get the suggested parent action for an alert type."""
    return _SUGGESTED_ACTIONS.get(alert_type, _DEFAULT_ACTION)
```

- [ ] **Step 4: Integrate into alert creation**

In `src/alerts/service.py`, import and use the templates when creating alerts. In the `create_alert` function, after the alert object is created, add calm_title and calm_body fields:

```python
from src.alerts.calm_templates import calm_message, suggested_action

# After creating the alert object, set friendly fields:
alert.calm_title = calm_message(data.alert_type or "default", member_name=member_name, platform=data.platform)
alert.calm_action = suggested_action(data.alert_type or "default")
```

Note: This requires `calm_title` and `calm_action` columns on the Alert model. If they don't exist, store these in the existing `body` field as JSON metadata instead:

```python
import json
calm_data = {
    "calm_message": calm_message(data.alert_type or "default", member_name=member_name, platform=data.platform),
    "suggested_action": suggested_action(data.alert_type or "default"),
}
# Store in alert metadata or body
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_calm_templates.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add src/alerts/calm_templates.py tests/unit/test_calm_templates.py src/alerts/service.py
git commit -m "feat: add calm alert language templates for parent-friendly notifications"
```

---

## Final Task: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md with launch excellence changes**

Add the following updates to CLAUDE.md:

1. Update version to `4.0.0` (Launch Excellence)
2. Add Moderation SLA dashboard to module list
3. Add new portal UI components (Select, Modal, Tabs, EmptyState, Badge) to design system section
4. Document "Calm Safety" UX philosophy
5. Document role-based navigation (family/school/club)
6. Document the 3-zone dashboard layout
7. Note that mobile API stubs have been wired
8. Update test counts
9. Add `safety/` page to the portal page list
10. Note Sentry crash reporting on both mobile apps
11. Document Redis as provisioned (no longer optional)
12. Document WebSocket service as deployed (Dockerfile.realtime)

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with Launch Excellence changes (v4.0.0)"
```

---

## Launch Gate Verification

After all tracks are complete, run the full verification:

```bash
# Backend tests
pytest tests/ -v

# Frontend type check + tests
cd portal && npx tsc --noEmit && npx vitest run

# Mobile tests
cd mobile && npx turbo run test

# Extension tests
cd extension && npx jest

# Verify Sentry integration (check Sentry dashboard for test events)
# Verify Redis connection (check Render dashboard)
# Verify WebSocket service health (curl https://bhapi-realtime.onrender.com/health)
# Verify moderation SLA dashboard (navigate to /moderation in portal)
```

All gates must pass before proceeding to A5 (public release).
