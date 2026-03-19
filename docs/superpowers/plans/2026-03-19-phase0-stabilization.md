# Phase 0: Emergency Stabilization — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete platform stabilization — archive legacy repos, scaffold the Expo monorepo, write architectural decision records, document incident response and compliance requirements, and prepare the foundation for Phase 1 feature work.

**Architecture:** No new production features. This phase produces documentation (ADRs, incident response plan, compliance research, moderation design), scaffolding (Expo monorepo with shared packages), and cleanup (legacy repo archival). COPPA 2026 enforcement is already complete.

**Tech Stack:** Expo SDK 52+ / TypeScript / Turborepo (monorepo scaffold) | Markdown (documentation) | GitHub CLI (repo management)

**Spec:** `docs/superpowers/specs/2026-03-19-bhapi-unified-platform-design.md` (v1.2, Sections 2.2, 8 Phase 0, 13, 14)

**Duration:** Weeks 1-5 (Mar 17 — Apr 22, 2026)
**Team:** 2-3 engineers
**Budget:** 10-15 person-weeks (8.5-12.7 net after 15% production overhead)

---

## File Structure

### Documents to Create

```
docs/
├── adrs/
│   ├── ADR-006-two-app-mobile-strategy.md
│   ├── ADR-007-cloudflare-media-storage.md
│   ├── ADR-008-websocket-realtime-service.md
│   ├── ADR-009-age-tier-permission-model.md
│   └── ADR-010-clean-break-no-data-migration.md
├── compliance/
│   ├── australian-online-safety-analysis.md
│   └── content-ownership-tos-draft.md
├── security/
│   └── incident-response-plan.md
└── architecture/
    └── moderation-pipeline-design.md
```

### Expo Monorepo to Scaffold

```
bhapi-mobile/                          # NEW repository root
├── apps/
│   ├── safety/
│   │   ├── app/
│   │   │   ├── _layout.tsx
│   │   │   └── index.tsx
│   │   ├── app.json
│   │   ├── babel.config.js
│   │   ├── tsconfig.json
│   │   └── package.json
│   └── social/
│       ├── app/
│       │   ├── _layout.tsx
│       │   └── index.tsx
│       ├── app.json
│       ├── babel.config.js
│       ├── tsconfig.json
│       └── package.json
├── packages/
│   ├── shared-ui/
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   ├── Button.tsx
│   │   │   └── Card.tsx
│   │   ├── __tests__/
│   │   │   ├── Button.test.tsx
│   │   │   └── Card.test.tsx
│   │   ├── tsconfig.json
│   │   └── package.json
│   ├── shared-auth/
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   └── token-manager.ts
│   │   ├── __tests__/
│   │   │   └── token-manager.test.ts
│   │   ├── tsconfig.json
│   │   └── package.json
│   ├── shared-api/
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   └── rest-client.ts
│   │   ├── __tests__/
│   │   │   └── rest-client.test.ts
│   │   ├── tsconfig.json
│   │   └── package.json
│   ├── shared-i18n/
│   │   ├── locales/
│   │   │   ├── en.json
│   │   │   ├── pt-BR.json
│   │   │   ├── es.json
│   │   │   ├── fr.json
│   │   │   ├── de.json
│   │   │   └── it.json
│   │   ├── src/
│   │   │   └── index.ts
│   │   ├── __tests__/
│   │   │   └── i18n.test.ts
│   │   ├── tsconfig.json
│   │   └── package.json
│   ├── shared-config/
│   │   ├── src/
│   │   │   ├── index.ts
│   │   │   ├── theme.ts
│   │   │   └── constants.ts
│   │   ├── __tests__/
│   │   │   └── theme.test.ts
│   │   ├── tsconfig.json
│   │   └── package.json
│   └── shared-types/
│       ├── src/
│       │   ├── index.ts
│       │   ├── auth.ts
│       │   └── common.ts
│       ├── tsconfig.json
│       └── package.json
├── turbo.json
├── package.json
├── tsconfig.base.json
├── .gitignore
└── README.md
```

---

## Task 1: Legacy Repo Audit (P0-2)

**Goal:** Document all features in bhapi-inc repos as reference inventory before archiving.

**Files:**
- Create: `docs/legacy/bhapi-api-feature-inventory.md`
- Create: `docs/legacy/bhapi-mobile-feature-inventory.md`
- Create: `docs/legacy/back-office-feature-inventory.md`

- [ ] **Step 1: Audit bhapi-api features**

Use GitHub API to inspect the repo structure and document endpoints, models, and integrations:

```bash
gh api repos/bhapi-inc/bhapi-api/git/trees/main?recursive=1 --jq '.tree[].path' | head -100
```

Create `docs/legacy/bhapi-api-feature-inventory.md` with:
- All REST endpoints (from Express routes)
- Database models (MongoDB schemas)
- Third-party integrations (Google Cloud AI: Perspective, Vision, Video Intelligence)
- Auth flow (2FA, rate limiting)
- WebSocket chat implementation details
- Content moderation logic (auto-assign moderators, toxicity thresholds)
- Open PRs summary (7 Snyk + 2 feature)

- [ ] **Step 2: Audit bhapi-mobile features**

```bash
gh api repos/bhapi-inc/bhapi-mobile/git/trees/main?recursive=1 --jq '.tree[].path' | head -150
```

