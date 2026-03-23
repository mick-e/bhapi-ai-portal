# Phase 3: Competitive Parity + Market Launch — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Launch both Bhapi apps publicly, ship cross-product intelligence engine, add location tracking + screen time + creative tools for Family+ tier, open B2B API for partners, and establish bundle pricing with a minimal free tier.

**Architecture:** Extends the Phase 2 backend (26 modules, 44 migrations, 3,854+ tests) with 4 new modules (`location/`, `screen_time/`, `creative/`, `api_platform/`), extends 3 existing modules (`intelligence/`, `billing/`, `alerts/`), adds 7 Alembic migrations (045-051), 13 new mobile screens, 6 new portal pages, and 6 new shared-ui components. Three-layer execution: Foundation → Features → Launch.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy async / Alembic / PostgreSQL 16 | Expo SDK 52+ / React Native / TypeScript / Turborepo | Next.js 15 (static export) | Redis 7 | Cloudflare R2/Images/Stream | Stripe | OpenAI Images API | react-native-skia | Maestro (mobile E2E)

**Spec:** `docs/superpowers/specs/2026-08-04-phase3-market-launch-design.md` (v1.0)

**Duration:** Weeks 21-26 (Aug 4 — Sep 17, 2026)
**Team:** 10-13 engineers
**Budget:** 60-78 person-weeks
**Phase 2 exit:** 32/32 tasks complete, 3,854+ backend tests passing, all pushed to master
**Next migration:** 045

---

## Dependency Graph

```
LAYER 1: FOUNDATION (Weeks 21-23) — Tasks 1-12
  Task 1  (P3-I1a): Intelligence event bus (Redis pub/sub) ─────┐
  Task 2  (P3-I1b): Correlation rules engine + migration 050 ───┤
  Task 3  (P3-I2):  Unified risk scoring ───────────────────────┤
  Task 4  (P3-B1):  Bundle pricing + feature gating + mig 049 ─┤
  Task 5  (P3-B3a): API platform OAuth 2.0 + models + mig 048 ─┤
  Task 6  (P3-B3b): API webhooks + delivery + rate limiting ────┤
  Task 7  (P3-F3a): Location models + migration 045 ────────────┤
  Task 8  (P3-F3b): Location service + router + privacy ────────┤
  Task 9  (P3-F3c): Location mobile screens (Safety app) ───────┤
  Task 10 (P3-F2a): Screen time models + migration 046 ─────────┤
  Task 11 (P3-F2b): Screen time service + router ───────────────┤
  Task 12 (P3-F2c): Screen time mobile screens ─────────────────┘
       │
       ▼
LAYER 2: FEATURES (Weeks 24-25) — Tasks 13-22
  Task 13 (P3-F1a): Creative models + migration 047 ────────────┐
  Task 14 (P3-F1b): Creative service (AI art, stories) ─────────┤
  Task 15 (P3-F1c): Creative mobile screens (Social app) ───────┤
  Task 16 (P3-F4):  Unified parent dashboard (portal + Safety) ─┤
  Task 17 (P3-I3):  Alert enrichment (correlated context) ──────┤
  Task 18 (P3-I4):  Behavioral anomaly correlation ─────────────┤
  Task 19 (P3-B3c): Developer portal pages + API docs ──────────┤
  Task 20 (P3-B2):  Channel partnership package (docs) ─────────┤
  Task 21 (P3-B4):  SOC 2 audit initiation + migration 051 ─────┤
  Task 22 (P3-F3d): School check-in + location consent ─────────┘
       │
       ▼
LAYER 3: LAUNCH (Week 26) — Tasks 23-27
  Task 23 (P3-L4):  Landing page redesign ──────────────────────┐
  Task 24 (P3-L5):  Cross-app onboarding (3 paths) ────────────┤
  Task 25 (P3-L3):  App Store optimization (6 languages) ───────┤
  Task 26 (P3-L1):  Bhapi Social public release ────────────────┤
  Task 27 (P3-L2):  Bhapi Safety public release ────────────────┘
```

**Parallelization:** Within each layer, tasks without mutual dependencies can run concurrently via subagents. Key serialization points:
- Tasks creating migrations (1-2 per layer) must be sequenced — each modifies `alembic/env.py`
- Tasks 7→8→9 (location) are sequential; Tasks 10→11→12 (screen time) are sequential
- Tasks 5→6→19 (API platform) are sequential
- Tasks 13→14→15 (creative) are sequential
- All Layer 1 tasks must complete before Layer 2 starts
- All Layer 2 tasks must complete before Layer 3 starts

**Cross-track dependencies:**
- Task 4 (feature gating) should complete early — Tasks 8, 11, 14 use `check_feature_gate()`
- Task 1 (event bus) must complete before Task 2 (correlation), Task 3 (scoring), Task 17 (enrichment), Task 18 (anomaly)

---

## File Structure

### New Backend Modules

```
src/
├── location/                      # NEW (Tasks 7-9, 22)
│   ├── __init__.py
│   ├── router.py                  # /api/v1/location endpoints
│   ├── service.py                 # Tracking, geofencing, kill switch, school check-in
│   ├── models.py                  # LocationRecord, Geofence, GeofenceEvent, SchoolCheckIn,
│   │                              #   LocationSharingConsent, LocationKillSwitch, LocationAuditLog
│   └── schemas.py
│
├── screen_time/                   # NEW (Tasks 10-12)
│   ├── __init__.py
│   ├── router.py                  # /api/v1/screen-time endpoints
│   ├── service.py                 # Rules, schedules, enforcement, extension requests
│   ├── models.py                  # ScreenTimeRule, ScreenTimeSchedule, ExtensionRequest
│   └── schemas.py
│
├── creative/                      # NEW (Tasks 13-15)
│   ├── __init__.py
│   ├── router.py                  # /api/v1/creative endpoints
│   ├── service.py                 # AI art, stories, stickers, drawings
│   ├── models.py                  # ArtGeneration, StoryTemplate, StoryCreation,
│   │                              #   StickerPack, Sticker, DrawingAsset
│   └── schemas.py
│
├── api_platform/                  # NEW (Tasks 5-6, 19)
│   ├── __init__.py
│   ├── router.py                  # /api/v1/platform endpoints
│   ├── oauth.py                   # OAuth 2.0 authorization server
│   ├── service.py                 # API key mgmt, usage metering, tier enforcement
│   ├── webhooks.py                # Webhook delivery, retry, HMAC signature
│   ├── models.py                  # OAuthClient, OAuthToken, APIKeyTier, WebhookEndpoint,
│   │                              #   WebhookDelivery, APIUsageRecord
│   └── schemas.py
│
├── intelligence/                  # EXTEND (Tasks 1-3, 17-18)
│   ├── event_bus.py               # NEW — Redis pub/sub event bus
│   ├── correlation.py             # NEW — Rule engine, pattern matching
│   ├── scoring.py                 # NEW — Unified risk score calculator
│   └── anomaly.py                 # NEW — Multi-signal deviation detection
│
├── billing/                       # EXTEND (Task 4)
│   ├── feature_gate.py            # NEW — FeatureGate model + check_feature_gate() dependency
│   └── tiers.py                   # NEW — Tier definitions, upgrade/downgrade logic
│
├── compliance/                    # EXTEND (Task 21)
│   └── soc2.py                    # NEW — Evidence collection, control mapping
│
└── alerts/                        # EXTEND (Task 17)
    (enriched_alert_id FK added to existing Alert model via migration)
```

### New Mobile Screens

```
mobile/apps/
├── safety/app/
│   ├── (dashboard)/
│   │   ├── location.tsx           # NEW — Real-time map, geofences, history
│   │   ├── geofences.tsx          # NEW — Create/edit/delete geofences
│   │   ├── screen-time.tsx        # NEW — Rules, schedules, usage chart
│   │   ├── extension-request.tsx  # NEW — Approve/deny time extensions
│   │   ├── unified.tsx            # NEW — Combined AI + social + location + screen time
│   │   └── creative-review.tsx    # NEW — Review child's AI art, stories, drawings
│   └── (settings)/
│       └── location-settings.tsx  # NEW — Kill switch, school consent, retention
│
├── social/app/
│   ├── (creative)/
│   │   ├── art-studio.tsx         # NEW — AI art generation
│   │   ├── story-creator.tsx      # NEW — Template browser + writing
│   │   ├── drawing.tsx            # NEW — react-native-skia canvas
│   │   └── stickers.tsx           # NEW — Sticker browser + personal library
│   └── (settings)/
│       ├── share-location.tsx     # NEW — One-tap location share
│       └── screen-time.tsx        # NEW — Usage, limits, request extension
│
└── packages/shared-ui/src/
    ├── LocationMap.tsx             # NEW — MapView wrapper
    ├── ScreenTimeBar.tsx           # NEW — Usage progress bar
    ├── RiskScoreCard.tsx           # NEW — Unified score with trend
    ├── CreativeToolbar.tsx         # NEW — Drawing tools
    ├── StickerGrid.tsx             # NEW — Sticker grid layout
    └── FeatureGateBanner.tsx       # NEW — "Upgrade to Family+" banner
```

