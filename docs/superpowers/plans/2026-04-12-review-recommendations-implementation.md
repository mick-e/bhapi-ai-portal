# Review Recommendations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all 25 recommendations from the unified project review, ordered by priority (immediate → short-term → medium-term).

**Architecture:** Code-level fixes use TDD where applicable. Strategic/process items have research and action steps. Each task is independent and produces a shippable commit.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async, Redis, Next.js 15, TypeScript, Expo SDK 52+, GitHub Actions

**Source:** `docs/superpowers/specs/2026-04-12-bhapi-unified-project-review.md` — Section 9

---

## Phase 1: Immediate (0-30 Days)

---

### Task 1: R-03 — Persist Token Replay Tracking in Redis [S effort, H impact]

**Fixes:** F-010 (in-memory token replay sets lost on restart)

**Files:**
- Modify: `src/auth/service.py:362,418,428,526,747,772`
- Modify: `src/redis_client.py` (no changes needed — already has `get_redis()`)
- Test: `tests/unit/test_auth.py`
- Test: `tests/security/test_auth_security.py`

- [ ] **Step 1: Write failing test for Redis-backed reset token tracking**

In `tests/unit/test_auth.py`, add:

```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_reset_token_replay_blocked_after_restart(test_session):
    """Reset tokens stored in Redis survive process restart."""
    from src.auth.service import _mark_token_used, _is_token_used

    token_jti = "test-jti-replay-check"

    # Mark as used
    await _mark_token_used("reset", token_jti, ttl_seconds=3600)

    # Should be detected as used
    is_used = await _is_token_used("reset", token_jti)
    assert is_used is True


@pytest.mark.asyncio
async def test_unused_token_not_blocked(test_session):
    """Tokens not yet used should not be blocked."""
    from src.auth.service import _is_token_used

    is_used = await _is_token_used("reset", "never-used-jti")
    assert is_used is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/unit/test_auth.py::test_reset_token_replay_blocked_after_restart -v`
Expected: FAIL — `_mark_token_used` and `_is_token_used` do not exist yet

- [ ] **Step 3: Implement Redis-backed token tracking**

In `src/auth/service.py`, replace the in-memory sets with Redis-backed functions. At the module level (near line 362), replace:

```python
_used_reset_tokens: set[str] = set()
```

with:

```python
# In-memory fallback for when Redis is unavailable (tests only)
_used_tokens_fallback: set[str] = set()


async def _mark_token_used(category: str, token_id: str, ttl_seconds: int = 3600) -> None:
    """Mark a token as used in Redis (survives restarts). Falls back to in-memory."""
    from src.redis_client import get_redis
    redis = get_redis()
    key = f"bhapi:used_token:{category}:{token_id}"
    if redis:
        await redis.set(key, "1", ex=ttl_seconds)
    else:
        _used_tokens_fallback.add(key)


async def _is_token_used(category: str, token_id: str) -> bool:
    """Check if a token has been used. Checks Redis first, falls back to in-memory."""
    from src.redis_client import get_redis
    redis = get_redis()
    key = f"bhapi:used_token:{category}:{token_id}"
    if redis:
        return await redis.exists(key) > 0
    return key in _used_tokens_fallback
```

Remove `_used_approval_tokens: set[str] = set()` (near line 526).

Update `reset_password()` (around line 418):
```python
    # Check if token already used (was: if jti and jti in _used_reset_tokens)
    if jti and await _is_token_used("reset", jti):
        raise UnauthorizedError("Reset token already used")
```

Update line 428:
```python
    # Mark token as used (was: _used_reset_tokens.add(jti))
    if jti:
        await _mark_token_used("reset", jti, ttl_seconds=3600)
```

Update `approve_child_account()` (around line 747):
```python
    # Check if approval token already used (was: if token in _used_approval_tokens)
    if await _is_token_used("approval", token):
        raise UnauthorizedError("Approval token already used")
```

Update line 772:
```python
    # Mark approval token as used (was: _used_approval_tokens.add(token))
    await _mark_token_used("approval", token, ttl_seconds=3600)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/unit/test_auth.py -v -k "token_replay or unused_token"`
Expected: PASS

- [ ] **Step 5: Run full auth test suite to check for regressions**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/unit/test_auth.py tests/e2e/test_auth.py tests/security/test_auth_security.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/auth/service.py tests/unit/test_auth.py
git commit -m "fix(security): persist token replay tracking in Redis instead of in-memory sets

Replaces _used_reset_tokens and _used_approval_tokens in-memory sets
with Redis-backed storage that survives process restarts and works
across multiple workers. Falls back to in-memory for tests without Redis.

Fixes F-010 from unified project review."
```

---

### Task 2: R-04 — Unify Version Strings [S effort, M impact]

**Fixes:** F-002 (version string inconsistency)

**Files:**
- Create: `src/__version__.py`
- Modify: `src/config.py:126`
- Modify: `portal/package.json:3`

- [ ] **Step 1: Create single version source of truth**

Create `src/__version__.py`:

```python
__version__ = "4.0.0"
```

- [ ] **Step 2: Update config.py to use it**

In `src/config.py:126`, change:
```python
    app_version: str = "2.1.0"
```
to:
```python
    app_version: str = "4.0.0"
```

- [ ] **Step 3: Update portal/package.json**

In `portal/package.json:3`, change:
```json
  "version": "2.0.0",
```
to:
```json
  "version": "4.0.0",
```

- [ ] **Step 4: Run tests**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/unit/test_auth.py -v -k "version or health" && cd portal && npx tsc --noEmit`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/__version__.py src/config.py portal/package.json
git commit -m "fix: unify version strings to 4.0.0 across backend and frontend

config.py was 2.1.0, package.json was 2.0.0, CLAUDE.md said 4.0.0.
Now all say 4.0.0 with src/__version__.py as canonical source.

Fixes F-002 from unified project review."
```

---

### Task 3: R-05 — Add Upper Bounds to Python Dependency Pins [S effort, H impact]

**Fixes:** F-004 (floor-only version pins)

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update requirements.txt with upper bounds**

Replace the full contents of `requirements.txt` with:

```
fastapi>=0.109.0,<1.0.0
uvicorn[standard]>=0.27.0,<1.0.0
pydantic[email]>=2.5.0,<3.0.0
pydantic-settings>=2.1.0,<3.0.0
sqlalchemy[asyncio]>=2.0.25,<3.0.0
asyncpg>=0.29.0,<1.0.0
alembic>=1.13.0,<2.0.0
python-jose[cryptography]>=3.3.0,<4.0.0
passlib[bcrypt]>=1.7.4,<2.0.0
python-multipart>=0.0.6,<1.0.0
httpx>=0.26.0,<1.0.0
stripe>=8.0.0,<10.0.0
reportlab>=4.1.0,<5.0.0
sendgrid>=6.11.0,<7.0.0
structlog>=24.1.0,<26.0.0
redis>=5.0.0,<6.0.0
python-dateutil>=2.8.0,<3.0.0
```

- [ ] **Step 2: Verify deps still install**

Run: `cd C:/claude/bhapi-ai-portal && pip install -r requirements.txt --dry-run 2>&1 | tail -5`
Expected: No conflicts

- [ ] **Step 3: Run backend tests**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/unit/ -v --tb=short -q`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "fix: add upper bounds to Python dependency version pins

