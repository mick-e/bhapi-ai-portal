# Phase 4: Market Leadership & Network Effects — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Phase 3's feature lead into compounding moats — ship enterprise-grade compliance (SOC 2 Type II, FERPA), platform/ecosystem (public API GA, SDKs, intelligence network), bundled value (Family+ tier, identity-protection partnership), international expansion (UK AADC re-review, NL/PL/SV i18n), and native OS integration (iOS 26 PermissionKit, Android Digital Wellbeing). Close the remaining 15 unclosed review recommendations along the way.

**Architecture:** Extends the Phase 3 platform with 2 new modules (`ferpa/`, `intelligence_network/`), extends 5 existing modules (`api_platform/`, `intelligence/`, `billing/`, `governance/`, `blocking/`), adds 8 Alembic migrations (054-061), 4 new portal pages, native-bridge code in both mobile apps, and a Vanta/Drata-driven SOC 2 evidence pipeline. Four-layer execution: Foundation (cleanup + compliance kickoff) → Platform (API GA + intelligence network) → Bundles & International → Native + Launch.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy async / Alembic / PostgreSQL 16 / Redis 7 | Next.js 15 (static export) | Expo SDK 52+ / React Native + native modules (Swift/Kotlin) / Turborepo | Stripe (bundle pricing) | Vanta or Drata (SOC 2 evidence) | OpenAPI 3.1 + redocly (developer portal) | scripts in Python (audit linters)

**Spec basis:** `docs/Bhapi_Gap_Analysis_Q2_2026.md` §10 (Deferred to Q4 2026+) and §14 (Strategic Recommendations Tier 3 + Tier 4); `docs/superpowers/plans/2026-04-12-review-recommendations-implementation.md` (15 unclosed tasks rolled in)

**Duration:** Weeks 1-26 (Oct 1, 2026 — Mar 31, 2027)
**Team:** 10-13 engineers + external (SOC 2 auditor, legal counsel for UK/EU)
**Budget:** ~120-160 person-weeks engineering + ~$60-110K external (SOC 2 audit, pen test, legal)
**Phase 3 exit prerequisites:** 27/27 Phase 3 tasks complete · mobile apps live in App Store + Play Store · all 25 Phase-3-era review recommendations closed or explicitly carried · backend version 4.0.0+ everywhere · all Phase 3 commits on origin
**Next migration:** 054

---

## Strategic context

Phase 3 (Sep 2026) shipped public-launch Bhapi Safety + Social, mobile device agent in production, location, screen time, creative tools, and a beta public API. Phase 4 is about converting that lead into **defensible moats** before competitors catch up — particularly GoGuardian/Gaggle in the school market and Bark/Aura in the family market.

### The four moats Phase 4 builds

1. **Certifications & compliance** — SOC 2 Type II + FERPA module unblock enterprise school sales (currently soft-blocked by procurement reviews)
2. **Platform & ecosystem** — Public API GA + 4 SDKs + developer portal create switching costs and partner channel
3. **Network effects** — Cross-customer intelligence network (anonymized threat sharing) creates a value flywheel competitors can't replicate without our installed base
4. **Bundled value** — Family+ tier with identity-protection partnership matches Aura's bundle play without forcing us to acquire an identity company

### Out of scope (deferred to Phase 5 / 2027 H2)

Per Gap Analysis §10 "Deferred" + §14.2 "What NOT to Do":

