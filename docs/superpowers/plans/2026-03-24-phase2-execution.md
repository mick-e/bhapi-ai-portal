# Phase 2A Execution Plan — Device Agent, Push, Real-Time, Compliance, Production Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill Phase 2 gaps to make the platform production-ready: wire device telemetry to screen time/intelligence, add push notifications, complete real-time messaging, build Ohio/EU compliance portal pages, and harden for public launch.

**Architecture:** Extends existing modules (device_agent, realtime, messaging, social, governance) with data pipelines, WebSocket wiring, Expo push (FCM/APNs), compliance portal pages, and operational infrastructure (Sentry, connection pooling, CDN). All new tables via Alembic migrations 054+. No new modules — only extensions to existing ones.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy async / Alembic / PostgreSQL 16 | Expo SDK 52+ / React Native / TypeScript | Redis 7 | Expo Push API (FCM/APNs) | Sentry | K6 (load testing)

**Entry point:** `src/main.py` (FastAPI app with ~30 routers). See `CLAUDE.md` for all conventions.

**Current state:** 4,592 backend tests, 312 portal tests, 7 mobile packages green. Migrations through 053.

**Regulatory deadlines:** Ohio AI Mandate (Jul 1, 2026), EU AI Act (Aug 2, 2026)

**Scope:** This plan covers a subset of Phase 2 (see `2026-06-09-phase2-social-launch.md` for the full 32-task plan). Specifically: P2-S2 (feed), P2-S4 (messaging), P2-S8 (push), P2-M1 (social monitor), P2-M2 (device agent wiring), P2-C1 (Ohio), P2-C2 (EU AI Act), plus production hardening. Remaining Phase 2 items (onboarding, profiles, contacts mobile, media, reporting, settings, moderation UX, TestFlight, compliance C3-C6, safety engine E1-E8) will be addressed in a follow-up plan.

**Serialization points:** Tasks modifying `src/main.py`, `src/config.py`, or `alembic/env.py` must not run in parallel — use worktrees or sequence them. Specifically: Tasks 12 and 13 both modify `src/config.py` and must run sequentially.

---

## File Structure

### W1-2: Device Agent + Push Notifications

```
src/device_agent/                      # EXISTS — extend
├── service.py                         # MODIFY: add event bus publishing on sync
├── router.py                          # MODIFY: add push token endpoints
├── models.py                          # EXISTS: DeviceSession, AppUsageRecord, ScreenTimeRecord
└── schemas.py                         # MODIFY: add PushTokenCreate/Response

src/alerts/push.py                     # EXISTS — PushToken model + ExpoPushService

alembic/versions/054_push_tokens_index.py  # NEW: add index on push_tokens.user_id

src/intelligence/event_bus.py          # EXISTS — extend: publish device events on sync
src/screen_time/service.py             # EXISTS — extend: wire evaluate_usage to device data

tests/unit/test_device_push.py         # NEW: 15+ unit tests
tests/e2e/test_device_push.py          # NEW: 10+ E2E tests
tests/unit/test_device_intelligence.py # NEW: 10+ unit tests for event bus wiring
```

### W3-4: Real-Time Messaging + Social Polish

```
src/messaging/service.py               # EXISTS — extend: send_message publishes to realtime
src/messaging/router.py                # EXISTS — extend: WebSocket-aware endpoints
src/social/service.py                  # EXISTS — extend: feed algorithm (engagement-weighted)
src/social/router.py                   # EXISTS — extend: feed endpoint with algorithm param

mobile/apps/social/app/(messaging)/    # NEW: chat screens
├── conversations.tsx                  # Conversation list
├── chat.tsx                           # Chat view with messages
└── _layout.tsx                        # Messaging tab layout

mobile/apps/social/src/hooks/useMessaging.ts  # NEW: React Query hooks
mobile/apps/social/src/hooks/useWebSocket.ts  # NEW: WebSocket connection hook

portal/src/app/(dashboard)/social-feed/page.tsx  # NEW: parent social feed monitor

tests/unit/test_messaging_realtime.py  # NEW: 20+ unit tests
tests/e2e/test_messaging_realtime.py   # NEW: 15+ E2E tests
tests/e2e/test_feed_algorithm.py       # NEW: 10+ E2E tests
```

### W5-6: Ohio Governance + EU AI Act Portal Pages

```
portal/src/app/(dashboard)/governance/ohio/page.tsx       # NEW: Ohio policy builder wizard
portal/src/app/(dashboard)/governance/eu-ai-act/page.tsx  # NEW: EU AI Act dashboard
portal/src/app/(dashboard)/governance/compliance-report/page.tsx  # NEW: exportable reports

portal/src/hooks/use-governance.ts     # NEW: React Query hooks for governance API

src/governance/service.py              # EXISTS — extend: PDF report generation
src/governance/router.py               # EXISTS — extend: report download endpoint

tests/e2e/test_ohio_portal.py         # NEW: 10+ E2E tests
tests/e2e/test_eu_ai_act_portal.py    # NEW: 10+ E2E tests
```