Create `docs/legacy/bhapi-mobile-feature-inventory.md` with:
- All 43 screens and their purpose
- All 29 components
- Navigation structure
- Redux store shape
- Push notification implementation
- Camera/media handling
- Parental consent flow
- Dependencies and versions (React Native 0.64.2, Axios 0.21, etc.)

- [ ] **Step 3: Audit back-office features**

```bash
gh api repos/bhapi-inc/back-office/git/trees/main?recursive=1 --jq '.tree[].path' | head -100
```

Create `docs/legacy/back-office-feature-inventory.md` with:
- All 16 pages and their purpose
- RBAC model (4 roles: super-admin, admin, moderator, support)
- Post moderation workflow (published/blocked/reported)
- Account/org management features
- Support ticket system
- Settings (analyzer thresholds)
- Email template editor
- Authorization bug at container.tsx:48 (document for reference)

- [ ] **Step 4: Commit inventory documents**

```bash
git add docs/legacy/
git commit -m "docs: add legacy repo feature inventories for bhapi-api, bhapi-mobile, back-office"
```

---

## Task 2: Archive Legacy Repos (P0-3)

**Goal:** Set bhapi-inc repos to read-only with README pointing to bhapi-ai-portal.

**Files:**
- Modify: README.md in each bhapi-inc repo (via GitHub API)

- [ ] **Step 1: Update bhapi-api README**

```bash
gh api repos/bhapi-inc/bhapi-api -X PATCH -f description="ARCHIVED — See github.com/mick-e/bhapi-ai-portal"
```

Create a PR or direct push to update the README with:
```markdown
# ⚠️ ARCHIVED

This repository has been archived. All Bhapi development has been unified into the
[Bhapi AI Portal](https://github.com/mick-e/bhapi-ai-portal) repository.

See: [ADR-005: Platform Unification](https://github.com/mick-e/bhapi-ai-portal/blob/master/docs/adrs/ADR-005-platform-unification.md)

Feature inventory: [bhapi-api-feature-inventory.md](https://github.com/mick-e/bhapi-ai-portal/blob/master/docs/legacy/bhapi-api-feature-inventory.md)
```

- [ ] **Step 2: Update bhapi-mobile README**

Same pattern as Step 1, linking to bhapi-mobile-feature-inventory.md.

- [ ] **Step 3: Update back-office README**

Same pattern as Step 1, linking to back-office-feature-inventory.md.

- [ ] **Step 4: Archive repos on GitHub**

```bash
gh api repos/bhapi-inc/bhapi-api -X PATCH -f archived=true
gh api repos/bhapi-inc/bhapi-mobile -X PATCH -f archived=true
gh api repos/bhapi-inc/back-office -X PATCH -f archived=true
```

- [ ] **Step 5: Verify archival**

```bash
gh api repos/bhapi-inc/bhapi-api --jq '.archived'   # Should output: true
gh api repos/bhapi-inc/bhapi-mobile --jq '.archived' # Should output: true
gh api repos/bhapi-inc/back-office --jq '.archived'  # Should output: true
```

---

## Task 3: Write ADR-006 Through ADR-010 (P0-4 to P0-7, P0-3)

**Goal:** Document all new architectural decisions as formal ADR documents.

**Files:**
- Create: `docs/adrs/ADR-006-two-app-mobile-strategy.md`
- Create: `docs/adrs/ADR-007-cloudflare-media-storage.md`
- Create: `docs/adrs/ADR-008-websocket-realtime-service.md`
- Create: `docs/adrs/ADR-009-age-tier-permission-model.md`
- Create: `docs/adrs/ADR-010-clean-break-no-data-migration.md`

Each ADR follows this template:

```markdown
# ADR-00X: Title

**Status:** Accepted
**Date:** 2026-03-19
**Deciders:** [team]

## Context

[Problem statement]

## Decision

[What we decided]

## Consequences

### Positive
- [benefit]

### Negative
- [tradeoff]

### Risks
- [risk and mitigation]
```

- [ ] **Step 1: Write ADR-006 — Two-App Mobile Strategy**

