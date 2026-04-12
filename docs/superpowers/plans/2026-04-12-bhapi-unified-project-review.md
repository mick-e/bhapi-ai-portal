# Bhapi AI Portal — Unified Project Review Execution Plan

> **For agentic workers:** This is a research/audit plan, not a code implementation plan. Execute tasks sequentially — Phase 1 tasks (1-5) run as parallel subagents, Phase 2 tasks (6-9) run sequentially to synthesize findings.

**Goal:** Produce a comprehensive, graded (A-F) project review of bhapi-ai-portal v4.0.0 across 6 dimensions: code quality, security, architecture, feature completeness, UX, and competitive position.

**Architecture:** 5 parallel audit agents produce dimension-specific findings, then a synthesis phase merges them into a single deliverable with executive summaries, a report card, and strategic recommendations.

**Output:** `docs/superpowers/specs/2026-04-12-bhapi-unified-project-review.md`

---

## Phase 1: Parallel Audit Agents

> All 5 tasks below MUST be dispatched simultaneously as parallel subagents. Each agent operates independently on the bhapi-ai-portal codebase at `C:\claude\bhapi-ai-portal`.

### Task 1: Code Quality Audit Agent

**Agent type:** general-purpose (read-only research)

**Prompt for agent:**

You are auditing the bhapi-ai-portal project at `C:\claude\bhapi-ai-portal` for **code quality**. This is a FastAPI + Next.js + Expo monorepo (v4.0.0). Produce a graded audit report.

**Run these commands and analyze output:**

1. `cd C:/claude/bhapi-ai-portal && ruff check src/ --statistics` — count lint violations by rule category
2. `cd C:/claude/bhapi-ai-portal && ruff check portal/src/ --statistics 2>/dev/null || echo "ruff not configured for TS"` — check if frontend has linting
3. Grep for `TODO|FIXME|HACK|XXX` across `src/`, `portal/src/`, `mobile/`, `extension/` — count by directory
4. Find all Python files >500 lines: `find src/ -name "*.py" -exec wc -l {} + | sort -rn | head -20`
5. Find all TypeScript files >500 lines: `find portal/src/ -name "*.tsx" -o -name "*.ts" | xargs wc -l | sort -rn | head -20`
6. Read `requirements.txt` and check for pinned vs unpinned deps
7. Read `portal/package.json` and `mobile/package.json` for dependency versions
8. Map test coverage: for each of the 28 backend modules in `src/`, check if corresponding test files exist in `tests/unit/` and `tests/e2e/`. List modules with 0 test files.
9. Check for dead/unused imports: `ruff check src/ --select F401 --statistics`
10. Check for code duplication patterns: look at `router.py` files across 5+ modules and identify repeated boilerplate

**Grading criteria (A-F):**
- A: <10 lint issues, all modules tested, no >500 LOC files, deps pinned, no TODOs
- B: <50 lint issues, >80% modules tested, <3 large files, mostly pinned deps
- C: <100 lint issues, >60% modules tested, some large files, mix of pinned/unpinned
- D: >100 lint issues, <60% modules tested, many large files
- F: >500 lint issues, major gaps in testing, widespread issues

**Output format (MUST follow exactly):**

```
## Code Quality Audit

### Executive Summary
[2-3 sentences, non-technical]

### Grade: [A-F]
[1 paragraph justification with specific numbers]

### Findings
1. [Critical|High|Medium|Low|Info] [Finding title] — [Details with file paths and line numbers]
2. ...

### Strengths
- [Strength with evidence]
- ...

### Recommendations
1. [Action item] — Effort: [S|M|L], Impact: [H|M|L]
2. ...
```

---

### Task 2: Security Audit Agent

**Agent type:** general-purpose (read-only research)

**Prompt for agent:**

You are auditing the bhapi-ai-portal project at `C:\claude\bhapi-ai-portal` for **security**. This is a FastAPI + Next.js platform handling children's data (COPPA/GDPR regulated). Produce a graded security audit.

**Investigate these areas:**

1. **Auth flow:** Read `src/auth/router.py`, `src/auth/service.py`, `src/dependencies.py`. Trace: registration → JWT issuance → token refresh → API key creation. Check for:
   - Token expiry enforcement
   - Refresh token rotation
   - Password hashing algorithm (bcrypt? argon2?)
   - Session invalidation on password change

2. **Public routes:** Read `src/main.py` and the AuthMiddleware. List every route that skips authentication. Check if any should require auth.