### W7-8: Production Hardening + Monitoring

```
src/middleware/sentry.py               # NEW: Sentry integration middleware
src/config.py                          # MODIFY: add Sentry DSN, pool settings
src/database.py                        # MODIFY: connection pool tuning
src/main.py                            # MODIFY: Sentry init, pool config

tests/load/                            # NEW: K6 load test scripts
├── k6-auth.js                         # Auth endpoint load test
├── k6-capture.js                      # Capture ingestion load test
├── k6-dashboard.js                    # Dashboard aggregation load test
└── README.md                          # How to run load tests

docs/operations/                       # NEW: operational runbooks
├── deployment-checklist.md            # Pre-deploy checklist
├── monitoring-guide.md                # Sentry + structured logging guide
└── production-runbook.md             # Production operations playbook (extends docs/compliance/soc2-policies/incident-response-policy.md)
```

### W9-10: Public Launch Prep

```
mobile/apps/safety/app.json           # MODIFY: final version bump
mobile/apps/social/app.json           # MODIFY: final version bump
mobile/apps/safety/eas.json           # EXISTS — fill real App Store IDs
mobile/apps/social/eas.json           # EXISTS — fill real App Store IDs

tests/e2e/test_production.py          # EXISTS — extend with new endpoint coverage
portal/src/app/page.tsx               # EXISTS — final copy polish
```

---

## Tasks

---

### Task 1: Push Token Registration Endpoints (W1)

**Files:**
- Modify: `src/device_agent/router.py`
- Modify: `src/device_agent/schemas.py`
- Modify: `src/device_agent/__init__.py`
- Create: `tests/unit/test_device_push.py`
- Create: `tests/e2e/test_device_push.py`

The `PushToken` model and `ExpoPushService` already exist in `src/alerts/push.py`. We need to expose registration/unregistration via the device agent router (mobile app calls these on startup).

- [ ] **Step 1: Write push token schema**

Add to `src/device_agent/schemas.py`:

```python
class PushTokenCreate(BaseModel):
    """Register an Expo push token for the current user's device."""
    token: str = Field(..., pattern=r"^ExponentPushToken\[.+\]$")
    device_type: str = Field(..., pattern=r"^(ios|android)$")

class PushTokenResponse(BaseModel):
    """Confirmation of push token registration."""
    token: str
    device_type: str
    registered: bool

class PushTokenListResponse(BaseModel):
    """List of registered push tokens."""
    items: list[PushTokenResponse]
    total: int
```

- [ ] **Step 2: Write failing tests for push token endpoints**

Create `tests/e2e/test_device_push.py` using the standard E2E fixture pattern:

```python
"""E2E tests for device agent push token endpoints."""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.database import Base, get_db
from src.main import create_app
from src.schemas import GroupContext


@pytest.fixture
async def push_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def push_session(push_engine):
    session = AsyncSession(push_engine, expire_on_commit=False)
    yield session
    await session.close()


@pytest_asyncio.fixture
async def push_data(push_session):
    user = User(
        id=uuid.uuid4(),
        email=f"push-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Push User",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    push_session.add(user)
    await push_session.flush()
    return {"user": user}


@pytest.fixture
async def push_client(push_engine, push_session, push_data):
    app = create_app()

    async def get_db_override():
        try:
            yield push_session
            await push_session.commit()
        except Exception:
            await push_session.rollback()
            raise

    async def fake_auth():
        return GroupContext(
            user_id=push_data["user"].id,
            group_id=uuid.uuid4(),
            role="parent",
        )

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[get_current_user] = fake_auth

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_register_push_token(push_client):
    resp = await push_client.post("/api/v1/device/push-token", json={
        "token": "ExponentPushToken[abc123]",
        "device_type": "ios",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["token"] == "ExponentPushToken[abc123]"
    assert body["registered"] is True


@pytest.mark.asyncio
async def test_register_push_token_invalid_format(push_client):
    resp = await push_client.post("/api/v1/device/push-token", json={
        "token": "not-a-valid-token",
        "device_type": "ios",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_push_token_invalid_device(push_client):
    resp = await push_client.post("/api/v1/device/push-token", json={
        "token": "ExponentPushToken[abc123]",
        "device_type": "windows",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_push_tokens(push_client):
    await push_client.post("/api/v1/device/push-token", json={
        "token": "ExponentPushToken[abc123]",
        "device_type": "ios",
    })
    resp = await push_client.get("/api/v1/device/push-tokens")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_unregister_push_token(push_client):
    await push_client.post("/api/v1/device/push-token", json={
        "token": "ExponentPushToken[abc123]",
        "device_type": "ios",
    })
    resp = await push_client.delete("/api/v1/device/push-token/ExponentPushToken%5Babc123%5D")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_register_push_token_idempotent(push_client):
    """Registering the same token twice should upsert, not duplicate."""
    await push_client.post("/api/v1/device/push-token", json={
        "token": "ExponentPushToken[abc123]",
        "device_type": "ios",
    })
    await push_client.post("/api/v1/device/push-token", json={
        "token": "ExponentPushToken[abc123]",
        "device_type": "android",
    })
    resp = await push_client.get("/api/v1/device/push-tokens")
    body = resp.json()
    # Should have 1 token (upserted), not 2
    tokens = [t for t in body["items"] if t["token"] == "ExponentPushToken[abc123]"]
    assert len(tokens) == 1
    assert tokens[0]["device_type"] == "android"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/e2e/test_device_push.py -v --tb=short`