### New Portal Pages

```
portal/src/app/
├── (dashboard)/
│   └── unified/page.tsx           # NEW — Unified parent dashboard
├── (marketing)/
│   ├── page.tsx                   # MODIFY — Landing page hero redesign
│   ├── families/page.tsx          # NEW — Family features + pricing
│   ├── schools/page.tsx           # NEW — School features + compliance
│   ├── partners/page.tsx          # NEW — Partnership program
│   └── pricing/page.tsx           # NEW — Tier comparison matrix
└── (developers)/
    ├── page.tsx                   # NEW — API overview + apply
    ├── dashboard/page.tsx         # NEW — API key mgmt + usage
    ├── webhooks/page.tsx          # NEW — Webhook management
    └── docs/page.tsx              # NEW — Interactive API docs
```

### New Alembic Migrations

| Number | Tables | Task |
|--------|--------|------|
| 045 | `location_records`, `geofences`, `geofence_events`, `school_checkins`, `location_sharing_consents`, `location_kill_switches`, `location_audit_logs` | Task 7 |
| 046 | `screen_time_rules`, `screen_time_schedules`, `extension_requests` | Task 10 |
| 047 | `art_generations`, `story_templates`, `story_creations`, `sticker_packs`, `stickers`, `drawing_assets` | Task 13 |
| 048 | `oauth_clients`, `oauth_tokens`, `api_key_tiers`, `webhook_endpoints`, `webhook_deliveries`, `api_usage_records` | Task 5 |
| 049 | `feature_gates` + seed data | Task 4 |
| 050 | `correlation_rules`, `enriched_alerts` + seed 14 rules | Task 2 |
| 051 | `audit_policies`, `evidence_collections`, `compliance_controls` | Task 21 |

**CRITICAL:** Migrations must be sequenced (each modifies `alembic/env.py`). Recommended order: 045 → 046 → 047 → 048 → 049 → 050 → 051. Each migration file MUST be committed and pushed — uncommitted migrations cause production crashes (lesson from 2026-03-12).

---

## LAYER 1: FOUNDATION (Weeks 21-23)

### Task 1 (P3-I1a): Intelligence Event Bus — Redis Pub/Sub

**Files:**
- Create: `src/intelligence/event_bus.py`
- Modify: `src/intelligence/__init__.py` (add event bus exports)
- Create: `tests/unit/test_intelligence_event_bus.py`
- Create: `tests/e2e/test_intelligence_event_bus.py`

**Tests Required:** Unit ≥15, E2E ≥10

- [ ] **Step 1: Write event bus unit tests**

Create `tests/unit/test_intelligence_event_bus.py`:
```python
"""Unit tests for intelligence event bus."""

import pytest
from unittest.mock import AsyncMock, patch

from src.intelligence.event_bus import (
    EventBus,
    publish_event,
    subscribe,
    EVENT_AI_SESSION,
    EVENT_SOCIAL_ACTIVITY,
    EVENT_DEVICE,
    EVENT_LOCATION,
)


@pytest.mark.asyncio
async def test_publish_event_formats_channel():
    """publish_event sends JSON payload to correct Redis channel."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_AI_SESSION, {"child_id": "abc", "platform": "chatgpt"})
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "bhapi:events:ai_session"


@pytest.mark.asyncio
async def test_publish_event_includes_timestamp():
    """Published events include a timestamp field."""
    mock_redis = AsyncMock()
    with patch("src.intelligence.event_bus.get_redis", return_value=mock_redis):
        await publish_event(EVENT_DEVICE, {"device_id": "d1"})
        import json
        payload = json.loads(mock_redis.publish.call_args[0][1])
        assert "timestamp" in payload
        assert "data" in payload


@pytest.mark.asyncio
async def test_publish_event_graceful_without_redis():
    """publish_event degrades gracefully when Redis is unavailable."""
    with patch("src.intelligence.event_bus.get_redis", return_value=None):
        # Should not raise
        await publish_event(EVENT_AI_SESSION, {"child_id": "abc"})


@pytest.mark.asyncio
async def test_event_channels_are_defined():
    """All four event channel constants are defined."""
    assert EVENT_AI_SESSION == "bhapi:events:ai_session"
    assert EVENT_SOCIAL_ACTIVITY == "bhapi:events:social_activity"
    assert EVENT_DEVICE == "bhapi:events:device"
    assert EVENT_LOCATION == "bhapi:events:location"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_intelligence_event_bus.py -v
```
Expected: FAIL — `event_bus` module does not exist.

- [ ] **Step 3: Implement event bus module**

Create `src/intelligence/event_bus.py`:
```python
"""Intelligence event bus — Redis pub/sub for cross-module event correlation.

Channels:
- bhapi:events:ai_session — AI platform usage events from capture module
- bhapi:events:social_activity — Social feed/messaging events from social module
- bhapi:events:device — Device agent events (app usage, screen time)
- bhapi:events:location — Location events (geofence, check-in)

Events are JSON payloads with structure:
  {"timestamp": "ISO8601", "event_type": "channel_name", "data": {...}}
"""

import json
from datetime import datetime, timezone

import structlog

from src.redis_client import get_redis

logger = structlog.get_logger()

# Channel constants
EVENT_AI_SESSION = "bhapi:events:ai_session"
EVENT_SOCIAL_ACTIVITY = "bhapi:events:social_activity"
EVENT_DEVICE = "bhapi:events:device"
EVENT_LOCATION = "bhapi:events:location"

ALL_CHANNELS = [EVENT_AI_SESSION, EVENT_SOCIAL_ACTIVITY, EVENT_DEVICE, EVENT_LOCATION]


async def publish_event(channel: str, data: dict) -> None:
    """Publish an event to a Redis channel.

    Gracefully degrades if Redis is unavailable (logs warning, does not raise).
    """
    redis = get_redis()
    if redis is None:
        logger.warning("event_bus_no_redis", channel=channel)
        return

    payload = json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": channel,
        "data": data,
    })
    try:
        await redis.publish(channel, payload)
        logger.debug("event_published", channel=channel)
    except Exception:
        logger.exception("event_publish_failed", channel=channel)


async def subscribe(channels: list[str] | None = None):
    """Subscribe to event channels. Returns an async iterator of events.

    Usage:
        async for event in subscribe([EVENT_AI_SESSION]):
            process(event)
    """
    redis = get_redis()
    if redis is None:
        logger.warning("event_bus_subscribe_no_redis")
        return

    sub_channels = channels or ALL_CHANNELS
    pubsub = redis.pubsub()
    await pubsub.subscribe(*sub_channels)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    yield json.loads(message["data"])
                except json.JSONDecodeError:
                    logger.warning("event_bus_invalid_json", data=message["data"])
    finally:
        await pubsub.unsubscribe(*sub_channels)
        await pubsub.close()
```

- [ ] **Step 4: Update __init__.py exports**

Add to `src/intelligence/__init__.py`:
```python
from src.intelligence.event_bus import (
    EVENT_AI_SESSION,
    EVENT_DEVICE,
    EVENT_LOCATION,
    EVENT_SOCIAL_ACTIVITY,
    publish_event,
    subscribe,
)
```
Add these to the `__all__` list.

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_intelligence_event_bus.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Write E2E tests for event publishing**

Create `tests/e2e/test_intelligence_event_bus.py` — test event publishing via capture/social endpoints that trigger events. At minimum 10 tests covering: publish from each channel, graceful degradation, payload structure validation.

- [ ] **Step 7: Run full test suite for intelligence module**

```bash
pytest tests/ -k "intelligence" -v
```
Expected: All pass (existing + new).

- [ ] **Step 8: Commit**

```bash
git add src/intelligence/event_bus.py src/intelligence/__init__.py
git add tests/unit/test_intelligence_event_bus.py tests/e2e/test_intelligence_event_bus.py
git commit -m "feat(P3-I1a): intelligence event bus — Redis pub/sub for cross-module correlation"
```

---

### Task 2 (P3-I1b): Correlation Rules Engine + Migration 050

**Files:**
- Create: `src/intelligence/correlation.py`
- Modify: `src/intelligence/models.py` (add CorrelationRule, EnrichedAlert)
- Modify: `src/intelligence/schemas.py` (add correlation schemas)
- Modify: `src/intelligence/router.py` (add correlation endpoints)
- Modify: `src/intelligence/__init__.py` (add correlation exports)
- Create: `alembic/versions/050_correlation_rules.py`
- Modify: `alembic/env.py` (add model imports)
- Create: `tests/unit/test_correlation.py`
- Create: `tests/e2e/test_correlation.py`
- Create: `tests/security/test_correlation_security.py`

