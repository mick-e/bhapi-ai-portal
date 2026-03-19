# ADR-003: Single PostgreSQL Database (No MongoDB Migration)

**Status:** Superseded by ADR-010
**Date:** 2026-03-17 (updated 2026-03-19)
**Deciders:** Engineering Team

## Context

The legacy Bhapi App (bhapi-inc/bhapi-api) uses MongoDB with Mongoose ODM. The Bhapi AI Portal uses PostgreSQL with SQLAlchemy async and Alembic migrations. The original question was whether to migrate MongoDB data to PostgreSQL.

## Decision

**No migration.** PostgreSQL is the sole database for the unified platform. All new social features (feed, messaging, contacts, moderation) are built as new tables in the existing PostgreSQL database via Alembic migrations.

The legacy MongoDB data is abandoned (ADR-010: clean break). Reasons:
- ~0 active users on the legacy platform (1.0 App Store rating, non-functional per user reviews)
- 18 known Snyk vulnerabilities in the legacy repos
- 0 tests across all 3 legacy repos — no confidence in data integrity
- Importing unvalidated data from an insecure system into a children's safety platform introduces unacceptable risk

The legacy MongoDB instance should be kept read-only for 12 months to satisfy any GDPR data subject access requests from former users, then decommissioned.

## Consequences

### Positive
- Single database technology to operate, monitor, back up, and tune
- All data benefits from PostgreSQL's ACID transactions, foreign key constraints, and Alembic migrations
- No ETL script development, testing, or validation effort
- No data quality risks from importing legacy data
- Clean schema design for social features (not constrained by MongoDB document shapes)

### Negative
- Any existing legacy users lose their data (negligible impact — ~0 active users)
- 12-month MongoDB read-only retention cost for GDPR compliance

### Risks
- **Former user GDPR request:** A legacy user could request their data under GDPR right of access. **Mitigation:** MongoDB kept read-only for 12 months with documented access procedure. After 12 months, data deleted per retention policy.

## Alternatives Considered

### Migrate MongoDB Data to PostgreSQL
- Originally planned (see git history for the full migration strategy)
- **Rejected because:** ADR-010 (clean break) eliminates the need. No users to migrate, and importing unvalidated data into a children's platform is irresponsible.

### Keep MongoDB for Social Features
- Two databases in parallel
- **Rejected because:** Operational burden, no cross-database referential integrity, doubles attack surface.

## Related ADRs

- [ADR-005](005-platform-unification.md) — Platform unification (PostgreSQL is the unified data layer)
- [ADR-010](010-clean-break-no-data-migration.md) — Clean break / no data migration (supersedes the original migration plan)