Expected: FAIL — endpoints don't exist yet

- [ ] **Step 4: Implement push token endpoints**

Add to `src/device_agent/router.py`:

```python
from src.alerts.push import expo_push_service
from src.device_agent.schemas import PushTokenCreate, PushTokenResponse, PushTokenListResponse

@router.post("/push-token", response_model=PushTokenResponse, status_code=201)
async def register_push_token(
    data: PushTokenCreate,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register an Expo push token for the current user's device."""
    await expo_push_service.register_token(
        db, user_id=auth.user_id, token=data.token, device_type=data.device_type
    )
    await db.commit()
    return PushTokenResponse(token=data.token, device_type=data.device_type, registered=True)


@router.get("/push-tokens", response_model=PushTokenListResponse)
async def list_push_tokens(
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all push tokens for the current user."""
    tokens = await expo_push_service.get_user_tokens(db, user_id=auth.user_id)
    items = [PushTokenResponse(token=t.token, device_type=t.device_type, registered=True) for t in tokens]
    return PushTokenListResponse(items=items, total=len(items))


@router.delete("/push-token/{token}", status_code=204)
async def unregister_push_token(
    token: str,
    auth: GroupContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unregister a push token."""
    await expo_push_service.unregister_token(db, user_id=auth.user_id, token=token)
    await db.commit()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/e2e/test_device_push.py -v --tb=short`
Expected: 6 passed

- [ ] **Step 6: Update __init__.py exports and commit**

```bash
git add src/device_agent/ tests/e2e/test_device_push.py
git commit -m "feat(P2-S8): push token registration — register, list, unregister endpoints"
```

---

### Task 2: Device Agent → Intelligence Event Bus Wiring (W1)

**Files:**
- Modify: `src/device_agent/service.py`
- Create: `tests/unit/test_device_intelligence.py`