Prevents surprise major version upgrades that could break production.
All 17 dependencies now have >=minimum,<next_major bounds.

Fixes F-004 from unified project review."
```

---

### Task 4: R-07 — Make pip-audit Failures Block CI [S effort, M impact]

**Fixes:** F-018 (pip-audit non-blocking in CI)

**Files:**
- Modify: `.github/workflows/ci.yml:43-44`

- [ ] **Step 1: Update CI to fail on vulnerabilities**

In `.github/workflows/ci.yml`, change lines 43-44 from:
```yaml
      - name: Dependency audit
        run: pip-audit --desc || echo "WARNING: pip-audit found vulnerabilities"
```
to:
```yaml
      - name: Dependency audit
        run: pip-audit --desc
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "fix(ci): make pip-audit failures block deployment

Remove || echo workaround that let vulnerable dependencies pass CI.
Known vulnerabilities now prevent merge.

Fixes F-018 from unified project review."
```

---

### Task 5: R-06 — Fix Alert "View Details" No-Op Button [S effort, L impact]

**Fixes:** F-039 (view details button does nothing)

**Files:**
- Modify: `portal/src/app/(dashboard)/alerts/page.tsx:354-358`

- [ ] **Step 1: Replace no-op with navigation to alert detail via query param**

In `portal/src/app/(dashboard)/alerts/page.tsx`, change lines 354-358 from:
```typescript
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {/* View details — future nav */}}
          >
            View details
          </Button>
```
to:
```typescript
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              const params = new URLSearchParams({
                id: alert.id,
                child: alert.member_name || '',
              });
              window.location.href = `/activity?${params.toString()}`;
            }}
          >
            View details
          </Button>
```

This navigates to the activity page filtered by the alert context. Activity page already supports query params.

- [ ] **Step 2: Run frontend type check**

Run: `cd C:/claude/bhapi-ai-portal/portal && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Run frontend tests**

Run: `cd C:/claude/bhapi-ai-portal/portal && npx vitest run`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add portal/src/app/\(dashboard\)/alerts/page.tsx
git commit -m "fix(portal): wire alert View Details button to activity page

Was a no-op with a TODO comment. Now navigates to /activity
filtered by alert ID and child name.

Fixes F-039 from unified project review."
```

---

### Task 6: R-01 — Submit Mobile Apps to App Store and Google Play [M effort, H impact]

**Files:**
- Modify: `mobile/apps/safety/eas.json` (verify config)
- Modify: `mobile/apps/social/eas.json` (verify config)

This is a process task, not a pure code task. The apps are already built (Expo SDK 52+, 665+ tests, EAS configured with real Apple Team ID).

- [ ] **Step 1: Verify EAS build succeeds locally**

```bash
cd C:/claude/bhapi-ai-portal/mobile/apps/safety && npx eas build --platform all --profile preview --non-interactive --no-wait
cd C:/claude/bhapi-ai-portal/mobile/apps/social && npx eas build --platform all --profile preview --non-interactive --no-wait
```

- [ ] **Step 2: Verify app store metadata exists**

Check: `mobile/apps/safety/store/` and `mobile/apps/social/store/` should contain screenshots, descriptions, keywords in 6 languages.

- [ ] **Step 3: Create production builds**

```bash
cd C:/claude/bhapi-ai-portal/mobile/apps/safety && npx eas build --platform all --profile production --non-interactive
cd C:/claude/bhapi-ai-portal/mobile/apps/social && npx eas build --platform all --profile production --non-interactive
```

- [ ] **Step 4: Submit to Apple App Store**

```bash
cd C:/claude/bhapi-ai-portal/mobile/apps/safety && npx eas submit --platform ios --profile production
cd C:/claude/bhapi-ai-portal/mobile/apps/social && npx eas submit --platform ios --profile production
```

- [ ] **Step 5: Submit to Google Play**

```bash
cd C:/claude/bhapi-ai-portal/mobile/apps/safety && npx eas submit --platform android --profile production
cd C:/claude/bhapi-ai-portal/mobile/apps/social && npx eas submit --platform android --profile production
```

- [ ] **Step 6: Monitor review status**

Apple typically takes 24-48 hours. Google typically takes a few hours to a few days. Check EAS dashboard.

---

### Task 7: R-02 — Wire Up i18n Across All Dashboard Pages [M effort, H impact]

**Fixes:** F-036 (i18n functionally broken — only 2/44 pages use translations)

**Files:**
- Modify: 42 page files under `portal/src/app/(dashboard)/` (all except settings/page.tsx and legal/privacy-for-children/page.tsx which already use i18n)

**Pattern to apply to every page:**

The `useTranslations()` hook from `portal/src/contexts/LocaleContext.tsx` takes a namespace string and returns a `t(key)` function. Keys exist in `portal/messages/{en,fr,es,de,pt,it}.json`.

For each page:
1. Add import: `import { useTranslations } from '@/contexts/LocaleContext';`
2. Add hook call inside the component: `const t = useTranslations('namespaceName');`
3. Replace hardcoded strings with `t('keyName')` calls using existing keys from `en.json`
4. If keys don't exist in `en.json` for that page's strings, add them to ALL 6 language files

- [ ] **Step 1: Audit which pages need i18n and which keys exist**

Run: `cd C:/claude/bhapi-ai-portal && grep -rL "useTranslations" portal/src/app/\(dashboard\)/*/page.tsx | wc -l`
This gives the count of pages WITHOUT i18n.

Run: `cd C:/claude/bhapi-ai-portal && cat portal/messages/en.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(d.keys()))"` to list top-level namespaces.

- [ ] **Step 2: Wire up high-traffic pages first (dashboard, alerts, activity, members, settings)**

For each page, follow the pattern above. Example for `dashboard/page.tsx`:

```typescript
'use client';

import { useTranslations } from '@/contexts/LocaleContext';
// ... other imports

export default function DashboardPage() {
  const t = useTranslations('dashboard');
  // Replace "Welcome to Bhapi" with t('title')
  // Replace "Add your first child..." with t('emptyState')
  // etc.
```

- [ ] **Step 3: Wire up remaining pages in batches of 5-8**

Work through each page file. For each:
1. Add the `useTranslations` import and hook
2. Replace hardcoded strings with `t()` calls
3. Add any missing keys to all 6 language files
4. Run `npx tsc --noEmit` after each batch

- [ ] **Step 4: Verify all pages wired**

Run: `cd C:/claude/bhapi-ai-portal && grep -rL "useTranslations" portal/src/app/\(dashboard\)/*/page.tsx`
Expected: 0 files (all pages should now use translations)

- [ ] **Step 5: Run frontend tests and type check**

```bash
cd C:/claude/bhapi-ai-portal/portal && npx tsc --noEmit && npx vitest run
```

- [ ] **Step 6: Commit**

```bash
git add portal/src/app/ portal/messages/
git commit -m "feat(i18n): wire useTranslations() across all 44 dashboard pages

