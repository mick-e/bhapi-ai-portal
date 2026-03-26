# Change Management Policy

**Version:** 1.0
**Effective:** 2026-08-01
**Owner:** CTO
**Review cycle:** Annual

## 1. Purpose

Ensure all changes to the Bhapi platform are authorized, tested, and traceable.

## 2. Code Changes

### 2.1 Repository
- Single monorepo: `bhapi-ai-portal` (GitHub)
- Primary branch: `master` with direct push workflow
- All commits include descriptive messages with task IDs (e.g., `feat(P2-S1): ...`)

### 2.2 Review Process
- Code review required before merge for production-impacting changes
- Automated CI via GitHub Actions on every push
- Type checking (`tsc --noEmit`) required — vitest does not catch type errors

### 2.3 Testing Requirements
- **Backend:** 4,639+ tests (pytest) — unit, E2E, security
- **Frontend:** 174+ tests (vitest) + type check
- **Mobile:** 665+ tests (jest via Turborepo)
- **Extension:** 43 tests (jest)
- All tests must pass before deployment

## 3. Database Changes

### 3.1 Migration Process
- All schema changes via Alembic migrations
- Migration files MUST be committed and pushed (uncommitted migrations caused multi-day outage 2026-03-12)
- `alembic/env.py` must import ALL models
- Migrations run automatically on deploy (`alembic upgrade head` in Dockerfile CMD)

### 3.2 Migration Review
- Verify generated migration with `git status`
- Test migration against SQLite in test suite
- Production runs against PostgreSQL 16

## 4. Deployment

### 4.1 Infrastructure
- Render auto-deploy from `master` branch
- Docker multi-stage build (Python + Node)
- Health check: `SELECT 1` SQL query

### 4.2 Rollback
- Render supports instant rollback to previous deploy
- Alembic supports downgrade migrations
- Feature flags for gradual rollout (via billing feature gates)

## 5. Emergency Changes

- Hotfixes pushed directly to `master` with `fix:` prefix
- Post-incident review within 48 hours
- Root cause documented in incident log