3. **SQL injection:** Grep for `text(` in `src/` (raw SQL). Check if any use string formatting/f-strings for query construction. Check for proper parameterization.

4. **Headers/CORS:** Read the middleware stack. Check CSP policy, HSTS config, X-Frame-Options, Permissions-Policy against OWASP recommendations.

5. **Secrets management:** 
   - Check `.gitignore` for `.env*` patterns
   - Grep for hardcoded secrets/keys in `src/` (patterns: `sk_`, `sk-`, `api_key =`, `secret =`, `password =` with string literals)
   - Read `src/config.py` — how are secrets loaded? Any defaults that could leak?

6. **COPPA consent enforcement:** Read `src/capture/service.py` and grep for `check_third_party_consent` and `check_family_agreement` across all of `src/`. Verify every external API call (SendGrid, Twilio, Google Cloud AI, Hive/Sensity) is gated.

7. **Rate limiting:** Read `src/middleware/rate_limit.py` (or similar). Check which endpoints have rate limits and which don't. Check the fail-open vs fail-closed config.

8. **Stripe webhooks:** Read `src/billing/` — check webhook signature validation, event deduplication.

9. **Encryption:** Read `src/encryption.py` — algorithm, key derivation, rotation support.

10. **Dependency vulnerabilities:** Run `cd C:/claude/bhapi-ai-portal && pip-audit 2>/dev/null || echo "pip-audit not available"` and check CI config for vulnerability scanning.

**Grading criteria (A-F):**
- A: No critical/high findings, complete COPPA enforcement, strong auth, proper secrets management
- B: No critical findings, <3 high findings, COPPA mostly enforced, good auth
- C: No critical findings but >3 high findings, some COPPA gaps, adequate auth
- D: 1+ critical findings, significant COPPA gaps, auth weaknesses
- F: Multiple critical findings, SQL injection, leaked secrets, broken auth

**Output format (MUST follow exactly):**

```
## Security Audit

### Executive Summary
[2-3 sentences, non-technical]

### Grade: [A-F]
[1 paragraph justification]

### Findings
1. [Critical|High|Medium|Low|Info] [Finding title] — [Details with file paths and line numbers]
2. ...

### Strengths
- [Strength with evidence]
- ...

### Recommendations
1. [Action item] — Effort: [S|M|L], Impact: [H|M|L]
2. ...
```

---

### Task 3: Architecture Review Agent

**Agent type:** general-purpose (read-only research)

**Prompt for agent:**

You are auditing the bhapi-ai-portal project at `C:\claude\bhapi-ai-portal` for **architecture quality**. This is a monorepo with 28 FastAPI backend modules, a Next.js frontend, 2 Expo mobile apps, and a browser extension. Produce a graded architecture review.

**Investigate these areas:**

1. **Module coupling:** The project claims "no cross-module imports." Verify this:
   - For each module directory under `src/`, grep for imports from other modules (e.g., in `src/alerts/`, grep for `from src.billing` or `from src.capture` etc.)
   - List any violations with file paths and line numbers
   - Check `__init__.py` files — are they proper public interfaces or do they re-export internals?

2. **DB schema health:** 
   - Read `alembic/versions/` — are there 53 sequential migrations with no gaps?
   - Read 3-4 model files (`src/auth/models.py`, `src/social/models.py`, `src/capture/models.py`, `src/billing/models.py`) — check for proper use of mixins, relationship definitions, index coverage
   - Check `alembic/env.py` — are all models imported?
   - Look for potential N+1 query patterns in service files (loading relationships without `selectinload`/`joinedload`)

3. **3-service boundary:**
   - Read `src/main.py` — how are the 28 modules mounted?
   - Read `src/realtime/main.py` — is it truly independent or does it import from core modules?
   - Read `src/jobs/` — does it duplicate logic from core modules or properly call through service interfaces?
   - Read `render.yaml` — are the 3 services properly isolated with separate DB pools?

4. **Async correctness:**
   - Grep for `time.sleep(` in `src/` (blocking call in async context)
   - Grep for `open(` without `aio` prefix in `src/` (sync file I/O)
   - Grep for `requests.` in `src/` (sync HTTP client — should be httpx)
   - Check if any CPU-intensive operations run in the event loop without `run_in_executor`

5. **API design consistency:**
   - Read 5 router files and check: consistent pagination? Consistent error responses? Consistent URL naming (kebab-case vs snake_case)?
   - Check the pagination contract: is it `{items, total, page, page_size, total_pages}` everywhere?