**Tests Required:** Unit ≥25, E2E ≥15, Security ≥15

- [ ] **Step 1: Add CorrelationRule and EnrichedAlert models**

Add to `src/intelligence/models.py`:
```python
class CorrelationRule(Base, UUIDMixin, TimestampMixin):
    """A configurable rule that matches patterns across event types."""

    __tablename__ = "correlation_rules"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition: Mapped[dict] = mapped_column(JSONType, nullable=False)
    action_severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium",
    )  # low, medium, high, critical
    notification_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="alert",
    )  # alert, email, push, sms
    age_tier_filter: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
    )  # young, preteen, teen, null=all
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EnrichedAlert(Base, UUIDMixin, TimestampMixin):
    """An alert enriched with cross-product correlation context."""

    __tablename__ = "enriched_alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    correlation_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("correlation_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    correlation_context: Mapped[str] = mapped_column(Text, nullable=False)
    contributing_signals: Mapped[dict] = mapped_column(JSONType, nullable=False)
    unified_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium",
    )  # low, medium, high
```

- [ ] **Step 2: Create migration 050**

```bash
alembic revision --autogenerate -m "correlation_rules_enriched_alerts"
```
Verify the generated file creates both tables + seeds 14 default correlation rules (see spec Section 5.2 for the 14 rule definitions). Add model imports to `alembic/env.py`.

- [ ] **Step 3: Write correlation service**

Create `src/intelligence/correlation.py` with:
- `evaluate_event(db, event)` — Match incoming event against active rules within 48h window
- `get_rules(db, age_tier=None)` — List active rules, optionally filtered by age tier
- `create_enriched_alert(db, alert_id, rule_id, context, signals, score, confidence)` — Create enriched alert
- `get_enriched_alert(db, alert_id)` — Get enrichment for an alert

- [ ] **Step 4: Add correlation endpoints to router**

Add to `src/intelligence/router.py`:
- `GET /correlation-rules` — List active rules (admin only)
- `POST /correlation-rules` — Create rule (admin only)
- `PUT /correlation-rules/{id}` — Update rule (admin only)
- `GET /enriched-alerts/{alert_id}` — Get enrichment for an alert

- [ ] **Step 5: Write unit tests (≥25)**

Create `tests/unit/test_correlation.py` testing: rule evaluation against mock events, age tier filtering, time window enforcement, enriched alert creation, rule CRUD.

- [ ] **Step 6: Write E2E tests (≥15)**

Create `tests/e2e/test_correlation.py` testing: full flow from event → rule match → enriched alert creation, multiple rules matching same event, no match when conditions unmet.

- [ ] **Step 7: Write security tests (≥15)**

Create `tests/security/test_correlation_security.py` testing: non-admin cannot create/update rules, enriched alerts only visible to parent of the child, rule condition injection prevention.

- [ ] **Step 8: Run all tests**

```bash
pytest tests/ -k "correlation" -v
```
Expected: All pass.

- [ ] **Step 9: Verify migration committed**

```bash
git status  # Verify migration file is tracked
```

- [ ] **Step 10: Commit**

```bash
git add src/intelligence/correlation.py src/intelligence/models.py src/intelligence/schemas.py
git add src/intelligence/router.py src/intelligence/__init__.py
git add alembic/versions/050_correlation_rules.py alembic/env.py
git add tests/unit/test_correlation.py tests/e2e/test_correlation.py tests/security/test_correlation_security.py
git commit -m "feat(P3-I1b): correlation rules engine — pattern matching, enriched alerts, 14 default rules"
```

---

### Task 3 (P3-I2): Unified Risk Scoring

**Files:**
- Create: `src/intelligence/scoring.py`
- Modify: `src/intelligence/__init__.py` (add scoring exports)
- Modify: `src/intelligence/router.py` (add scoring endpoints)
- Modify: `src/intelligence/schemas.py` (add scoring schemas)
- Create: `tests/unit/test_unified_scoring.py`
- Create: `tests/e2e/test_unified_scoring.py`

**Tests Required:** Unit ≥25, E2E ≥15

- [ ] **Step 1: Write scoring unit tests**

Create `tests/unit/test_unified_scoring.py` testing:
- Score computation with all 4 signal sources
- Age-tier weight differences (young weights AI higher, teen weights social higher)
- Confidence calculation based on data volume (< 7 days = low, 7-30 = medium, 30+ = high)
- Trend calculation (7-day and 30-day rolling)
- Score boundary: always 0-100

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_unified_scoring.py -v
```

- [ ] **Step 3: Implement scoring module**

Create `src/intelligence/scoring.py` with:
- `compute_unified_score(db, child_id)` — Compute 0-100 score from 4 signal sources
- `get_score_trend(db, child_id, days=30)` — Rolling trend (increasing/stable/decreasing)
- `get_score_breakdown(db, child_id)` — Per-signal-source breakdown with weights
- Weight table (from spec):
  - Young (5-9): AI=0.40, Social=0.20, Device=0.20, Location=0.20
  - Pre-teen (10-12): AI=0.30, Social=0.30, Device=0.20, Location=0.20
  - Teen (13-15): AI=0.25, Social=0.35, Device=0.20, Location=0.20

- [ ] **Step 4: Add scoring endpoints**

Add to `src/intelligence/router.py`:
- `GET /risk-score/{child_id}` — Unified score + confidence + trend
- `GET /risk-score/{child_id}/breakdown` — Per-source breakdown
- `GET /risk-score/{child_id}/history` — Score history (7-day, 30-day)

- [ ] **Step 5: Write E2E tests (≥15)**

Create `tests/e2e/test_unified_scoring.py` — full flow with test data from capture, social, device_agent modules.

- [ ] **Step 6: Run full intelligence test suite**

```bash
pytest tests/ -k "intelligence or scoring" -v
```

- [ ] **Step 7: Commit**

```bash
git add src/intelligence/scoring.py src/intelligence/__init__.py
git add src/intelligence/router.py src/intelligence/schemas.py
git add tests/unit/test_unified_scoring.py tests/e2e/test_unified_scoring.py
git commit -m "feat(P3-I2): unified risk scoring — weighted 4-source score, confidence, trends"
```

---

### Task 4 (P3-B1): Bundle Pricing + Feature Gating + Migration 049

**Files:**
- Create: `src/billing/feature_gate.py`
- Create: `src/billing/tiers.py`
- Modify: `src/billing/models.py` (add FeatureGate model)
- Modify: `src/billing/router.py` (add pricing/tier endpoints)
- Modify: `src/billing/schemas.py` (add tier schemas)
- Create: `alembic/versions/049_feature_gates.py`
- Modify: `alembic/env.py`
- Create: `tests/unit/test_feature_gating.py`
- Create: `tests/e2e/test_bundle_pricing.py`
- Create: `tests/security/test_feature_gating_security.py`

**Tests Required:** Unit ≥20, E2E ≥15, Security ≥10

- [ ] **Step 1: Add FeatureGate model**

Add to `src/billing/models.py`:
```python
class FeatureGate(Base, UUIDMixin, TimestampMixin):
    """Maps features to required subscription tiers."""

    __tablename__ = "feature_gates"

    feature_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    required_tier: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # free, family, family_plus, school, enterprise
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

- [ ] **Step 2: Create migration 049 with seed data**

Seed feature gates:
- `location_tracking` → `family_plus`
- `screen_time` → `family_plus`
- `creative_tools` → `family_plus`
- `api_access` → `school`
- `unified_dashboard` → `family`
- `real_time_alerts` → `family`
- `blocking` → `family`
- `reports` → `family`
- `social_access` → `family`

- [ ] **Step 3: Create feature gate dependency**

Create `src/billing/feature_gate.py`:
```python
"""Feature gating middleware — checks subscription tier before allowing access."""

from uuid import UUID

import structlog
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models import FeatureGate, Subscription
from src.database import get_db
from src.exceptions import ForbiddenError

logger = structlog.get_logger()

TIER_HIERARCHY = ["free", "family", "family_plus", "school", "enterprise"]


def check_feature_gate(feature_key: str):
    """FastAPI dependency that checks if the user's tier allows access to a feature."""

    async def _check(
        db: AsyncSession = Depends(get_db),
        group_id: UUID = None,  # resolved from auth context
    ):
        gate = await db.execute(
            select(FeatureGate).where(FeatureGate.feature_key == feature_key)
        )
        gate = gate.scalar_one_or_none()
        if gate is None:
            return  # No gate = allowed

        sub = await db.execute(
            select(Subscription).where(Subscription.group_id == group_id)
        )
        sub = sub.scalar_one_or_none()
        user_tier = sub.plan_type if sub else "free"

        if TIER_HIERARCHY.index(user_tier) < TIER_HIERARCHY.index(gate.required_tier):
            raise ForbiddenError(
                f"This feature requires {gate.required_tier} tier or higher. "
                f"Upgrade at /pricing"
            )

    return _check
```