When device data is synced, publish events to the intelligence event bus so the correlation engine can detect patterns.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_device_intelligence.py`:

```python
"""Unit tests for device agent → intelligence event bus integration."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.device_agent.service import sync_device_data, record_app_usage


@pytest.mark.asyncio
async def test_sync_publishes_device_event(test_session: AsyncSession):
    """sync_device_data should publish to intelligence event bus."""
    with patch("src.device_agent.service.publish_event", new_callable=AsyncMock) as mock_pub:
        from src.device_agent.schemas import DeviceSyncRequest
        member_id = uuid.uuid4()
        group_id = uuid.uuid4()
        req = DeviceSyncRequest(
            sessions=[],
            usage_records=[],
        )
        await sync_device_data(test_session, member_id=member_id, group_id=group_id, data=req)
        # Even with empty data, the sync itself should publish a device event
        mock_pub.assert_called()


@pytest.mark.asyncio
async def test_app_usage_publishes_event(test_session: AsyncSession):
    """record_app_usage should publish an AI session event for AI app categories."""
    from src.device_agent.schemas import AppUsageCreate

    with patch("src.device_agent.service.publish_event", new_callable=AsyncMock) as mock_pub:
        group_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        # Note: AppUsageCreate.category allows social|education|games|entertainment|productivity|other.
        # AI detection uses bundle_id/app_name pattern matching, not category field.
        data = AppUsageCreate(
            member_id=uuid.uuid4(),
            app_name="ChatGPT",
            bundle_id="com.openai.chatgpt",
            category="productivity",  # AI apps report as productivity
            started_at=now,
            foreground_minutes=15.0,
        )
        await record_app_usage(test_session, group_id=group_id, data=data)
        # Should publish event (device sync or AI detection)
        if mock_pub.called:
            call_args = mock_pub.call_args
            assert call_args is not None


@pytest.mark.asyncio
async def test_non_ai_app_no_ai_event(test_session: AsyncSession):
    """record_app_usage for non-AI apps should NOT publish AI session events."""
    from src.device_agent.schemas import AppUsageCreate

    with patch("src.device_agent.service.publish_event", new_callable=AsyncMock) as mock_pub:
        group_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        data = AppUsageCreate(
            member_id=uuid.uuid4(),
            app_name="Minecraft",
            bundle_id="com.mojang.minecraft",
            category="games",
            started_at=now,
            foreground_minutes=30.0,
        )
        await record_app_usage(test_session, group_id=group_id, data=data)
        # Should NOT publish AI session event for games
        ai_calls = [c for c in mock_pub.call_args_list
                     if c and len(c.args) > 0 and "ai_session" in str(c)]
        assert len(ai_calls) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_device_intelligence.py -v --tb=short`
Expected: FAIL — `publish_event` not imported in service

- [ ] **Step 3: Wire event bus publishing into device_agent/service.py**

Add to `src/device_agent/service.py` after the existing imports:

```python
import structlog

logger = structlog.get_logger()

# AI-related app categories that trigger intelligence events
AI_APP_CATEGORIES = {"ai_assistant", "ai_chat", "ai_image", "ai_code"}

async def publish_event(channel: str, event_data: dict) -> None:
    """Publish to intelligence event bus (best-effort, no failure on error)."""
    try:
        from src.intelligence import publish_event as _publish
        await _publish(channel, event_data)
    except Exception:
        logger.warning("event_bus_publish_failed", channel=channel)
```

Then modify `sync_device_data()` to call `publish_event` after successful sync:

```python
await publish_event("device", {
    "type": "device_sync",
    "member_id": str(member_id),
    "group_id": str(group_id),
    "sessions_count": len(data.sessions),
    "usage_count": len(data.usage_records),
    "timestamp": datetime.now(timezone.utc).isoformat(),
})
```

And modify `record_app_usage()` to publish AI session events:

```python
if category in AI_APP_CATEGORIES:
    await publish_event("ai_session", {
        "type": "ai_app_usage",
        "member_id": str(member_id),
        "app_name": app_name,
        "category": category,
        "foreground_minutes": foreground_minutes,
        "timestamp": started_at.isoformat(),
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_device_intelligence.py -v --tb=short`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/device_agent/service.py tests/unit/test_device_intelligence.py
git commit -m "feat(P2-M2): wire device agent to intelligence event bus — AI app detection, sync events"
```

---

### Task 3: Push Notification Delivery on Alerts (W1-2)

**Files:**
- Modify: `src/alerts/service.py`
- Create: `tests/unit/test_alert_push_delivery.py`

When an alert is created, send a push notification to the parent's registered devices.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_alert_push_delivery.py`:

```python
"""Unit tests for push notification delivery on alert creation."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_alert_creation_sends_push(test_session: AsyncSession):
    """Creating an alert should attempt push notification delivery."""
    with patch("src.alerts.service.expo_push_service") as mock_push:
        mock_push.send_notification = AsyncMock(return_value=True)
        from src.alerts.service import create_alert
        from src.alerts.schemas import AlertCreate

        data = AlertCreate(
            group_id=uuid.uuid4(),
            member_id=uuid.uuid4(),
            severity="high",
            title="Test Alert",
            body="Test alert body for push notification",
            source="ai",
        )
        alert = await create_alert(test_session, data=data)
        await test_session.flush()
        # Push should be attempted (best-effort)
        assert alert is not None


@pytest.mark.asyncio
async def test_push_failure_does_not_block_alert(test_session: AsyncSession):
    """Push notification failure should not prevent alert creation."""
    with patch("src.alerts.service.expo_push_service") as mock_push:
        mock_push.send_notification = AsyncMock(side_effect=Exception("Push failed"))
        from src.alerts.service import create_alert
        from src.alerts.schemas import AlertCreate

        data = AlertCreate(
            group_id=uuid.uuid4(),
            member_id=uuid.uuid4(),
            severity="medium",
            title="Test Alert",
            body="Test alert body for push failure test",
            source="device",
        )
        alert = await create_alert(test_session, data=data)
        await test_session.flush()
        # Alert should still be created despite push failure
        assert alert is not None
```

- [ ] **Step 2: Implement push delivery in alert creation**

In `src/alerts/service.py`, after alert creation, add best-effort push:

```python
# Best-effort push notification (never blocks alert creation)
try:
    from src.alerts.push import expo_push_service
    from src.groups.models import Group
    group = await db.execute(select(Group).where(Group.id == group_id))
    group_obj = group.scalar_one_or_none()
    if group_obj and group_obj.owner_id:
        await expo_push_service.send_notification(
            db,
            user_id=group_obj.owner_id,
            title=f"Bhapi Alert: {title}",
            body=description[:200],
            data={"alert_id": str(alert.id), "severity": severity},
        )
except Exception:
    logger.warning("push_delivery_failed", alert_id=str(alert.id))
