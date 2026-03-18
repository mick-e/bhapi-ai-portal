# ADR-005: Platform Unification and Repository Consolidation

## Status: Accepted

## Date: 2026-03-17

## Context

The Bhapi ecosystem currently spans four repositories across two GitHub organizations:

| Repository | Organization | Stack | Tests | Status |
|-----------|-------------|-------|-------|--------|
| `bhapi-api` | bhapi-inc | Node.js/Express + MongoDB | 0 | Legacy, no active development |
| `bhapi-app` | bhapi-inc | React Native 0.64 | 0 | Legacy, no active development |
| `bhapi-web` | bhapi-inc | React (CRA) | 0 | Legacy, no active development |
| `bhapi-ai-portal` | mick-e | FastAPI + Next.js + PostgreSQL | 1,400+ | Active, v2.1.0 |

The three `bhapi-inc` repositories collectively have 0 automated tests, use outdated dependencies (React Native 0.64, Create React App), and have not seen active feature development. The AI Portal has 1,400+ tests (639 E2E, 521 unit, 154 security), 19 backend modules, a Next.js frontend with i18n and WCAG 2.1 AA compliance, and a Chrome/Firefox/Safari extension monitoring 10 AI platforms.

Maintaining four repositories with duplicate infrastructure (two separate auth systems, two databases, two deployment pipelines) creates confusion about which codebase is authoritative and doubles operational burden.

## Decision

Unify all Bhapi products under a single "Bhapi Platform" brand with the AI Portal repository as the sole active codebase.

### Execution plan:

1. **Rename repository**: `mick-e/bhapi-ai-portal` becomes `mick-e/bhapi-platform`. GitHub handles redirects from the old name automatically.

2. **Archive legacy repositories**: All three `bhapi-inc` repositories (`bhapi-api`, `bhapi-app`, `bhapi-web`) are archived on GitHub (read-only, visible, not deletable by accident). Archive commit message documents the reason and points to the new repository.

3. **Data migration**: MongoDB data is migrated to PostgreSQL per ADR-003. User accounts are deduplicated by email.

4. **Mobile app**: Greenfielded on Expo SDK 52+ per ADR-004. The old `bhapi-app` React Native 0.64 code is archived, not ported.

5. **Social features**: Built as new modules in the existing FastAPI backend per ADR-002. The old `bhapi-api` Express routes serve as functional reference only.

6. **Auth unification**: The AI Portal's JWT + API key system becomes the single auth layer per ADR-001.

7. **Brand consolidation**:
   - Domain: `bhapi.ai` (already owned and serving the AI Portal).
   - Product name: "Bhapi Platform" (or simply "Bhapi").
   - The AI safety monitoring features remain core, with social features as a new product vertical.

8. **CI/CD**: Single GitHub Actions pipeline. Single Render deployment (already configured via `render.yaml`).

## Consequences

**Positive:**

- One repository to maintain, one CI pipeline, one deployment, one set of dependencies to keep current.
- Zero-test legacy code is archived, not carried forward. The unified platform starts with 1,400+ tests as its baseline, not 0.
- Single auth system eliminates the "which login do I use?" confusion for users.
- Single database eliminates cross-database integrity issues and reduces hosting costs.
- Developer onboarding involves one codebase, one set of patterns, one `README`.
- Security patches are applied in one place. No risk of forgetting to patch the "other" API.
- The brand story is simple: Bhapi is one product, not a confusing collection of loosely related repos.

**Negative:**

- Archiving repositories is psychologically difficult (sunk cost). The team must accept that code with 0 tests and outdated dependencies has negative value, not positive value.
- GitHub redirects from the old repository name will work, but any hardcoded references (CI scripts, documentation, bookmarks) need updating.
- Users of the old Bhapi App will need to create new accounts on the unified platform (mitigated by email-based deduplication during migration).
- The monorepo grows in scope, which increases CI build times (mitigated by targeted test runs and caching).

## Alternatives Considered

### Keep Separate Repositories, Add Integration Layer

- **Pros**: No migration effort. Each team works independently. Microservices architecture is theoretically more scalable.
- **Cons**: The three legacy repos have 0 tests and outdated dependencies. "Keeping" them means either investing significant effort to bring them to a testable state or continuing to operate untested code in production. An integration layer (API gateway, shared auth service) adds complexity without reducing the total amount of code to maintain. Two databases, two auth systems, and four CI pipelines remain. The "integration layer" becomes a fifth thing to maintain.
- **Rejected because**: The legacy repos provide negative value in their current state. Integrating them requires more effort than replacing them, and the end result is more complex.

### Incremental Migration (Keep All Repos Active, Migrate Feature by Feature)

- **Pros**: Lower risk per step. Old system remains available as fallback. No big-bang cutover.
- **Cons**: Extends the period of maintaining duplicate infrastructure. Every feature that exists in both the old and new system must be kept in sync during the migration period. Users may be confused about which system to use. The "incremental" approach often stalls partway through, leaving the organization permanently maintaining two half-complete systems. With 0 tests in the legacy repos, there is no way to verify that the old system still works correctly during the migration.
- **Rejected because**: The legacy repos have no tests, making incremental migration unverifiable. The risk of a clean cutover (archive old, use new) is actually lower than the risk of an indefinite dual-system maintenance period.

### Rewrite Everything from Scratch

- **Pros**: Perfectly clean codebase. No legacy patterns carried forward.
- **Cons**: The AI Portal is not legacy. It has 1,400+ tests, 19 modules, COPPA/GDPR compliance, a production deployment, and active users. Rewriting it would discard months of validated, production-proven code. This is the classic "second system effect" antipattern.
- **Rejected because**: The AI Portal is the good codebase. The decision is to archive the bad code and keep the good code, not to throw away everything and start over.