6. **Error propagation:**
   - Read `src/exceptions.py` — is the hierarchy clean?
   - Check 3-4 service files — do they use the exception hierarchy consistently?
   - Check if any endpoints catch-all swallow errors

7. **Connection pool sizing:**
   - Read `src/database.py` — how is pooling configured?
   - With 35 total connections on Render Starter (max 97 connections on Starter PostgreSQL), is there headroom?

8. **Frontend architecture:**
   - Read `portal/next.config.js` or `portal/next.config.mjs` — static export constraints
   - Check `portal/src/app/` — how many layouts, are there nested layouts, route grouping?
   - Check `portal/src/hooks/` — data fetching patterns, API client setup

**Grading criteria (A-F):**
- A: Zero coupling violations, clean schema, proper async, consistent API, well-bounded services
- B: <3 coupling issues, minor schema gaps, mostly async-correct, consistent API
- C: <10 coupling issues, some schema debt, occasional blocking calls, API inconsistencies
- D: >10 coupling issues, schema problems, blocking calls in hot paths, inconsistent API
- F: Spaghetti architecture, circular dependencies, major schema issues, widespread blocking

**Output format (MUST follow exactly):**

```
## Architecture Review

### Executive Summary
[2-3 sentences, non-technical]

### Grade: [A-F]
[1 paragraph justification]

### Findings
1. [Critical|High|Medium|Low|Info] [Finding title] — [Details with file paths and line numbers]
2. ...

### Strengths
- [Strength with evidence]
- ...

### Recommendations
1. [Action item] — Effort: [S|M|L], Impact: [H|M|L]
2. ...
```

---

### Task 4: Feature & UX Audit Agent

**Agent type:** general-purpose (read-only research)

**Prompt for agent:**

You are auditing the bhapi-ai-portal project at `C:\claude\bhapi-ai-portal` for **feature completeness and usability**. This platform serves parents, school admins, and clubs monitoring children's AI usage. Produce a graded assessment covering both features and UX.

**Part A — Feature Completeness:**

1. **Module inventory:** For each of the 28 backend modules in `src/`, read the `router.py` and categorize:
   - **Complete:** Has routes, service logic, models, tests, frontend page
   - **Functional:** Has routes and logic but missing frontend or tests
   - **Skeleton:** Has route stubs but minimal logic
   - **Missing:** Referenced in docs but doesn't exist

2. **Regulatory compliance check:**
   - Read `src/compliance/` — COPPA 2026 features (deny-by-default consent, child-friendly notices, parental dashboard, deletion). What's implemented vs missing?
   - Check for EU AI Act transparency features
   - Check for Ohio school AI governance features
   - Check for FERPA compliance features

3. **Billing maturity:**
   - Read `src/billing/router.py` and `src/billing/service.py` — Stripe integration depth
   - Check: plan creation, subscription management, webhook handling, invoice generation, refunds, trial management, per-seat pricing
   - Read the frontend billing page(s)

4. **Integration depth:**
   - Read `src/integrations/` — are Clever, ClassLink, Yoti, Google Workspace, Entra SSO real implementations or stubs?
   - Check for OAuth token handling, data sync logic, error handling

5. **Mobile readiness:**
   - Read 5-6 mobile screens in `mobile/apps/safety/app/` and `mobile/apps/social/app/`
   - Check: are they wired to real API calls or still using mocks?
   - Check shared packages: `mobile/packages/shared-api/` — real HTTP client or stubs?

6. **Extension coverage:**
   - Read `extension/src/content/platforms/` — how many of the 10 platform detectors have real detection logic vs placeholder?

**Part B — Usability & UX:**

7. **Frontend page audit:** Read 10 key pages in `portal/src/app/`:
   - Dashboard, alerts, activity, members, settings, safety, billing, compliance, moderation, social-feed
   - For each: Does it have loading state? Error state? Empty state? Is the layout consistent?

8. **i18n completeness:**
   - Read `portal/messages/en.json` and one other language file (e.g., `fr.json`)
   - Compare key counts — are they equal? Any keys in EN missing from FR?