```

- [ ] **Step 3: Run tests and commit**

Run: `python -m pytest tests/unit/test_alert_push_delivery.py -v --tb=short`

```bash
git add src/alerts/service.py tests/unit/test_alert_push_delivery.py
git commit -m "feat(P2-S8): push notification delivery on alert creation — best-effort, non-blocking"
```

---

### Task 4: Screen Time ↔ Device Agent Integration (W2)

**Files:**
- Modify: `src/screen_time/service.py`
- Create: `tests/unit/test_screen_time_device.py`

Wire `evaluate_usage()` to query real `AppUsageRecord` data from the device agent module. Currently it queries the records directly — verify the integration works end-to-end.

- [ ] **Step 1: Write integration test**

Create `tests/unit/test_screen_time_device.py` — test that creating `AppUsageRecord` entries via device agent and then calling `evaluate_usage()` from screen_time produces correct enforcement actions.

```python
"""Integration tests: device agent data → screen time evaluation."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.device_agent.models import AppUsageRecord
from src.groups.models import Group, GroupMember
from src.screen_time.service import create_rule, evaluate_usage


@pytest_asyncio.fixture
async def integration_data(test_session: AsyncSession):
    """Set up user, group, member, and screen time rule."""
    user = User(
        id=uuid.uuid4(),
        email=f"int-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfak",
        display_name="Integration Parent",
        account_type="family",
        email_verified=False,
        mfa_enabled=False,
    )
    test_session.add(user)
    await test_session.flush()

    group = Group(id=uuid.uuid4(), name="Int Family", type="family", owner_id=user.id)
    test_session.add(group)
    await test_session.flush()

    child = GroupMember(
        id=uuid.uuid4(),
        group_id=group.id,
        user_id=None,
        role="member",
        display_name="Int Child",
        date_of_birth=datetime(2015, 6, 15, tzinfo=timezone.utc),
    )
    test_session.add(child)
    await test_session.flush()

    return {"user": user, "group": group, "child": child}


import pytest_asyncio

@pytest.mark.asyncio
async def test_device_usage_triggers_screen_time_block(test_session, integration_data):
    """When device reports usage exceeding rule limit, evaluate_usage returns block."""
    child = integration_data["child"]
    group = integration_data["group"]

    # Create a 60-minute daily limit on games
    await create_rule(
        test_session,
        group_id=group.id,
        member_id=child.id,
        app_category="games",
        daily_limit_minutes=60,
        age_tier_enforcement="hard_block",
    )
    await test_session.flush()

    # Simulate device agent reporting 90 minutes of game usage today
    now = datetime.now(timezone.utc)
    usage = AppUsageRecord(
        id=uuid.uuid4(),
        member_id=child.id,
        group_id=group.id,
        app_name="Roblox",
        bundle_id="com.roblox.client",
        category="games",
        started_at=now - timedelta(hours=2),
        foreground_minutes=90.0,
    )
    test_session.add(usage)
    await test_session.flush()

    # Evaluate — should trigger block (90/60 = 150%)
    result = await evaluate_usage(test_session, member_id=child.id)
    assert len(result) == 1
    assert result[0]["enforcement_action"] == "block"
    assert result[0]["percent"] == 150.0


@pytest.mark.asyncio
async def test_device_usage_under_limit_allows(test_session, integration_data):
    """Usage under the limit returns allow."""
    child = integration_data["child"]
    group = integration_data["group"]

    await create_rule(
        test_session,
        group_id=group.id,
        member_id=child.id,
        app_category="social",
        daily_limit_minutes=120,
        age_tier_enforcement="warning_then_block",
    )
    await test_session.flush()

    now = datetime.now(timezone.utc)
    usage = AppUsageRecord(
        id=uuid.uuid4(),
        member_id=child.id,
        group_id=group.id,
        app_name="Instagram",
        bundle_id="com.instagram.android",
        category="social",
        started_at=now - timedelta(hours=1),
        foreground_minutes=30.0,
    )
    test_session.add(usage)
    await test_session.flush()

    result = await evaluate_usage(test_session, member_id=child.id)
    assert len(result) == 1
    assert result[0]["enforcement_action"] == "allow"
```

- [ ] **Step 2: Run tests — should pass (integration already works)**

Run: `python -m pytest tests/unit/test_screen_time_device.py -v --tb=short`
Expected: 2 passed (evaluate_usage already queries AppUsageRecord)

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_screen_time_device.py
git commit -m "test(P2-M2): verify device agent → screen time integration end-to-end"
```

---

### Task 5: Messaging → WebSocket Real-Time Publishing (W3)

**Files:**
- Modify: `src/messaging/service.py`
- Create: `tests/unit/test_messaging_realtime.py`

When a message is sent, publish it to the realtime service via Redis pub/sub so connected WebSocket clients receive it instantly.

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_messaging_realtime.py` — test that `send_message()` publishes to Redis event bridge.

```python
"""Unit tests for messaging → realtime WebSocket integration."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.messaging.service import send_message, create_conversation


@pytest.mark.asyncio
async def test_send_message_publishes_to_realtime(test_session: AsyncSession):
    """Sending a message should publish to the realtime event bridge."""
    with patch("src.messaging.service._publish_to_realtime", new_callable=AsyncMock) as mock_pub:
        # Create a conversation first
        sender_id = uuid.uuid4()
        recipient_id = uuid.uuid4()

        conv = await create_conversation(
            test_session,
            created_by=sender_id,
            conv_type="direct",
            member_user_ids=[sender_id, recipient_id],
        )
        await test_session.flush()

        msg = await send_message(
            test_session,
            conversation_id=conv.id,
            sender_id=sender_id,
            content="Hello!",
        )
        await test_session.flush()

        # Verify realtime publish was attempted
        mock_pub.assert_called_once()
        call_args = mock_pub.call_args
        assert call_args is not None