Key content:
- **Context:** Need mobile presence for both parents (monitoring) and children (social). Single app with role switching is UX-hostile and app store review complication (children's app vs monitoring tool have different review guidelines).
- **Decision:** Two separate Expo apps in a Turborepo monorepo. Bhapi Safety (com.bhapi.safety) for parents. Bhapi Social (com.bhapi.social) for children 5-15. Shared packages for auth, API, i18n, UI, config, types.
- **Consequences:** Positive — separate App Store listings, separate review processes, age-appropriate UX. Negative — two apps to maintain, two CI pipelines, potential user confusion about which app to install.

- [ ] **Step 2: Write ADR-007 — Cloudflare Media Storage**

Key content:
- **Context:** Social app needs image/video storage with CDN, automatic resizing, video transcoding, and integration with content moderation pipeline.
- **Decision:** Cloudflare R2 (storage, zero egress fees) + Cloudflare Images (auto-resize, variants) + Cloudflare Stream (video transcode, HLS/DASH). Webhooks to backend for moderation pipeline integration.
- **Consequences:** Positive — zero egress fees, global CDN, automatic processing. Negative — vendor lock-in to Cloudflare, new operational dependency. Risk — cost at scale needs monitoring.

- [ ] **Step 3: Write ADR-008 — WebSocket Real-Time Service**

Key content:
- **Context:** Social app needs real-time messaging, typing indicators, presence, and live feed updates. Long-lived WebSocket connections have different scaling characteristics than REST API requests.
- **Decision:** Separate FastAPI WebSocket service. Connects to same PostgreSQL + Redis. Communicates with monolith via Redis pub/sub. Lazy DB connection acquisition (no persistent connections per WebSocket session). Pool limit: 10 connections.
- **Consequences:** Positive — independent scaling, no REST latency impact. Negative — operational complexity (second service to deploy/monitor), Redis as critical dependency for inter-service communication.

- [ ] **Step 4: Write ADR-009 — Age-Tier Permission Model**

Key content:
- **Context:** Children 5-15 have vastly different maturity levels. COPPA applies to under-13. Australian legislation restricts under-16. Need graduated feature access.
- **Decision:** Three tiers: Young (5-9), Pre-teen (10-12), Teen (13-15). Feature matrix per tier stored in `age_tier_configs` table with `jurisdiction` column for per-country minimum ages. Parent overrides via `feature_overrides` JSON. Moderation mode: pre-publish for 5-12, post-publish for 13-15.
- **Consequences:** Positive — age-appropriate UX, regulatory compliance, parent control. Negative — complexity in feature gating (every social endpoint must check tier), testing burden (3x test matrices).

- [ ] **Step 5: Write ADR-010 — Clean Break / No Data Migration**

Key content:
- **Context:** Legacy bhapi.com runs on MongoDB with Node.js/Express. The AI Portal runs on PostgreSQL with FastAPI. Legacy app has negligible active users and 18 known security vulnerabilities.
- **Decision:** No data migration from MongoDB. Clean start in PostgreSQL. Legacy repos archived as feature reference only. New App Store listing (com.bhapi.social), no connection to existing com.bhapi bundle.
- **Consequences:** Positive — no migration complexity, no importing unvalidated data into children's platform, clean security posture. Negative — any existing users lose their data (negligible impact given ~0 active users).

- [ ] **Step 6: Commit all ADRs**

```bash
git add docs/adrs/ADR-006-two-app-mobile-strategy.md \
        docs/adrs/ADR-007-cloudflare-media-storage.md \
        docs/adrs/ADR-008-websocket-realtime-service.md \
        docs/adrs/ADR-009-age-tier-permission-model.md \
        docs/adrs/ADR-010-clean-break-no-data-migration.md
git commit -m "docs: add ADR-006 through ADR-010 for unified platform decisions"
```

---

## Task 4: Scaffold Expo Monorepo (P0-8)

**Goal:** Create the Expo monorepo with Turborepo, two app shells, and six shared packages with stub implementations and tests.

**Files:**
- Create: `bhapi-mobile/` directory tree (see File Structure above)
- Tests: Shared package unit tests (≥20 total)

- [ ] **Step 1: Initialize monorepo root**

```bash
mkdir -p /c/claude/bhapi-mobile
cd /c/claude/bhapi-mobile
git init
```

Create `package.json`:
```json
{
  "name": "bhapi-mobile",
  "private": true,
  "workspaces": ["apps/*", "packages/*"],
  "scripts": {
    "build": "turbo run build",
    "test": "turbo run test",
    "lint": "turbo run lint",
    "typecheck": "turbo run typecheck"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "typescript": "^5.4.0"
  }
}
```

Create `turbo.json`:
```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    },
    "test": {
      "dependsOn": ["^build"]
    },
    "lint": {},
    "typecheck": {
      "dependsOn": ["^build"]
    }
  }
}
```

Create `tsconfig.base.json`:
```json
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  }
}
```

Create `.gitignore`:
```
node_modules/
dist/
.expo/
.turbo/
*.tsbuildinfo
ios/
android/
```

- [ ] **Step 2: Create shared-config package**

Create `packages/shared-config/package.json`:
```json
{
  "name": "@bhapi/config",
  "version": "0.1.0",
  "private": true,
  "main": "src/index.ts",
  "scripts": {
    "test": "jest",
    "typecheck": "tsc --noEmit"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "ts-jest": "^29.0.0",
    "@types/jest": "^29.0.0"
  }
}
```

Create `packages/shared-config/src/theme.ts`:
```typescript
export const colors = {
  primary: {
    50: '#FFF3ED',
    100: '#FFE4D4',
    500: '#FF6B35',
    600: '#E55A2B',
    700: '#CC4A21',
  },
  accent: {
    50: '#F0FDFA',
    100: '#CCFBF1',
    500: '#0D9488',
    600: '#0B7C72',
    700: '#096B5C',
  },
  neutral: {
    50: '#FAFAFA',
    100: '#F5F5F5',
    200: '#E5E5E5',
    500: '#737373',
    700: '#404040',
    900: '#171717',
  },
  semantic: {
    error: '#DC2626',
    warning: '#F59E0B',
    success: '#16A34A',
    info: '#2563EB',
  },
} as const;

export const typography = {
  fontFamily: 'Inter',
  sizes: {
    xs: 12,
    sm: 14,
    base: 16,
    lg: 18,
    xl: 20,
    '2xl': 24,
    '3xl': 30,
  },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  '2xl': 48,
} as const;
```

Create `packages/shared-config/src/constants.ts`:
```typescript
export const API_VERSION = 'v1';

export const AGE_TIERS = {
  YOUNG: { min: 5, max: 9, label: 'young' },
  PRETEEN: { min: 10, max: 12, label: 'preteen' },
  TEEN: { min: 13, max: 15, label: 'teen' },
} as const;

export const MEMBER_LIMITS = {
  FREE: 5,
  FAMILY: 5,
  FAMILY_PLUS: 10,
  SCHOOL: Infinity,
  ENTERPRISE: Infinity,
} as const;

export const SUBSCRIPTION_TIERS = {
  FREE: 'free',
  FAMILY: 'family',
  FAMILY_PLUS: 'family_plus',
  SCHOOL: 'school',
  ENTERPRISE: 'enterprise',
} as const;

export type SubscriptionTier = typeof SUBSCRIPTION_TIERS[keyof typeof SUBSCRIPTION_TIERS];
export type AgeTier = typeof AGE_TIERS[keyof typeof AGE_TIERS]['label'];
```

Create `packages/shared-config/src/index.ts`:
```typescript
export { colors, typography, spacing } from './theme';
export { API_VERSION, AGE_TIERS, MEMBER_LIMITS, SUBSCRIPTION_TIERS } from './constants';
export type { SubscriptionTier, AgeTier } from './constants';
```

Create `packages/shared-config/__tests__/theme.test.ts`:
```typescript
import { colors, typography, spacing } from '../src/theme';

describe('theme', () => {
  test('primary color is Bhapi orange', () => {
    expect(colors.primary[500]).toBe('#FF6B35');
  });

  test('accent color is Bhapi teal', () => {
    expect(colors.accent[500]).toBe('#0D9488');
  });

  test('font family is Inter', () => {
    expect(typography.fontFamily).toBe('Inter');
  });

  test('spacing scale is consistent', () => {
    expect(spacing.sm).toBeLessThan(spacing.md);
    expect(spacing.md).toBeLessThan(spacing.lg);
  });
});
```

- [ ] **Step 3: Create shared-types package**

Create `packages/shared-types/src/auth.ts`:
```typescript
export interface User {
  id: string;
  email: string;
  role: 'parent' | 'child' | 'school_admin' | 'moderator' | 'support' | 'super_admin';
  group_id: string | null;
  email_verified: boolean;
  created_at: string;
}

export interface AuthTokenPayload {
  user_id: string;
  group_id: string | null;
  role: string;
  permissions: string[];
  type: 'session';
  exp: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  user: User;
}
```

Create `packages/shared-types/src/common.ts`:
```typescript
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

export interface ErrorResponse {
  error: string;
  code: string;
}

export interface ApiResponse<T> {
  data: T | null;
  error: ErrorResponse | null;
  loading: boolean;
}
```

Create `packages/shared-types/src/index.ts`:
```typescript
export type { User, AuthTokenPayload, LoginRequest, LoginResponse } from './auth';
export type { PaginatedResponse, ErrorResponse, ApiResponse } from './common';
```

- [ ] **Step 4: Create shared-auth package**

Create `packages/shared-auth/src/token-manager.ts`:
```typescript
/**
 * Token manager for JWT auth.
 * In production, uses expo-secure-store.
 * This stub uses in-memory storage for testing.
 */

let _accessToken: string | null = null;

export const tokenManager = {
  async getToken(): Promise<string | null> {
    // TODO Phase 1: Replace with SecureStore.getItemAsync('access_token')
    return _accessToken;
  },

  async setToken(token: string): Promise<void> {
    // TODO Phase 1: Replace with SecureStore.setItemAsync('access_token', token)
    _accessToken = token;
  },

  async clearToken(): Promise<void> {
    // TODO Phase 1: Replace with SecureStore.deleteItemAsync('access_token')
    _accessToken = null;
  },

  async isAuthenticated(): Promise<boolean> {
    const token = await this.getToken();
    if (!token) return false;
    // Check expiry (JWT payload is base64 encoded)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  },
};
```

Create `packages/shared-auth/__tests__/token-manager.test.ts`:
```typescript
import { tokenManager } from '../src/token-manager';

// Helper: create a JWT-like token with given expiry
function makeToken(expSeconds: number): string {
  const header = btoa(JSON.stringify({ alg: 'HS256' }));
  const payload = btoa(JSON.stringify({
    user_id: 'test-123',
    type: 'session',
    exp: Math.floor(Date.now() / 1000) + expSeconds,
  }));
  return `${header}.${payload}.fake-signature`;
}

describe('tokenManager', () => {
  beforeEach(async () => {
    await tokenManager.clearToken();
  });

  test('getToken returns null when no token set', async () => {
    expect(await tokenManager.getToken()).toBeNull();
  });

  test('setToken stores and getToken retrieves', async () => {
    const token = makeToken(3600);
    await tokenManager.setToken(token);
    expect(await tokenManager.getToken()).toBe(token);
  });

  test('clearToken removes stored token', async () => {
    await tokenManager.setToken(makeToken(3600));
    await tokenManager.clearToken();
    expect(await tokenManager.getToken()).toBeNull();
  });

  test('isAuthenticated returns false with no token', async () => {
    expect(await tokenManager.isAuthenticated()).toBe(false);
  });

  test('isAuthenticated returns true with valid unexpired token', async () => {
    await tokenManager.setToken(makeToken(3600)); // expires in 1 hour
    expect(await tokenManager.isAuthenticated()).toBe(true);
  });

  test('isAuthenticated returns false with expired token', async () => {
    await tokenManager.setToken(makeToken(-60)); // expired 60s ago
    expect(await tokenManager.isAuthenticated()).toBe(false);
  });
});
```

- [ ] **Step 5: Create shared-api package**

Create `packages/shared-api/src/rest-client.ts`:
```typescript
/**
 * REST API client for Bhapi backend.
 * Wraps fetch with auth headers, error handling, and retry logic.
 */

import type { ErrorResponse } from '@bhapi/types';

export interface ApiClientConfig {
  baseUrl: string;
  getToken: () => Promise<string | null>;
}

export class ApiClient {
  private config: ApiClientConfig;

  constructor(config: ApiClientConfig) {
    this.config = config;
  }

  async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const token = await this.config.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.config.baseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error: ErrorResponse = await response.json().catch(() => ({
        error: response.statusText,
        code: `HTTP_${response.status}`,
      }));
      throw new ApiError(response.status, error.code, error.error);
    }

    return response.json();
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }

  post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('POST', path, body);
  }

  put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('PUT', path, body);
  }

  delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path);
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
```

Create `packages/shared-api/__tests__/rest-client.test.ts`:
```typescript
import { ApiClient, ApiError } from '../src/rest-client';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('ApiClient', () => {
  const client = new ApiClient({
    baseUrl: 'https://api.bhapi.ai',
    getToken: async () => 'test-token-123',
  });

  beforeEach(() => {
    mockFetch.mockReset();
  });

  test('GET request includes auth header', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: 'test' }),
    });

    await client.get('/api/v1/test');

    expect(mockFetch).toHaveBeenCalledWith(
      'https://api.bhapi.ai/api/v1/test',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token-123',
        }),
      }),
    );
  });

  test('POST request sends JSON body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: '1' }),
    });

    await client.post('/api/v1/test', { name: 'test' });

    expect(mockFetch).toHaveBeenCalledWith(
      'https://api.bhapi.ai/api/v1/test',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'test' }),
      }),
    );
  });

  test('throws ApiError on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 403,
      json: async () => ({ error: 'Forbidden', code: 'FORBIDDEN' }),
    });

    await expect(client.get('/api/v1/secret'))
      .rejects
      .toThrow(ApiError);
  });

  test('ApiError contains status and code', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ error: 'Not found', code: 'NOT_FOUND' }),
    });

    try {
      await client.get('/api/v1/missing');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(404);
      expect((e as ApiError).code).toBe('NOT_FOUND');
    }
  });

  test('handles no token gracefully', async () => {
    const noAuthClient = new ApiClient({
      baseUrl: 'https://api.bhapi.ai',
      getToken: async () => null,
    });

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await noAuthClient.get('/api/v1/public');

    const callHeaders = mockFetch.mock.calls[0][1].headers;
    expect(callHeaders.Authorization).toBeUndefined();
  });
});
```

- [ ] **Step 6: Create shared-i18n package**

Create `packages/shared-i18n/locales/en.json`:
```json
{
  "common": {
    "loading": "Loading...",
    "error": "Something went wrong",
    "retry": "Try again",
    "cancel": "Cancel",
    "save": "Save",
    "delete": "Delete",
    "confirm": "Confirm"
  },
  "auth": {
    "login": "Log in",
    "register": "Create account",
    "logout": "Log out",
    "email": "Email address",
    "password": "Password"
  },
  "safety": {
    "dashboard": "Dashboard",
    "alerts": "Alerts",
    "activity": "Activity",
    "settings": "Settings"
  },
  "social": {
    "feed": "Feed",
    "messages": "Messages",
    "profile": "Profile",
    "create_post": "Create post"
  }
}
```

Create minimal stubs for other 5 locales (pt-BR, es, fr, de, it) with same keys but translated values for `common` section. Other sections can use English as placeholder with `// TODO: translate` comments.

Create `packages/shared-i18n/src/index.ts`:
```typescript
import en from '../locales/en.json';

type Locale = 'en' | 'pt-BR' | 'es' | 'fr' | 'de' | 'it';

const localeLoaders: Record<Locale, () => Promise<typeof en>> = {
  en: () => Promise.resolve(en),
  'pt-BR': () => import('../locales/pt-BR.json'),
  es: () => import('../locales/es.json'),
  fr: () => import('../locales/fr.json'),
  de: () => import('../locales/de.json'),
  it: () => import('../locales/it.json'),
};

export async function loadLocale(locale: Locale): Promise<typeof en> {
  const loader = localeLoaders[locale] ?? localeLoaders.en;
  return loader();
}

export function t(translations: typeof en, key: string): string {
  const parts = key.split('.');
  let current: unknown = translations;
  for (const part of parts) {
    if (current && typeof current === 'object' && part in current) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return key; // Fallback to key if translation missing
    }
  }
  return typeof current === 'string' ? current : key;
}

export type { Locale };
```

Create `packages/shared-i18n/__tests__/i18n.test.ts`:
```typescript
import { loadLocale, t } from '../src';

describe('i18n', () => {
  test('loads English locale', async () => {
    const translations = await loadLocale('en');
    expect(translations.common.loading).toBe('Loading...');
  });

  test('t() resolves nested keys', async () => {
    const translations = await loadLocale('en');
    expect(t(translations, 'common.loading')).toBe('Loading...');
    expect(t(translations, 'auth.login')).toBe('Log in');
  });

  test('t() returns key for missing translations', async () => {
    const translations = await loadLocale('en');
    expect(t(translations, 'nonexistent.key')).toBe('nonexistent.key');
  });
});
```

- [ ] **Step 7: Create shared-ui package stubs**

Create `packages/shared-ui/src/Button.tsx`:
```typescript
import React from 'react';
import { TouchableOpacity, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '@bhapi/config';

export interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  disabled?: boolean;
  accessibilityLabel?: string;
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  accessibilityLabel,
}: ButtonProps) {
  const bgColor = variant === 'primary' ? colors.primary[600]
    : variant === 'secondary' ? colors.accent[500]
    : 'transparent';

  const textColor = variant === 'outline' ? colors.primary[600] : '#FFFFFF';
  const fontSize = size === 'sm' ? typography.sizes.sm
    : size === 'lg' ? typography.sizes.lg
    : typography.sizes.base;

  const paddingVertical = size === 'sm' ? spacing.xs
    : size === 'lg' ? spacing.md
    : spacing.sm;

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || isLoading}
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityRole="button"
      style={[
        styles.base,
        { backgroundColor: bgColor, paddingVertical, opacity: disabled ? 0.5 : 1 },
        variant === 'outline' && { borderWidth: 1, borderColor: colors.primary[600] },
      ]}
    >
      {isLoading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <Text style={[styles.text, { color: textColor, fontSize }]}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: 8,
    paddingHorizontal: spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 44, // WCAG tap target
  },
  text: {
    fontFamily: typography.fontFamily,
    fontWeight: '600',
  },
});
```

Create `packages/shared-ui/src/Card.tsx`:
```typescript
import React from 'react';
import { View, StyleSheet } from 'react-native';
import { colors, spacing } from '@bhapi/config';

export interface CardProps {
  children: React.ReactNode;
  padding?: keyof typeof spacing;
}

export function Card({ children, padding = 'md' }: CardProps) {
  return (
    <View style={[styles.card, { padding: spacing[padding] }]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
});
```

Create `packages/shared-ui/src/index.ts`:
```typescript
export { Button } from './Button';
export type { ButtonProps } from './Button';
export { Card } from './Card';
export type { CardProps } from './Card';
```

Create `packages/shared-ui/__tests__/Button.test.tsx` and `Card.test.tsx` with basic render tests using React Native Testing Library.

- [ ] **Step 8: Create Safety app shell**

Create `apps/safety/app.json`:
```json
{
  "expo": {
    "name": "Bhapi Safety",
    "slug": "bhapi-safety",
    "version": "0.1.0",
    "scheme": "bhapi-safety",
    "platforms": ["ios", "android"],
    "ios": { "bundleIdentifier": "com.bhapi.safety" },
    "android": { "package": "com.bhapi.safety" },
    "plugins": ["expo-router"]
  }
}
```

Create `apps/safety/app/_layout.tsx`:
```typescript
import { Stack } from 'expo-router';

export default function RootLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
```

Create `apps/safety/app/index.tsx`:
```typescript
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography } from '@bhapi/config';

export default function SafetyHome() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Bhapi Safety</Text>
      <Text style={styles.subtitle}>Parent monitoring dashboard</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#FFFFFF' },
  title: { fontSize: typography.sizes['2xl'], fontWeight: '700', color: colors.primary[600] },
  subtitle: { fontSize: typography.sizes.base, color: colors.neutral[500], marginTop: 8 },
});
```

- [ ] **Step 9: Create Social app shell**

Create `apps/social/app.json`:
```json
{
  "expo": {
    "name": "Bhapi Social",
    "slug": "bhapi-social",
    "version": "0.1.0",
    "scheme": "bhapi-social",
    "platforms": ["ios", "android"],
    "ios": { "bundleIdentifier": "com.bhapi.social" },
    "android": { "package": "com.bhapi.social" },
    "plugins": ["expo-router"]
  }
}
```

Create `apps/social/app/_layout.tsx` and `apps/social/app/index.tsx` (same pattern as Safety, with "Bhapi Social" and "Safe social for kids" text).

- [ ] **Step 10: Install dependencies and verify build**

```bash
cd /c/claude/bhapi-mobile
npm install
npx turbo run typecheck
npx turbo run test
```

Expected: All packages typecheck. All tests pass (≥20 tests across shared packages).

- [ ] **Step 11: Commit monorepo**

```bash
cd /c/claude/bhapi-mobile
git add -A
git commit -m "feat: scaffold Expo monorepo with shared packages and app shells

- Turborepo workspace with apps/safety, apps/social, 6 shared packages
- shared-config: theme (orange/teal), constants (age tiers, subscription tiers)
- shared-types: auth types, common response types
- shared-auth: token manager with JWT expiry check
- shared-api: REST client with auth headers and error handling
- shared-i18n: 6-language loader with nested key resolution
- shared-ui: Button and Card components (WCAG 44pt targets)
- 20+ unit tests across shared packages"
```

---

## Task 5: Australian Compliance Research (P0-9)

**Goal:** Legal analysis of Australian Online Safety Act + Social Media Minimum Age Bill. Determine whether Bhapi Social qualifies for exemption.

**Files:**
- Create: `docs/compliance/australian-online-safety-analysis.md`

- [ ] **Step 1: Research and document Australian requirements**

Create `docs/compliance/australian-online-safety-analysis.md` covering:

1. **Online Safety Act 2021** — Basic Online Safety Expectations, cyberbullying takedown scheme, image-based abuse reporting, eSafety Commissioner powers
2. **Social Media Minimum Age Bill 2024** — Under-16 ban, exemption criteria, enforcement timeline, penalties
3. **Exemption analysis** — Does Bhapi Social qualify as a "designated internet service" or is it exempt as an educational/safety platform? Document arguments for and against.
4. **Fallback plan** — If exemption denied: Social app serves 16+ in AU only (jurisdiction-based age gate in `age_tier_configs.jurisdiction`). Safety app available for all ages.
5. **Technical requirements** — Yoti age verification (mandatory in AU), eSafety Commissioner automated reporting API, 24h content takedown SLA, cyberbullying rapid-response workflow
6. **Timeline** — When to engage AU legal counsel, when to submit exemption application (if applicable)

- [ ] **Step 2: Commit**

```bash
git add docs/compliance/australian-online-safety-analysis.md
git commit -m "docs: Australian Online Safety Act + Social Media Minimum Age Bill analysis"
```

---

## Task 6: Moderation Pipeline Design (P0-10)

**Goal:** Technical design document for the pre-publish / post-publish content moderation pipeline.

**Files:**
- Create: `docs/architecture/moderation-pipeline-design.md`

- [ ] **Step 1: Write moderation architecture document**

Create `docs/architecture/moderation-pipeline-design.md` covering:

1. **Pipeline overview** — Flow diagram from content submission to approve/reject
2. **Age-tier routing** — How content enters pre-publish vs post-publish pipeline based on `age_tier_configs.tier`
3. **Fast-path keyword classifier** — Word list structure (per-tier, per-category), matching algorithm (<100ms target), hold-and-release queue design
4. **AI classification** — Vertex AI / keyword fallback, 14-category risk taxonomy scoring, confidence thresholds
5. **Image pipeline** — Cloudflare Images webhook → CSAM check (PhotoDNA) → Hive/Sensity classification → approve/reject. Pre-signed upload URL flow.
6. **Video pipeline** — Cloudflare Stream upload → frame extraction (key frames at 1fps) → classify frames → approve/reject
7. **CSAM detection** — PhotoDNA integration point, NCMEC CyberTipline API, evidence preservation, account suspension
8. **Moderation queue schema** — `moderation_queue` table design, status transitions, SLA tracking
9. **Performance targets** — Pre-publish <2s p95, post-publish takedown <60s p95, keyword check <100ms
10. **Observability** — Latency dashboards, false positive/negative sampling, queue depth alerts
11. **Module boundaries** — `src/moderation/` owns queue + decisions tables, communicates with `src/social/`, `src/messaging/`, `src/media/` via public interfaces

Include sequence diagrams for:
- Pre-publish flow (5-9 and 10-12 tiers)
- Post-publish flow (13-15 tier)
- Image upload + moderation flow
- CSAM detection + NCMEC reporting flow

- [ ] **Step 2: Commit**

```bash
git add docs/architecture/moderation-pipeline-design.md
git commit -m "docs: moderation pipeline architecture design (pre-publish, post-publish, CSAM)"
```

---

## Task 7: Incident Response Plan (P0-12)

**Goal:** Documented incident response plan covering data breach, child safety, platform abuse, and service outage.

**Files:**
- Create: `docs/security/incident-response-plan.md`

- [ ] **Step 1: Write incident response plan**

Create `docs/security/incident-response-plan.md` based on spec Section 14.1. Cover all four categories:

1. **Data Breach** — Detection, containment, scope assessment, regulatory notification (COPPA/FTC, EU GDPR/DPA 72h, AU OAIC), parent notification, remediation, post-incident review
2. **Child Safety Incident** — Self-harm (parent alert <5min, escalate to emergency contacts at 30min), predator contact (block <15min, NCMEC if applicable, FBI ICAC), CSAM (NCMEC <30min, suspend account), imminent danger (911/emergency)
3. **Platform Abuse** — Coordinated harassment (<1h removal), viral harmful content (<30min takedown), mass account creation (rate limit, CAPTCHA)
4. **Service Outage** — SEV-1 (all hands, <1h restore), SEV-2 (disable content creation if moderation down — fail closed), SEV-3 (normal triage)

Include:
- Contact list (NCMEC CyberTipline URL/phone, FBI ICAC, eSafety Commissioner, relevant DPAs)
- Decision authority matrix (who can take platform offline, who approves law enforcement contact)
- Communication templates (parent notification, school notification, regulatory notification)
- Post-incident review template

- [ ] **Step 2: Commit**

```bash
git add docs/security/incident-response-plan.md
git commit -m "docs: incident response plan (breach, child safety, abuse, outage)"
```

---

## Task 8: Content Ownership ToS (P0-13)

**Goal:** Draft Terms of Service covering content ownership, minor consent, and AI-generated content.

**Files:**
- Create: `docs/compliance/content-ownership-tos-draft.md`

- [ ] **Step 1: Draft ToS document**

Create `docs/compliance/content-ownership-tos-draft.md` covering:

1. **Acceptance by parent/guardian** — Minors cannot agree to ToS. Parent/guardian agrees on behalf during onboarding. Written in child-friendly language per UK AADC.
2. **Content ownership** — Child-created content owned by child (represented by parent). Bhapi holds limited license for display, moderation, and platform operation only.
3. **No training on child content** — Bhapi will NOT use child-created content to train AI/ML models. Moderation models use synthetic/curated datasets only.
4. **AI-generated content** — Content created using Bhapi AI tools (Phase 3) licensed to child for personal use. AI provider terms apply. No commercial rights.
5. **Content removal** — Child/parent can delete content at any time. Platform can remove content that violates community guidelines. Moderation decisions can be appealed.
6. **Data retention** — Content retained per COPPA/GDPR retention policies. Deleted content purged from CDN within 72h, hard-deleted from DB within 30 days.
7. **CSAM exception** — Content flagged as CSAM preserved for law enforcement per legal obligation, even after account deletion.

**Note:** This is a DRAFT for legal review. Not for public use until reviewed by legal counsel.

- [ ] **Step 2: Commit**

```bash
git add docs/compliance/content-ownership-tos-draft.md
git commit -m "docs: draft content ownership ToS (minors, AI content, no-training policy)"
```

---

## Task 9: Hiring Pipeline (P0-11)

**Goal:** Publish job descriptions and start interview pipeline for Phase 1 team ramp.

**Files:**
- Create: `docs/hiring/phase1-roles.md`

- [ ] **Step 1: Document roles needed**

Create `docs/hiring/phase1-roles.md` with job descriptions for:

1. **Senior Mobile Engineer (Expo/React Native)** — Build Safety + Social apps. Expo monorepo, shared packages, real-time messaging. 2-3 positions.
2. **Senior Backend Engineer (Python/FastAPI)** — Social modules, moderation pipeline, WebSocket service. 1-2 positions.
3. **Safety/ML Engineer** — Content moderation models, grooming/cyberbullying detection, CSAM integration. 1 position.
4. **DevOps/Security Engineer** — CI/CD for monorepo, Cloudflare integration, security hardening, penetration testing. 1 position (can be fractional/contract).

Each role should include: responsibilities, required experience, nice-to-have, and compensation range.

- [ ] **Step 2: Commit**

```bash
git add docs/hiring/phase1-roles.md
git commit -m "docs: Phase 1 hiring plan — 4 roles, 5-7 engineers"
```

---

## Task 10: Update CLAUDE.md (Cross-Cutting)

**Goal:** Update CLAUDE.md to reflect the unified platform direction, new ADRs, and monorepo.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add unified platform section to CLAUDE.md**

Add to CLAUDE.md (after existing content, before Appendix):

```markdown
## Unified Platform (ADR-005, Phase 0+)

The Bhapi platform is being unified per the design spec at `docs/superpowers/specs/2026-03-19-bhapi-unified-platform-design.md`.

### Key Decisions (ADRs)
- ADR-001 through ADR-005: See `docs/adrs/`
- ADR-006: Two mobile apps (Safety + Social) in Expo monorepo
- ADR-007: Cloudflare R2/Images/Stream for media storage
- ADR-008: Separate WebSocket real-time service
- ADR-009: Three age tiers (5-9, 10-12, 13-15)
- ADR-010: Clean break from legacy repos (no MongoDB migration)

### Mobile Monorepo
- Location: separate `bhapi-mobile` repository
- Structure: Turborepo + Expo SDK 52+ with 6 shared packages
- Apps: `com.bhapi.safety` (parent) and `com.bhapi.social` (child)

### New Backend Modules (Phase 1+)
Social features built as new modules in `src/`. See spec Section 2.3 for full list.
Next migration: 032.

### Moderation Pipeline
Pre-publish for under-13, post-publish for 13-15. See `docs/architecture/moderation-pipeline-design.md`.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with unified platform direction and ADR references"
```

---

## Phase 0 Exit Checklist

Run this checklist at end of Phase 0 (April 22):

- [ ] COPPA 2026 compliant (already done)
- [ ] Legacy repos archived (3/3 read-only on GitHub)
- [ ] Legacy feature inventories committed (3 documents)
- [ ] ADR-006 through ADR-010 written and committed
- [ ] Expo monorepo scaffolded, CI green, ≥20 shared package tests passing
- [ ] Australian compliance requirements documented
- [ ] Moderation pipeline architecture designed and reviewed
- [ ] Incident response plan documented
- [ ] Content ownership ToS drafted
- [ ] Hiring roles published, interview pipeline active
- [ ] CLAUDE.md updated
- [ ] Test count: ≥1,887 (existing 1,847 + 20 monorepo + 20 any backend)
- [ ] All documents committed and pushed to master

**When complete:** Write the Phase 1 detailed implementation plan at `docs/superpowers/plans/2026-04-23-phase1-moat-defense.md` using the current codebase state, actual team composition, and any lessons from Phase 0.