- [ ] **Step 4: Create tier definitions**

Create `src/billing/tiers.py` with tier constants, pricing info, annual discount logic, and free tier weekly email cron helper.

- [ ] **Step 5: Write tests (unit ≥20, E2E ≥15, security ≥10)**

Test: tier hierarchy enforcement, feature gate blocking, upgrade path, free tier email summary, annual discount calculation, bypass prevention.

- [ ] **Step 6: Run tests and commit**

```bash
pytest tests/ -k "feature_gat or bundle_pricing" -v
git add src/billing/feature_gate.py src/billing/tiers.py src/billing/models.py
git add src/billing/router.py src/billing/schemas.py
git add alembic/versions/049_feature_gates.py alembic/env.py
git add tests/unit/test_feature_gating.py tests/e2e/test_bundle_pricing.py tests/security/test_feature_gating_security.py
git commit -m "feat(P3-B1): bundle pricing — Free/Family/Family+/School/Enterprise, feature gating"
```

---

### Task 5 (P3-B3a): API Platform — OAuth 2.0 + Models + Migration 048

**Files:**
- Create: `src/api_platform/__init__.py`
- Create: `src/api_platform/models.py`
- Create: `src/api_platform/schemas.py`
- Create: `src/api_platform/oauth.py`
- Create: `src/api_platform/service.py`
- Create: `src/api_platform/router.py`
- Modify: `src/main.py` (register api_platform router)
- Create: `alembic/versions/048_api_platform_tables.py`
- Modify: `alembic/env.py`
- Create: `tests/unit/test_api_platform.py`
- Create: `tests/e2e/test_api_platform.py`
- Create: `tests/security/test_api_platform_security.py`

**Tests Required:** Unit ≥20, E2E ≥15, Security ≥15

- [ ] **Step 1: Create models following device_agent pattern**

Create `src/api_platform/models.py` with: `OAuthClient`, `OAuthToken`, `APIKeyTier`, `WebhookEndpoint`, `WebhookDelivery`, `APIUsageRecord`. Follow the exact model pattern from `src/device_agent/models.py` (UUIDMixin, TimestampMixin, mapped_column).

- [ ] **Step 2: Create schemas following device_agent pattern**

Create `src/api_platform/schemas.py` with Pydantic schemas for each model (Create, Response, List). Follow `src/device_agent/schemas.py` pattern exactly.

- [ ] **Step 3: Create OAuth 2.0 provider**

Create `src/api_platform/oauth.py`:
- Authorization code flow with PKCE
- Scopes: `read:alerts`, `read:compliance`, `read:activity`, `write:webhooks`, `read:risk_scores`, `read:checkins`, `read:screen_time`
- Token lifetime: access 1h, refresh 30 days
- Consent screen data helper (plain language scope descriptions)

- [ ] **Step 4: Create service + router**

Create `src/api_platform/service.py` and `src/api_platform/router.py` following device_agent patterns:
- `POST /api/v1/platform/clients` — Register OAuth client (admin approved)
- `GET /api/v1/platform/clients` — List clients
- `POST /api/v1/platform/authorize` — OAuth authorization
- `POST /api/v1/platform/token` — Token exchange
- `GET /api/v1/platform/usage` — Usage metrics for a client

- [ ] **Step 5: Register router in main.py**

Add to `src/main.py`:
```python
from src.api_platform.router import router as api_platform_router
app.include_router(api_platform_router, prefix="/api/v1/platform", tags=["platform"])
```

- [ ] **Step 6: Create migration 048, update alembic/env.py**

- [ ] **Step 7: Write tests (unit ≥20, E2E ≥15, security ≥15)**

Security tests: OAuth token validation, scope enforcement, rate limiting per tier, token refresh, revocation, PKCE enforcement.

- [ ] **Step 8: Run tests and commit**

```bash
pytest tests/ -k "api_platform" -v
git add src/api_platform/ alembic/versions/048_api_platform_tables.py alembic/env.py src/main.py
git add tests/unit/test_api_platform.py tests/e2e/test_api_platform.py tests/security/test_api_platform_security.py
git commit -m "feat(P3-B3a): API platform — OAuth 2.0, client management, tier-based rate limiting"
```

---

### Task 6 (P3-B3b): API Webhooks + Delivery + Rate Limiting

**Files:**
- Create: `src/api_platform/webhooks.py`
- Modify: `src/api_platform/router.py` (add webhook endpoints)
- Modify: `src/api_platform/service.py` (add webhook/rate limit logic)
- Create: `tests/unit/test_api_webhooks.py`
- Create: `tests/e2e/test_api_webhooks.py`

**Tests Required:** Unit ≥10, E2E ≥5

- [ ] **Step 1: Implement webhook delivery**

Create `src/api_platform/webhooks.py`:
- `deliver_webhook(endpoint, event_type, payload)` — POST with HMAC-SHA256 signature in `X-Bhapi-Signature`
- Retry: 3 attempts with exponential backoff (10s, 60s, 300s)
- Log delivery in `WebhookDelivery` table
- Events: `alert.created`, `risk_score.changed`, `compliance.report_ready`, `checkin.event`, `screen_time.limit_reached`

- [ ] **Step 2: Add webhook management endpoints**

Add to router:
- `POST /api/v1/platform/webhooks` — Register webhook endpoint
- `GET /api/v1/platform/webhooks` — List endpoints for a client
- `DELETE /api/v1/platform/webhooks/{id}` — Remove endpoint
- `POST /api/v1/platform/webhooks/{id}/test` — Send test event
- `GET /api/v1/platform/webhooks/{id}/deliveries` — Delivery log

- [ ] **Step 3: Implement per-tier rate limiting**

Add rate limit middleware using existing `RateLimitMiddleware` pattern:
- School: 1,000 req/hr
- Partner: 5,000 req/hr
- Enterprise: 10,000 req/hr

- [ ] **Step 4: Write tests and commit**

```bash
pytest tests/ -k "webhook" -v
git add src/api_platform/webhooks.py src/api_platform/router.py src/api_platform/service.py
git add tests/unit/test_api_webhooks.py tests/e2e/test_api_webhooks.py
git commit -m "feat(P3-B3b): API webhooks — HMAC delivery, retry, rate limiting per tier"
```

---

### Task 7 (P3-F3a): Location Models + Migration 045

**Files:**
- Create: `src/location/__init__.py`
- Create: `src/location/models.py`
- Create: `src/location/schemas.py`
- Create: `alembic/versions/045_location_tables.py`
- Modify: `alembic/env.py`
- Create: `tests/unit/test_location_models.py`

**Tests Required:** Unit ≥10

- [ ] **Step 1: Create location models**

Create `src/location/models.py` with 7 models following `src/device_agent/models.py` pattern:
- `LocationRecord`: `id`, `member_id` (FK group_members), `group_id` (FK groups), `latitude` (Float, encrypted), `longitude` (Float, encrypted), `accuracy` (Float), `source` (gps/network/fused), `recorded_at` (DateTime tz). Index on `(member_id, recorded_at)`.
- `Geofence`: `id`, `group_id`, `member_id`, `name` (String 100), `latitude`, `longitude`, `radius_meters` (Float), `notify_on_enter` (Boolean), `notify_on_exit` (Boolean). Max 10 per child enforced in service.
- `GeofenceEvent`: `id`, `geofence_id` (FK), `member_id`, `event_type` (enter/exit), `recorded_at`.
- `SchoolCheckIn`: `id`, `member_id`, `group_id`, `geofence_id` (FK), `check_in_at`, `check_out_at`.
- `LocationSharingConsent`: `id`, `member_id`, `group_id` (school group), `granted_by` (parent user_id), `granted_at`, `revoked_at`.
- `LocationKillSwitch`: `id`, `member_id`, `activated_by` (parent user_id), `activated_at`, `deactivated_at`.
- `LocationAuditLog`: `id`, `member_id`, `accessor_id`, `data_type` (current/history/checkin), `accessed_at`.

- [ ] **Step 2: Create schemas**

Create `src/location/schemas.py` following `src/device_agent/schemas.py` pattern.

- [ ] **Step 3: Create migration 045, update alembic/env.py**

```bash
alembic revision --autogenerate -m "location_tables"
git status  # Verify migration file tracked
```

- [ ] **Step 4: Write model unit tests and commit**