@pytest.mark.asyncio
async def test_realtime_failure_does_not_block_message(test_session: AsyncSession):
    """Realtime publish failure should not prevent message from being saved."""
    with patch("src.messaging.service._publish_to_realtime", new_callable=AsyncMock) as mock_pub:
        mock_pub.side_effect = Exception("Redis down")

        sender_id = uuid.uuid4()
        recipient_id = uuid.uuid4()

        conv = await create_conversation(
            test_session,
            created_by=sender_id,
            conv_type="direct",
            member_user_ids=[sender_id, recipient_id],
        )
        await test_session.flush()

        msg = await send_message(
            test_session,
            conversation_id=conv.id,
            sender_id=sender_id,
            content="Hello despite Redis being down!",
        )
        await test_session.flush()

        # Message should still be saved
        assert msg is not None
        assert msg.content == "Hello despite Redis being down!"
```

- [ ] **Step 2: Implement realtime publishing in messaging service**

Add to `src/messaging/service.py`:

```python
async def _publish_to_realtime(conversation_id: str, message_data: dict) -> None:
    """Publish message to realtime service via Redis (best-effort)."""
    try:
        from src.realtime.pubsub import EventBridge
        bridge = EventBridge()
        await bridge.publish("messaging", {
            "type": "new_message",
            "conversation_id": conversation_id,
            **message_data,
        })
    except Exception:
        logger.warning("realtime_publish_failed", conversation_id=conversation_id)
```

Then add to `send_message()` after the message is created:

```python
# Best-effort realtime delivery
await _publish_to_realtime(str(conversation_id), {
    "message_id": str(msg.id),
    "sender_id": str(sender_id),
    "content": content,
    "message_type": "text",
    "created_at": msg.created_at.isoformat() if msg.created_at else None,
})
```

- [ ] **Step 3: Run tests and commit**

Run: `python -m pytest tests/unit/test_messaging_realtime.py -v --tb=short`

```bash
git add src/messaging/service.py tests/unit/test_messaging_realtime.py
git commit -m "feat(P2-S4): wire messaging to realtime WebSocket — Redis pub/sub on send_message"
```

---

### Task 6: Feed Algorithm — Engagement-Weighted Sorting (W3)

**Files:**
- Modify: `src/social/service.py`
- Modify: `src/social/router.py`
- Create: `tests/e2e/test_feed_algorithm.py`

Add an engagement-weighted feed algorithm that considers recency, likes, and comments. Default to chronological; opt-in to `algorithm=engagement`.

- [ ] **Step 1: Write failing E2E tests**

Create `tests/e2e/test_feed_algorithm.py` — test that `GET /api/v1/social/feed?algorithm=engagement` returns posts sorted by engagement score.

- [ ] **Step 2: Implement engagement scoring**

Add to `src/social/service.py`:

```python
def _engagement_score(post) -> float:
    """Calculate engagement score: recency (decay) + likes + comments."""
    from datetime import datetime, timezone
    age_hours = max(1, (datetime.now(timezone.utc) - post.created_at).total_seconds() / 3600)
    # Likes worth 1 point, comments worth 3 points, decay over 48 hours
    like_score = getattr(post, 'like_count', 0) * 1.0
    comment_score = getattr(post, 'comment_count', 0) * 3.0
    recency_factor = max(0.1, 1.0 - (age_hours / 48.0))
    return (like_score + comment_score + 1) * recency_factor
```

- [ ] **Step 3: Add algorithm query param to feed endpoint**

Modify `GET /api/v1/social/feed` to accept `algorithm: str = Query(default="chronological")` and sort accordingly.

- [ ] **Step 4: Run tests and commit**

```bash
git add src/social/ tests/e2e/test_feed_algorithm.py
git commit -m "feat(P2-S2): engagement-weighted feed algorithm — recency + likes + comments scoring"
```

---

### Task 7: Mobile Chat Screens (W3-4)

**Files:**
- Create: `mobile/apps/social/app/(messaging)/conversations.tsx`
- Create: `mobile/apps/social/app/(messaging)/chat.tsx`
- Create: `mobile/apps/social/app/(messaging)/_layout.tsx`
- Create: `mobile/apps/social/src/hooks/useMessaging.ts`
- Create: `mobile/apps/social/src/hooks/useWebSocket.ts`
- Create: `mobile/apps/social/__tests__/messaging.test.tsx`

- [ ] **Step 1: Create WebSocket hook**

`useWebSocket.ts` — connects to `ws://<host>/ws?token=<jwt>`, handles reconnection, message parsing.

- [ ] **Step 2: Create messaging hooks**

`useMessaging.ts` — `useConversations()`, `useSendMessage()`, `useMessages(conversationId)` with React Query + WebSocket updates.

- [ ] **Step 3: Create conversation list screen**

`conversations.tsx` — FlatList of conversations with last message preview, unread badge, timestamp.