9. **Accessibility:**
   - Grep for `aria-` attributes in `portal/src/`
   - Grep for `role=` attributes
   - Check color contrast: read the Tailwind config or global CSS for the orange (#FF6B35) and teal (#0D9488) colors — do they meet WCAG AA on white?
   - Check mobile accessibility: read `mobile/packages/shared-ui/` for MotionProvider, ContrastProvider, FontProvider

10. **Onboarding flow:**
    - Read the registration page and dashboard page
    - Is there a clear first-time user path? Contextual onboarding cards?
    - What does a new user with zero data see?

**Grading criteria:**

*Feature Completeness (A-F):*
- A: All 28 modules complete with frontend + tests, all regulatory features implemented, integrations real
- B: >80% modules complete, key regulatory features done, most integrations real
- C: >60% modules complete, some regulatory gaps, mix of real/skeleton integrations
- D: <60% complete, major regulatory gaps, mostly skeleton integrations
- F: Majority skeleton/missing, regulatory non-compliance

*Usability & UX (A-F):*
- A: All pages have loading/error/empty states, full i18n, WCAG AA, polished onboarding
- B: Most pages handled, minor i18n gaps, good accessibility, functional onboarding
- C: Some pages missing states, notable i18n gaps, basic accessibility
- D: Many pages missing states, significant i18n gaps, poor accessibility
- F: No error handling, no i18n, no accessibility consideration

**Output format (MUST follow exactly):**

```
## Feature Completeness Assessment

### Executive Summary
[2-3 sentences, non-technical]

### Grade: [A-F]
[1 paragraph justification]

### Findings
1. [Critical|High|Medium|Low|Info] [Finding title] — [Details]
2. ...

### Strengths
- [Strength with evidence]

### Recommendations
1. [Action item] — Effort: [S|M|L], Impact: [H|M|L]

---

## Usability & UX Assessment

### Executive Summary
[2-3 sentences, non-technical]

### Grade: [A-F]
[1 paragraph justification]

### Findings
1. [Critical|High|Medium|Low|Info] [Finding title] — [Details]
2. ...

### Strengths
- [Strength with evidence]

### Recommendations
1. [Action item] — Effort: [S|M|L], Impact: [H|M|L]
```

---

### Task 5: Competitive Intelligence Agent

**Agent type:** general-purpose (web research + file reading)

**Prompt for agent:**

You are conducting competitive intelligence for the bhapi-ai-portal project at `C:\claude\bhapi-ai-portal`. Produce an updated competitive analysis comparing Bhapi against 8 competitors.

**Step 1: Read the existing gap analysis**

Read `C:\claude\bhapi-ai-portal\docs\Bhapi_Gap_Analysis_Q2_2026.md` (it's 105KB — read in chunks). Extract:
- Competitor feature lists as of March 17, 2026
- Pricing data
- Market sizing
- Strategic recommendations made

**Step 2: Web research for current state (April 2026)**

For each competitor, search the web for current information:

1. **Bark** (bark.us) — current pricing, features, any new AI monitoring capabilities, app store ratings
2. **Qustodio** (qustodio.com) — current pricing, features, platform support, international presence
3. **Net Nanny** (netnanny.com) — current pricing, features, any recent product updates
4. **Google Family Link** — current features, any 2026 updates, limitations
5. **Apple Screen Time** — current features, any iOS 19/macOS 16 changes
6. **GoGuardian** (goguardian.com) — current AI monitoring capabilities, pricing, school coverage
7. **Gaggle** (gaggle.net) — current features, human review model updates, pricing
8. **Securly** (securly.com) — current features, international expansion, pricing

For each search, note the date accessed and URL source.

**Step 3: Build updated feature comparison matrix**

Create a feature matrix with these categories (rows) and competitors (columns):

Categories:
- AI chat monitoring (which platforms?)
- Content filtering
- Screen time management
- Location tracking
- Social media monitoring
- App management/blocking
- SMS/call monitoring
- Email monitoring
- Self-harm/suicide detection
- Cyberbullying detection
- Deepfake detection
- CSAM detection
- Safe social network
- School deployment (Chromebook/managed devices)
- SIS integration (Clever, ClassLink)
- SSO (Google, Microsoft, Apple)
- Age verification
- Parental alerts
- AI literacy/education
- Regulatory compliance (COPPA, EU AI Act, FERPA)
- API platform/developer tools
- Multi-language support
- Mobile apps (iOS/Android)
- Browser extension
- Pricing (monthly/annual)

**Step 4: Pricing comparison**

Build a pricing table:
| Competitor | Free Tier | Basic | Premium | School/Enterprise |
|-----------|-----------|-------|---------|-------------------|

Include Bhapi's pricing: Free / Family $9.99 / Family+ $14.99 / School $2.99/seat / Enterprise custom

**Step 5: Differentiation analysis**

Based on the feature matrix, identify:
- Where Bhapi leads (features no competitor has)
- Where Bhapi trails (table-stakes features Bhapi lacks)
- Bhapi's unique positioning (what combination of features is unique?)
- Competitive moat strength (sustainable vs temporary advantages)

**Step 6: Gap analysis delta**

Compare your findings against the March 2026 gap analysis. What has changed in the competitive landscape in the last month? What findings from the original analysis are now outdated?

**Output format (MUST follow exactly):**

```
## Competitive Analysis

### 8.1 Market Landscape Update
[What shifted since March 17, 2026 gap analysis]

### 8.2 Competitor Set
[Already documented in design spec — reference it]

### 8.3 Feature Comparison Matrix
[Full matrix table]

### 8.4 Pricing Comparison
[Pricing table with all 9 products]

### 8.5 Differentiation Analysis
#### Where Bhapi Leads
- ...
#### Where Bhapi Trails
- ...
#### Unique Positioning
- ...
#### Moat Strength
- ...

### 8.6 App Store & Review Sentiment
[Ratings, common complaints, trends for each competitor]

### Executive Summary
[2-3 sentences, non-technical]

### Grade: [A-F]
[1 paragraph justification — grade is Bhapi's competitive POSITION, not quality]

### Findings
1. [Critical|High|Medium|Low|Info] [Finding title] — [Details]
2. ...

### Strengths
- [Bhapi competitive advantage with evidence]

### Recommendations
1. [Action item] — Effort: [S|M|L], Impact: [H|M|L]

### Data Sources
[URL, date accessed for each competitor]
```

---

## Phase 2: Synthesis

> Phase 2 tasks run sequentially AFTER all Phase 1 agents return results.

### Task 6: Merge Agent Findings

- [ ] **Step 1:** Collect output from all 5 agents
- [ ] **Step 2:** Create unified findings table — assign sequential IDs (F-001, F-002, ...) across all dimensions
- [ ] **Step 3:** Resolve conflicting assessments (e.g., if security agent flags something the architecture agent missed, or vice versa)
- [ ] **Step 4:** Cross-reference findings — tag findings that span multiple dimensions (e.g., a missing test [Code Quality] for a security-critical module [Security])

---

### Task 7: Write Report Card & Executive Summary

- [ ] **Step 1:** Compile the 6 dimension grades into a report card table:

```markdown
| Dimension | Grade | One-Line Summary |
|-----------|-------|-----------------|
| Code Quality | [X] | [summary] |
| Security | [X] | [summary] |
| Architecture | [X] | [summary] |
| Feature Completeness | [X] | [summary] |
| Usability & UX | [X] | [summary] |
| Competitive Position | [X] | [summary] |
| **Overall** | **[X]** | **[summary]** |
```

- [ ] **Step 2:** Calculate overall grade (weighted: Security 25%, Architecture 20%, Code Quality 15%, Features 15%, UX 10%, Competitive 15%)
- [ ] **Step 3:** Write executive summary: overall grade, top 5 strengths, top 5 risks, strategic verdict (2-3 paragraphs, non-technical language)

---

### Task 8: Write Strategic Recommendations

- [ ] **Step 1:** Extract all recommendations from the 6 dimension reports
- [ ] **Step 2:** De-duplicate and merge overlapping recommendations
- [ ] **Step 3:** Categorize into time horizons:
  - **Immediate (0-30 days):** Critical fixes, quick wins, security issues
  - **Short-term (30-90 days):** Competitive parity items, testing gaps, architecture improvements
  - **Medium-term (90-180 days):** Differentiation investments, market expansion, major features
- [ ] **Step 4:** For each recommendation, document: description, effort (S/M/L), impact (H/M/L), dimensions affected

---

### Task 9: Assemble Final Document & Commit

- [ ] **Step 1:** Assemble all sections into `docs/superpowers/specs/2026-04-12-bhapi-unified-project-review.md` following the deliverable structure from the design spec
- [ ] **Step 2:** Add appendices:
  - A. Methodology (tools, techniques, data sources used)
  - B. Full findings table (all F-xxx findings sorted by severity)
  - C. Competitor data sources (URLs, dates)
  - D. Gap analysis delta (changes since March 2026)
- [ ] **Step 3:** Self-review: scan for placeholders, internal contradictions, missing cross-references
- [ ] **Step 4:** Commit:
```bash
git add docs/superpowers/specs/2026-04-12-bhapi-unified-project-review.md
git commit -m "docs: add comprehensive unified project review (6 dimensions, A-F graded)"
```
- [ ] **Step 5:** Present summary to user with key findings and overall grade