```bash
pytest tests/unit/test_location_models.py -v
git add src/location/ alembic/versions/045_location_tables.py alembic/env.py
git add tests/unit/test_location_models.py
git commit -m "feat(P3-F3a): location models — 7 tables, privacy controls, audit logging"
```

---

### Task 8 (P3-F3b): Location Service + Router + Privacy Controls

**Files:**
- Create: `src/location/service.py`
- Create: `src/location/router.py`
- Modify: `src/location/__init__.py` (add public exports)
- Modify: `src/main.py` (register location router)
- Create: `tests/unit/test_location_service.py`
- Create: `tests/e2e/test_location.py`
- Create: `tests/security/test_location_security.py`

**Tests Required:** Unit ≥20, E2E ≥15, Security ≥15

- [ ] **Step 1: Implement location service**

Create `src/location/service.py` with:
- `report_location(db, member_id, group_id, lat, lng, accuracy, source)` — Store location (check kill switch first, encrypt lat/lng)
- `get_current_location(db, member_id, accessor_id)` — Latest location (audit log entry, decrypt)
- `get_location_history(db, member_id, accessor_id, start, end)` — 30-day max (paginated, audit log)
- `create_geofence(db, group_id, member_id, ...)` — Max 10 per child enforced
- `check_geofence(db, member_id, lat, lng)` — Haversine distance check, create GeofenceEvent if crossed
- `activate_kill_switch(db, member_id, parent_id)` — Immediately stop tracking
- `deactivate_kill_switch(db, member_id, parent_id)` — Re-enable tracking
- `delete_location_history(db, member_id)` — GDPR Article 17 erasure
- `purge_expired_locations(db)` — Cron: delete records older than 30 days

- [ ] **Step 2: Implement router**

Create `src/location/router.py` following `src/device_agent/router.py` pattern. All endpoints from spec Section 5.1. Register in `src/main.py` with prefix `/api/v1/location`.

- [ ] **Step 3: Add feature gating**

All location endpoints use `Depends(check_feature_gate("location_tracking"))` — returns 403 for non-Family+ users.

- [ ] **Step 4: Write tests (unit ≥20, E2E ≥15, security ≥15)**

Security tests must cover: kill switch prevents location reads, audit log records all access, school admin cannot see real-time location (only check-in), COPPA consent required for <13, encrypted storage verification, GDPR erasure completeness.

- [ ] **Step 5: Run tests and commit**

```bash
pytest tests/ -k "location" -v
git add src/location/service.py src/location/router.py src/location/__init__.py src/main.py
git add tests/unit/test_location_service.py tests/e2e/test_location.py tests/security/test_location_security.py
git commit -m "feat(P3-F3b): location service — tracking, geofencing, kill switch, audit log, GDPR erasure"
```

---

### Task 9 (P3-F3c): Location Mobile Screens (Safety App)

**Files:**
- Create: `mobile/apps/safety/app/(dashboard)/location.tsx`
- Create: `mobile/apps/safety/app/(dashboard)/geofences.tsx`
- Create: `mobile/apps/safety/app/(settings)/location-settings.tsx`
- Create: `mobile/packages/shared-ui/src/LocationMap.tsx`
- Create: `mobile/packages/shared-types/src/location.ts`
- Create: `mobile/apps/safety/__tests__/location.test.ts`

**Tests Required:** Component ≥15

- [ ] **Step 1: Create location TypeScript types**

Create `mobile/packages/shared-types/src/location.ts` with interfaces for LocationRecord, Geofence, GeofenceEvent, KillSwitch matching backend schemas.

- [ ] **Step 2: Create LocationMap shared component**

Create `mobile/packages/shared-ui/src/LocationMap.tsx` — MapView wrapper with child marker pin, geofence circles overlay, last-updated timestamp.

- [ ] **Step 3: Create location dashboard screen**

Create `mobile/apps/safety/app/(dashboard)/location.tsx` — Real-time child location on map, geofence list, location history (30-day), kill switch toggle.

- [ ] **Step 4: Create geofence management screen**

Create `mobile/apps/safety/app/(dashboard)/geofences.tsx` — Create/edit/delete geofences, map picker for center point, radius slider, enter/exit notification toggles.

- [ ] **Step 5: Create location settings screen**

Create `mobile/apps/safety/app/(settings)/location-settings.tsx` — Kill switch (prominent), school consent toggles, retention info, delete all history button.

- [ ] **Step 6: Write component tests (≥15) and commit**

```bash
cd mobile && npx turbo run test
git add mobile/apps/safety/ mobile/packages/shared-ui/src/LocationMap.tsx mobile/packages/shared-types/src/location.ts
git commit -m "feat(P3-F3c): location mobile screens — map, geofences, kill switch, settings"
```

---

### Task 10 (P3-F2a): Screen Time Models + Migration 046

**Files:**
- Create: `src/screen_time/__init__.py`
- Create: `src/screen_time/models.py`
- Create: `src/screen_time/schemas.py`
- Create: `alembic/versions/046_screen_time_tables.py`
- Modify: `alembic/env.py`
- Create: `tests/unit/test_screen_time_models.py`

**Tests Required:** Unit ≥10

- [ ] **Step 1: Create screen time models**

Create `src/screen_time/models.py`:
- `ScreenTimeRule`: `id`, `group_id`, `member_id`, `app_category` (social/games/education/entertainment/productivity/all), `daily_limit_minutes` (Integer), `age_tier_enforcement` (hard_block/warning_then_block/warning_only), `enabled` (Boolean).
- `ScreenTimeSchedule`: `id`, `rule_id` (FK), `day_type` (weekday/weekend/custom), `blocked_start` (Time), `blocked_end` (Time), `description`.
- `ExtensionRequest`: `id`, `member_id`, `rule_id` (FK), `requested_minutes` (Integer), `status` (pending/approved/denied/expired), `requested_at`, `responded_at`, `responded_by` (parent user_id).

- [ ] **Step 2: Create schemas, migration 046, commit**

Follow same pattern as Task 7.

```bash
git add src/screen_time/ alembic/versions/046_screen_time_tables.py alembic/env.py
git add tests/unit/test_screen_time_models.py
git commit -m "feat(P3-F2a): screen time models — rules, schedules, extension requests"
```

---

### Task 11 (P3-F2b): Screen Time Service + Router

**Files:**
- Create: `src/screen_time/service.py`
- Create: `src/screen_time/router.py`
- Modify: `src/screen_time/__init__.py`
- Modify: `src/main.py` (register router)
- Create: `tests/unit/test_screen_time_service.py`
- Create: `tests/e2e/test_screen_time.py`
- Create: `tests/security/test_screen_time_security.py`

**Tests Required:** Unit ≥15, E2E ≥10, Security ≥10

- [ ] **Step 1: Implement service**

Create `src/screen_time/service.py`:
- `create_rule(db, group_id, member_id, ...)` — Create screen time rule
- `get_rules(db, group_id, member_id)` — Get active rules for a child
- `evaluate_usage(db, member_id)` — Compare AppUsageRecord data against rules, return status
- `create_extension_request(db, member_id, rule_id, minutes)` — Child requests more time (max 2/day young, 5/day teen)
- `respond_to_extension(db, request_id, parent_id, approved)` — Approve/deny (auto-deny after 15 min)
- `get_weekly_report(db, member_id)` — Aggregate screen time data from ScreenTimeRecord

- [ ] **Step 2: Implement router with feature gating**

All endpoints use `Depends(check_feature_gate("screen_time"))`. Register in main.py as `/api/v1/screen-time`.

- [ ] **Step 3: Write tests and commit**

Age-tier enforcement tests: young=hard_block, preteen=warning_then_block, teen=warning_only. Extension request rate limiting.

```bash
git add src/screen_time/ src/main.py tests/
git commit -m "feat(P3-F2b): screen time service — rules, schedules, extension requests, age-tier enforcement"
```

---

### Task 12 (P3-F2c): Screen Time Mobile Screens

**Files:**
- Create: `mobile/apps/safety/app/(dashboard)/screen-time.tsx`
- Create: `mobile/apps/safety/app/(dashboard)/extension-request.tsx`
- Create: `mobile/apps/social/app/(settings)/screen-time.tsx`
- Create: `mobile/packages/shared-ui/src/ScreenTimeBar.tsx`
- Create: `mobile/packages/shared-types/src/screen-time.ts`
- Create: `mobile/apps/safety/__tests__/screen-time.test.ts`
- Create: `mobile/apps/social/__tests__/screen-time.test.ts`

**Tests Required:** Component ≥15

- [ ] **Step 1: Create types + shared component**

`ScreenTimeBar.tsx` — horizontal progress bar showing usage vs limit (green → amber → red).

- [ ] **Step 2: Create Safety app screens**