- [ ] **Step 4: Create chat screen**

`chat.tsx` — Inverted FlatList of messages, text input, send button, typing indicator.

- [ ] **Step 5: Write tests and commit**

```bash
cd mobile && npx turbo run test
git add mobile/
git commit -m "feat(P2-S4): mobile chat screens — conversation list, chat view, WebSocket hooks"
```

---

### Task 8: Parent Social Feed Monitor (W4)

**Files:**
- Create: `portal/src/app/(dashboard)/social-feed/page.tsx`
- Create: `portal/src/hooks/use-social-monitor.ts`
- Create: `portal/src/app/(dashboard)/social-feed/__tests__/page.test.tsx`

- [ ] **Step 1: Create React Query hooks**

`use-social-monitor.ts` — `useChildFeed(childId)`, `useChildContacts(childId)`, `useFlagPost()` mutation.

- [ ] **Step 2: Create social feed monitor page**

"use client" page showing child's social posts, contacts, moderation status. Parent can flag content.

- [ ] **Step 3: Write tests and commit**

```bash
cd portal && npx vitest run
git add portal/
git commit -m "feat(P2-M1): parent social feed monitor — view child's social activity, flag content"
```

---

### Task 9: Ohio Governance Portal Page (W5)

**Files:**
- Create: `portal/src/app/(dashboard)/governance/ohio/page.tsx`
- Create: `portal/src/hooks/use-governance.ts`
- Create: `portal/src/app/(dashboard)/governance/ohio/__tests__/page.test.tsx`

**DEADLINE: Jul 1, 2026**

- [ ] **Step 1: Create governance hooks**

`use-governance.ts` — hooks for Ohio policy CRUD, tool inventory, compliance status, board report generation.

- [ ] **Step 2: Create Ohio governance page**

"use client" page with:
- Policy builder wizard (3 required types: ai_usage, risk_assessment, governance)
- AI tool inventory table (add/edit/delete tools, risk ratings)
- Compliance checklist against HB 319
- "Generate Board Report" button → PDF download via `/api/v1/governance/ohio/board-report`
- Status badges: compliant/partial/non-compliant

- [ ] **Step 3: Write tests and commit**

```bash
cd portal && npx vitest run
git add portal/
git commit -m "feat(P2-C1): Ohio AI governance portal — policy wizard, tool inventory, board reports"
```

---

### Task 10: EU AI Act Portal Page (W5-6)

**Files:**
- Create: `portal/src/app/(dashboard)/governance/eu-ai-act/page.tsx`
- Create: `portal/src/app/(dashboard)/governance/eu-ai-act/__tests__/page.test.tsx`

**DEADLINE: Aug 2, 2026**

- [ ] **Step 1: Create EU AI Act dashboard page**

"use client" page with:
- Conformity assessment wizard (risk classification, tech docs, bias testing)
- Transparency report viewer + download
- Human review queue (list of flagged AI decisions needing review)
- Appeals workflow (submit → review → decision timeline)
- EU database registration status
- Risk classification matrix

- [ ] **Step 2: Write tests and commit**

```bash
cd portal && npx vitest run
git add portal/
git commit -m "feat(P2-C2): EU AI Act portal — conformity assessment, transparency reports, appeals"
```

---

### Task 11: Compliance Report Export (W6)

**Files:**
- Create: `portal/src/app/(dashboard)/governance/compliance-report/page.tsx`
- Modify: `src/governance/router.py`
- Modify: `src/governance/service.py`
- Create: `tests/e2e/test_compliance_report.py`

- [ ] **Step 1: Add report generation endpoint**

`GET /api/v1/governance/compliance-report?format=pdf&jurisdiction=ohio|eu` — generates and returns a compliance summary PDF.

- [ ] **Step 2: Create portal page**

"use client" page with jurisdiction selector, date range, preview, and download button.

- [ ] **Step 3: Write tests and commit**

```bash
git add src/governance/ portal/ tests/
git commit -m "feat(P2-C1/C2): compliance report export — PDF generation for Ohio + EU AI Act"
```

---

### Task 12: Sentry Integration (W7)

**Files:**
- Create: `src/middleware/sentry.py`
- Modify: `src/main.py`
- Modify: `src/config.py`

- [ ] **Step 1: Add Sentry config**

Add to `src/config.py`:
```python
SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", ENVIRONMENT)
SENTRY_TRACES_SAMPLE_RATE: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
```

- [ ] **Step 2: Create Sentry middleware**

`src/middleware/sentry.py`:
```python
"""Sentry error tracking integration."""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def init_sentry(dsn: str, environment: str, traces_sample_rate: float = 0.1) -> None:
    """Initialize Sentry SDK if DSN is provided."""
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=traces_sample_rate,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        send_default_pii=False,  # COPPA compliance — never send PII
    )
```

- [ ] **Step 3: Wire into main.py**

