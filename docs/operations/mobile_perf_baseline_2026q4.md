# Mobile Perf Baseline — 2026 Q4 (Phase 4 Task 30)

**Status:** Baseline metrics PENDING device profiling. Code-side improvements landed.
**Owner:** Mobile engineering + QA (device testing required)
**Date:** 2026-04-19

## What shipped in this commit (code-side hardening)

### WebSocket reconnect: jitter + cap (`mobile/packages/shared-api/src/ws-client.ts`)

- **Before:** `delay = baseDelay × 2^attempts`. Unbounded — after 20 failed attempts the next retry was scheduled 12 days out.
- **After:**
  - `maxDelay` cap (default **60s**) prevents unbounded growth
  - ±20% random jitter on every retry prevents reconnection thundering herds on server restart
- Protects server during incidents (prevents all clients reconnecting in sync) and keeps client well-behaved under prolonged outages.

## What still needs physical-device profiling

### Battery (24h observation)

Tool: Android Studio Battery Historian; iOS Instruments → Energy Log.

Baseline to capture:
- [ ] Battery drain % per hour, idle
- [ ] Battery drain % per hour, active use
- [ ] Wake-lock duration
- [ ] Background CPU time

Target: **<3% per hour** active, **<0.5% per hour** idle (matches Gaggle / GoGuardian published baselines).

### Network (24h observation)

Tool: Android Studio Network Profiler; iOS Instruments → Network.

Baseline to capture:
- [ ] Bytes sent/received per hour, active
- [ ] Bytes sent/received per hour, idle
- [ ] Request count per hour
- [ ] Request p95 latency

Target: **<5 MB per hour** active (4G-tolerable).

### Reconnect behaviour (targeted test)

Test sequence:
1. Connect via WS
2. Kill network for 2 minutes
3. Restore network
4. Verify reconnect within ~30s (was up to 12+ days under prior bug)
5. Verify no duplicate message delivery

## Battery / network hotspots to investigate

Common Expo + React Native hotspots that merit code review once baseline data lands:

| Hotspot | Likely cause | Fix |
|---|---|---|
| High idle drain | Unnecessary background location updates | Tune `locationUpdatesDistanceMeters` / `LocationAccuracy` to coarser values when not actively geofencing |
| Chatty API polling | `useQuery` with aggressive `refetchInterval` | Switch to WS push for hot paths |
| Memory growth | Image cache unbounded | Configure `expo-image` cache policy |
| Wake-locks | Foreground service held across network drops | Tie service lifetime to active WS session |

## Maestro E2E tests (to add, post-baseline)

- `8h-background.yaml` — launch app, put in background, wait 8h, verify still receives push notifications and reconnects cleanly
- `network-recovery.yaml` — kill network mid-session, restore, verify recovery
- `app-suspend-resume.yaml` — suspend via OS, resume, verify session + state restored

## How to rerun the baseline

1. Install release build on target device
2. Charge to 100%, disconnect charger
3. Run `./scripts/start-battery-profile.sh <duration_hours>`
4. Compare output to this baseline doc; open tickets for regressions >10%

## Rollback plan for WS jitter change

If the 60s maxDelay cap turns out to be too aggressive (keeps hammering a down server), bump to 300s via the constructor option:
```ts
new WsClient({ maxDelay: 300_000 })
```
No migration needed.