Screen time dashboard (rules, usage charts) and extension request screen (approve/deny with child's message).

- [ ] **Step 3: Create Social app screen**

Child-facing screen time view — current usage, remaining time, "Request More Time" button.

- [ ] **Step 4: Write tests and commit**

```bash
cd mobile && npx turbo run test
git add mobile/
git commit -m "feat(P3-F2c): screen time mobile — dashboard, extension requests, child status view"
```

---

## LAYER 2: FEATURES (Weeks 24-25)

### Task 13 (P3-F1a): Creative Tools Models + Migration 047

**Files:**
- Create: `src/creative/__init__.py`
- Create: `src/creative/models.py`
- Create: `src/creative/schemas.py`
- Create: `alembic/versions/047_creative_tables.py`
- Modify: `alembic/env.py`
- Create: `tests/unit/test_creative_models.py`

**Tests Required:** Unit ≥10

- [ ] **Step 1: Create creative models**

Create `src/creative/models.py`:
- `ArtGeneration`: `id`, `member_id`, `group_id`, `prompt` (Text), `sanitized_prompt` (Text), `model` (String — dalle3), `image_url` (String — R2 URL), `cost` (Float), `moderation_status` (pending/approved/rejected), `created_at`.
- `StoryTemplate`: `id`, `title`, `theme` (adventure/friendship/mystery/science/fantasy/humor), `content_template` (Text), `min_age_tier` (young/preteen/teen), `template_type` (fill_in_blank/free_write).
- `StoryCreation`: `id`, `member_id`, `template_id` (FK nullable), `content` (Text), `moderation_status`, `posted_to_feed` (Boolean).
- `StickerPack`: `id`, `name`, `category` (branded/seasonal/educational/user_created), `is_curated` (Boolean).
- `Sticker`: `id`, `pack_id` (FK), `member_id` (nullable — null for curated), `image_url` (String — R2 256x256), `moderation_status`.
- `DrawingAsset`: `id`, `member_id`, `group_id`, `image_url` (String — R2 PNG), `moderation_status`, `posted_to_feed` (Boolean).

- [ ] **Step 2: Create schemas, migration 047, commit**

Seed 20+ story templates across 6 themes. Seed 3 curated sticker packs with placeholder sticker entries.

```bash
git add src/creative/ alembic/versions/047_creative_tables.py alembic/env.py
git commit -m "feat(P3-F1a): creative models — AI art, stories, stickers, drawings + 20 templates"
```

---

### Task 14 (P3-F1b): Creative Service — AI Art, Stories, Stickers

**Files:**
- Create: `src/creative/service.py`
- Create: `src/creative/router.py`
- Modify: `src/creative/__init__.py`
- Modify: `src/main.py`
- Create: `tests/unit/test_creative_service.py`
- Create: `tests/e2e/test_creative.py`
- Create: `tests/security/test_creative_security.py`

**Tests Required:** Unit ≥20, E2E ≥10, Security ≥10

- [ ] **Step 1: Implement creative service**

Create `src/creative/service.py`:
- `generate_art(db, member_id, prompt)` — Keyword filter prompt → OpenAI Images API → R2 upload → moderation pipeline → store ArtGeneration. Rate limits: 10/day young, 25/day preteen, 50/day teen.
- `get_story_templates(db, age_tier)` — Filtered by min_age_tier
- `create_story(db, member_id, template_id, content)` — Moderate → store
- `save_drawing(db, member_id, image_data)` — Upload PNG to R2 → moderate → store
- `create_custom_sticker(db, member_id, image_data)` — Resize to 256x256 → R2 → moderate
- `get_sticker_packs(db)` — List curated + user packs

- [ ] **Step 2: Implement router with feature gating**

All endpoints use `Depends(check_feature_gate("creative_tools"))`. Register as `/api/v1/creative`.

- [ ] **Step 3: Write tests**

Test: prompt filtering (block "nude", "violence", etc.), rate limiting per age tier, moderation pipeline integration, cost tracking in billing, R2 upload mock.

- [ ] **Step 4: Commit**

```bash
git add src/creative/ src/main.py tests/
git commit -m "feat(P3-F1b): creative service — AI art generation, stories, stickers, drawings"
```

---

### Task 15 (P3-F1c): Creative Mobile Screens (Social App)

**Files:**
- Create: `mobile/apps/social/app/(creative)/art-studio.tsx`
- Create: `mobile/apps/social/app/(creative)/story-creator.tsx`
- Create: `mobile/apps/social/app/(creative)/drawing.tsx`
- Create: `mobile/apps/social/app/(creative)/stickers.tsx`
- Create: `mobile/apps/safety/app/(dashboard)/creative-review.tsx` (parent view)
- Create: `mobile/packages/shared-ui/src/CreativeToolbar.tsx`
- Create: `mobile/packages/shared-ui/src/StickerGrid.tsx`
- Create: `mobile/apps/social/__tests__/creative.test.ts`

**Tests Required:** Component ≥20

- [ ] **Step 1: Create shared components**

`CreativeToolbar.tsx` — brush color picker, size slider, eraser, undo/redo buttons.
`StickerGrid.tsx` — grid layout for sticker browsing with category tabs.

- [ ] **Step 2: Create art studio screen**

Prompt input, "Generate" button, gallery of past creations, "Post to Feed" action. Show moderation status (pending/approved).

- [ ] **Step 3: Create story creator screen**

Template browser with theme tabs. Fill-in-the-blank for young tier, free-write for preteen/teen. Preview + "Post to Feed" action.

- [ ] **Step 4: Create drawing canvas**

`react-native-skia` canvas with CreativeToolbar. Save as PNG. Post to feed or save to gallery.

- [ ] **Step 5: Create sticker picker**

Browse curated packs + personal library. "Create Sticker" button (opens drawing canvas at 256x256).

- [ ] **Step 6: Create parent creative review screen**

Safety app screen showing child's art, stories, drawings. Moderation status visible. Parent can flag content.

- [ ] **Step 7: Write tests and commit**

```bash
cd mobile && npx turbo run test
git add mobile/
git commit -m "feat(P3-F1c): creative mobile — art studio, story creator, drawing canvas, stickers"
```

---

### Task 16 (P3-F4): Unified Parent Dashboard

**Files:**
- Create: `portal/src/app/(dashboard)/unified/page.tsx`
- Create: `portal/src/hooks/use-unified-dashboard.ts`
- Create: `mobile/apps/safety/app/(dashboard)/unified.tsx`
- Create: `mobile/packages/shared-ui/src/RiskScoreCard.tsx`
- Create: `portal/src/app/(dashboard)/unified/__tests__/page.test.tsx`

**Tests Required:** Portal vitest ≥15, Component ≥20

- [ ] **Step 1: Create RiskScoreCard component**

`RiskScoreCard.tsx` — Displays 0-100 score, trend arrow (up/down/stable), confidence badge (low/medium/high), top contributing factors.

- [ ] **Step 2: Create portal unified dashboard page**

`portal/src/app/(dashboard)/unified/page.tsx`:
- Child selector dropdown
- Risk summary card (from `GET /api/v1/intelligence/risk-score/{child_id}`)
- AI activity summary (from portal BFF)
- Social activity summary (from social module)
- Screen time chart (from screen_time module)
- Location map snapshot (from location module)
- Action center: pending approvals, unread alerts
- Comparison view toggle for multi-child families

- [ ] **Step 3: Create React Query hook**

`portal/src/hooks/use-unified-dashboard.ts` — aggregates data from multiple endpoints with parallel fetching.

- [ ] **Step 4: Create Safety app unified screen**

Mobile version with same sections, adapted for mobile layout. Uses RiskScoreCard, ScreenTimeBar, LocationMap components.

- [ ] **Step 5: Write tests and commit**

```bash
cd portal && npx vitest run
cd ../mobile && npx turbo run test
git add portal/ mobile/
git commit -m "feat(P3-F4): unified parent dashboard — combined risk, AI, social, screen time, location"
```

---

### Task 17 (P3-I3): Alert Enrichment — Correlated Context

**Files:**
- Modify: `src/alerts/models.py` (add enriched_alert_id FK)
- Modify: `src/alerts/service.py` (enrichment on alert creation)
- Modify: `src/alerts/router.py` (return enrichment data)
- Create: `tests/unit/test_alert_enrichment.py`
- Create: `tests/e2e/test_alert_enrichment.py`

**Tests Required:** Unit ≥15, E2E ≥10

- [ ] **Step 1: Add enriched_alert_id to Alert model + migration**

Add nullable FK to `src/alerts/models.py`: `enriched_alert_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("enriched_alerts.id"), nullable=True)`. The `enriched_alerts` table exists from Task 2 (migration 050), but adding a column to the existing `alerts` table requires its own migration. Run:
```bash
alembic revision --autogenerate -m "add_enriched_alert_id_to_alerts"
git status  # Verify migration file tracked
```
**CRITICAL:** Adding a model column without a migration will crash production (CLAUDE.md rule).

- [ ] **Step 2: Modify alert creation flow**

In `src/alerts/service.py`: after creating an alert, check if intelligence correlation engine has a match. If so, create `EnrichedAlert` and link to the alert.

- [ ] **Step 3: Return enrichment in alert detail**

Modify `src/alerts/router.py`: alert detail endpoint includes `correlation_context` and `contributing_signals` when `enriched_alert_id` is present.

- [ ] **Step 4: Write tests and commit**

Test: alert with enrichment, alert without enrichment, enrichment context string format, contributing signals JSON structure.

```bash
git add src/alerts/ tests/
git commit -m "feat(P3-I3): alert enrichment — correlated cross-product context on alerts"
```

---

### Task 18 (P3-I4): Behavioral Anomaly Correlation

**Files:**
- Create: `src/intelligence/anomaly.py`
- Modify: `src/intelligence/__init__.py`
- Modify: `src/intelligence/router.py`
- Create: `tests/unit/test_anomaly_detection.py`
- Create: `tests/e2e/test_anomaly_detection.py`

**Tests Required:** Unit ≥20, E2E ≥15

- [ ] **Step 1: Implement anomaly detection**

Create `src/intelligence/anomaly.py`:
- `compute_multi_signal_deviation(db, child_id)` — Read BehavioralBaseline, compute per-signal-type means and stddev, detect deviations >2σ
- `detect_evasion(db, child_id)` — Monitored AI usage drops but screen time stays high
- `detect_cross_signal_anomalies(db, child_id)` — Social withdrawal + AI spike, location change + new contacts
- `run_anomaly_scan(db, child_id)` — Run all detectors, create enriched alerts for matches

- [ ] **Step 2: Add anomaly endpoints**

- `GET /api/v1/intelligence/anomalies/{child_id}` — List detected anomalies
- `POST /api/v1/intelligence/anomalies/scan` — Trigger scan for a child (or all children via cron)

- [ ] **Step 3: Write tests and commit**

Test: baseline deviation >2σ triggers alert, evasion detection logic, cross-signal patterns, no false positive when within normal range.

```bash
git add src/intelligence/anomaly.py src/intelligence/__init__.py src/intelligence/router.py
git add tests/unit/test_anomaly_detection.py tests/e2e/test_anomaly_detection.py
git commit -m "feat(P3-I4): behavioral anomaly correlation — evasion detection, cross-signal patterns"
```

---

### Task 19 (P3-B3c): Developer Portal Pages + API Docs

**Files:**
- Create: `portal/src/app/(developers)/page.tsx`
- Create: `portal/src/app/(developers)/dashboard/page.tsx`
- Create: `portal/src/app/(developers)/webhooks/page.tsx`
- Create: `portal/src/app/(developers)/docs/page.tsx`
- Create: `portal/src/hooks/use-developer-portal.ts`
- Create: `portal/src/app/(developers)/__tests__/page.test.tsx`

**Tests Required:** Portal vitest ≥10

- [ ] **Step 1: Create developer landing page**

`/developers` — API overview, partnership tiers, "Apply for Access" form, link to docs.

- [ ] **Step 2: Create dashboard page**

`/developers/dashboard` — API key display (masked), usage chart (calls/day), current tier, upgrade CTA.

- [ ] **Step 3: Create webhooks page**

`/developers/webhooks` — Endpoint management (add URL, select events, view delivery log), test event sender.

- [ ] **Step 4: Create docs page**

`/developers/docs` — Embedded Swagger UI iframe pointing to `/api/docs`. Authentication guide, code samples.

- [ ] **Step 5: Write tests and commit**

```bash
cd portal && npx vitest run
git add portal/
git commit -m "feat(P3-B3c): developer portal — API dashboard, webhook management, interactive docs"
```

---

### Task 20 (P3-B2): Channel Partnership Package

**Files:**
- Create: `portal/src/app/(marketing)/partners/page.tsx`
- Create: `docs/partnerships/partner-onboarding.md`
- Create: `docs/partnerships/roi-calculator.md`
- Create: `docs/partnerships/deployment-guide.md`

**Tests Required:** None (documentation task)

- [ ] **Step 1: Create partner landing page**

`/partners` — Partnership program overview, commission structure (15% recurring), compliance package, CTA.

- [ ] **Step 2: Write partner documentation**

- Partner onboarding guide: reseller/referral model, commission, support
- ROI calculator template: input (student count, current cost), output (Bhapi cost, savings)
- Deployment guide: Chrome extension via Google Admin Console, SSO setup, SIS sync

- [ ] **Step 3: Commit**

```bash
git add portal/src/app/(marketing)/partners/ docs/partnerships/
git commit -m "feat(P3-B2): channel partnership package — onboarding, ROI calculator, deployment guide"
```

---

### Task 21 (P3-B4): SOC 2 Audit Initiation + Migration 051

**Files:**
- Create: `src/compliance/soc2.py`
- Modify: `src/compliance/models.py` (add audit models)
- Modify: `src/compliance/router.py` (add soc2 endpoints)
- Create: `alembic/versions/051_soc2_evidence.py`
- Modify: `alembic/env.py`
- Create: `docs/compliance/soc2-policies/`
- Create: `tests/unit/test_soc2.py`
- Create: `tests/e2e/test_soc2.py`

**Tests Required:** Unit ≥10, E2E ≥5

- [ ] **Step 1: Create SOC 2 models**

Add to `src/compliance/models.py`:
- `AuditPolicy`: `id`, `name`, `category` (security/availability/confidentiality/privacy), `description`, `version`, `effective_date`.
- `EvidenceCollection`: `id`, `policy_id` (FK), `evidence_type` (deployment_log/access_control/encryption/backup/incident), `collected_at`, `data` (JSONType).
- `ComplianceControl`: `id`, `control_id` (String — e.g., "CC6.1"), `description`, `status` (implemented/partial/planned), `evidence_ids` (JSON list).

- [ ] **Step 2: Create evidence collection service**

Create `src/compliance/soc2.py`:
- `collect_evidence(db)` — Auto-collect: deployment logs, access control lists, encryption status
- `get_readiness_report(db)` — Map controls to Trust Services Criteria
- `get_policies(db)` — List all policies

- [ ] **Step 3: Write policy documents**

Create `docs/compliance/soc2-policies/` with formalized versions of existing security docs.

- [ ] **Step 4: Create migration 051, write tests, commit**

```bash
git add src/compliance/soc2.py src/compliance/models.py src/compliance/router.py
git add alembic/versions/051_soc2_evidence.py alembic/env.py docs/compliance/soc2-policies/
git add tests/unit/test_soc2.py tests/e2e/test_soc2.py
git commit -m "feat(P3-B4): SOC 2 audit initiation — evidence collection, control mapping, policy docs"
```

---

### Task 22 (P3-F3d): School Check-In + Location Consent

**Files:**
- Modify: `src/location/service.py` (add school check-in functions)
- Modify: `src/location/router.py` (add school endpoints)
- Create: `tests/e2e/test_school_checkin.py`
- Create: `tests/security/test_school_location_security.py`

**Tests Required:** E2E ≥10, Security ≥10

- [ ] **Step 1: Implement school check-in service**

Add to `src/location/service.py`:
- `create_school_consent(db, member_id, school_group_id, parent_id)` — Parent opts in
- `revoke_school_consent(db, member_id, school_group_id, parent_id)` — Parent opts out
- `record_check_in(db, member_id, geofence_id)` — Only if consent active
- `record_check_out(db, member_id, geofence_id)` — Match to latest check-in
- `get_school_attendance(db, school_group_id, date)` — School admin: list check-in/check-out times (no location data)

- [ ] **Step 2: Add school endpoints**

- `POST /api/v1/location/school-consent` — Parent grants consent
- `DELETE /api/v1/location/school-consent/{id}` — Parent revokes
- `GET /api/v1/location/school/{group_id}/attendance` — School admin view (check-in times only, no coordinates)

- [ ] **Step 3: Write security tests**

Verify: school admin cannot see real-time location, school admin cannot see location history, school admin only sees check-in/check-out timestamps, consent required before check-in recorded, parent can revoke at any time.

- [ ] **Step 4: Commit**

```bash
git add src/location/ tests/
git commit -m "feat(P3-F3d): school check-in — parent consent, attendance records, privacy enforcement"
```

---

## LAYER 3: LAUNCH (Week 26)

### Task 23 (P3-L4): Landing Page Redesign

**Files:**
- Modify: `portal/src/app/page.tsx` (landing page)
- Create: `portal/src/app/(marketing)/families/page.tsx`
- Create: `portal/src/app/(marketing)/schools/page.tsx`
- Create: `portal/src/app/(marketing)/pricing/page.tsx`
- Create: `portal/src/hooks/use-social-proof.ts`
- Create: `portal/src/app/(marketing)/__tests__/page.test.tsx`

**Tests Required:** Portal vitest ≥10

- [ ] **Step 1: Redesign landing page hero**

Update `portal/src/app/page.tsx`:
- "Safe AI. Safe Social. One Platform." headline
- App Store + Google Play badges
- "Start Free" and "Book a Demo" CTAs
- Audience tabs: Families / Schools / Partners

- [ ] **Step 2: Create audience-specific pages**

`/families` — Family features, Family/Family+ pricing, testimonials.
`/schools` — School features, compliance badges, per-seat pricing.
`/pricing` — Full tier comparison matrix (Free/Family/Family+/School/Enterprise).

- [ ] **Step 3: Create social proof hook**

`use-social-proof.ts` — fetches school count and family count from lightweight API endpoint (cached 1h).

- [ ] **Step 4: Write tests and commit**

```bash
cd portal && npx vitest run
git add portal/
git commit -m "feat(P3-L4): landing page — unified marketing, audience tabs, pricing, social proof"
```

---

### Task 24 (P3-L5): Cross-App Onboarding — 3 Paths

**Files:**
- Modify: `mobile/apps/safety/app/(auth)/` (parent-initiated flow)
- Modify: `mobile/apps/social/app/(auth)/` (child-initiated flow)
- Create: `portal/src/app/(auth)/approve/page.tsx` (web approval fallback)
- Create: `mobile/packages/shared-types/src/onboarding.ts`
- Modify: `src/auth/service.py` (invite code generation, approval endpoints)
- Modify: `src/auth/router.py` (add onboarding endpoints)
- Create: `tests/e2e/test_cross_app_onboarding.py`
- Create: `tests/security/test_onboarding_security.py`

**Tests Required:** Unit ≥15, E2E ≥10, Security ≥10, Component ≥15

- [ ] **Step 1: Add backend onboarding endpoints**

Add to `src/auth/router.py`:
- `POST /api/v1/auth/invite-child` — Parent generates invite code for child
- `POST /api/v1/auth/accept-invite` — Child enters invite code → linked to family group
- `POST /api/v1/auth/request-parent-approval` — Child submits parent email → approval link sent
- `POST /api/v1/auth/approve-child` — Parent approves via token (app or web)

- [ ] **Step 2: Implement invite code logic**

In `src/auth/service.py`:
- `generate_invite_code(db, group_id, parent_id)` — 6-character alphanumeric, expires 48h
- `redeem_invite_code(db, code, child_user_id)` — Link child to group, assign age tier
- `send_parent_approval(db, child_id, parent_email)` — Email + optional SMS with approval link
- `approve_child_account(db, token, parent_id)` — Verify token, link child, create group if needed

- [ ] **Step 3: Update mobile auth flows**

Safety app: "Add Child" → enter child info → generate invite code → show code + share link.
Social app: "I have an invite code" → enter code → done. Or: "I need parent approval" → enter parent email → waiting screen.

- [ ] **Step 4: Create web approval page**

`portal/src/app/(auth)/approve/page.tsx` — For parents without Safety app. Token in URL query. Shows child info, approve/deny buttons, "Download Safety App" prompt.

- [ ] **Step 5: Deep links**

Configure `bhapi://invite/{code}` and `bhapi://approve/{token}` in both apps' Expo Linking config.

- [ ] **Step 6: Write tests and commit**

E2E: all 3 paths end-to-end. Security: expired codes rejected, approval tokens single-use, child cannot self-approve.

```bash
git add src/auth/ mobile/ portal/ tests/
git commit -m "feat(P3-L5): cross-app onboarding — parent-initiated, child-initiated, school-initiated"
```

---

### Task 25 (P3-L3): App Store Optimization — 6 Languages

**Files:**
- Create: `mobile/store-assets/screenshots/`
- Create: `mobile/store-assets/descriptions/`
- Modify: `mobile/apps/safety/app.json`
- Modify: `mobile/apps/social/app.json`

**Tests Required:** None (operational task)

- [ ] **Step 1: Generate screenshots**

Use Maestro E2E flows to capture screenshots on multiple device sizes. 6 languages × 2 apps × key screens.

- [ ] **Step 2: Write store descriptions**

Long + short descriptions for each app in 6 languages (EN, FR, ES, DE, PT-BR, IT). Keywords optimized per market.

- [ ] **Step 3: Update app.json configs**

Ensure privacy nutrition labels, background location justification, COPPA declarations are complete.

- [ ] **Step 4: Commit**

```bash
git add mobile/store-assets/ mobile/apps/
git commit -m "feat(P3-L3): App Store optimization — screenshots, descriptions, keywords in 6 languages"
```

---

### Task 26 (P3-L1): Bhapi Social — Public Release

**Files:**
- Modify: `mobile/apps/social/eas.json` (production profile)
- Modify: `mobile/apps/social/app.json` (version bump)

**Tests Required:** Maestro E2E ≥15

- [ ] **Step 1: Run full mobile test suite**

```bash
cd mobile && npx turbo run test
```
All must pass.

- [ ] **Step 2: Run Maestro E2E tests**

```bash
cd mobile && maestro test maestro/social-*.yaml
```

- [ ] **Step 3: Build production binaries**

```bash
eas build --platform all --profile production
```

- [ ] **Step 4: Submit to App Store + Google Play**

Submit via EAS Submit. Include background location justification, COPPA declaration, content moderation description. Use phased rollout on Google Play (10% → 25% → 50% → 100%).

- [ ] **Step 5: Commit**

```bash
git add mobile/apps/social/
git commit -m "feat(P3-L1): Bhapi Social public release — App Store + Google Play submission"
```

---

### Task 27 (P3-L2): Bhapi Safety — Public Release

**Files:**
- Modify: `mobile/apps/safety/eas.json` (production profile)
- Modify: `mobile/apps/safety/app.json` (version bump)

**Tests Required:** Maestro E2E ≥15

- [ ] **Step 1: Run full test suite**

Same as Task 26 but for Safety app.

- [ ] **Step 2: Run Maestro E2E tests**

```bash
cd mobile && maestro test maestro/safety-*.yaml
```

- [ ] **Step 3: Submit Apple background location form**

Detailed justification: "Bhapi Safety tracks children's location for parental safety monitoring. Background location is used for geofence notifications when children arrive at or leave designated safe zones (home, school). Location data is encrypted, retained for 30 days, and parents can disable tracking via a kill switch at any time."

- [ ] **Step 4: Submit Google background location access form**

- [ ] **Step 5: Build + submit**

```bash
eas build --platform all --profile production
```

- [ ] **Step 6: Commit**

```bash
git add mobile/apps/safety/
git commit -m "feat(P3-L2): Bhapi Safety public release — App Store + Google Play submission"
```

---

## Post-Implementation

### Update CLAUDE.md

After all tasks complete, update `CLAUDE.md`:
- Version → 4.0.0
- Add new modules: `location/`, `screen_time/`, `creative/`, `api_platform/`
- Update module table with new routes and prefixes
- Update migration count (045-051)
- Update test count
- Add Phase 3 backend modules table
- Add new environment variables (OPENAI_API_KEY for creative tools)

### Update CHANGELOG.md

Add Phase 3 release notes with all 17 deliverables.

### Final Test Run

```bash
pytest tests/ -v                        # Backend
cd portal && npx vitest run              # Frontend
cd portal && npx tsc --noEmit            # Type check
cd ../mobile && npx turbo run test       # Mobile
cd ../extension && npx jest              # Extension
```

**Target:** ≥5,623 total tests passing.

---

## Exit Criteria Checklist

- [ ] Both apps publicly available on iOS App Store + Google Play Store
- [ ] ≥500 family signups
- [ ] ≥10 school deployments active
- [ ] App Store rating ≥4.0 (both apps)
- [ ] Bundle conversion ≥10% free → paid
- [ ] Cross-product intelligence engine live, generating correlated alerts
- [ ] Screen time + location tracking live for Family+ tier
- [ ] Location kill switch functional, audit log recording all access
- [ ] School check-in/check-out live with parent opt-in consent
- [ ] Creative tools live (AI art + stories + drawing + stickers) with moderation
- [ ] Public API beta live with ≥3 approved partner integrations
- [ ] Channel partnership package complete
- [ ] SOC 2 Type II audit engagement signed
- [ ] Landing page live with audience-specific messaging
- [ ] Cross-app onboarding functional (all 3 paths)
- [ ] Free tier operational with weekly email summary + upgrade CTA
- [ ] Feature gating enforced on all tier-restricted endpoints
- [ ] **Test count: ≥5,623 total**
- [ ] **All Alembic migrations (045-051) committed and pushed**
- [ ] **0 open critical/high security findings**