- VR/metaverse monitoring (market still early)
- Building 30+ social media monitoring (compete on AI lane, not Bark's lane)
- Native Stories/Reels in Bhapi Social (stabilization first)
- Federal US AI legislation response (await actual legislation)
- Building a full identity-protection product in-house (use partnership instead)

---

## Dependency Graph

```
LAYER 1: FOUNDATION & COMPLIANCE KICKOFF (Weeks 1-6, Oct-Nov 2026) — Tasks 1-10
  Task 1  (R-09):    Tighten CSP — remove unsafe-inline + HSTS preload ──┐
  Task 2  (R-10):    Audit 144 except Exception blocks ──────────────────┤
  Task 3  (R-16):    OAuth auth-code exchange (move token out of URL) ───┤
  Task 4  (R-25):    Module isolation CI linter ──────────────────────────┤
  Task 5  (R-13):    Publish AI monitoring accuracy benchmarks ──────────┤
  Task 6  (R-18a):   FERPA models + migration 054 ──────────────────────┤
  Task 7  (R-18b):   FERPA service + router + access logging ────────────┤
  Task 8  (R-18c):   FERPA portal page + annual notification templates ──┤
  Task 9  (R-21a):   SOC 2 — engage auditor + select Vanta or Drata ─────┤
  Task 10 (R-21b):   SOC 2 — gap assessment + control inventory ─────────┘
       │
       ▼
LAYER 2: PLATFORM & ECOSYSTEM (Weeks 7-14, Dec 2026 — Jan 2027) — Tasks 11-19
  Task 11 (R-19a):   Location portal page ────────────────────────────────┐
  Task 12 (R-19b):   Screen-time portal page ────────────────────────────┤
  Task 13 (R-19c):   Creative review portal page ────────────────────────┤
  Task 14 (R-19d):   Insights portal page (intelligence module UI) ──────┤
  Task 15 (R-20):    Contextual onboarding cards ────────────────────────┤
  Task 16 (P4-API1): Public API GA — rate-tier plans + usage metering ───┤
  Task 17 (P4-API2): SDKs — Python, JS, Swift, Kotlin (auto-generated) ──┤
  Task 18 (P4-NET1): Intelligence network models + migration 055-056 ────┤
  Task 19 (P4-NET2): Intelligence network — anonymized threat sharing ───┘
       │
       ▼
LAYER 3: BUNDLES & INTERNATIONAL (Weeks 15-22, Feb-Mar 2027) — Tasks 20-27
  Task 20 (R-22):    School pricing — $1.99/seat + free 90-day pilot ────┐
  Task 21 (P4-B1):   Bhapi Family+ bundle tier ($19.99/mo) ──────────────┤
  Task 22 (P4-B2):   Identity protection partnership integration ────────┤
  Task 23 (R-24):    AI bypass / VPN detection for schools ──────────────┤
  Task 24 (P4-INT1): UK AADC re-review compliance updates ───────────────┤
  Task 25 (P4-INT2): Australia eSafety production sign-off + audit ──────┤
  Task 26 (P4-INT3): NL / PL / SV i18n translations (3 new languages) ───┤
  Task 27 (P4-AQ):   Acquisition target evaluation (Blinx / Kinzoo) ─────┘
       │
       ▼
LAYER 4: NATIVE OS INTEGRATION & LAUNCH (Weeks 23-26, Apr 2027) — Tasks 28-32
  Task 28 (R-23):    Apple PermissionKit (iOS 26) integration ───────────┐
  Task 29 (P4-NAT1): Android Digital Wellbeing API integration ──────────┤
  Task 30 (P4-NAT2): Mobile agent production hardening (perf + battery) ─┤
  Task 31 (R-21c):   SOC 2 Type II audit close — report issued ──────────┤
  Task 32 (P4-LNCH): Phase 4 launch comms + metrics dashboard ───────────┘
```

**Parallelization rules:**
- Tasks 1-5 (cleanup) can all run concurrently — independent files
- Tasks 6→7→8 (FERPA) are sequential — service depends on models, page depends on service
- Tasks 9-10 (SOC 2) gate Task 31 (audit close, 6-month observation period)
- Tasks 11-14 (portal pages) can run in parallel — independent Next.js pages
- Tasks 16→17 sequential — SDKs are generated from the GA API spec
- Tasks 18→19 sequential — service depends on models
- Tasks 28+29 in parallel — different OS integrations
- Task 32 (launch) gates on everything in its layer

**Cross-track dependencies:**
- Task 9 (SOC 2 auditor engagement) **must complete by Week 4** to start the 6-month observation window in time for Task 31 close
- Task 4 (module isolation linter) must complete before Task 16 — API GA reorganization may shake loose violations
- Task 18 (intelligence network models) requires migration 055 to be coordinated with 054 (FERPA) — same `alembic/env.py` file

---

## File Structure

### New backend modules

```
src/
├── ferpa/                            # NEW (Tasks 6-8)
│   ├── __init__.py                   # Public interface
│   ├── router.py                     # /api/v1/ferpa endpoints
│   ├── service.py                    # Educational record CRUD, access logging,
│   │                                 #   annual notification generation,
│   │                                 #   third-party data-sharing agreements
│   ├── models.py                     # EducationalRecord, AccessLog, AnnualNotification,
│   │                                 #   DataSharingAgreement
│   └── schemas.py
│
├── intelligence_network/             # NEW (Tasks 18-19)
│   ├── __init__.py
│   ├── router.py                     # /api/v1/intel-network endpoints
│   ├── service.py                    # Threat ingest, anonymization, distribution
│   ├── anonymizer.py                 # k-anonymity transforms, differential privacy noise
│   ├── models.py                     # ThreatSignal, NetworkSubscription, SignalDelivery
│   └── schemas.py
│
├── api_platform/                     # EXTEND (Tasks 16-17)
│   ├── tiers.py                      # NEW — Free / Developer / Business / Enterprise tiers
│   ├── usage_metering.py             # NEW — Per-key request counts + monthly aggregation
│   └── openapi_export.py             # NEW — OpenAPI 3.1 spec export for SDK generation
│
├── intelligence/                     # EXTEND (Task 14 — UI surface)
│   └── (no new files; portal page consumes existing /api/v1/intelligence)
│
├── billing/                          # EXTEND (Tasks 20-22)
│   ├── plans.py                      # MODIFY — add SCHOOL_PILOT_PLAN, FAMILY_PLUS_PLAN
│   └── partnerships.py               # NEW — identity-protection partner webhook handlers
│
├── blocking/                         # EXTEND (Task 23)
│   └── vpn_detection.py              # NEW — VPN/proxy/incognito bypass detection
│
└── main.py                           # MODIFY — register ferpa, intelligence_network routers;
                                      #   tighten CSP (Task 1); register VPN detection middleware
```

### New frontend pages

```
portal/src/app/(dashboard)/
├── ferpa/page.tsx                    # NEW (Task 8) — FERPA dashboard for school admins
├── location/page.tsx                 # NEW (Task 11)
├── screen-time/page.tsx              # NEW (Task 12)
├── creative/page.tsx                 # NEW (Task 13)
├── insights/page.tsx                 # NEW (Task 14)
└── intel-network/page.tsx            # NEW (Task 19) — community threat feed

portal/src/components/ui/
└── OnboardingCard.tsx                # NEW (Task 15)
```

### Mobile-side native modules

```
mobile/apps/safety/native/
├── ios/PermissionKitBridge.swift     # NEW (Task 28) — iOS 26 PermissionKit shim
└── android/DigitalWellbeingBridge.kt # NEW (Task 29) — Android usage stats / wellbeing API

mobile/packages/shared-native/        # NEW
├── package.json
├── src/index.ts                      # JS API: requestParentApproval(), getScreenTimeStats()
└── src/types.ts
```

### Migrations (054-061)

| # | Subject | Task |
|---|---|---|
| 054 | FERPA tables (educational_records, access_logs, annual_notifications, data_sharing_agreements) | 6 |
| 055 | Intelligence network — threat_signals, network_subscriptions | 18 |
| 056 | Intelligence network — signal_deliveries, anonymization_audit | 18 |
| 057 | API platform — tiers (key_tiers, usage_records, monthly_usage_aggregates) | 16 |
| 058 | Billing — feature_gate adds family_plus_features rows; pilot tracking column | 20-21 |
| 059 | Partnerships — identity_protection_links table | 22 |
| 060 | VPN/bypass — bypass_attempts table | 23 |
| 061 | UK AADC — adds region_specific_consent JSON column to consent_records | 24 |

### Scripts & tooling

```
scripts/
├── lint_module_imports.py            # NEW (Task 4)
├── generate_sdk.py                   # NEW (Task 17) — SDK generator wrapper
└── soc2/
    ├── evidence_collector.py         # NEW (Task 10) — exports access logs / change history
    └── control_inventory.yaml        # NEW (Task 10) — control → evidence mapping
```

---

## Layer 1: Foundation & Compliance Kickoff (Weeks 1-6)

Closes the remaining tech-debt review recommendations and starts the 6-month SOC 2 observation window. Nothing here ships externally — it's the platform on which Layers 2-4 stand.

---

### Task 1 (R-09): Tighten CSP — remove unsafe-inline from script-src + HSTS preload

**Files:**
- Modify: `src/main.py` (CSP middleware section, lines ~117-126)
- Test: `tests/security/test_security_headers.py`

- [ ] **Step 1: Locate current CSP middleware**

Run: `cd C:/claude/bhapi-ai-portal && grep -n "Content-Security-Policy\|Strict-Transport-Security" src/main.py`

Note the exact line numbers — they may have drifted from the plan's original `:118-126` reference.

- [ ] **Step 2: Write failing test that asserts CSP has no unsafe-inline in script-src**

In `tests/security/test_security_headers.py`, add:

```python
@pytest.mark.asyncio
async def test_csp_script_src_has_no_unsafe_inline(client):
    """script-src must NOT allow 'unsafe-inline' (XSS protection)."""
    response = await client.get("/health/live")
    csp = response.headers.get("Content-Security-Policy", "")
    # Find the script-src directive
    directives = {d.split()[0]: d for d in csp.split("; ") if d}
    script_src = directives.get("script-src", "")
    assert "'unsafe-inline'" not in script_src, (
        f"script-src still allows unsafe-inline: {script_src}"
    )


@pytest.mark.asyncio
async def test_hsts_includes_preload(client):
    """HSTS header should include 'preload' directive for HSTS preload list eligibility."""
    response = await client.get("/health/live")
    hsts = response.headers.get("Strict-Transport-Security", "")
    assert "preload" in hsts, f"HSTS missing preload: {hsts}"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/security/test_security_headers.py -v -k "unsafe_inline or hsts_includes_preload" --no-cov`
Expected: FAIL — current CSP has `'unsafe-inline'` in script-src; HSTS lacks `preload`.

- [ ] **Step 4: Update CSP and HSTS in src/main.py**

Replace the CSP block with:

```python
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https:; "
        "connect-src 'self' https://api.stripe.com https://js.stripe.com; "
        "frame-src https://js.stripe.com; "
        "frame-ancestors 'none'"
    )
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
```

Style-src keeps `unsafe-inline` (Tailwind requires it). Stripe Elements added to `connect-src` and `frame-src`.

- [ ] **Step 5: Run security test suite**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/security/ -v --no-cov`
Expected: All pass. If portal pages break locally with CSP violations, those inline scripts must be moved to external `.js` files — investigate the specific page.

- [ ] **Step 6: Smoke-test the portal locally**

```bash
cd C:/claude/bhapi-ai-portal && uvicorn src.main:app --port 8000 &
# Visit http://localhost:8000 — open browser console, look for CSP violations
```

Fix any violation by moving the offending inline script into an external file.

- [ ] **Step 7: Commit**

```bash
git add src/main.py tests/security/test_security_headers.py
git commit -m "fix(security): remove unsafe-inline from CSP script-src, add HSTS preload

Tightens CSP by removing 'unsafe-inline' from script-src (prevents XSS
via inline scripts). Adds HSTS preload directive. Adds Stripe JS to
connect-src and frame-src for Stripe Elements support.

Fixes F-011, F-012. Implements R-09 from review-recommendations plan."
```

---

### Task 2 (R-10): Audit 144 bare `except Exception` blocks

**Files:**
- Modify: Multiple files across `src/` (start with `src/portal/service.py` — 26 catches)
- Test: existing test suite (no new tests; behavior preservation only)

- [ ] **Step 1: Generate authoritative list of bare exception blocks**

Run:
```bash
cd C:/claude/bhapi-ai-portal && grep -rn "except Exception" src/ --include="*.py" | grep -v __pycache__ > docs/audits/exception_audit_phase4.txt && wc -l docs/audits/exception_audit_phase4.txt
```

- [ ] **Step 2: Categorize each occurrence**

For each `except Exception` block, classify into one of:

- **K (Keep — fire-and-forget):** SSE broadcast, push notification, audit log write. Replace `pass` with `logger.debug("operation_degraded", exc_info=True, ...)` so failures are visible without breaking the request.
- **F (Fix — should propagate):** Business logic in rewards, privacy, group operations. Replace with either `logger.warning("operation_failed", exc_info=True, ...)` or remove the try/except entirely so the error bubbles up.
- **R (Remove — wrapping safe ops):** The wrapped code can never throw; drop the try/except.

Annotate the audit file with K / F / R per line.

- [ ] **Step 3: Fix the worst offender first — `src/portal/service.py` (26 catches)**

Read `src/portal/service.py` end-to-end. For each `except Exception: pass`, replace with the categorized fix. Most will be K (the dashboard wraps each section in a try/except by design — that pattern is correct, it just shouldn't silently swallow).

Example:
```python
# Before
try:
    activity = await get_activity_summary(db, group_id)
except Exception:
    pass

# After
try:
    activity = await get_activity_summary(db, group_id)
except Exception:
    logger.debug("dashboard_section_degraded", section="activity", exc_info=True)
    degraded_sections.append("activity")
```

- [ ] **Step 4: Run portal tests**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/unit/test_portal.py tests/e2e/test_portal.py --no-cov -v
```
Expected: All pass.

- [ ] **Step 5: Commit Phase 1 fix**

```bash
git add src/portal/service.py docs/audits/exception_audit_phase4.txt
git commit -m "fix: replace bare except Exception:pass in portal/service.py with structured logging

26 catches in dashboard aggregator now log at debug level instead of
silently swallowing. degraded_sections tracking remains intact.

Part of R-10 from review-recommendations plan."
```

- [ ] **Step 6: Process remaining 70 files in batches of 10**

For each batch:
1. Read context around each `except Exception`
2. Apply categorized fix (K / F / R)
3. Run targeted tests for the touched modules
4. Commit the batch

Suggested batches:
- Batch A: `src/groups/` (rewards.py, privacy.py, family_agreement.py)
- Batch B: `src/risk/` and `src/alerts/`
- Batch C: `src/integrations/` (Clever, ClassLink, Yoti, SSO)
- Batch D: `src/billing/`, `src/email/`, `src/sms/`
- Batch E: `src/intelligence/`, `src/social/`, `src/moderation/`
- Batch F: `src/capture/`, `src/blocking/`, `src/governance/`
- Batch G: everything else

- [ ] **Step 7: Verify count is zero**

```bash
cd C:/claude/bhapi-ai-portal && grep -rn "except Exception.*pass" src/ --include="*.py" | grep -v __pycache__ | wc -l
```
Expected: `0`.

- [ ] **Step 8: Run full backend test suite**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/ -q --no-cov --tb=short
```
Expected: All pass (~4,639+ tests).

- [ ] **Step 9: Final commit**

```bash
git add src/
git commit -m "fix: complete except Exception audit — 0 bare blocks remaining

All 144 'except Exception:pass' blocks across 70 files reviewed and
categorized: fire-and-forget (debug log), business-logic (warning log
or removed), or unnecessary (removed). No more silent error swallowing.

Fixes F-001. Completes R-10 from review-recommendations plan."
```

---

### Task 3 (R-16): OAuth auth-code exchange (move session token out of redirect URL)

**Files:**
- Modify: `src/auth/router.py` (OAuth callback handler, around line 450)
- Modify: `portal/src/app/(auth)/oauth/callback/page.tsx`
- Test: `tests/security/test_oauth_security.py`

- [ ] **Step 1: Write failing security test**

In `tests/security/test_oauth_security.py`, add:

```python
@pytest.mark.asyncio
async def test_oauth_callback_does_not_leak_token_in_url(client, monkeypatch):
    """OAuth callback redirect must NOT contain a session token in the URL."""
    # Mock provider exchange to return a fake user
    monkeypatch.setattr(
        "src.auth.oauth_providers.exchange_code",
        AsyncMock(return_value={"email": "test@example.com", "sub": "google-12345"}),
    )

    response = await client.get(
        "/api/v1/auth/oauth/google/callback?code=fake&state=fake",
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers["location"]
    # Must contain a short-lived auth code, NOT a session token
    assert "code=" in location
    assert "token=" not in location
    assert "session=" not in location
    assert "Bearer" not in location


@pytest.mark.asyncio
async def test_oauth_code_exchange_works(client, monkeypatch):
    """POST /api/v1/auth/oauth/exchange swaps a one-time code for a session."""
    # Setup: get a real auth code first via callback (use mocked provider)
    monkeypatch.setattr(
        "src.auth.oauth_providers.exchange_code",
        AsyncMock(return_value={"email": "test@example.com", "sub": "google-12345"}),
    )
    callback = await client.get(
        "/api/v1/auth/oauth/google/callback?code=fake&state=fake",
        follow_redirects=False,
    )
    location = callback.headers["location"]
    code = location.split("code=")[1].split("&")[0]

    # Now exchange it
    response = await client.post("/api/v1/auth/oauth/exchange", json={"code": code})
    assert response.status_code == 200
    assert "token" in response.json()
    # Cookie must also be set
    assert "session" in response.cookies or "session_token" in response.cookies

    # Code must be one-time-use — second exchange fails
    response2 = await client.post("/api/v1/auth/oauth/exchange", json={"code": code})
    assert response2.status_code == 401
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/security/test_oauth_security.py -v -k "oauth_callback_does_not_leak or oauth_code_exchange_works" --no-cov`
Expected: FAIL.

- [ ] **Step 3: Update OAuth callback to redirect with auth code**

In `src/auth/router.py`, replace the section that builds the redirect URL with:

```python
    # Generate short-lived auth code (60s TTL in Redis) instead of leaking session token
    import secrets
    auth_code = secrets.token_urlsafe(32)
    from src.redis_client import get_redis
    redis = get_redis()
    if redis is None:
        # Tests-only fallback: use in-memory dict (cleared per test)
        from src.auth.service import _oauth_code_fallback
        _oauth_code_fallback[auth_code] = session_token
    else:
        await redis.set(f"bhapi:oauth_code:{auth_code}", session_token, ex=60)

    redirect_url = f"{settings.oauth_redirect_base_url}/oauth/callback?code={auth_code}&state={state}"
    return RedirectResponse(url=redirect_url, status_code=302)
```

- [ ] **Step 4: Add the exchange endpoint**

In `src/auth/router.py`, add:

```python
@router.post("/oauth/exchange")
async def exchange_oauth_code(
    code: str = Body(..., embed=True),
    response: Response = None,
):
    """Exchange a one-time short-lived OAuth auth code for a session token."""
    from src.redis_client import get_redis
    from src.auth.service import _oauth_code_fallback, _set_session_cookie

    redis = get_redis()
    key = f"bhapi:oauth_code:{code}"

    if redis is None:
        session_token = _oauth_code_fallback.pop(code, None)
    else:
        session_token = await redis.get(key)
        if session_token:
            await redis.delete(key)  # one-time use

    if not session_token:
        raise UnauthorizedError("Invalid or expired authorization code")

    payload = JSONResponse({"token": session_token})
    _set_session_cookie(payload, session_token)
    return payload
```

Add the in-memory fallback dict near the top of `src/auth/service.py`:
```python
_oauth_code_fallback: dict[str, str] = {}
```

- [ ] **Step 5: Update frontend OAuth callback page**

In `portal/src/app/(auth)/oauth/callback/page.tsx`, replace token-from-URL parsing with code-exchange flow:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function OAuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    if (!code) {
      setError('Missing OAuth code');
      return;
    }
    fetch('/api/v1/auth/oauth/exchange', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ code }),
    })
      .then(async (r) => {
        if (!r.ok) throw new Error('Exchange failed');
        return r.json();
      })
      .then(() => router.push('/dashboard'))
      .catch((e) => setError(String(e)));
  }, [searchParams, router]);

  if (error) return <div className="p-6 text-red-600">Sign-in failed: {error}</div>;
  return <div className="p-6 text-gray-600">Completing sign-in…</div>;
}
```

- [ ] **Step 6: Run tests**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/e2e/test_oauth.py tests/security/test_oauth_security.py --no-cov -v
cd C:/claude/bhapi-ai-portal/portal && npx tsc --noEmit
```
Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add src/auth/router.py src/auth/service.py portal/src/app/\(auth\)/oauth/callback/page.tsx tests/security/test_oauth_security.py
git commit -m "fix(security): replace OAuth token-in-URL with one-time auth code exchange

OAuth callback now redirects with a 60-second-TTL auth code (in Redis,
in-memory fallback for tests). Frontend exchanges the code via POST
/api/v1/auth/oauth/exchange — code is single-use and the session token
is set as an httpOnly cookie + returned in the response body.

Fixes F-014. Implements R-16 from review-recommendations plan."
```

---

### Task 4 (R-25): Module isolation CI linter

**Files:**
- Create: `scripts/lint_module_imports.py`
- Modify: `.github/workflows/ci.yml`
- Likely modify: many `src/<module>/__init__.py` files (re-exports for the linter to allow them)

Full implementation matches `docs/superpowers/plans/2026-04-12-review-recommendations-implementation.md` Task 25 (lines 1666-1833). Reproduce here for self-containment:

- [ ] **Step 1: Create the linter**

Create `scripts/lint_module_imports.py` with the AST-based linter from the source plan (section "Task 25 / R-25"). Allowed imports: `src.exceptions`, `src.models`, `src.schemas`, `src.config`, `src.database`, `src.dependencies`, `src.encryption`, `src.redis_client`, `src.__version__`, plus self-imports and any `__init__.py` public-interface imports. Forbidden: top-level imports from another module's internal files.

- [ ] **Step 2: Run the linter to enumerate current violations**

```bash
cd C:/claude/bhapi-ai-portal && python scripts/lint_module_imports.py 2>&1 | tee docs/audits/module_isolation_audit.txt
```
Expected: a list of violations.

- [ ] **Step 3: Fix violations by adding re-exports to `__init__.py`**

For each violation, prefer adding the imported symbol to the source module's `__init__.py`:

```python
# Example: src/groups/__init__.py
from src.groups.models import Group, GroupMember, FamilyAgreement
from src.groups.service import get_group, add_member

__all__ = ["Group", "GroupMember", "FamilyAgreement", "get_group", "add_member"]
```

Then update the offending file:
```python
# Before
from src.groups.models import Group
# After
from src.groups import Group
```

For cycle-breaking, deferred imports inside function bodies are acceptable.

- [ ] **Step 4: Re-run linter until clean**

```bash
cd C:/claude/bhapi-ai-portal && python scripts/lint_module_imports.py
```
Expected: `No cross-module import violations found.`

- [ ] **Step 5: Wire into CI**

In `.github/workflows/ci.yml`, after the ruff lint step, add:

```yaml
      - name: Module isolation lint
        run: python scripts/lint_module_imports.py
```

- [ ] **Step 6: Run full backend test suite**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/ -q --no-cov --tb=short
```
Expected: All pass (re-exports must not break import resolution).

- [ ] **Step 7: Commit**

```bash
git add scripts/lint_module_imports.py .github/workflows/ci.yml src/
git commit -m "feat(ci): enforce module isolation via AST-based import linter

AST linter rejects top-level cross-module internal imports (e.g.,
src.alerts.service importing from src.groups.models). Allowed: shared
infra modules, self-imports, __init__.py public interfaces, deferred
imports inside function bodies. Runs in CI on every push.

Fixes F-021. Implements R-25 from review-recommendations plan."
```

---

### Task 5 (R-13): Publish AI monitoring accuracy benchmarks

**Files:**
- Create: `src/risk/benchmarks.py`
- Create: `tests/benchmarks/data/risk_test_corpus.json`
- Create: `tests/benchmarks/test_risk_accuracy.py`
- Create: `docs/benchmarks/ai-monitoring-accuracy-2026-q4.md`

This is a measurement task — the value is the *published number*, not the code.

- [ ] **Step 1: Assemble the labeled test corpus**

Build `tests/benchmarks/data/risk_test_corpus.json` with at least 50 examples per risk category × 14 categories = 700+ examples minimum. Each entry:

```json
{
  "id": "uuid",
  "platform": "chatgpt|gemini|claude|...",
  "content": "the AI conversation excerpt",
  "true_category": "self_harm|sexual_content|...",
  "true_severity": "low|medium|high|critical",
  "notes": "edge case description if applicable"
}
```

Sources for examples:
- Synthetic generation (use Claude with explicit "label this corpus" prompts; manually validate 100% — cannot trust unverified synthetic data for accuracy claims)
- Public datasets where licenses allow (e.g., Anthropic's HarmBench, if license permits)
- Internal capture data (anonymized + parent-consented only — must clear with legal)

Include edge cases: sarcasm, code discussions about violence, educational content about risks, multi-language content.

- [ ] **Step 2: Build the benchmark runner**

Create `src/risk/benchmarks.py`:

```python
"""AI monitoring accuracy benchmarks. Runs the risk pipeline over a labeled
corpus and produces a markdown report with precision/recall/F1 per category."""
import asyncio
import json
from collections import defaultdict
from pathlib import Path
from src.risk.pipeline import classify_content


async def run_benchmark(corpus_path: Path) -> dict:
    corpus = json.loads(corpus_path.read_text())
    results = []
    for example in corpus:
        predicted = await classify_content(
            content=example["content"],
            platform=example["platform"],
        )
        results.append({
            "id": example["id"],
            "true_category": example["true_category"],
            "predicted_category": predicted.category,
            "true_severity": example["true_severity"],
            "predicted_severity": predicted.severity,
            "match": predicted.category == example["true_category"],
        })

    by_cat = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for r in results:
        if r["true_category"] == r["predicted_category"]:
            by_cat[r["true_category"]]["tp"] += 1
        else:
            by_cat[r["true_category"]]["fn"] += 1
            by_cat[r["predicted_category"]]["fp"] += 1

    metrics = {}
    for cat, counts in by_cat.items():
        precision = counts["tp"] / (counts["tp"] + counts["fp"]) if (counts["tp"] + counts["fp"]) else 0
        recall = counts["tp"] / (counts["tp"] + counts["fn"]) if (counts["tp"] + counts["fn"]) else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
        metrics[cat] = {"precision": precision, "recall": recall, "f1": f1, **counts}
    return {"per_category": metrics, "total": len(results)}


def render_report(metrics: dict) -> str:
    lines = ["# Bhapi AI Monitoring Accuracy — 2026 Q4", ""]
    lines.append(f"**Corpus size:** {metrics['total']} labeled examples\n")
    lines.append("| Category | Precision | Recall | F1 | TP | FP | FN |")
    lines.append("|---|---|---|---|---|---|---|")
    for cat, m in sorted(metrics["per_category"].items()):
        lines.append(
            f"| {cat} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | "
            f"{m['tp']} | {m['fp']} | {m['fn']} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys
    corpus = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/benchmarks/data/risk_test_corpus.json")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/benchmarks/ai-monitoring-accuracy-2026-q4.md")
    metrics = asyncio.run(run_benchmark(corpus))
    out.write_text(render_report(metrics))
    print(f"Report written to {out}")
```

- [ ] **Step 3: Run the benchmark**

```bash
cd C:/claude/bhapi-ai-portal && python -m src.risk.benchmarks
```

Expected: Report written to `docs/benchmarks/ai-monitoring-accuracy-2026-q4.md` containing per-category precision/recall/F1.

- [ ] **Step 4: Add a CI guard test**

In `tests/benchmarks/test_risk_accuracy.py`:

```python
import asyncio
import json
from pathlib import Path
from src.risk.benchmarks import run_benchmark

CORPUS = Path("tests/benchmarks/data/risk_test_corpus.json")
MIN_CORPUS_SIZE = 700  # 50 per category × 14 categories
MIN_OVERALL_F1 = 0.75   # threshold below which we don't ship


def test_corpus_meets_minimum_size():
    assert len(json.loads(CORPUS.read_text())) >= MIN_CORPUS_SIZE


def test_overall_accuracy_above_threshold():
    metrics = asyncio.run(run_benchmark(CORPUS))
    f1s = [m["f1"] for m in metrics["per_category"].values()]
    avg_f1 = sum(f1s) / len(f1s) if f1s else 0
    assert avg_f1 >= MIN_OVERALL_F1, f"Average F1 {avg_f1:.3f} below threshold {MIN_OVERALL_F1}"
```

- [ ] **Step 5: Run the guard test**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/benchmarks/ -v --no-cov
```
Expected: Pass. If F1 below threshold, decide whether to retrain/tune classifier or lower the threshold (with justification).

- [ ] **Step 6: Polish the report for procurement audiences**

Edit `docs/benchmarks/ai-monitoring-accuracy-2026-q4.md` to add a methodology section, false-positive rate analysis, and direct comparison to Gaggle's "40x fewer false positives" claim. Format for non-technical school procurement reviewers.

- [ ] **Step 7: Commit**

```bash
git add src/risk/benchmarks.py tests/benchmarks/ docs/benchmarks/
git commit -m "feat: publish AI monitoring accuracy benchmarks (precision/recall/F1)

Adds reproducible benchmark runner over a 700+ labeled corpus across
14 risk categories. Generates a procurement-ready report with per-category
metrics and false-positive rate. CI guard ensures we don't regress below
0.75 average F1.

Implements R-13 from review-recommendations plan."
```

---

### Task 6 (R-18a): FERPA models + migration 054

**Files:**
- Create: `src/ferpa/__init__.py`
- Create: `src/ferpa/models.py`
- Create: `src/ferpa/schemas.py`
- Create: `alembic/versions/054_ferpa_compliance.py`
- Modify: `alembic/env.py` (import the new models)

- [ ] **Step 1: Create module structure**

```bash
cd C:/claude/bhapi-ai-portal && mkdir -p src/ferpa
touch src/ferpa/__init__.py src/ferpa/models.py src/ferpa/schemas.py src/ferpa/service.py src/ferpa/router.py
```

- [ ] **Step 2: Define models**

Create `src/ferpa/models.py`:

```python
"""FERPA compliance models — educational records, access logs, notifications."""
import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models import Base, UUIDMixin, TimestampMixin


class EducationalRecord(Base, UUIDMixin, TimestampMixin):
    """Designation of which data elements are FERPA-covered educational records."""
    __tablename__ = "ferpa_educational_records"

    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"), index=True)
    record_type: Mapped[str] = mapped_column(String(64))  # academic, behavioral, attendance, ai_usage
    description: Mapped[str] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String(32))  # directory, non_directory, excluded
    designated_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))


class AccessLog(Base, UUIDMixin, TimestampMixin):
    """Audit log of FERPA-covered record access — required by 34 CFR 99.32."""
    __tablename__ = "ferpa_access_logs"

    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"), index=True)
    accessor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("group_members.id"), index=True)
    record_type: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(128))  # legitimate_educational_interest, parental_request, etc.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AnnualNotification(Base, UUIDMixin, TimestampMixin):
    """Annual FERPA notification dispatched to parents."""
    __tablename__ = "ferpa_annual_notifications"

    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"), index=True)
    school_year: Mapped[str] = mapped_column(String(16))  # "2026-2027"
    template_version: Mapped[str] = mapped_column(String(32))
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    recipients_count: Mapped[int] = mapped_column(default=0)
    delivery_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class DataSharingAgreement(Base, UUIDMixin, TimestampMixin):
    """FERPA §99.31 third-party data sharing agreement record."""
    __tablename__ = "ferpa_data_sharing_agreements"

    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"), index=True)
    third_party_name: Mapped[str] = mapped_column(String(256))
    purpose: Mapped[str] = mapped_column(Text)
    data_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    signed_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    effective_from: Mapped[datetime]
    effective_until: Mapped[datetime | None] = mapped_column(nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
```

- [ ] **Step 3: Define schemas**

Create `src/ferpa/schemas.py`:

```python
import uuid
from datetime import datetime
from pydantic import BaseModel


class EducationalRecordCreate(BaseModel):
    record_type: str
    description: str
    classification: str  # directory | non_directory | excluded


class EducationalRecordResponse(BaseModel):
    id: uuid.UUID
    record_type: str
    description: str
    classification: str
    created_at: datetime


class AccessLogCreate(BaseModel):
    member_id: uuid.UUID
    record_type: str
    purpose: str
    notes: str | None = None


class AccessLogResponse(BaseModel):
    id: uuid.UUID
    accessor_user_id: uuid.UUID
    member_id: uuid.UUID
    record_type: str
    purpose: str
    notes: str | None
    created_at: datetime


class AnnualNotificationResponse(BaseModel):
    id: uuid.UUID
    school_year: str
    sent_at: datetime | None
    recipients_count: int


class DataSharingAgreementCreate(BaseModel):
    third_party_name: str
    purpose: str
    data_categories: list[str]
    effective_from: datetime
    effective_until: datetime | None = None
    document_url: str | None = None
```

- [ ] **Step 4: Wire models into alembic**

In `alembic/env.py`, add:
```python
from src.ferpa import models as ferpa_models  # noqa: F401
```

- [ ] **Step 5: Generate migration**

```bash
cd C:/claude/bhapi-ai-portal && alembic revision --autogenerate -m "add FERPA compliance tables"
```

Verify the generated file in `alembic/versions/054_*.py` includes all four tables. Rename if necessary so the filename starts with `054_`.

- [ ] **Step 6: Apply migration locally**

```bash
cd C:/claude/bhapi-ai-portal && alembic upgrade head
```

- [ ] **Step 7: Verify migration file is tracked**

```bash
git status alembic/versions/
```
Migration file MUST appear. **An uncommitted migration is the same as no migration** (per CLAUDE.md ADR section 9 — caused a multi-day production outage in March 2026).

- [ ] **Step 8: Commit**

```bash
git add src/ferpa/ alembic/versions/054_*.py alembic/env.py
git commit -m "feat(ferpa): add educational record + access log + notification + agreement models

Migration 054 adds 4 FERPA-covered tables. Models follow existing
SQLAlchemy 2.x async pattern with UUIDMixin + TimestampMixin. Wired
into alembic/env.py per CLAUDE.md autogenerate requirement.

Part of R-18 from review-recommendations plan."
```

---

### Task 7 (R-18b): FERPA service + router + access-log enforcement

**Files:**
- Create: `src/ferpa/service.py`
- Create: `src/ferpa/router.py`
- Modify: `src/main.py` (register router)
- Test: `tests/unit/test_ferpa.py`
- Test: `tests/e2e/test_ferpa.py`

- [ ] **Step 1: Write failing test for record CRUD**

In `tests/e2e/test_ferpa.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ferpa_record_designation_lifecycle(client: AsyncClient, school_admin_headers):
    # Create
    response = await client.post(
        "/api/v1/ferpa/records",
        json={"record_type": "ai_usage", "description": "ChatGPT conversation logs",
              "classification": "non_directory"},
        headers=school_admin_headers,
    )
    assert response.status_code == 201
    record_id = response.json()["id"]

    # List
    response = await client.get("/api/v1/ferpa/records", headers=school_admin_headers)
    assert response.status_code == 200
    assert any(r["id"] == record_id for r in response.json()["items"])


@pytest.mark.asyncio
async def test_ferpa_access_log_required_purpose(client, school_admin_headers, student_member_id):
    response = await client.post(
        "/api/v1/ferpa/access-log",
        json={"member_id": str(student_member_id), "record_type": "ai_usage",
              "purpose": "legitimate_educational_interest",
              "notes": "Reviewing AI safety incident"},
        headers=school_admin_headers,
    )
    assert response.status_code == 201

    # Listing returns it
    response = await client.get(
        f"/api/v1/ferpa/access-log?member_id={student_member_id}",
        headers=school_admin_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


@pytest.mark.asyncio
async def test_only_school_admins_can_designate_records(client, family_user_headers):
    response = await client.post(
        "/api/v1/ferpa/records",
        json={"record_type": "academic", "description": "test", "classification": "directory"},
        headers=family_user_headers,
    )
    assert response.status_code == 403  # FERPA module is school-account-only
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/e2e/test_ferpa.py --no-cov -v`
Expected: FAIL (404 or import error — module not registered yet).

- [ ] **Step 3: Implement service**

Create `src/ferpa/service.py`:

```python
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.ferpa.models import EducationalRecord, AccessLog, AnnualNotification, DataSharingAgreement
from src.ferpa.schemas import EducationalRecordCreate, AccessLogCreate, DataSharingAgreementCreate
from src.exceptions import NotFoundError


async def create_educational_record(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID, payload: EducationalRecordCreate
) -> EducationalRecord:
    rec = EducationalRecord(
        group_id=group_id,
        record_type=payload.record_type,
        description=payload.description,
        classification=payload.classification,
        designated_by_user_id=user_id,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec


async def list_educational_records(db: AsyncSession, group_id: uuid.UUID) -> list[EducationalRecord]:
    result = await db.execute(
        select(EducationalRecord).where(EducationalRecord.group_id == group_id)
    )
    return list(result.scalars().all())


async def log_access(
    db: AsyncSession, group_id: uuid.UUID, accessor_user_id: uuid.UUID, payload: AccessLogCreate
) -> AccessLog:
    log = AccessLog(
        group_id=group_id,
        accessor_user_id=accessor_user_id,
        member_id=payload.member_id,
        record_type=payload.record_type,
        purpose=payload.purpose,
        notes=payload.notes,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def list_access_logs(
    db: AsyncSession, group_id: uuid.UUID, member_id: uuid.UUID | None = None
) -> list[AccessLog]:
    stmt = select(AccessLog).where(AccessLog.group_id == group_id)
    if member_id:
        stmt = stmt.where(AccessLog.member_id == member_id)
    stmt = stmt.order_by(AccessLog.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_data_sharing_agreement(
    db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID, payload: DataSharingAgreementCreate
) -> DataSharingAgreement:
    agreement = DataSharingAgreement(
        group_id=group_id,
        third_party_name=payload.third_party_name,
        purpose=payload.purpose,
        data_categories=payload.data_categories,
        signed_by_user_id=user_id,
        effective_from=payload.effective_from,
        effective_until=payload.effective_until,
        document_url=payload.document_url,
    )
    db.add(agreement)
    await db.commit()
    await db.refresh(agreement)
    return agreement
```

- [ ] **Step 4: Implement router**

Create `src/ferpa/router.py`:

```python
import uuid
from fastapi import APIRouter, Depends, status
from src.dependencies import AuthContext, DbSession, require_school_account
from src.ferpa import service
from src.ferpa.schemas import (
    EducationalRecordCreate, EducationalRecordResponse,
    AccessLogCreate, AccessLogResponse,
    DataSharingAgreementCreate,
)

router = APIRouter(prefix="/api/v1/ferpa", tags=["ferpa"])


@router.post(
    "/records",
    response_model=EducationalRecordResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_school_account)],
)
async def create_record(
    payload: EducationalRecordCreate,
    db: DbSession,
    auth: AuthContext,
):
    rec = await service.create_educational_record(db, auth.group_id, auth.user_id, payload)
    return rec


@router.get(
    "/records",
    dependencies=[Depends(require_school_account)],
)
async def list_records(db: DbSession, auth: AuthContext):
    items = await service.list_educational_records(db, auth.group_id)
    return {"items": items, "total": len(items)}


@router.post(
    "/access-log",
    response_model=AccessLogResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_school_account)],
)
async def create_access_log(
    payload: AccessLogCreate,
    db: DbSession,
    auth: AuthContext,
):
    return await service.log_access(db, auth.group_id, auth.user_id, payload)


@router.get(
    "/access-log",
    dependencies=[Depends(require_school_account)],
)
async def get_access_log(
    db: DbSession,
    auth: AuthContext,
    member_id: uuid.UUID | None = None,
):
    items = await service.list_access_logs(db, auth.group_id, member_id)
    return {"items": items, "total": len(items)}


@router.post(
    "/sharing-agreements",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_school_account)],
)
async def create_sharing_agreement(
    payload: DataSharingAgreementCreate,
    db: DbSession,
    auth: AuthContext,
):
    return await service.create_data_sharing_agreement(db, auth.group_id, auth.user_id, payload)
```

If `require_school_account` dependency doesn't exist yet in `src/dependencies.py`, add:

```python
async def require_school_account(auth: AuthContext = Depends(...)):
    if auth.account_type != "school":
        raise ForbiddenError("FERPA endpoints require a school account")
    return auth
```

- [ ] **Step 5: Register router in main.py**

In `src/main.py`, add:
```python
from src.ferpa.router import router as ferpa_router
app.include_router(ferpa_router)
```

- [ ] **Step 6: Update __init__.py public interface**

In `src/ferpa/__init__.py`:
```python
from src.ferpa.models import EducationalRecord, AccessLog, AnnualNotification, DataSharingAgreement

__all__ = ["EducationalRecord", "AccessLog", "AnnualNotification", "DataSharingAgreement"]
```

- [ ] **Step 7: Run tests**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/e2e/test_ferpa.py tests/unit/test_ferpa.py --no-cov -v
```
Expected: All pass.

- [ ] **Step 8: Commit**

```bash
git add src/ferpa/ src/main.py src/dependencies.py tests/
git commit -m "feat(ferpa): add service + router for educational records, access logs, agreements

CRUD for FERPA-covered record designations, audit logging for legitimate
educational interest accesses (34 CFR 99.32), and §99.31 third-party
data-sharing agreement registration. School-account-only via
require_school_account dependency.

Part of R-18 from review-recommendations plan."
```

---

### Task 8 (R-18c): FERPA portal page + annual notification template

**Files:**
- Create: `portal/src/app/(dashboard)/ferpa/page.tsx`
- Create: `portal/src/hooks/use-ferpa.ts`
- Create: `portal/messages/{en,fr,es,de,pt,it}.json` — add `ferpa` namespace
- Create: `src/ferpa/notification_templates.py` — annual notification copy

- [ ] **Step 1: Add i18n keys for ferpa namespace**

Add to all 6 `portal/messages/*.json` files:

```json
"ferpa": {
  "title": "FERPA Compliance",
  "subtitle": "Educational record designations, access logs, and data-sharing agreements",
  "tabs": {
    "records": "Educational Records",
    "access": "Access Log",
    "notifications": "Annual Notifications",
    "agreements": "Data Sharing"
  },
  "designate": "Designate Record Type",
  "logAccess": "Log Access",
  "loading": "Loading FERPA data…",
  "empty": "No records designated yet."
}
```

(Translate to FR/ES/DE/PT/IT — use the same translation pipeline as previous i18n work.)

- [ ] **Step 2: Create the React Query hook**

In `portal/src/hooks/use-ferpa.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export function useFerpaRecords() {
  return useQuery({
    queryKey: ['ferpa', 'records'],
    queryFn: () => apiClient.get('/api/v1/ferpa/records'),
  });
}

export function useFerpaAccessLog(memberId?: string) {
  return useQuery({
    queryKey: ['ferpa', 'access-log', memberId],
    queryFn: () => apiClient.get(`/api/v1/ferpa/access-log${memberId ? `?member_id=${memberId}` : ''}`),
  });
}

export function useDesignateRecord() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { record_type: string; description: string; classification: string }) =>
      apiClient.post('/api/v1/ferpa/records', payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ferpa', 'records'] }),
  });
}
```

- [ ] **Step 3: Create the page**

Create `portal/src/app/(dashboard)/ferpa/page.tsx` following the existing dashboard page pattern (Tabs component, EmptyState on empty, error/loading states, useTranslations hook). Wire to the hooks above.

Reference existing pages like `portal/src/app/(dashboard)/governance/page.tsx` for the pattern — same Tabs UI structure.

- [ ] **Step 4: Add notification templates**

Create `src/ferpa/notification_templates.py`:

```python
"""FERPA annual notification templates per 34 CFR 99.7. Contents reviewed by counsel."""
from string import Template

ANNUAL_NOTIFICATION_TEMPLATE_V1 = Template("""
Dear $parent_name,

This notice fulfills the annual FERPA notification requirement of $school_name for school year $school_year.

Under the Family Educational Rights and Privacy Act (FERPA), parents and eligible students have the right to:

1. Inspect and review the student's education records
2. Request amendment of records believed to be inaccurate
3. Provide written consent before disclosure of personally identifiable information
4. File a complaint with the U.S. Department of Education

The following data categories are designated as educational records:
$record_categories

For full text of these rights and procedures to exercise them, visit:
$portal_url/ferpa/notice

To opt out of directory-information disclosures, contact $contact_email by $opt_out_deadline.

Sincerely,
$school_name
""".strip())
```

- [ ] **Step 5: Run frontend tests + type check**

```bash
cd C:/claude/bhapi-ai-portal/portal && npx tsc --noEmit && npx vitest run
```
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add portal/src/app/\(dashboard\)/ferpa/ portal/src/hooks/use-ferpa.ts portal/messages/ src/ferpa/notification_templates.py
git commit -m "feat(ferpa): add school admin portal page + annual notification template

FERPA dashboard page with Records / Access Log / Notifications /
Agreements tabs. Annual notification template per 34 CFR 99.7
(reviewed by counsel). i18n in all 6 languages.

Closes R-18 / Task 18 from review-recommendations plan."
```

---

### Task 9 (R-21a): SOC 2 — engage auditor + select Vanta or Drata

**This is a process task. No code changes; tracked here so it's not forgotten.**

Output: signed engagement letter and chosen evidence-collection vendor.

- [ ] **Step 1: Request quotes from 3 SOC 2 audit firms**

Recommended (based on Gap Analysis §12 cost guidance, $30-50K):
- A-LIGN, Schellman, Prescient Assurance

Scope: Type II audit covering Security, Availability, and Confidentiality Trust Service Criteria. Observation period: 6 months.

- [ ] **Step 2: Evaluate evidence-collection platforms**

Evaluate Vanta, Drata, and Secureframe. Decision criteria:
- Integrations with current stack (GitHub, AWS or Render, Stripe, SendGrid)
- Pricing for our size (< 50 employees)
- Auditor compatibility (does our chosen audit firm work with this platform?)

- [ ] **Step 3: Sign engagement + provision platform**

Output: SOW signed, platform provisioned, kickoff date confirmed. Observation window must start by **end of Week 4** for a Q1 2027 close (Task 31).

- [ ] **Step 4: Document the decision**

Add a note to `docs/compliance/soc2/engagement.md` recording auditor name, platform vendor, kickoff date, target close date, and primary contacts on each side.

- [ ] **Step 5: Commit the decision doc**

```bash
git add docs/compliance/soc2/engagement.md
git commit -m "docs(soc2): record auditor + platform engagement decision

Begins R-21 (SOC 2 Type II) from review-recommendations plan. Audit
period observation window opens this week."
```

---

### Task 10 (R-21b): SOC 2 — gap assessment + control inventory

**Files:**
- Create: `scripts/soc2/control_inventory.yaml`
- Create: `scripts/soc2/evidence_collector.py`
- Create: `docs/compliance/soc2/gap_assessment.md`

- [ ] **Step 1: Build the control inventory**

Create `scripts/soc2/control_inventory.yaml` listing all SOC 2 Trust Service Criteria controls and how each is met:

```yaml
# SOC 2 Type II Control Inventory — Bhapi
# Maps each Trust Service Criteria control to evidence and owner
controls:
  CC1.1:
    description: "Demonstrates commitment to integrity and ethical values"
    evidence: ["docs/compliance/code_of_conduct.md", "hr/employee_handbook.pdf"]
    owner: "leadership"
    status: "met"
  CC2.1:
    description: "Communicates information to support functioning of internal control"
    evidence: ["docs/operations/incident_response_plan.md", "Slack #security channel logs"]
    owner: "security"
    status: "met"
  CC6.1:
    description: "Logical and physical access controls restrict access"
    evidence: ["AWS IAM policies", "src/auth/ — JWT + RBAC", "Render team membership"]
    owner: "engineering"
    status: "met"
  CC6.6:
    description: "Encryption at rest and in transit"
    evidence: ["src/encryption.py — Fernet/KMS", "PostgreSQL TLS config", "Render TLS termination"]
    owner: "engineering"
    status: "met"
  CC7.1:
    description: "Detection of security events"
    evidence: ["structlog correlation IDs", "Render audit logs", "src/intelligence/anomaly.py"]
    owner: "security"
    status: "met"
  # ... continue for all relevant controls (Security, Availability, Confidentiality)
```

(The full TSC catalog has ~100 controls. Map every applicable control. Mark `status: gap` for any not currently met — these become Phase 4 work items.)

- [ ] **Step 2: Build the evidence collector**

Create `scripts/soc2/evidence_collector.py` that exports per-quarter evidence the auditor needs:
- Access logs (from FERPA module + auth audit logs)
- Change history (`git log --since="3 months ago"`)
- Backup/restore test records
- Incident reports
- Access-review attestations

- [ ] **Step 3: Document the gap assessment**

Create `docs/compliance/soc2/gap_assessment.md` with:
- Each control with `status: gap`
- Remediation plan + owner per gap
- Target close date (must be inside the observation window — at least 4 weeks of "control operating effectively" needed before close)

- [ ] **Step 4: Commit**

```bash
git add scripts/soc2/ docs/compliance/soc2/
git commit -m "feat(soc2): add control inventory + evidence collector + gap assessment

Maps SOC 2 TSC controls to existing evidence sources. Identifies gaps
that must close before audit window ends (Q1 2027). Evidence collector
script exports per-quarter audit packages.

Part of R-21 from review-recommendations plan."
```

---

## Layer 2: Platform & Ecosystem (Weeks 7-14)

Builds the public face of the platform: portal pages for backend modules that lack UI, public API GA, SDKs, and the cross-customer intelligence network.

---

### Tasks 11-14 (R-19): Portal pages for location, screen-time, creative, insights

These four pages follow the same pattern. Implement each as a separate task; the structure below is the template — replace `LOCATION` with the relevant module per task.

**Per-page template:**

**Files:**
- Create: `portal/src/app/(dashboard)/<page>/page.tsx`
- Create: `portal/src/hooks/use-<feature>.ts`
- Modify: `portal/messages/{en,fr,es,de,pt,it}.json` (add namespace)
- Modify: `portal/src/components/Sidebar.tsx` (add nav entry, role-gated)

#### Per-page steps

- [ ] **Step 1: Add i18n namespace to all 6 message files**

Example for location:
```json
"location": {
  "title": "Location",
  "subtitle": "Where your children are throughout the day",
  "geofences": "Geofences",
  "checkIn": "School Check-in",
  "history": "Location History",
  "killSwitch": "Disable location tracking",
  "empty": "No location data yet — install the mobile agent on your child's device to begin tracking."
}
```

- [ ] **Step 2: Create the React Query hook**

In `portal/src/hooks/use-location.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export function useGeofences() {
  return useQuery({ queryKey: ['location', 'geofences'], queryFn: () => apiClient.get('/api/v1/location/geofences') });
}

export function useLocationHistory(memberId: string, days = 7) {
  return useQuery({
    queryKey: ['location', 'history', memberId, days],
    queryFn: () => apiClient.get(`/api/v1/location/history?member_id=${memberId}&days=${days}`),
  });
}

export function useKillSwitch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiClient.post('/api/v1/location/kill-switch'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['location'] }),
  });
}
```

- [ ] **Step 3: Create the page**

Create `portal/src/app/(dashboard)/location/page.tsx` following the pattern in existing pages (e.g., `portal/src/app/(dashboard)/governance/page.tsx`). Use:
- `useTranslations('location')` for all copy
- Loading/error/empty states (use `EmptyState` component)
- React Query hooks above
- Tailwind via existing utility classes
- Lucide icons only

For location specifically: include a map view (use react-leaflet or similar — match what mobile app uses for consistency).

- [ ] **Step 4: Wire into sidebar (role-gated)**

In `portal/src/components/Sidebar.tsx`, add the entry to the `family` and (where relevant) `school` role lists.

- [ ] **Step 5: Type check + tests**

```bash
cd C:/claude/bhapi-ai-portal/portal && npx tsc --noEmit && npx vitest run
```
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add portal/src/app/\(dashboard\)/location/ portal/src/hooks/use-location.ts portal/messages/ portal/src/components/Sidebar.tsx
git commit -m "feat(portal): add location dashboard page

Map view, geofence list, school check-in log, location history timeline,
kill switch. Wired to /api/v1/location/* endpoints (Phase 3 module).
Role-gated to family + school in sidebar.

Part of R-19 from review-recommendations plan."
```

**Repeat steps 1-6 for:**
- Task 12: Screen-time page (`/screen-time`) — per-app usage chart, schedule, extension request inbox
- Task 13: Creative review page (`/creative`) — gallery of AI art/stories/stickers, moderation status, approve/reject
- Task 14: Insights page (`/insights`) — social-graph viz, anomaly alerts, correlation analysis, trend lines

---

### Task 15 (R-20): Contextual onboarding cards

**Files:**
- Create: `portal/src/components/ui/OnboardingCard.tsx`
- Modify: `portal/src/app/(dashboard)/{alerts,activity,safety,members}/page.tsx`

Full implementation follows `docs/superpowers/plans/2026-04-12-review-recommendations-implementation.md` Task 20 (lines 1432-1522). Reproduce the component verbatim and add cards to the four pages with the suggested copy.

- [ ] **Step 1: Create the OnboardingCard component**

Create `portal/src/components/ui/OnboardingCard.tsx` as in the source plan.

- [ ] **Step 2: Add cards to the 4 priority pages**

Per the source plan: alerts, activity, safety, members. Use the suggested copy.

- [ ] **Step 3: Type check + tests**

```bash
cd C:/claude/bhapi-ai-portal/portal && npx tsc --noEmit && npx vitest run
```

- [ ] **Step 4: Commit**

```bash
git add portal/src/components/ui/OnboardingCard.tsx portal/src/app/
git commit -m "feat(portal): add dismissible contextual onboarding cards on key pages

Replaces missing onboarding flow noted in F-038. Cards persist dismissed
state in localStorage. Tealboard styling matches Calm Safety design.

Closes R-20 from review-recommendations plan."
```

---

### Task 16 (P4-API1): Public API GA — rate-tier plans + usage metering

**Files:**
- Create: `src/api_platform/tiers.py`
- Create: `src/api_platform/usage_metering.py`
- Create: `alembic/versions/057_api_platform_tiers.py`
- Modify: `src/api_platform/router.py` — wire tiers into key issuance
- Modify: `alembic/env.py`
- Test: `tests/unit/test_api_tiers.py`, `tests/e2e/test_api_metering.py`

- [ ] **Step 1: Define the four tiers**

Create `src/api_platform/tiers.py`:

```python
"""Public API rate-limit tiers. Defines per-tier limits + features for each plan."""
from dataclasses import dataclass


@dataclass(frozen=True)
class APITier:
    name: str
    monthly_request_quota: int
    requests_per_minute: int
    webhooks_enabled: bool
    sandbox_only: bool
    price_monthly: float


FREE_TIER = APITier("free", 10_000, 60, False, True, 0.0)
DEVELOPER_TIER = APITier("developer", 100_000, 300, True, False, 49.0)
BUSINESS_TIER = APITier("business", 1_000_000, 1500, True, False, 299.0)
ENTERPRISE_TIER = APITier("enterprise", 10_000_000, 6000, True, False, 1499.0)

TIERS = {t.name: t for t in [FREE_TIER, DEVELOPER_TIER, BUSINESS_TIER, ENTERPRISE_TIER]}


def get_tier(name: str) -> APITier:
    if name not in TIERS:
        raise ValueError(f"Unknown API tier: {name}")
    return TIERS[name]
```

- [ ] **Step 2: Define usage metering models**

Create `src/api_platform/usage_metering.py`:

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import ForeignKey, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from src.models import Base, UUIDMixin, TimestampMixin


class APIKeyTier(Base, UUIDMixin, TimestampMixin):
    """Assigns an API key to a tier."""
    __tablename__ = "api_key_tiers"
    api_key_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_keys.id"), unique=True, index=True)
    tier_name: Mapped[str] = mapped_column(String(32))


class APIUsageRecord(Base, UUIDMixin, TimestampMixin):
    """One row per API request — used for per-minute rate limiting check."""
    __tablename__ = "api_usage_records"
    api_key_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_keys.id"), index=True)
    endpoint: Mapped[str] = mapped_column(String(256))
    status_code: Mapped[int]
    response_time_ms: Mapped[int]


class MonthlyUsageAggregate(Base, UUIDMixin, TimestampMixin):
    """Pre-aggregated monthly counts for quota enforcement + billing."""
    __tablename__ = "api_usage_monthly_aggregates"
    api_key_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_keys.id"), index=True)
    year_month: Mapped[str] = mapped_column(String(7), index=True)  # "2026-10"
    request_count: Mapped[int] = mapped_column(BigInteger, default=0)
```

- [ ] **Step 3: Wire models into alembic and generate migration**

```bash
cd C:/claude/bhapi-ai-portal && alembic revision --autogenerate -m "add API platform tiers and usage metering"
```

Verify the migration in `alembic/versions/057_*.py` includes all 3 tables. Add the import in `alembic/env.py`.

- [ ] **Step 4: Write failing test for quota enforcement**

In `tests/e2e/test_api_metering.py`:

```python
@pytest.mark.asyncio
async def test_free_tier_request_quota_enforced(client, api_key_free_tier):
    """Free tier returns 429 once monthly quota exhausted."""
    # Pre-populate monthly aggregate at quota
    # ... (set MonthlyUsageAggregate.request_count = 10_000)

    response = await client.get(
        "/api/v1/platform/test-endpoint",
        headers={"Authorization": f"Bearer {api_key_free_tier}"},
    )
    assert response.status_code == 429
    assert "quota" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_per_minute_rate_limit_enforced(client, api_key_free_tier):
    """Free tier rejects bursts above 60 RPM."""
    # Make 60 requests quickly — should succeed
    for _ in range(60):
        await client.get("/api/v1/platform/test-endpoint",
                         headers={"Authorization": f"Bearer {api_key_free_tier}"})
    # 61st within the same minute → 429
    response = await client.get("/api/v1/platform/test-endpoint",
                                headers={"Authorization": f"Bearer {api_key_free_tier}"})
    assert response.status_code == 429
```

- [ ] **Step 5: Implement enforcement middleware**

In `src/api_platform/router.py`, add a dependency or middleware that:
1. Looks up the API key's tier (via `APIKeyTier`)
2. Checks `MonthlyUsageAggregate.request_count` against `tier.monthly_request_quota`
3. Checks per-minute window via Redis sliding window (key: `api_rpm:{api_key_id}:{minute}`)
4. On allow: record `APIUsageRecord` and increment monthly aggregate
5. On reject: return 429 with `Retry-After` header

- [ ] **Step 6: Run tests**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/e2e/test_api_metering.py tests/unit/test_api_tiers.py --no-cov -v
```
Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add src/api_platform/ alembic/versions/057_*.py alembic/env.py tests/
git commit -m "feat(api_platform): GA — 4 rate-limit tiers with usage metering and quota enforcement

Free / Developer / Business / Enterprise tiers with monthly quotas
(10k/100k/1M/10M) and per-minute limits (60/300/1500/6000). Redis
sliding window for RPM, monthly aggregate table for quota. Returns
429 with Retry-After when exceeded.

Implements P4-API1 from Phase 4 plan."
```

---

### Task 17 (P4-API2): SDKs — Python, JS, Swift, Kotlin (auto-generated)

**Files:**
- Create: `scripts/generate_sdk.py`
- Create: `src/api_platform/openapi_export.py`
- Create: `sdks/python/`, `sdks/js/`, `sdks/swift/`, `sdks/kotlin/`
- Create: `.github/workflows/sdk_release.yml`

- [ ] **Step 1: Add OpenAPI export endpoint**

In `src/api_platform/openapi_export.py`, add a function that generates a clean OpenAPI 3.1 spec for only the public API (filter out internal endpoints):

```python
from fastapi.openapi.utils import get_openapi


def export_public_openapi(app) -> dict:
    spec = get_openapi(
        title="Bhapi Public API",
        version="1.0.0",
        description="Public API for the Bhapi Family AI Governance Platform",
        routes=[r for r in app.routes if r.path.startswith("/api/v1/platform/")],
    )
    spec["servers"] = [{"url": "https://api.bhapi.ai"}]
    return spec
```

Add a CLI entry point in `scripts/generate_sdk.py` that exports the spec to `sdks/openapi.json`.

- [ ] **Step 2: Generate SDKs via openapi-generator**

```bash
cd C:/claude/bhapi-ai-portal && python scripts/generate_sdk.py
# Then for each language:
npx @openapitools/openapi-generator-cli generate \
  -i sdks/openapi.json -g python -o sdks/python -p packageName=bhapi
npx @openapitools/openapi-generator-cli generate \
  -i sdks/openapi.json -g typescript-fetch -o sdks/js
npx @openapitools/openapi-generator-cli generate \
  -i sdks/openapi.json -g swift5 -o sdks/swift
npx @openapitools/openapi-generator-cli generate \
  -i sdks/openapi.json -g kotlin -o sdks/kotlin
```

- [ ] **Step 3: Add a smoke test per SDK**

For each SDK, write a minimal integration test that imports the client and makes a no-op request against a mock server (or against `pytest`'s test client for Python; mock-fetch for JS).

- [ ] **Step 4: Add release workflow**

Create `.github/workflows/sdk_release.yml` that:
1. Regenerates SDKs from current OpenAPI spec
2. Bumps SDK version
3. Publishes Python to PyPI, JS to npm, Swift to SwiftPM, Kotlin to Maven Central
4. Triggers on tagged releases

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_sdk.py src/api_platform/openapi_export.py sdks/ .github/workflows/sdk_release.yml
git commit -m "feat(api_platform): generate Python/JS/Swift/Kotlin SDKs from OpenAPI spec

Auto-generated SDKs in sdks/{python,js,swift,kotlin}. CI workflow
publishes on tagged releases. OpenAPI 3.1 spec exported via
src/api_platform/openapi_export.py — filters to /api/v1/platform/* only.

Implements P4-API2 from Phase 4 plan."
```

---

### Task 18 (P4-NET1): Intelligence network models + migrations 055-056

**Files:**
- Create: `src/intelligence_network/__init__.py`
- Create: `src/intelligence_network/models.py`
- Create: `src/intelligence_network/anonymizer.py`
- Create: `alembic/versions/055_intel_network_signals.py`
- Create: `alembic/versions/056_intel_network_deliveries.py`
- Modify: `alembic/env.py`

- [ ] **Step 1: Create module + define models**

Create `src/intelligence_network/models.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, JSON, String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from src.models import Base, UUIDMixin, TimestampMixin


class ThreatSignal(Base, UUIDMixin, TimestampMixin):
    """An anonymized threat signal contributed to the network.
    Anonymization runs in src.intelligence_network.anonymizer before insertion."""
    __tablename__ = "intel_network_threat_signals"

    # NOTE: NO direct group_id or member_id — anonymization strips identifiers
    signal_type: Mapped[str] = mapped_column(String(64), index=True)  # phishing_pattern, dependency_indicator, etc.
    severity: Mapped[str] = mapped_column(String(16))
    pattern_data: Mapped[dict] = mapped_column(JSON)  # k-anonymized pattern features
    sample_size: Mapped[int]  # Number of source events aggregated
    contributor_region: Mapped[str | None] = mapped_column(String(8), nullable=True)  # Coarse region only
    confidence: Mapped[float]


class NetworkSubscription(Base, UUIDMixin, TimestampMixin):
    """A group's subscription to receive intelligence network signals."""
    __tablename__ = "intel_network_subscriptions"
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    signal_types: Mapped[list[str]] = mapped_column(JSON, default=list)  # filter by type
    minimum_severity: Mapped[str] = mapped_column(String(16), default="medium")


class SignalDelivery(Base, UUIDMixin, TimestampMixin):
    """Audit log of signal deliveries to subscribers."""
    __tablename__ = "intel_network_signal_deliveries"
    subscription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intel_network_subscriptions.id"), index=True)
    signal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intel_network_threat_signals.id"), index=True)
    delivered_at: Mapped[datetime]
    acknowledged: Mapped[bool] = mapped_column(default=False)


class AnonymizationAudit(Base, UUIDMixin, TimestampMixin):
    """Audit trail of the anonymization process per signal — for compliance review."""
    __tablename__ = "intel_network_anonymization_audit"
    signal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("intel_network_threat_signals.id"), index=True)
    technique: Mapped[str] = mapped_column(String(64))  # k_anonymity, dp_noise, generalization
    parameters: Mapped[dict] = mapped_column(JSON)
```

- [ ] **Step 2: Create the anonymizer**

Create `src/intelligence_network/anonymizer.py`:

```python
"""Anonymization for intelligence network signals.
Combines k-anonymity (group quasi-identifiers) and differential-privacy noise."""
import hashlib
import secrets
from typing import Any


def k_anonymize(records: list[dict], quasi_identifiers: list[str], k: int = 5) -> list[dict]:
    """Generalize quasi-identifiers so each combination appears at least k times.
    Records that can't be k-anonymized are dropped."""
    # Group by quasi-identifier tuple
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        key = tuple(r.get(qi) for qi in quasi_identifiers)
        groups.setdefault(key, []).append(r)
    # Drop groups smaller than k
    return [r for key, rs in groups.items() if len(rs) >= k for r in rs]


def add_dp_noise(value: float, epsilon: float = 1.0) -> float:
    """Add Laplace noise calibrated for differential privacy."""
    import random
    scale = 1.0 / epsilon
    # Laplace noise via inverse CDF
    u = random.random() - 0.5
    return value - scale * (1 if u >= 0 else -1) * abs(u)


def hash_identifier(value: str, salt: str = "") -> str:
    """One-way hash for identifiers we need to count uniques but not recover."""
    return hashlib.sha256((salt + value).encode()).hexdigest()[:16]


def anonymize_signal(raw_event: dict) -> dict:
    """Transform a single event into an anonymized signal payload."""
    # Strip direct identifiers
    payload = {k: v for k, v in raw_event.items() if k not in {"user_id", "member_id", "email", "name"}}
    # Generalize timestamps to hour-of-day buckets
    if "timestamp" in payload:
        payload["hour_of_day"] = payload["timestamp"].hour if hasattr(payload["timestamp"], "hour") else None
        del payload["timestamp"]
    # Coarsen location to country-level if present
    if "location" in payload and isinstance(payload["location"], dict):
        payload["region"] = payload["location"].get("country")
        del payload["location"]
    return payload
```

- [ ] **Step 3: Generate migrations**

```bash
cd C:/claude/bhapi-ai-portal && alembic revision --autogenerate -m "add intel network threat signals + subscriptions"
# Then split into two migration files: 055 (signals + subscriptions) and 056 (deliveries + audit)
```

Or, simpler: produce one migration file with all four tables. Renumber so it lands at `055_*.py`. (Splitting is optional — was suggested for readability but a single migration is fine.)

- [ ] **Step 4: Apply migration locally**

```bash
cd C:/claude/bhapi-ai-portal && alembic upgrade head
```

- [ ] **Step 5: Verify migration tracked**

```bash
git status alembic/versions/
```
Migration files MUST appear.

- [ ] **Step 6: Commit**

```bash
git add src/intelligence_network/ alembic/versions/055_*.py alembic/env.py
git commit -m "feat(intel_network): add anonymized threat signal models + anonymizer

Models: ThreatSignal, NetworkSubscription, SignalDelivery, AnonymizationAudit.
Anonymizer applies k-anonymity (k=5 default), differential-privacy Laplace
noise, identifier hashing, and quasi-identifier generalization. Audit
trail per anonymization for compliance review.

Part of P4-NET1/P4-NET2 from Phase 4 plan."
```

---

### Task 19 (P4-NET2): Intelligence network — service, router, cross-customer threat distribution

**Files:**
- Create: `src/intelligence_network/service.py`
- Create: `src/intelligence_network/router.py`
- Create: `portal/src/app/(dashboard)/intel-network/page.tsx`
- Modify: `src/main.py` (register router)
- Modify: `portal/messages/*.json` (add `intelNetwork` namespace)
- Test: `tests/unit/test_intel_network.py`, `tests/e2e/test_intel_network.py`, `tests/security/test_intel_network_anonymization.py`

- [ ] **Step 1: Write failing security test for anonymization**

In `tests/security/test_intel_network_anonymization.py`:

```python
@pytest.mark.asyncio
async def test_no_pii_in_distributed_signals(test_session):
    """Signals delivered to subscribers must not contain PII or group identifiers."""
    from src.intelligence_network.service import contribute_signal, fetch_signals_for_subscriber

    # Contribute a signal containing PII
    raw_event = {
        "user_id": "user-12345",
        "email": "alice@example.com",
        "member_id": "member-67890",
        "pattern": "phishing_link_detected",
        "timestamp": datetime.now(timezone.utc),
        "location": {"country": "US", "city": "San Francisco", "lat": 37.7, "lng": -122.4},
    }
    signal = await contribute_signal(test_session, group_id=uuid4(), raw_event=raw_event)

    # Fetch as a subscriber
    delivered = await fetch_signals_for_subscriber(test_session, subscription_group_id=uuid4())

    for sig in delivered:
        assert "user_id" not in sig.pattern_data
        assert "email" not in sig.pattern_data
        assert "member_id" not in sig.pattern_data
        assert "lat" not in sig.pattern_data
        assert "lng" not in sig.pattern_data
        # City should be coarsened to country-level
        assert "city" not in sig.pattern_data


@pytest.mark.asyncio
async def test_signals_below_k_threshold_not_distributed(test_session):
    """A signal type with fewer than k=5 contributing groups is not distributed."""
    # Contribute one signal of a unique type from a single group
    # Verify it does NOT appear in any subscriber's feed
    pass
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/security/test_intel_network_anonymization.py --no-cov -v`
Expected: FAIL (functions don't exist).

- [ ] **Step 3: Implement service**

Create `src/intelligence_network/service.py`:

```python
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.intelligence_network.models import (
    ThreatSignal, NetworkSubscription, SignalDelivery, AnonymizationAudit,
)
from src.intelligence_network.anonymizer import anonymize_signal


async def contribute_signal(
    db: AsyncSession, group_id: uuid.UUID, raw_event: dict
) -> ThreatSignal:
    """Contribute a raw event to the network — runs anonymization first."""
    anonymized = anonymize_signal(raw_event)

    signal = ThreatSignal(
        signal_type=raw_event.get("pattern", "unknown"),
        severity=raw_event.get("severity", "medium"),
        pattern_data=anonymized,
        sample_size=1,
        contributor_region=anonymized.get("region"),
        confidence=raw_event.get("confidence", 0.5),
    )
    db.add(signal)
    await db.flush()

    audit = AnonymizationAudit(
        signal_id=signal.id,
        technique="anonymize_signal_v1",
        parameters={"stripped": ["user_id", "email", "member_id", "location"]},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(signal)
    return signal


async def fetch_signals_for_subscriber(
    db: AsyncSession, subscription_group_id: uuid.UUID, limit: int = 50
) -> list[ThreatSignal]:
    """Return signals matching a group's subscription preferences.
    Excludes signals whose signal_type has fewer than k=5 contributors."""
    sub = (await db.execute(
        select(NetworkSubscription).where(NetworkSubscription.group_id == subscription_group_id)
    )).scalar_one_or_none()
    if not sub or not sub.enabled:
        return []

    # k-anonymity at the signal_type level: only distribute types with >=5 contributors
    # (tracked via sample_size on aggregated signals — emit aggregates, not raw signals)
    stmt = select(ThreatSignal).where(ThreatSignal.sample_size >= 5)
    if sub.signal_types:
        stmt = stmt.where(ThreatSignal.signal_type.in_(sub.signal_types))
    severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    min_sev = severity_order.get(sub.minimum_severity, 1)
    stmt = stmt.order_by(ThreatSignal.created_at.desc()).limit(limit)
    signals = list((await db.execute(stmt)).scalars().all())

    # Filter by severity in Python (severity strings need ordering)
    signals = [s for s in signals if severity_order.get(s.severity, 0) >= min_sev]

    # Audit deliveries
    for s in signals:
        db.add(SignalDelivery(subscription_id=sub.id, signal_id=s.id,
                              delivered_at=datetime.now(timezone.utc)))
    await db.commit()
    return signals
```

- [ ] **Step 4: Implement router + portal page**

Router (`src/intelligence_network/router.py`):
- `POST /api/v1/intel-network/subscribe` — opt in
- `DELETE /api/v1/intel-network/subscribe` — opt out
- `GET /api/v1/intel-network/feed` — fetch signals for the authenticated group
- `POST /api/v1/intel-network/feedback` — mark signal as helpful/false-positive (improves future filtering)

Portal page (`portal/src/app/(dashboard)/intel-network/page.tsx`) — list view of recent signals, severity badges, opt-in toggle, signal-type filter.

- [ ] **Step 5: Run tests**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/unit/test_intel_network.py tests/e2e/test_intel_network.py tests/security/test_intel_network_anonymization.py --no-cov -v
cd C:/claude/bhapi-ai-portal/portal && npx tsc --noEmit && npx vitest run
```
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/intelligence_network/ src/main.py portal/src/app/\(dashboard\)/intel-network/ portal/messages/ tests/
git commit -m "feat(intel_network): cross-customer anonymized threat signal sharing

Subscribers receive aggregated, k-anonymized (k=5) threat signals from
across the customer base. Contribution flow runs anonymizer before
insertion. Audit trail per anonymization. Opt-in only — subscriptions
default to disabled. Portal page shows feed + opt-in toggle + filters.

Implements P4-NET2 from Phase 4 plan. Foundation for community moat."
```

---

## Layer 3: Bundles & International (Weeks 15-22)

Counters Aura's bundle play, opens international markets, closes the school-pricing review recommendation.

---

### Task 20 (R-22): School pricing — $1.99/seat + free 90-day pilot

**Files:**
- Modify: `src/billing/plans.py`
- Create: Stripe Dashboard objects (manual — record IDs)
- Test: `tests/unit/test_billing_plans.py`

- [ ] **Step 1: Read current school plan definition**

```bash
cd C:/claude/bhapi-ai-portal && grep -n "SCHOOL\|school" src/billing/plans.py | head -30
```

- [ ] **Step 2: Update the school plan and add pilot**

In `src/billing/plans.py`, replace the `SCHOOL_PLAN` definition and add `SCHOOL_PILOT_PLAN`:

```python
SCHOOL_PLAN = {
    "name": "School",
    "id": "school_v2",  # bumped — old is "school_v1"
    "price_monthly": 1.99,  # was 2.99 — Phase 4 R-22 reduction
    "price_annual": 19.99,
    "per_seat": True,
    "features": [...]  # carry forward existing list
}

SCHOOL_PILOT_PLAN = {
    "name": "School Pilot",
    "id": "school_pilot",
    "price_monthly": 0,
    "per_seat": True,
    "max_seats": 50,
    "duration_days": 90,
    "auto_convert_to": "school_v2",  # at end of pilot, convert to paid school plan
    "features": [...]  # full feature parity with paid School
}
```

- [ ] **Step 3: Write failing test**

In `tests/unit/test_billing_plans.py`:

```python
def test_school_plan_priced_at_1_99():
    from src.billing.plans import SCHOOL_PLAN
    assert SCHOOL_PLAN["price_monthly"] == 1.99


def test_school_pilot_is_free_and_capped():
    from src.billing.plans import SCHOOL_PILOT_PLAN
    assert SCHOOL_PILOT_PLAN["price_monthly"] == 0
    assert SCHOOL_PILOT_PLAN["max_seats"] == 50
    assert SCHOOL_PILOT_PLAN["duration_days"] == 90
```

- [ ] **Step 4: Run test, verify it passes**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/unit/test_billing_plans.py --no-cov -v
```

- [ ] **Step 5: Create new Stripe price IDs**

In Stripe Dashboard:
1. Create a new monthly price for `school_v2` at $1.99 USD/month per seat
2. Create a new annual price at $19.99 USD/year per seat
3. Create a $0 price for `school_pilot` (use Stripe trials or zero-priced subscription)
4. Record the new price IDs in `src/billing/plans.py` (or `.env` per existing pattern)

**This step touches production billing — get user confirmation before flipping the price ID switch in production.**

- [ ] **Step 6: Commit**

```bash
git add src/billing/plans.py tests/unit/test_billing_plans.py
git commit -m "feat(billing): School tier reduced to \$1.99/seat/mo; add free 90-day pilot

Was \$2.99/seat. Reduction undercuts GoGuardian (\$4-8/student/year)
and Gaggle (\$3.75-6/student/year) while remaining sustainable above
infrastructure cost. Free pilot plan (50 seats, 90 days, auto-converts
to paid) matches GoGuardian's pilot strategy.

Implements R-22 from review-recommendations plan. Phase 4 Task 20."
```

---

### Task 21 (P4-B1): Bhapi Family+ bundle tier ($19.99/mo)

**Files:**
- Modify: `src/billing/plans.py`
- Modify: `src/billing/feature_gate.py`
- Create: `alembic/versions/058_family_plus_features.py`
- Test: `tests/e2e/test_family_plus_bundle.py`

- [ ] **Step 1: Define the bundle tier**

In `src/billing/plans.py`, add:

```python
FAMILY_PLUS_PLAN = {
    "name": "Bhapi Family+",
    "id": "family_plus",
    "price_monthly": 19.99,
    "price_annual": 199.99,
    "per_seat": False,
    "max_family_members": 8,  # higher than base Family (5)
    "features": [
        "ai_monitoring_all_platforms",
        "social_app_access",
        "device_agent",
        "screen_time_management",
        "location_tracking",
        "creative_tools",
        "intel_network_signals",
        "identity_protection_partner",  # Phase 4 Task 22
        "priority_support",
    ],
}
```

- [ ] **Step 2: Add feature gate entries via migration**

Generate migration 058 that seeds `FeatureGate` rows for the new `family_plus` features. Apply locally and verify.

- [ ] **Step 3: Write E2E test**

In `tests/e2e/test_family_plus_bundle.py`:

```python
@pytest.mark.asyncio
async def test_family_plus_unlocks_all_premium_features(client, family_plus_user_headers):
    """A Family+ subscriber has all premium feature gates open."""
    for feature in [
        "screen_time_management", "location_tracking", "creative_tools",
        "intel_network_signals", "identity_protection_partner",
    ]:
        response = await client.get(
            f"/api/v1/billing/feature-check?feature={feature}",
            headers=family_plus_user_headers,
        )
        assert response.status_code == 200
        assert response.json()["allowed"] is True


@pytest.mark.asyncio
async def test_base_family_does_not_have_family_plus_features(client, family_user_headers):
    """A base Family subscriber does NOT have Family+ premium features."""
    response = await client.get(
        "/api/v1/billing/feature-check?feature=identity_protection_partner",
        headers=family_user_headers,
    )
    assert response.status_code == 200
    assert response.json()["allowed"] is False
```

- [ ] **Step 4: Run test, verify pass**

- [ ] **Step 5: Create Stripe price IDs**

Same as Task 20 Step 5 — create new Stripe products + prices for `family_plus`. **Confirm with user before flipping production.**

- [ ] **Step 6: Commit**

```bash
git add src/billing/plans.py src/billing/feature_gate.py alembic/versions/058_*.py tests/
git commit -m "feat(billing): launch Bhapi Family+ bundle tier (\$19.99/mo, all features + identity)

Bundles AI monitoring + Social app + device agent + screen time +
location + creative + intel network + identity-protection partnership
+ priority support into a single \$19.99/mo plan. Counters Aura's
bundled value play (\$32/mo for less depth in AI monitoring).

Implements P4-B1 from Phase 4 plan."
```

---

### Task 22 (P4-B2): Identity protection partnership integration

**Files:**
- Create: `src/billing/partnerships.py`
- Create: `alembic/versions/059_identity_protection_links.py`
- Modify: `src/billing/router.py`
- Test: `tests/e2e/test_identity_partnership.py`

**Prerequisites — process work before code:**
1. Identify and sign agreement with identity-protection partner (e.g., Aura via API, IDX, Identity Guard, or LifeLock if API access available). This is a business-development task. Output: API credentials + partner contact + revenue share terms.
2. Confirm legal: cross-product data sharing requires explicit consent from each user (Family+ subscription opt-in not sufficient — separate `identity_protection_consent` flag needed).

- [ ] **Step 1: Create partnership integration module**

Create `src/billing/partnerships.py` with:
- Partner API client (httpx async, `bhapi_partnership_api_key` env var)
- `provision_identity_protection(user_id, email, dependents)` — registers user with partner
- `revoke_identity_protection(user_id)` — cancels on Bhapi-side cancellation
- Webhook handler for partner callbacks (account verified, alert raised, etc.)

- [ ] **Step 2: Define link table**

Migration 059 adds:
```python
class IdentityProtectionLink(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "identity_protection_links"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    partner_account_id: Mapped[str] = mapped_column(String(128))
    consent_given_at: Mapped[datetime]
    consent_text_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="active")  # active, suspended, cancelled
```

- [ ] **Step 3: Wire into Family+ activation**

When a user starts a Family+ subscription, surface a one-time consent flow: "Activate your bundled identity protection?" → on consent, call `provision_identity_protection()` and create the link.

- [ ] **Step 4: Write E2E test**

In `tests/e2e/test_identity_partnership.py`:

```python
@pytest.mark.asyncio
async def test_family_plus_activation_offers_identity_protection(client, family_plus_user_headers, monkeypatch):
    """After Family+ subscription activation, identity protection consent is offered."""
    # Mock partner API
    monkeypatch.setattr(
        "src.billing.partnerships.partner_client.create_account",
        AsyncMock(return_value={"account_id": "partner-12345"}),
    )

    response = await client.post(
        "/api/v1/billing/identity-protection/activate",
        json={"consent_text_version": "v1", "agreed": True},
        headers=family_plus_user_headers,
    )
    assert response.status_code == 201
    assert response.json()["partner_account_id"] == "partner-12345"


@pytest.mark.asyncio
async def test_identity_protection_requires_explicit_consent(client, family_plus_user_headers):
    """Activation rejects requests without explicit consent."""
    response = await client.post(
        "/api/v1/billing/identity-protection/activate",
        json={"agreed": False},
        headers=family_plus_user_headers,
    )
    assert response.status_code == 400
```

- [ ] **Step 5: Run tests**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/e2e/test_identity_partnership.py --no-cov -v
```

- [ ] **Step 6: Commit**

```bash
git add src/billing/partnerships.py alembic/versions/059_*.py src/billing/router.py tests/
git commit -m "feat(partnerships): integrate identity-protection partner API for Family+

Provisions identity-protection partner account on Family+ activation
with explicit per-user consent (separate from subscription consent).
Webhook handler for partner-side alerts. Audit trail of consent text
version for legal records.

Implements P4-B2 from Phase 4 plan. Counters Aura bundle without
acquiring an identity-protection product."
```

---

### Task 23 (R-24): AI bypass / VPN detection for schools

**Files:**
- Create: `src/blocking/vpn_detection.py`
- Create: `alembic/versions/060_bypass_attempts.py`
- Modify: `extension/src/content/monitor.ts`
- Modify: `src/blocking/router.py`
- Test: `tests/e2e/test_vpn_detection.py`

Full implementation pattern follows the source plan Task 24 (lines 1628-1662). Detect:
- VPN/proxy via WebRTC IP leak + DNS resolution anomaly
- Alternative AI URLs (chat.openai.com vs. OpenAI mirrors)
- Incognito mode
- Extension tampering (manifest hash check)

Backend:
- Receive bypass-attempt events
- Classify type
- Generate alerts (school-admin severity = high)
- Auto-block on 3+ attempts in 60min

- [ ] **Step 1: Add backend models + migration 060**

```python
class BypassAttempt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "bypass_attempts"
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("group_members.id"), index=True)
    bypass_type: Mapped[str] = mapped_column(String(32))  # vpn, proxy, alt_url, incognito, tampering
    detection_signals: Mapped[dict] = mapped_column(JSON)
    auto_blocked: Mapped[bool] = mapped_column(default=False)
```

- [ ] **Step 2: Implement detection in extension**

In `extension/src/content/monitor.ts`, add detection probes (WebRTC stun, manifest hash check, URL pattern match against alt-AI list). On detection, POST to `/api/v1/blocking/bypass-attempt`.

- [ ] **Step 3: Implement backend handler + auto-block logic**

`src/blocking/vpn_detection.py` — classify, persist, alert, optionally auto-block.

- [ ] **Step 4: Write E2E test**

```python
@pytest.mark.asyncio
async def test_three_bypass_attempts_within_hour_triggers_auto_block(client, school_extension_token):
    for _ in range(3):
        response = await client.post(
            "/api/v1/blocking/bypass-attempt",
            json={"bypass_type": "vpn", "detection_signals": {"webrtc_leak": True}},
            headers={"Authorization": f"Bearer {school_extension_token}"},
        )
        assert response.status_code == 201
    # Third attempt should have triggered auto-block
    response = await client.get("/api/v1/blocking/rules?member_id=...", headers=...)
    assert any(r["reason"] == "vpn_bypass_auto" for r in response.json()["items"])
```

- [ ] **Step 5: Run tests + commit**

```bash
git add src/blocking/ extension/src/ alembic/versions/060_*.py tests/
git commit -m "feat(blocking): VPN/proxy/incognito/tampering bypass detection

Extension probes for WebRTC IP leak, alt-AI URLs, incognito mode, and
manifest tampering. Backend classifies attempts, alerts school admins,
and auto-blocks after 3 attempts in 60 minutes. Matches Gaggle's
'blocks AI bypass attempts' capability.

Implements R-24 from review-recommendations plan."
```

---

### Task 24 (P4-INT1): UK AADC re-review compliance updates

**Files:**
- Modify: `src/compliance/uk_aadc.py` (or create if missing)
- Create: `alembic/versions/061_uk_region_consent.py`
- Modify: `src/auth/service.py` (registration flow — UK detection + AADC consent)
- Modify: `portal/src/app/(auth)/register/page.tsx`
- Test: `tests/e2e/test_uk_aadc_compliance.py`

Output: pass UK AADC re-review (deadline: 2026-12-31).

- [ ] **Step 1: Read current UK AADC implementation**

```bash
cd C:/claude/bhapi-ai-portal && find src/compliance -name "*uk*" -o -name "*aadc*"
```

- [ ] **Step 2: Engage UK legal counsel for the re-review**

Process step. Counsel reviews the 15 standards:
1. Best interests of the child · 2. Data Protection Impact Assessments · 3. Age-appropriate application · 4. Transparency · 5. Detrimental use of data · 6. Policies and community standards · 7. Default settings (high privacy) · 8. Data minimisation · 9. Data sharing · 10. Geolocation · 11. Parental controls · 12. Profiling · 13. Nudge techniques · 14. Connected toys · 15. Online tools.

Document the audit findings in `docs/compliance/uk_aadc_2026_review.md`.

- [ ] **Step 3: Implement remediation per finding**

Per each finding, create a sub-task. Common changes likely needed:
- Default geolocation OFF for under-18 UK users
- Stronger transparency pop-up at registration
- Disable any nudge techniques in mobile apps for under-18

- [ ] **Step 4: Add region-specific consent column**

Migration 061 adds `region_specific_consent JSON` to `consent_records`. Stores per-region consent metadata so AADC consent is verifiable.

- [ ] **Step 5: Update registration flow**

Detect UK users (geo-IP at registration); show AADC-specific consent screen; record consent in `region_specific_consent`.

- [ ] **Step 6: Write tests**

In `tests/e2e/test_uk_aadc_compliance.py`:

```python
@pytest.mark.asyncio
async def test_uk_user_sees_aadc_consent_at_registration(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "uk-test@example.com", "password": "...",
              "country_code": "GB", "privacy_notice_accepted": True},
    )
    # Should return a follow-up step requesting AADC consent
    assert response.status_code == 200
    body = response.json()
    assert body.get("requires_aadc_consent") is True


@pytest.mark.asyncio
async def test_uk_under_18_geolocation_default_off(client, uk_under_18_user_headers):
    response = await client.get("/api/v1/location/preferences", headers=uk_under_18_user_headers)
    assert response.json()["geolocation_enabled"] is False
```

- [ ] **Step 7: Commit**

```bash
git add src/compliance/uk_aadc.py src/auth/service.py portal/src/app/\(auth\)/register/page.tsx alembic/versions/061_*.py docs/compliance/ tests/
git commit -m "feat(compliance): UK AADC re-review updates — geolocation defaults, AADC consent screen

Per UK AADC re-review (counsel-led): geolocation default OFF for under-18
UK users, AADC-specific consent at registration with audit trail, removal
of nudge techniques in mobile apps for under-18. Region-specific consent
metadata in consent_records (migration 061).

Implements P4-INT1 from Phase 4 plan."
```

---

### Task 25 (P4-INT2): Australia eSafety production sign-off + audit

**Files:**
- Modify: `docs/compliance/australian-online-safety-analysis.md`
- Modify: `src/compliance/au_esafety.py` (if remediation needed)

**Process task — review existing implementation (already in CLAUDE.md as supported), confirm production sign-off, archive evidence.**

- [ ] **Step 1: Pull the current AU compliance analysis doc**

Read `docs/compliance/australian-online-safety-analysis.md` — identify any unresolved items.

- [ ] **Step 2: Run an evidence collection pass**

For each AU eSafety requirement, collect evidence (screenshots, code references, test runs) into `docs/compliance/au_esafety_evidence_2026q4/`.

- [ ] **Step 3: External reviewer or counsel sign-off**

Engage Australian legal counsel or eSafety-Commissioner-friendly reviewer for sign-off letter.

- [ ] **Step 4: Commit evidence + sign-off**

```bash
git add docs/compliance/au_esafety_evidence_2026q4/ docs/compliance/australian-online-safety-analysis.md
git commit -m "docs(compliance): Australia eSafety production sign-off — Phase 4

Counsel-reviewed evidence package for all eSafety requirements. AU
market formally cleared for marketing.

Implements P4-INT2 from Phase 4 plan."
```

---

### Task 26 (P4-INT3): NL / PL / SV i18n translations

**Files:**
- Create: `portal/messages/nl.json`, `pl.json`, `sv.json`
- Modify: `portal/src/contexts/LocaleContext.tsx` (register new locales)
- Modify: `mobile/packages/shared-i18n/` similarly

- [ ] **Step 1: Engage professional translation service**

Send the canonical `portal/messages/en.json` to a translation service (Lokalise, Phrase, or similar) for NL/PL/SV translations. Avoid machine translation only — use professional reviewers.

- [ ] **Step 2: Add the locale files**

Drop the returned JSON files into `portal/messages/{nl,pl,sv}.json`. Verify all keys present (compare to `en.json` key set).

- [ ] **Step 3: Register the locales in LocaleContext**

In `portal/src/contexts/LocaleContext.tsx`, add NL/PL/SV to the supported locales list.

- [ ] **Step 4: Repeat for mobile**

Mobile uses `mobile/packages/shared-i18n/` — add the same JSON files there.

- [ ] **Step 5: Smoke-test each locale**

Manually load each locale in a local dev server and visit 5 key pages — confirm no missing keys (look for raw `dashboard.title`-style strings).

- [ ] **Step 6: Commit**

```bash
git add portal/messages/ portal/src/contexts/LocaleContext.tsx mobile/packages/shared-i18n/
git commit -m "feat(i18n): add Dutch (nl), Polish (pl), and Swedish (sv) translations

Now 9 supported languages. Translations professionally reviewed.
Total catalog covers core EU markets (EN/FR/ES/DE/PT/IT/NL/PL/SV).

Implements P4-INT3 from Phase 4 plan."
```

---

### Task 27 (P4-AQ): Acquisition target evaluation (Blinx / Kinzoo)

**This is a process / business-development task. No code commits.**

Per Gap Analysis §14.1 Tier 4 #20: "Consider acquisition of safe social network (Blinx/Kinzoo) — Faster than building Bhapi App features."

- [ ] **Step 1: Reach out to Blinx + Kinzoo founders for exploratory conversations**

Position as a partnership/acquisition discussion. Bhapi already has a Social app (Phase 3 launch); the question is whether acquiring an established player accelerates user growth.

- [ ] **Step 2: Diligence checklist**

If either party engages:
- Tech stack & code-quality audit (modeled on the Q2 2026 gap analysis we did internally)
- User base size + engagement metrics + cohort retention
- Cap table + outstanding obligations
- IP/trademark conflicts
- Product overlap analysis vs. Bhapi Social

- [ ] **Step 3: Decision point**

Output one of:
- Proceed to LOI (engage M&A counsel)
- Partnership instead of acquisition (e.g., content distribution deal)
- Pass entirely (focus on organic Bhapi Social growth)

Document the decision + rationale at `docs/strategy/acquisition_evaluation_2026q4.md` (do NOT commit anything that contains confidential third-party details).

---

## Layer 4: Native OS Integration & Launch (Weeks 23-26)

Mobile native modules, SOC 2 audit close, launch comms.

---

### Task 28 (R-23): Apple PermissionKit (iOS 26) integration

**Files:**
- Create: `mobile/apps/safety/native/ios/PermissionKitBridge.swift`
- Create: `mobile/packages/shared-native/`
- Modify: `mobile/apps/safety/app.json` (add iOS entitlements)

**Prerequisite:** iOS 26 SDK availability (verify timing — may shift from this layer if Apple delays).

- [ ] **Step 1: Verify iOS 26 SDK available + read PermissionKit docs**

Apple's PermissionKit (iOS 26) provides:
- Parental approval requests
- Screen Time integration hooks
- Privacy-preserving age signals

Read Apple developer documentation. Verify Expo SDK version supports iOS 26 native modules.

- [ ] **Step 2: Create the native module**

Create `mobile/apps/safety/native/ios/PermissionKitBridge.swift`:

```swift
import Foundation
import React
import PermissionKit  // iOS 26 framework

@objc(PermissionKitBridge)
class PermissionKitBridge: NSObject {

  @objc
  func requestParentApproval(
    _ reason: String,
    childAccountId: String,
    resolver resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    PermissionKit.requestApproval(reason: reason, childId: childAccountId) { result in
      switch result {
      case .approved:
        resolve(["status": "approved"])
      case .denied:
        resolve(["status": "denied"])
      case .timeout:
        resolve(["status": "timeout"])
      @unknown default:
        reject("unknown", "Unknown PermissionKit response", nil)
      }
    }
  }

  @objc
  static func requiresMainQueueSetup() -> Bool { false }
}
```

Add the Objective-C bridge header (`PermissionKitBridge.m`) per React Native native module convention.

- [ ] **Step 3: Create JS/TS wrapper in shared-native package**

Create `mobile/packages/shared-native/src/index.ts`:

```typescript
import { NativeModules, Platform } from 'react-native';

const { PermissionKitBridge } = NativeModules;

export interface ParentApprovalResult {
  status: 'approved' | 'denied' | 'timeout' | 'unsupported';
}

export async function requestParentApproval(
  reason: string,
  childAccountId: string,
): Promise<ParentApprovalResult> {
  if (Platform.OS !== 'ios') return { status: 'unsupported' };
  if (!PermissionKitBridge) return { status: 'unsupported' };
  return PermissionKitBridge.requestParentApproval(reason, childAccountId);
}
```

- [ ] **Step 4: Wire into Safety + Social app flows**

In Bhapi Social, when a child under 13 attempts to send a contact request, call `requestParentApproval()` instead of (or in addition to) the existing in-app parent approval flow.

- [ ] **Step 5: Add iOS entitlements**

In `mobile/apps/safety/app.json` (or via EAS config plugin), add the PermissionKit entitlement.

- [ ] **Step 6: Test on physical iOS 26 device**

Native modules can't be fully tested in CI. Test on a physical iOS 26 device (or simulator if Apple provides PermissionKit-aware sim). Document test results.

- [ ] **Step 7: Commit**

```bash
git add mobile/apps/safety/native/ios/ mobile/packages/shared-native/ mobile/apps/safety/app.json mobile/apps/social/
git commit -m "feat(mobile): integrate Apple PermissionKit (iOS 26) for parental approval

Native iOS module wraps PermissionKit's parental approval API.
JS/TS surface in shared-native package — falls back to in-app approval
on Android or pre-iOS 26. Wired into contact-request and content-posting
flows in Social app for under-13 users.

Implements R-23 from review-recommendations plan."
```

---

### Task 29 (P4-NAT1): Android Digital Wellbeing API integration

**Files:**
- Create: `mobile/apps/safety/native/android/DigitalWellbeingBridge.kt`
- Modify: `mobile/packages/shared-native/src/index.ts`
- Modify: `mobile/apps/safety/android/app/build.gradle`

- [ ] **Step 1: Verify access to Android Usage Stats API**

Android's `UsageStatsManager` requires the `PACKAGE_USAGE_STATS` permission (special permission — user must grant in Settings, not just at install). Plan a UX flow that explains this requirement.

- [ ] **Step 2: Create the native bridge**

Create `mobile/apps/safety/native/android/DigitalWellbeingBridge.kt`:

```kotlin
package ai.bhapi.safety.native

import android.app.usage.UsageStatsManager
import android.content.Context
import com.facebook.react.bridge.*

class DigitalWellbeingBridge(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    override fun getName() = "DigitalWellbeingBridge"

    @ReactMethod
    fun getDailyAppUsage(promise: Promise) {
        try {
            val usm = reactApplicationContext
                .getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
            val end = System.currentTimeMillis()
            val start = end - 24 * 60 * 60 * 1000L
            val stats = usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, start, end)

            val result = Arguments.createArray()
            stats.forEach { stat ->
                val map = Arguments.createMap()
                map.putString("packageName", stat.packageName)
                map.putDouble("totalTimeMs", stat.totalTimeInForeground.toDouble())
                map.putDouble("lastTimeUsed", stat.lastTimeUsed.toDouble())
                result.pushMap(map)
            }
            promise.resolve(result)
        } catch (e: SecurityException) {
            promise.reject("PERMISSION_DENIED",
                "PACKAGE_USAGE_STATS not granted. Direct user to Settings.")
        }
    }

    @ReactMethod
    fun openUsageStatsSettings(promise: Promise) {
        val intent = android.content.Intent(android.provider.Settings.ACTION_USAGE_ACCESS_SETTINGS)
        intent.flags = android.content.Intent.FLAG_ACTIVITY_NEW_TASK
        reactApplicationContext.startActivity(intent)
        promise.resolve(null)
    }
}
```

Register the package in `MainApplication.kt`.

- [ ] **Step 3: Extend the JS wrapper**

In `mobile/packages/shared-native/src/index.ts`:

```typescript
export interface AppUsageEntry {
  packageName: string;
  totalTimeMs: number;
  lastTimeUsed: number;
}

export async function getDailyAppUsage(): Promise<AppUsageEntry[]> {
  if (Platform.OS !== 'android') return [];
  const { DigitalWellbeingBridge } = NativeModules;
  if (!DigitalWellbeingBridge) return [];
  return DigitalWellbeingBridge.getDailyAppUsage();
}

export async function openUsageStatsSettings(): Promise<void> {
  if (Platform.OS !== 'android') return;
  const { DigitalWellbeingBridge } = NativeModules;
  return DigitalWellbeingBridge?.openUsageStatsSettings();
}
```

- [ ] **Step 4: Wire into Safety app screen-time screen**

Replace the placeholder screen-time data in the Android branch with real `getDailyAppUsage()` data. On `PERMISSION_DENIED`, render a CTA with `openUsageStatsSettings()`.

- [ ] **Step 5: Test on physical Android device**

CI cannot grant `PACKAGE_USAGE_STATS`. Manual test required. Document.

- [ ] **Step 6: Commit**

```bash
git add mobile/apps/safety/native/android/ mobile/apps/safety/android/ mobile/packages/shared-native/src/index.ts
git commit -m "feat(mobile): integrate Android Digital Wellbeing / Usage Stats API

Native Kotlin bridge calls UsageStatsManager. JS/TS wrapper in
shared-native. Handles PACKAGE_USAGE_STATS permission gating with a
CTA into system Settings when denied. Backfills the screen-time
screen with real usage data on Android.

Implements P4-NAT1 from Phase 4 plan."
```

---

### Task 30 (P4-NAT2): Mobile agent production hardening (perf + battery)

**Files:**
- Modify: various files in `mobile/apps/safety/` (data sync intervals, batching)
- Test: Maestro E2E flows on real devices

- [ ] **Step 1: Profile current battery + network usage**

Run mobile app on a physical device for 24 hours of typical usage. Capture:
- Battery drain percentage (Android Studio Battery Historian; iOS Instruments)
- Network bytes sent/received
- Background CPU time

Document baseline in `docs/operations/mobile_perf_baseline_2026q4.md`.

- [ ] **Step 2: Identify top 3 hot-paths**

Review profile output. Common hotspots:
- Polling intervals too short
- Image uploads not batched
- WebSocket reconnect loops

- [ ] **Step 3: Implement targeted fixes**

Per hotspot:
- Coalesce polling into push (use existing realtime service)
- Batch image uploads (queue + flush every 60s when on Wi-Fi)
- Use exponential-backoff for reconnect

- [ ] **Step 4: Re-profile + verify improvement**

Re-run 24-hour profile. Document delta.

- [ ] **Step 5: Maestro E2E test for production scenarios**

Add E2E flows for:
- 8-hour background operation (no user interaction)
- Network drop + recovery
- App suspend + resume

- [ ] **Step 6: Commit**

```bash
git add mobile/ docs/operations/
git commit -m "perf(mobile): production hardening — battery, network batching, reconnect strategy

Reduces battery drain by Xpct, network usage by Y%, after 24-hour
profile-driven optimization. Maestro E2E flows added for background
operation, network recovery, and app lifecycle.

Implements P4-NAT2 from Phase 4 plan."
```

(Replace X / Y with actual measured values before committing.)

---

### Task 31 (R-21c): SOC 2 Type II audit close — report issued

**This is the final step of the SOC 2 workstream started in Tasks 9-10.**

- [ ] **Step 1: Confirm 6-month observation window has elapsed**

Started Week 4 of Layer 1 (~mid-October 2026). Closes ~mid-April 2027 (Week 26 of Phase 4).

- [ ] **Step 2: Final evidence package**

Run `python scripts/soc2/evidence_collector.py --quarter 2027-Q1` and ship the output to the auditor along with all earlier quarters' evidence.

- [ ] **Step 3: Auditor fieldwork + report drafting**

The audit firm will run interviews, sample testing, and produce a draft report. Address findings within 2 weeks.

- [ ] **Step 4: Receive final SOC 2 Type II report**

Receive the signed report. Store in `docs/compliance/soc2/2027_q1_type_ii_report.pdf` (gitignored — confidential).

- [ ] **Step 5: Update marketing + sales collateral**

Update bhapi.ai pricing page, sales decks, RFP responses to note "SOC 2 Type II certified."

- [ ] **Step 6: Commit (non-confidential parts)**

```bash
git add docs/compliance/soc2/ portal/src/app/
git commit -m "feat(soc2): SOC 2 Type II report issued — update marketing collateral

Audit report received and on file (not committed — confidential).
Pricing page, RFP collateral, and sales decks updated with certification
badge.

Closes R-21 from review-recommendations plan."
```

---

### Task 32 (P4-LNCH): Phase 4 launch comms + metrics dashboard

**Files:**
- Create: `docs/launch/phase4_comms_plan.md`
- Modify: `portal/src/app/(dashboard)/admin/metrics/page.tsx` (Phase 4 KPIs)

- [ ] **Step 1: Build internal Phase 4 metrics dashboard**

In `portal/src/app/(dashboard)/admin/metrics/page.tsx`, add a Phase 4 KPI section:

| KPI | Target | Source |
|---|---|---|
| School deployments | 25+ | `groups` where account_type=school, active subscription |
| Family subscriptions | 2,500+ | `subscriptions` where plan in (family, family_plus), status=active |
| API partners (beta+) | 10+ | `oauth_clients` where verified=true |
| AI platforms monitored | 15+ | static count |
| FERPA module adoption | 5+ schools | `groups` with FERPA records designated |
| Family+ conversion | 15% of family base | derived |
| Intel network signals delivered | 1,000+/month | `signal_deliveries` count |
| SOC 2 status | Issued | static |

- [ ] **Step 2: Write the comms plan**

`docs/launch/phase4_comms_plan.md` covers:
- External announcement (blog post, press release if any)
- Customer email (existing schools + families)
- Sales team enablement (one-pager on new tiers, SOC 2, FERPA)
- Channel partner notification (any partners who joined via Public API)
- Social media plan

- [ ] **Step 3: Push the announcement**

Coordinate with marketing. Stagger:
- Day 1: Customer email + portal banner
- Day 3: Public blog post + social
- Day 7: Press release (if applicable)

- [ ] **Step 4: Commit**

```bash
git add docs/launch/phase4_comms_plan.md portal/src/app/\(dashboard\)/admin/metrics/page.tsx
git commit -m "feat: Phase 4 launch — metrics dashboard + comms plan

Phase 4 ships: SOC 2 Type II, FERPA module, public API GA, 4 SDKs,
intel network, Family+ bundle, identity-protection partnership,
school pricing reduction, UK AADC re-review pass, AU sign-off, NL/PL/SV
i18n, iOS 26 PermissionKit, Android Digital Wellbeing.

Closes Phase 4."
```

---

## Success Metrics (Phase 4 exit gates)

These must all be true by Phase 4 close (end of March 2027) for the phase to count as shipped:

| Metric | Phase 3 exit | Phase 4 target | Source |
|---|---|---|---|
| **All 25 review recommendations closed or carried** | 10/25 done | 25/25 closed/carried | this plan |
| **SOC 2 Type II report issued** | Initiated | **Issued** | Task 31 |
| **FERPA module live in production** | None | Live | Tasks 6-8 |
| **Public API GA (not beta)** | Beta | GA, 4 SDKs published | Tasks 16-17 |
| **Intel network — 1,000+ signals/month delivered** | None | Live | Tasks 18-19 |
| **Family+ subscription tier live** | None | Live, 15%+ conversion | Task 21 |
| **School deployments** | 5+ | 25+ | metrics dashboard |
| **Family subscriptions (all plans)** | 500+ | 2,500+ | metrics dashboard |
| **AI platforms monitored** | 10 | 15+ | static count |
| **i18n languages supported** | 6 | 9 (added NL/PL/SV) | Task 26 |
| **No `except Exception:pass` blocks remaining** | 144 | 0 | Task 2 |
| **Module isolation lint clean in CI** | 0 violations enforced | enforced | Task 4 |
| **CSP `script-src` no longer permits `unsafe-inline`** | Yes (permits) | No | Task 1 |

---

## Deferred to Phase 5 / 2027 H2 (explicit non-goals)

Per Gap Analysis §10 + §14.2, NOT in Phase 4:

- VR/metaverse monitoring
- Building 30+ social media monitoring (compete on AI lane)
- Native Stories/Reels in Bhapi Social
- Full federal US AI legislation response
- Building identity-protection product in-house (use partnership instead)
- New geographic markets beyond UK/EU/AU/LATAM

If any of these are reprioritized mid-Phase, brainstorm a new spec rather than stretching this plan.

---

## Risks (Phase-4-specific, beyond Gap Analysis §13)

| ID | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| P4-R1 | iOS 26 PermissionKit delayed by Apple | Medium | High | Defer Task 28 to Phase 5; ship without if needed |
| P4-R2 | SOC 2 audit findings can't close in window | Medium | Critical | Early gap assessment (Task 10), aggressive remediation, audit firm with experience in our control set |
| P4-R3 | Identity-protection partnership doesn't sign | Medium | High | Have 2 backup partners identified; ship Family+ without bundle and add partner mid-Phase |
| P4-R4 | UK AADC re-review fails | Low | High | Engage counsel early; over-comply; remediate before re-review submission |
| P4-R5 | Public API SDK adoption is zero | High | Medium | Treat as marketing problem; recruit 3 design partners during beta |
| P4-R6 | Intel network has too few contributors to clear k-anonymity threshold | Medium | Medium | Seed with internal anonymized data from Bhapi's own customer base; lower k temporarily if necessary |
| P4-R7 | Mobile native modules break Expo OTA updates | Low | Medium | Rebuild + redeploy via EAS for native module changes; document in release runbook |
| P4-R8 | School pricing cut destroys margin without expanding base | Medium | Medium | Monitor unit economics weekly; revert to $2.99 if conversion doesn't improve within 60 days |

---

## Self-Review Checklist

Before kicking off execution, verify:

- [ ] All 15 unclosed review recommendations have a corresponding Task in this plan (R-09=1, R-10=2, R-16=3, R-25=4, R-13=5, R-18=6/7/8, R-21=9/10/31, R-19=11/12/13/14, R-20=15, R-22=20, R-24=23, R-23=28). **R-01 (app store submission) and R-12 (User lazy loading) and R-04 (version sync) and R-15 (consent in moderation) and R-11 (risk pagination) and R-08 (billing page) and R-06 (alert button) and R-02 (i18n wiring) and R-07 (pip-audit blocks CI) and R-05 (dependency upper bounds) and R-03 (Redis token replay) — closed pre-Phase-4.**
- [ ] Each Task has at least one explicit verification step (test command + expected output) before its commit
- [ ] No Task contains placeholders, "TBD", or "implement appropriately" — all code shown or referenced by exact path/line
- [ ] Migration numbers are sequential and unique (054, 055, 057, 058, 059, 060, 061; 056 absorbed into 055 per Task 18 Step 3)
- [ ] Tasks that touch production billing (20, 21, 22) explicitly require user confirmation before flipping Stripe price IDs
- [ ] Process tasks (9, 10, 25, 27, 31) are explicitly labeled and don't claim code commits where there are none
- [ ] Cross-task dependencies in the dependency graph match what each task actually requires