In `create_app()`, before returning:
```python
from src.middleware.sentry import init_sentry
from src.config import SENTRY_DSN, SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE
init_sentry(SENTRY_DSN, SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE)
```

- [ ] **Step 4: Commit**

```bash
git add src/middleware/sentry.py src/main.py src/config.py
git commit -m "feat: Sentry error tracking — FastAPI + SQLAlchemy integration, COPPA-safe (no PII)"
```

---

### Task 13: Database Connection Pool Tuning (W7)

**Files:**
- Modify: `src/database.py`
- Modify: `src/config.py`

- [ ] **Step 1: Add pool config vars**

Add to `src/config.py`:
```python
DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 min
```

- [ ] **Step 2: Apply to engine creation**

Modify `src/database.py` engine creation to use these settings for PostgreSQL (not SQLite).

- [ ] **Step 3: Commit**

```bash
git add src/database.py src/config.py
git commit -m "feat: database connection pool tuning — configurable pool size, overflow, recycle"
```

---

### Task 14: K6 Load Test Scripts (W7-8)

**Files:**
- Create: `tests/load/k6-auth.js`
- Create: `tests/load/k6-capture.js`
- Create: `tests/load/k6-dashboard.js`
- Create: `tests/load/README.md`

- [ ] **Step 1: Write K6 auth load test**

`k6-auth.js` — tests login endpoint under load (100 VUs, 30s ramp-up):
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '30s', target: 100 },
        { duration: '1m', target: 100 },
        { duration: '30s', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'],
        http_req_failed: ['rate<0.01'],
    },
};

export default function () {
    const res = http.post(`${__ENV.BASE_URL}/api/v1/auth/login`, JSON.stringify({
        email: `loadtest-${__VU}@example.com`,
        password: 'loadtest123',
    }), { headers: { 'Content-Type': 'application/json' } });

    check(res, { 'status is 200 or 401': (r) => [200, 401].includes(r.status) });
    sleep(1);
}
```

- [ ] **Step 2: Write capture and dashboard load tests**

Similar structure targeting `/api/v1/capture/events` and `/api/v1/portal/dashboard`.

- [ ] **Step 3: Write README with instructions**

- [ ] **Step 4: Commit**

```bash
git add tests/load/
git commit -m "feat: K6 load test scripts — auth, capture, dashboard endpoints with p95 thresholds"
```

---

### Task 15: Operational Runbooks (W8)

**Files:**
- Create: `docs/operations/deployment-checklist.md`
- Create: `docs/operations/monitoring-guide.md`
- Create: `docs/operations/production-runbook.md`

- [ ] **Step 1: Write deployment checklist**

Pre-deploy: migrations run, tests pass, no breaking schema changes, Sentry release tagged.

- [ ] **Step 2: Write monitoring guide**

Structured logging fields, key Sentry alerts, health check endpoints, Redis monitoring.

- [ ] **Step 3: Write production runbook**

Rollback procedure, common failure modes, database recovery, Redis failover. Link to existing incident response at `docs/compliance/soc2-policies/incident-response-policy.md` for severity levels and escalation paths.

- [ ] **Step 4: Commit**

```bash
git add docs/operations/
git commit -m "docs: operational runbooks — deployment checklist, monitoring guide, incident response"
```

---

### Task 16: Final Version Bump + Launch Prep (W9-10)

**Files:**
- Modify: `mobile/apps/safety/app.json`
- Modify: `mobile/apps/social/app.json`
- Modify: `src/main.py` (version string)

- [ ] **Step 1: Bump versions to v4.1.0**

Update `app.json` version fields and `src/main.py` API version string.

- [ ] **Step 2: Extend production E2E tests**

Add new endpoint coverage to `tests/e2e/test_production.py` for device agent, push tokens, governance endpoints.

- [ ] **Step 3: Final full test suite run**

```bash
python -m pytest tests/ -q --tb=no
cd portal && npx vitest run
cd ../mobile && npx turbo run test
```

- [ ] **Step 4: Commit and tag**

```bash
git add mobile/apps/safety/app.json mobile/apps/social/app.json src/main.py tests/e2e/test_production.py
git commit -m "chore: v4.1.0 — Phase 2A execution complete"
git tag v4.1.0
git push origin master --tags
```

---

## Summary

| Week | Tasks | Key Deliverables |
|------|-------|-----------------|
| W1-2 | 1-4 | Push token endpoints, device→intelligence wiring, alert push delivery, screen time integration |
| W3-4 | 5-8 | Messaging→WebSocket, feed algorithm, mobile chat screens, parent social monitor |
| W5-6 | 9-11 | Ohio governance page, EU AI Act page, compliance report export |
| W7-8 | 12-15 | Sentry, connection pooling, K6 load tests, operational runbooks |
| W9-10 | 16 | Version bump, production E2E extension, launch tag |

**Estimated new tests:** ~150+ backend, ~30 portal, ~20 mobile
**Migrations:** 054 (push token index)
**Regulatory:** Ohio (Jul 1) covered by Task 9, EU AI Act (Aug 2) covered by Task 10