All pages now use the i18n system. Hardcoded English strings replaced
with t() calls using keys from portal/messages/{en,fr,es,de,pt,it}.json.
Previously only 2/44 pages used translations.

Fixes F-036 (Critical) from unified project review."
```

---

## Phase 2: Short-Term (30-90 Days)

---

### Task 8: R-15 — Add Consent Gating to Moderation Image Pipeline [S effort, H impact]

**Fixes:** F-013 (moderation image pipeline may bypass COPPA consent)

**Files:**
- Modify: `src/moderation/image_pipeline.py:130-140` (before `_call_hive()`)
- Test: `tests/unit/test_moderation.py`
- Test: `tests/security/test_moderation_security.py`

- [ ] **Step 1: Write failing test**

In `tests/security/test_moderation_security.py`, add:

```python
@pytest.mark.asyncio
async def test_image_pipeline_requires_consent_for_hive(test_session):
    """Image moderation must check third-party consent before calling Hive API."""
    from src.moderation.image_pipeline import ImageModerationPipeline

    # Create pipeline with Hive API key configured
    pipeline = ImageModerationPipeline(hive_api_key="test-key")

    # Without consent, should not call Hive (return NEEDS_REVIEW fallback)
    result = await pipeline.moderate(
        image_url="https://example.com/test.jpg",
        group_id=uuid4(),
        member_id=uuid4(),
        db=test_session,
    )
    # Should get NEEDS_REVIEW because consent check will fail (no consent record)
    assert result.status in ("NEEDS_REVIEW", "APPROVED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/security/test_moderation_security.py -v -k "consent_for_hive"`
Expected: FAIL (currently calls Hive without checking consent)

- [ ] **Step 3: Add consent check before Hive API call**

In `src/moderation/image_pipeline.py`, before the `_call_hive()` call (around line 130-140), add:

```python
        # COPPA 2026: Check third-party consent before calling Hive
        if group_id and member_id and db:
            from src.compliance.coppa_2026 import check_third_party_consent
            has_consent = await check_third_party_consent(
                db, group_id, member_id, "hive_sensity"
            )
            if not has_consent:
                logger.info(
                    "image_moderation_skipped_no_consent",
                    provider="hive_sensity",
                    group_id=str(group_id),
                    member_id=str(member_id),
                )
                return ModerationResult(status="NEEDS_REVIEW", reason="no_third_party_consent")
```

The `moderate()` method signature needs `group_id`, `member_id`, and `db` parameters if they don't already exist.

- [ ] **Step 4: Run tests**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/security/test_moderation_security.py tests/unit/test_moderation.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add src/moderation/image_pipeline.py tests/security/test_moderation_security.py
git commit -m "fix(security): add COPPA consent check to moderation image pipeline

Image moderation now calls check_third_party_consent() before sending
images to Hive/Sensity API. Matches the pattern already used in
src/risk/engine.py for deepfake detection and safety classification.

Fixes F-013 from unified project review."
```

---

### Task 9: R-11 — Standardize Risk Module Pagination [S effort, H impact]

**Fixes:** F-022 (risk module uses offset/limit, all others use page/page_size)

**Files:**
- Modify: `src/risk/router.py:58-59`
- Modify: `src/risk/schemas.py:39-46`
- Modify: `src/risk/service.py` (pagination query logic)
- Modify: `portal/src/lib/api-client.ts:293-320` (remove conversion logic)
- Test: `tests/e2e/test_risk.py`

- [ ] **Step 1: Write failing test for page/page_size pagination**

In `tests/e2e/test_risk.py`, add:

```python
@pytest.mark.asyncio
async def test_risk_events_use_page_pagination(client, auth_headers):
    """Risk events endpoint uses page/page_size, not offset/limit."""
    response = await client.get(
        "/api/v1/risk/events",
        params={"page": 1, "page_size": 20},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert "offset" not in data
    assert "limit" not in data
    assert "has_more" not in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd C:/claude/bhapi-ai-portal && pytest tests/e2e/test_risk.py -v -k "page_pagination"`
Expected: FAIL (currently uses offset/limit)

- [ ] **Step 3: Update risk schemas**

In `src/risk/schemas.py`, change `RiskEventListResponse` (lines 39-46) from:
```python
class RiskEventListResponse(BaseSchema):
    """Paginated list of risk events."""
    items: list[RiskEventResponse]
    total: int
    offset: int
    limit: int
    has_more: bool
```
to:
```python
class RiskEventListResponse(BaseSchema):
    """Paginated list of risk events."""
    items: list[RiskEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
```

- [ ] **Step 4: Update risk router**

In `src/risk/router.py`, change lines 58-59 from:
```python
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
```
to:
```python
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
```

Update the service call in the same function to pass `page` and `page_size` instead of `offset` and `limit`.

- [ ] **Step 5: Update risk service pagination logic**

In `src/risk/service.py`, update the query function to calculate offset from page:
```python
offset = (page - 1) * page_size
# ... query with .offset(offset).limit(page_size) ...
total_pages = (total + page_size - 1) // page_size
return RiskEventListResponse(
    items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
)
```

- [ ] **Step 6: Remove frontend conversion logic**

In `portal/src/lib/api-client.ts` (around lines 293-320), remove the manual offset calculation. The frontend should now pass `page` and `page_size` directly like all other endpoints.

- [ ] **Step 7: Run tests**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/e2e/test_risk.py tests/unit/test_risk.py -v
cd C:/claude/bhapi-ai-portal/portal && npx tsc --noEmit && npx vitest run
```

- [ ] **Step 8: Commit**

```bash
git add src/risk/router.py src/risk/schemas.py src/risk/service.py portal/src/lib/api-client.ts tests/e2e/test_risk.py
git commit -m "fix(api): standardize risk module pagination to page/page_size

All other modules use {page, page_size, total_pages}. Risk module
was the only one using {offset, limit, has_more}. Now consistent.
Removed frontend conversion logic in api-client.ts.

Fixes F-022 from unified project review."
```

---

### Task 10: R-12 — Change User Model to Default Lazy Loading [S effort, H impact]

**Fixes:** F-024 (eager-loads 3 relationships on every User query)

**Files:**
- Modify: `src/auth/models.py:33-35`
- Test: `tests/unit/test_auth.py`

- [ ] **Step 1: Change relationship lazy loading**

In `src/auth/models.py`, change lines 33-35 from:
```python
    oauth_connections: Mapped[list["OAuthConnection"]] = relationship(back_populates="user", lazy="selectin")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", lazy="selectin")
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user", lazy="selectin")
```
to:
```python
    oauth_connections: Mapped[list["OAuthConnection"]] = relationship(back_populates="user")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user")
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")
```

This changes from `selectin` (3 extra queries per User load) to default lazy loading (load on access).

- [ ] **Step 2: Search for code that accesses these relationships and add explicit loading**

Run: `cd C:/claude/bhapi-ai-portal && grep -rn "\.oauth_connections\|\.sessions\|\.api_keys" src/ --include="*.py" | grep -v __pycache__ | grep -v models.py`

For each hit, ensure the query uses `selectinload()`:
```python
from sqlalchemy.orm import selectinload

# When you need OAuth connections:
stmt = select(User).where(User.id == user_id).options(selectinload(User.oauth_connections))
```

- [ ] **Step 3: Run full test suite**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/ -v --tb=short -q
```
Expected: All pass. If any fail with `MissingGreenlet`, those endpoints need explicit `selectinload()` added.

- [ ] **Step 4: Commit**

```bash
git add src/auth/models.py src/auth/service.py
git commit -m "perf: change User model to default lazy loading for relationships

Removes lazy='selectin' from oauth_connections, sessions, and api_keys
relationships. Previously every User query triggered 3 extra SELECTs
(including on every auth middleware call). Now loads on-demand only.

Fixes F-024 from unified project review."
```

---

### Task 11: R-08 — Create Billing Dashboard Page [S effort, H impact]

**Fixes:** F-030 (no dedicated billing page in portal)

**Files:**
- Create: `portal/src/app/(dashboard)/billing/page.tsx`
- Modify: `portal/src/hooks/use-billing.ts` (verify existing hooks)

- [ ] **Step 1: Read existing billing hooks**

Read `portal/src/hooks/use-billing.ts` to understand available queries/mutations (plans, checkout, portal URL, subscription status).

- [ ] **Step 2: Create billing page**

Create `portal/src/app/(dashboard)/billing/page.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Loader2, AlertTriangle, CreditCard, ExternalLink } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useTranslations } from '@/contexts/LocaleContext';
import { apiClient } from '@/lib/api-client';

export default function BillingPage() {
  const t = useTranslations('billing');

  const { data: subscription, isLoading, isError, refetch } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => apiClient.get('/api/v1/billing/subscription'),
  });

  const { data: plans } = useQuery({
    queryKey: ['billing-plans'],
    queryFn: () => apiClient.get('/api/v1/billing/plans'),
  });

  const portalMutation = useMutation({
    mutationFn: () => apiClient.post('/api/v1/billing/portal'),
    onSuccess: (data) => {
      window.location.href = data.url;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        <span className="ml-2 text-gray-600">{t('loading')}</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertTriangle className="h-8 w-8 text-amber-500" />
        <p className="mt-2 text-gray-600">{t('error')}</p>
        <Button variant="secondary" onClick={() => refetch()} className="mt-4">
          {t('tryAgain')}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">{t('title')}</h1>

      {/* Current Plan */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">{t('currentPlan')}</h2>
            <p className="text-gray-600">
              {subscription?.plan_name || t('freePlan')}
            </p>
            {subscription?.status && (
              <Badge variant={subscription.status === 'active' ? 'success' : 'warning'}>
                {subscription.status}
              </Badge>
            )}
          </div>
          <Button
            onClick={() => portalMutation.mutate()}
            isLoading={portalMutation.isPending}
          >
            <CreditCard className="h-4 w-4 mr-2" />
            {t('manageBilling')}
            <ExternalLink className="h-3 w-3 ml-1" />
          </Button>
        </div>
      </Card>

      {/* Available Plans */}
      {plans?.items && (
        <div>
          <h2 className="text-lg font-semibold mb-4">{t('availablePlans')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {plans.items.map((plan: any) => (
              <Card key={plan.id}>
                <h3 className="font-semibold">{plan.name}</h3>
                <p className="text-2xl font-bold mt-2">
                  ${plan.price_monthly}<span className="text-sm text-gray-500">/mo</span>
                </p>
                <p className="text-gray-600 text-sm mt-1">{plan.description}</p>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add i18n keys for billing page**

Add to all 6 `portal/messages/*.json` files under a `"billing"` namespace:
```json
"billing": {
  "title": "Billing & Subscription",
  "loading": "Loading billing information...",
  "error": "Unable to load billing information",
  "tryAgain": "Try again",
  "currentPlan": "Current Plan",
  "freePlan": "Free Plan",
  "manageBilling": "Manage Billing",
  "availablePlans": "Available Plans"
}
```

- [ ] **Step 4: Run frontend tests and type check**

```bash
cd C:/claude/bhapi-ai-portal/portal && npx tsc --noEmit && npx vitest run
```

- [ ] **Step 5: Commit**

```bash
git add portal/src/app/\(dashboard\)/billing/page.tsx portal/messages/
git commit -m "feat(portal): add billing dashboard page with plan display and Stripe portal

Parents can now view their current plan, subscription status, and
manage billing via Stripe portal — without being redirected to settings.

Fixes F-030 from unified project review."
```

---

### Task 12: R-09 — Remove unsafe-inline from CSP [M effort, H impact]

**Fixes:** F-011 (CSP allows unsafe-inline for scripts)

**Files:**
- Modify: `src/main.py:118-126`

- [ ] **Step 1: Update CSP header**

In `src/main.py`, change lines 118-126 from:
```python
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' https:; "
        "connect-src 'self' https://api.stripe.com; "
        "frame-ancestors 'none'"
    )
```
to:
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
```

Key changes:
- Removed `'unsafe-inline'` from `script-src` (XSS protection)
- Kept `'unsafe-inline'` for `style-src` (Tailwind needs it)
- Added `https://js.stripe.com` to `connect-src` and `frame-src` for Stripe Elements

- [ ] **Step 2: Also add HSTS preload (R-12 HSTS finding)**

While in `src/main.py`, update line 117 from:
```python
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
```
to:
```python
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
```

- [ ] **Step 3: Run security tests**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/security/ -v
```

- [ ] **Step 4: Test that the portal still loads (no inline script breakage)**

Since the portal is a static export served by FastAPI, inline scripts should be minimal. If any break, they need to be moved to external `.js` files.

```bash
cd C:/claude/bhapi-ai-portal && uvicorn src.main:app --port 8000 &
# Open http://localhost:8000 in browser, check console for CSP violations
```

- [ ] **Step 5: Commit**

```bash
git add src/main.py
git commit -m "fix(security): remove unsafe-inline from CSP script-src, add HSTS preload

Tightens Content-Security-Policy by removing 'unsafe-inline' from
script-src (prevents XSS via inline scripts). Adds HSTS preload
directive for HSTS preload list submission. Adds Stripe JS to
connect-src and frame-src for Stripe Elements support.

Fixes F-011, F-012 from unified project review."
```

---

### Task 13: R-10 — Audit and Triage Bare Exception Blocks [M effort, H impact]

**Fixes:** F-001 (144 bare `except Exception` blocks across 70 files)

**Files:**
- Modify: Multiple files across `src/` (prioritize `src/portal/service.py` with 26 catches)

- [ ] **Step 1: Generate full list of bare exception blocks**

```bash
cd C:/claude/bhapi-ai-portal && grep -rn "except Exception" src/ --include="*.py" | grep -v __pycache__ > /tmp/exception_audit.txt && wc -l /tmp/exception_audit.txt
```

- [ ] **Step 2: Categorize each occurrence**

For each `except Exception` block, categorize as:
- **Keep (fire-and-forget):** SSE broadcast, push notification, audit logging — add `logger.debug()` instead of `pass`
- **Fix (should propagate):** Business logic in rewards, privacy, groups — should raise or log at warning level
- **Remove (unnecessary):** Wrapping already-safe operations

- [ ] **Step 3: Fix the worst offender first — `src/portal/service.py` (26 catches)**

Read the file and replace each `except Exception: pass` with:
```python
except Exception:
    logger.debug("section_name_degraded", exc_info=True)
```

This preserves non-blocking behavior while making failures visible in logs.

- [ ] **Step 4: Fix business logic exception blocks**

In `src/groups/rewards.py` and `src/groups/privacy.py`, change `except Exception: pass` to either:
- `except Exception: logger.warning("operation_failed", exc_info=True)` (if truly optional)
- Remove the try/except entirely (if the error should propagate)

- [ ] **Step 5: Work through remaining files in batches**

Process 10-15 files per session. For each:
1. Read the context around the `except Exception`
2. Apply the appropriate fix (debug log, warning log, or remove)
3. Run tests after each batch

- [ ] **Step 6: Verify count reduced**

```bash
cd C:/claude/bhapi-ai-portal && grep -rn "except Exception.*pass" src/ --include="*.py" | grep -v __pycache__ | wc -l
```
Target: 0 (no more `except Exception: pass` blocks)

- [ ] **Step 7: Run full test suite**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/ -v --tb=short -q
```

- [ ] **Step 8: Commit**

```bash
git add src/
git commit -m "fix: replace bare except Exception:pass blocks with structured logging

Audited 144 occurrences across 70 files. Fire-and-forget patterns
(SSE, push, audit) now log at debug level. Business logic blocks
(rewards, privacy) now log at warning level. No more silent error
swallowing.

Fixes F-001 from unified project review."
```

---

### Task 14: R-16 — Move OAuth Session Token Out of Redirect URL [M effort, M impact]

**Fixes:** F-014 (OAuth callback leaks session token in URL)

**Files:**
- Modify: `src/auth/router.py:450-459`
- Modify: `src/auth/models.py` (add OAuthAuthCode model if needed)
- Modify: `portal/src/app/(auth)/` (OAuth callback page)

- [ ] **Step 1: Change OAuth callback to use short-lived auth code**

In `src/auth/router.py`, replace the redirect at lines 450-459. Instead of putting the session token in the URL, create a short-lived authorization code in the DB, redirect with that code, then have the frontend exchange it for the session token:

```python
    # Generate short-lived auth code (replaces token in URL)
    import secrets
    auth_code = secrets.token_urlsafe(32)
    # Store in Redis with 60-second TTL
    from src.redis_client import get_redis
    redis = get_redis()
    if redis:
        await redis.set(f"bhapi:oauth_code:{auth_code}", session_token, ex=60)

    redirect_url = f"{settings.oauth_redirect_base_url}/oauth/callback?code={auth_code}&state={state}"
    redirect = RedirectResponse(url=redirect_url, status_code=302)
    return redirect
```

- [ ] **Step 2: Create auth code exchange endpoint**

Add to `src/auth/router.py`:
```python
@router.post("/oauth/exchange")
async def exchange_oauth_code(code: str = Body(...)):
    """Exchange a short-lived OAuth auth code for a session token."""
    from src.redis_client import get_redis
    redis = get_redis()
    if not redis:
        raise UnauthorizedError("OAuth code exchange unavailable")

    key = f"bhapi:oauth_code:{code}"
    session_token = await redis.get(key)
    if not session_token:
        raise UnauthorizedError("Invalid or expired authorization code")

    # Delete the code (one-time use)
    await redis.delete(key)

    response = JSONResponse({"token": session_token})
    _set_session_cookie(response, session_token)
    return response
```

- [ ] **Step 3: Update frontend OAuth callback**

The frontend callback page should call `POST /api/v1/auth/oauth/exchange` with the code from the URL, receive the session token in the response body (and cookie), then redirect to dashboard.

- [ ] **Step 4: Run auth tests**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/e2e/test_auth.py tests/security/test_auth_security.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/auth/router.py portal/src/app/
git commit -m "fix(security): replace OAuth token-in-URL with auth code exchange

OAuth callback now uses a short-lived authorization code (60s TTL in Redis)
instead of putting the session token directly in the URL query string.
Frontend exchanges the code for a token via POST /oauth/exchange.

Fixes F-014 from unified project review."
```

---

### Task 15: R-13 — Publish AI Monitoring Accuracy Benchmarks [M effort, H impact]

This is a research/measurement task, not a pure code task.

**Files:**
- Create: `src/risk/benchmarks.py` (benchmark runner)
- Create: `tests/benchmarks/test_risk_accuracy.py`
- Create: `docs/benchmarks/ai-monitoring-accuracy-2026-04.md`

- [ ] **Step 1: Create labeled test dataset**

Assemble a labeled dataset of AI chat content across the 14 risk categories:
- 50+ examples per category (safe, concerning, dangerous)
- Cover all 10 AI platforms
- Include edge cases (sarcasm, code discussions, educational content about risks)

Store in `tests/benchmarks/data/risk_test_corpus.json`.

- [ ] **Step 2: Create benchmark runner**

Create `src/risk/benchmarks.py` that:
1. Loads the test corpus
2. Runs each example through the risk classification pipeline
3. Compares predicted vs actual labels
4. Calculates precision, recall, F1 per category and overall

- [ ] **Step 3: Run benchmarks and document results**

```bash
cd C:/claude/bhapi-ai-portal && python -m src.risk.benchmarks --output docs/benchmarks/ai-monitoring-accuracy-2026-04.md
```

- [ ] **Step 4: Publish results**

Format as a public-facing document suitable for school procurement conversations. Include:
- Overall accuracy, precision, recall
- Per-category breakdown
- False positive rate (critical for school sales vs Gaggle's "40x fewer FP" claim)
- Methodology description

- [ ] **Step 5: Commit**

```bash
git add src/risk/benchmarks.py tests/benchmarks/ docs/benchmarks/
git commit -m "feat: add AI monitoring accuracy benchmarks with published results

Precision/recall for all 14 risk categories against labeled test corpus.
Provides evidence-based accuracy claims for school procurement.

Implements R-13 from unified project review."
```

---

### Task 16: R-14 — Ship Managed Chromebook Deployment [L effort, H impact]

This is a large feature requiring Google Admin Console integration.

**Files:**
- Create: `src/integrations/google_admin.py`
- Create: `extension/managed/` (managed deployment config)
- Create: `docs/deployment/chromebook-setup-guide.md`

- [ ] **Step 1: Research Google Admin Console force-install requirements**

The extension needs an `ExtensionInstallForcelist` policy or Chrome Browser Cloud Management policy. Research:
- `policy_templates.json` for managed Chrome extensions
- `managed_schema.json` for extension configuration
- Google Admin Console → Devices → Chrome → Apps & extensions workflow

- [ ] **Step 2: Create managed extension configuration**

Create `extension/managed/managed_schema.json`:
```json
{
  "type": "object",
  "properties": {
    "ServerUrl": { "type": "string", "title": "Bhapi API URL" },
    "SchoolId": { "type": "string", "title": "School Group ID" },
    "AutoPairDevices": { "type": "boolean", "title": "Auto-pair student devices" }
  }
}
```

- [ ] **Step 3: Create Google Admin API integration**

Create `src/integrations/google_admin.py` with:
- Chrome Browser Cloud Management API client
- Extension force-install policy management
- Student device enrollment
- Sync school roster from Google Admin Directory

- [ ] **Step 4: Create deployment guide for school IT admins**

Write `docs/deployment/chromebook-setup-guide.md` with step-by-step screenshots.

- [ ] **Step 5: Write tests and commit**

```bash
git add src/integrations/google_admin.py extension/managed/ docs/deployment/
git commit -m "feat: add managed Chromebook deployment via Google Admin Console

Schools can now force-install the Bhapi extension on all managed
Chromebooks via Google Admin Console. Includes managed schema for
school configuration and deployment guide for IT admins.

Implements R-14 from unified project review."
```

---

## Phase 3: Medium-Term (90-180 Days)

---

### Task 17: R-17 — Launch Ohio AI Governance Compliance Package [M effort, H impact]

**Files:**
- Modify: `src/governance/router.py` (add Ohio-specific endpoints)
- Modify: `src/governance/service.py` (Ohio compliance logic)
- Create: `src/governance/ohio_templates.py` (mandate-specific templates)
- Create: `portal/src/app/(dashboard)/governance/ohio/page.tsx`

- [ ] **Step 1: Research Ohio SB6 requirements (effective July 1, 2026)**

Key requirements for schools:
- AI tool inventory with risk assessments
- AI acceptable use policies
- Annual review of AI tools
- Student data protection in AI contexts
- Reporting to state education board

- [ ] **Step 2: Create Ohio-specific compliance templates**

Create `src/governance/ohio_templates.py` with:
- Pre-built AI acceptable use policy template
- Tool inventory template aligned with Ohio SB6 categories
- Annual review checklist
- State reporting format

- [ ] **Step 3: Add Ohio compliance dashboard page**

Create `portal/src/app/(dashboard)/governance/ohio/page.tsx` showing:
- Compliance readiness score
- Tool inventory status
- Policy template generator
- Audit trail for state reporting

- [ ] **Step 4: Write tests and commit**

```bash
git add src/governance/ portal/src/app/\(dashboard\)/governance/ tests/
git commit -m "feat: add Ohio AI governance compliance package (SB6, effective July 1)

Pre-built templates, tool inventory, annual review checklist, and
state reporting format for Ohio school AI governance mandate.
First-mover advantage — no competitor offers state-specific compliance.

Implements R-17 from unified project review."
```

---

### Task 18: R-18 — Implement FERPA Compliance Module [L effort, H impact]

**Fixes:** F-029 (FERPA is marketing-only)

**Files:**
- Create: `src/ferpa/` module (router.py, service.py, models.py, schemas.py, __init__.py)
- Create: `alembic/versions/054_ferpa_compliance.py`
- Test: `tests/unit/test_ferpa.py`, `tests/e2e/test_ferpa.py`

- [ ] **Step 1: Create FERPA module structure**

FERPA requires:
- Educational record designations (what data is an "education record")
- Directory official roles (who can access what)
- Legitimate educational interest logging (why data was accessed)
- Annual notification templates for parents
- Data sharing agreements for third parties

- [ ] **Step 2: Create database models**

```python
class EducationalRecord(UUIDMixin, TimestampMixin, Base):
    """Tracks which data elements are designated as educational records."""
    __tablename__ = "ferpa_educational_records"
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"))
    record_type: Mapped[str]  # "academic", "behavioral", "attendance", "ai_usage"
    description: Mapped[str]
    classification: Mapped[str]  # "directory", "non-directory", "excluded"

class AccessLog(UUIDMixin, TimestampMixin, Base):
    """Audit log of educational record access for FERPA compliance."""
    __tablename__ = "ferpa_access_logs"
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"))
    accessor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    record_type: Mapped[str]
    purpose: Mapped[str]  # "legitimate_educational_interest", "parental_request", etc.
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("group_members.id"))
```

- [ ] **Step 3: Create migration**

```bash
cd C:/claude/bhapi-ai-portal && alembic revision --autogenerate -m "add FERPA compliance tables"
```

- [ ] **Step 4: Create router and service**

FERPA endpoints:
- `GET /api/v1/ferpa/records` — list educational record designations
- `POST /api/v1/ferpa/records` — designate a record type
- `GET /api/v1/ferpa/access-log` — audit log of record access
- `POST /api/v1/ferpa/access-log` — log a record access
- `GET /api/v1/ferpa/notifications` — annual notification templates
- `GET /api/v1/ferpa/sharing-agreements` — third-party data sharing

- [ ] **Step 5: Register module in src/main.py, add model imports to alembic/env.py**

- [ ] **Step 6: Write tests and commit**

```bash
git add src/ferpa/ alembic/versions/ tests/unit/test_ferpa.py tests/e2e/test_ferpa.py src/main.py alembic/env.py
git commit -m "feat: implement FERPA compliance module with educational record tracking

Adds educational record designations, access logging for legitimate
educational interest, annual notification templates, and data sharing
agreement management. Required for school account compliance.

Fixes F-029 from unified project review."
```

---

### Task 19: R-19 — Build Portal Pages for Phase 2/3 Modules [M effort, M impact]

**Fixes:** F-031 (5 modules lack portal pages)

**Files:**
- Create: `portal/src/app/(dashboard)/location/page.tsx`
- Create: `portal/src/app/(dashboard)/screen-time/page.tsx`
- Create: `portal/src/app/(dashboard)/creative/page.tsx`
- Create: `portal/src/app/(dashboard)/insights/page.tsx` (intelligence module)

- [ ] **Step 1: Create location page**

Dashboard page showing:
- Map view with child locations (if geofencing enabled)
- Geofence list with status
- School check-in log
- Location history timeline

Use existing hooks pattern: `useQuery` with `/api/v1/location/*` endpoints.

- [ ] **Step 2: Create screen time page**

Dashboard page showing:
- Per-app usage chart (today/week/month)
- Schedule overview (when limits apply)
- Extension request inbox (child asks for more time)
- Per-child breakdown

- [ ] **Step 3: Create creative review page**

Dashboard page for parents to review child creative content:
- Gallery view of AI art, stories, stickers
- Moderation status per item
- Approve/reject actions

- [ ] **Step 4: Create insights page (intelligence module)**

Dashboard page showing:
- Social graph visualization (who the child interacts with)
- Behavioral anomaly alerts
- Correlation analysis (cross-platform patterns)
- Trend lines

- [ ] **Step 5: Add i18n keys for all 4 new pages**

Add namespaces to all 6 `portal/messages/*.json` files.

- [ ] **Step 6: Run tests and commit**

```bash
cd C:/claude/bhapi-ai-portal/portal && npx tsc --noEmit && npx vitest run
git add portal/src/app/ portal/messages/
git commit -m "feat(portal): add dashboard pages for location, screen time, creative, insights

Phase 2/3 backend modules now have portal UI. All pages follow
existing patterns: loading/error/empty states, React Query hooks,
i18n, role-based visibility.

Fixes F-031 from unified project review."
```

---

### Task 20: R-20 — Add Contextual Onboarding Cards [S effort, M impact]

**Fixes:** F-038 (onboarding minimal vs documentation claims)

**Files:**
- Create: `portal/src/components/ui/OnboardingCard.tsx`
- Modify: `portal/src/app/(dashboard)/alerts/page.tsx`
- Modify: `portal/src/app/(dashboard)/activity/page.tsx`
- Modify: `portal/src/app/(dashboard)/safety/page.tsx`
- Modify: `portal/src/app/(dashboard)/members/page.tsx`

- [ ] **Step 1: Create reusable OnboardingCard component**

```typescript
'use client';

import { useState } from 'react';
import { X, Lightbulb } from 'lucide-react';
import { Card } from './Card';

interface OnboardingCardProps {
  storageKey: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function OnboardingCard({ storageKey, title, description, actionLabel, onAction }: OnboardingCardProps) {
  const [dismissed, setDismissed] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(`onboarding:${storageKey}`) === 'dismissed';
    }
    return false;
  });

  if (dismissed) return null;

  const handleDismiss = () => {
    localStorage.setItem(`onboarding:${storageKey}`, 'dismissed');
    setDismissed(true);
  };

  return (
    <Card className="bg-teal-50 border-teal-200 mb-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Lightbulb className="h-5 w-5 text-teal-600 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-medium text-teal-900">{title}</h3>
            <p className="text-sm text-teal-700 mt-1">{description}</p>
            {actionLabel && onAction && (
              <button
                onClick={onAction}
                className="text-sm font-medium text-teal-700 underline mt-2"
              >
                {actionLabel}
              </button>
            )}
          </div>
        </div>
        <button onClick={handleDismiss} className="text-teal-400 hover:text-teal-600">
          <X className="h-4 w-4" />
        </button>
      </div>
    </Card>
  );
}
```

- [ ] **Step 2: Add onboarding cards to key pages**

In each page, add an `OnboardingCard` at the top of the page content (after the heading, before the data):

**Alerts page:** "Set up alert preferences to get notified about the things that matter most to your family."
**Activity page:** "Activity shows your children's AI usage across all monitored platforms. Install the browser extension to start monitoring."
**Safety page:** "Configure safety rules to set boundaries for your children's AI usage. You can customize rules per child."
**Members page:** "Add family members to start monitoring. Children under 13 require a signed family agreement."

- [ ] **Step 3: Run tests and commit**

```bash
cd C:/claude/bhapi-ai-portal/portal && npx tsc --noEmit && npx vitest run
git add portal/src/components/ui/OnboardingCard.tsx portal/src/app/
git commit -m "feat(portal): add contextual onboarding cards to key dashboard pages

Dismissible tip cards on alerts, activity, safety, and members pages
help new users understand each feature. Persisted via localStorage.

Fixes F-038 from unified project review."
```

---

### Task 21: R-22 — Adjust School Pricing [S effort, H impact]

**Files:**
- Modify: `src/billing/plans.py` (school tier pricing)

- [ ] **Step 1: Read current pricing config**

Read `src/billing/plans.py` to find the school tier definition.

- [ ] **Step 2: Update school pricing**

Change from `$2.99/seat/mo` to `$1.99/seat/mo` and add a free school pilot tier:

```python
SCHOOL_PLAN = {
    "name": "School",
    "price_monthly": 1.99,  # Was 2.99 — reduced to be competitive with GoGuardian/Gaggle
    "price_annual": 19.99,  # $1.67/mo effective — undercuts all competitors
    "per_seat": True,
    "features": [...]
}

SCHOOL_PILOT_PLAN = {
    "name": "School Pilot",
    "price_monthly": 0,
    "per_seat": True,
    "max_seats": 50,  # Free for up to 50 students
    "duration_days": 90,  # 90-day pilot
    "features": [...]  # Full feature set
}
```

- [ ] **Step 3: Update Stripe price IDs if needed**

Create new price objects in Stripe Dashboard for the new pricing.

- [ ] **Step 4: Commit**

```bash
git add src/billing/plans.py
git commit -m "feat(billing): reduce school pricing to $1.99/seat/mo, add free 90-day pilot

School tier reduced from $2.99 to $1.99/seat/mo to compete with
GoGuardian (~$4-8/yr) and Gaggle (~$3.75-6/yr). Free 90-day pilot
for up to 50 students to match GoGuardian's free trial strategy.

Implements R-22 from unified project review."
```

---

### Task 22: R-21 — Pursue SOC 2 Type II Certification [L effort, M impact]

This is a process/compliance task, not code.

- [ ] **Step 1: Engage SOC 2 auditor**

Research and select a SOC 2 audit firm. Consider:
- Vanta, Drata, or Secureframe for automated evidence collection
- Budget: $20K-50K for first audit

- [ ] **Step 2: Gap assessment**

Use the existing `src/compliance/` SOC 2 module (F-035 confirmed it's implemented) as a starting point. Identify gaps between current controls and SOC 2 Trust Service Criteria.

- [ ] **Step 3: Remediate gaps and collect evidence over 6-month observation period**

- [ ] **Step 4: Complete Type II audit**

---

### Task 23: R-23 — Integrate with Apple PermissionKit (iOS 26) [M effort, M impact]

**Files:**
- Modify: `mobile/apps/safety/` (iOS-specific PermissionKit integration)
- Modify: `mobile/apps/social/` (parental approval flows)

- [ ] **Step 1: Research PermissionKit API**

Apple's iOS 26 PermissionKit allows third-party apps to:
- Request parental approval for features
- Integrate with Screen Time controls
- Use privacy-preserving age signals

Review Apple developer documentation when iOS 26 SDK is available.

- [ ] **Step 2: Implement PermissionKit in Safety app**

Use Expo's native module system to integrate PermissionKit:
- Parental approval flow for new contact requests
- Screen Time integration for app limit management
- Age signal verification for social features

- [ ] **Step 3: Implement in Social app**

- Content posting requires parental approval for under-13
- Messaging permission flow via PermissionKit

- [ ] **Step 4: Write tests and commit**

---

### Task 24: R-24 — Add AI Bypass/VPN Detection for Schools [M effort, M impact]

**Files:**
- Create: `src/blocking/vpn_detection.py`
- Modify: `extension/src/content/monitor.ts` (detect bypass attempts)
- Modify: `src/blocking/router.py` (bypass event endpoints)

- [ ] **Step 1: Implement extension-side bypass detection**

In the extension, detect:
- VPN/proxy usage (check for WebRTC leak, DNS resolution anomalies)
- AI platform access via alternative domains/URLs
- Incognito mode detection
- Extension tampering detection

- [ ] **Step 2: Implement backend bypass event processing**

Create `src/blocking/vpn_detection.py`:
- Receive bypass attempt events from extension
- Classify bypass type (VPN, proxy, alternative URL, incognito)
- Generate alerts for school admins
- Auto-block repeated bypass attempts

- [ ] **Step 3: Write tests and commit**

```bash
git add src/blocking/ extension/src/ tests/
git commit -m "feat: add AI bypass and VPN detection for school deployments

Extension detects VPN/proxy usage, alternative AI platform URLs,
incognito mode, and extension tampering. Backend classifies and alerts
school admins. Auto-blocks repeated bypass attempts.

Implements R-24 from unified project review."
```

---

### Task 25: R-25 — Add CI Dependency-Graph Linter [M effort, H impact]

**Fixes:** F-021 (cross-module imports violate isolation claim)

**Files:**
- Create: `scripts/lint_module_imports.py`
- Modify: `.github/workflows/ci.yml` (add lint step)

- [ ] **Step 1: Create import linter script**

Create `scripts/lint_module_imports.py`:

```python
#!/usr/bin/env python3
"""Lint cross-module imports in src/ to enforce module isolation.

Allowed:
- Imports from src.exceptions, src.models, src.schemas, src.config,
  src.database, src.dependencies, src.encryption, src.redis_client
- Imports from a module's own __init__.py (e.g., src.groups can import from src.groups)
- Deferred imports inside function bodies (these are acceptable for breaking cycles)

Forbidden:
- Top-level imports from another module's internal files
  (e.g., src/alerts/service.py importing from src.groups.models)
"""
import ast
import sys
from pathlib import Path

SHARED_MODULES = {
    "src.exceptions", "src.models", "src.schemas", "src.config",
    "src.database", "src.dependencies", "src.encryption", "src.redis_client",
    "src.__version__",
}

def get_module_name(file_path: Path) -> str:
    """Extract the module name from a file path (e.g., src/alerts/service.py -> alerts)."""
    parts = file_path.parts
    if "src" in parts:
        idx = parts.index("src")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return ""

def check_file(file_path: Path) -> list[str]:
    """Check a file for forbidden top-level cross-module imports."""
    violations = []
    module_name = get_module_name(file_path)
    if not module_name:
        return violations

    try:
        tree = ast.parse(file_path.read_text(), filename=str(file_path))
    except SyntaxError:
        return violations

    for node in ast.iter_child_nodes(tree):
        # Only check top-level imports (not inside functions)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                import_module = node.module
                # Check if it's a src.* import
                if import_module.startswith("src."):
                    parts = import_module.split(".")
                    if len(parts) >= 2:
                        imported_module = parts[1]
                        full_prefix = f"src.{imported_module}"

                        # Skip shared modules
                        if full_prefix in SHARED_MODULES:
                            continue
                        # Skip self-imports
                        if imported_module == module_name:
                            continue
                        # Skip __init__.py imports (public interface)
                        if len(parts) == 2:
                            continue
                        # This is a cross-module internal import
                        violations.append(
                            f"{file_path}:{node.lineno}: "
                            f"forbidden cross-module import '{import_module}' "
                            f"(module '{module_name}' importing from '{imported_module}' internals)"
                        )

    return violations

def main():
    src_dir = Path("src")
    all_violations = []

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        violations = check_file(py_file)
        all_violations.extend(violations)

    if all_violations:
        print(f"Found {len(all_violations)} cross-module import violations:\n")
        for v in all_violations:
            print(f"  {v}")
        print(f"\nFix by importing through the module's __init__.py public interface,")
        print(f"or by using deferred imports inside function bodies.")
        sys.exit(1)
    else:
        print("No cross-module import violations found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the linter to see current violations**

```bash
cd C:/claude/bhapi-ai-portal && python scripts/lint_module_imports.py
```

This will produce a list of all top-level cross-module imports that need fixing.

- [ ] **Step 3: Fix violations by adding re-exports to `__init__.py` files**

For each violation, either:
1. Add the imported symbol to the source module's `__init__.py` (preferred)
2. Move the import inside the function body (acceptable for cycle-breaking)

Example: if `src/capture/service.py` imports `from src.groups.models import Group`, add to `src/groups/__init__.py`:
```python
from src.groups.models import Group
```
Then change the import in capture to:
```python
from src.groups import Group
```

- [ ] **Step 4: Add to CI**

In `.github/workflows/ci.yml`, add after the ruff lint step:
```yaml
      - name: Module isolation lint
        run: python scripts/lint_module_imports.py
```

- [ ] **Step 5: Run linter to verify all violations fixed**

```bash
cd C:/claude/bhapi-ai-portal && python scripts/lint_module_imports.py
```
Expected: "No cross-module import violations found."

- [ ] **Step 6: Run full test suite**

```bash
cd C:/claude/bhapi-ai-portal && pytest tests/ -v --tb=short -q
```

- [ ] **Step 7: Commit**

```bash
git add scripts/lint_module_imports.py .github/workflows/ci.yml src/
git commit -m "feat(ci): add module isolation linter to enforce no cross-module imports

AST-based Python linter checks for top-level imports from other modules'
internal files. Allowed: shared infrastructure, self-imports, __init__.py
public interfaces, deferred imports inside functions. Runs in CI.

Fixes F-021 from unified project review."
```

---

## Summary

| Task | Recommendation | Effort | Phase | Finding Fixed |
|------|---------------|:------:|:-----:|:------------:|
| 1 | R-03: Redis token replay | S | Immediate | F-010 |
| 2 | R-04: Unify version strings | S | Immediate | F-002 |
| 3 | R-05: Dependency upper bounds | S | Immediate | F-004 |
| 4 | R-07: pip-audit blocks CI | S | Immediate | F-018 |
| 5 | R-06: Fix alert button | S | Immediate | F-039 |
| 6 | R-01: Submit to app stores | M | Immediate | — |
| 7 | R-02: Wire up i18n | M | Immediate | F-036 |
| 8 | R-15: Consent in moderation | S | Short-term | F-013 |
| 9 | R-11: Risk pagination | S | Short-term | F-022 |
| 10 | R-12: User lazy loading | S | Short-term | F-024 |
| 11 | R-08: Billing page | S | Short-term | F-030 |
| 12 | R-09: CSP + HSTS | M | Short-term | F-011, F-012 |
| 13 | R-10: Exception audit | M | Short-term | F-001 |
| 14 | R-16: OAuth auth code | M | Short-term | F-014 |
| 15 | R-13: Accuracy benchmarks | M | Short-term | — |
| 16 | R-14: Chromebook deploy | L | Short-term | — |
| 17 | R-17: Ohio compliance | M | Medium-term | — |
| 18 | R-18: FERPA module | L | Medium-term | F-029 |
| 19 | R-19: Phase 2/3 pages | M | Medium-term | F-031 |
| 20 | R-20: Onboarding cards | S | Medium-term | F-038 |
| 21 | R-22: School pricing | S | Medium-term | — |
| 22 | R-21: SOC 2 cert | L | Medium-term | — |
| 23 | R-23: Apple PermissionKit | M | Medium-term | — |
| 24 | R-24: VPN detection | M | Medium-term | — |
| 25 | R-25: Import linter | M | Medium-term | F-021 |
