# ADR-003: MongoDB to PostgreSQL Migration

**Status:** Accepted
**Date:** 2026-03-17
**Deciders:** Engineering Team

## Context

The Bhapi ecosystem currently uses two database technologies:

- **Bhapi AI Portal**: PostgreSQL with SQLAlchemy async, Alembic migrations (16 migrations), GIN-indexed full-text search, and async connection pooling. This database backs 1,400+ passing tests and handles all safety-critical data (risk assessments, compliance records, billing).
- **Bhapi App (bhapi-inc/bhapi-api)**: MongoDB with Mongoose ODM. Stores user profiles, posts, messages, and follower relationships. The MongoDB instance has no migration tooling, no schema validation beyond Mongoose schemas, and 0 automated tests covering data integrity.

Platform unification requires a single data layer. We need to decide which database to standardize on and how to migrate.

## Decision

Migrate all data from MongoDB to PostgreSQL. The AI Portal's PostgreSQL database becomes the single source of truth for the unified platform.

### Migration Strategy

1. **Schema mapping**: Map each MongoDB collection to PostgreSQL tables with proper types, constraints, foreign keys, and indexes. Create Alembic migrations for all new tables.

2. **ETL script**: Build a Python ETL script (`scripts/migrate_mongo_to_pg.py`) that:
   - Connects to MongoDB read-only.
   - Transforms documents to relational rows (flattening nested objects, normalizing arrays into junction tables).
   - Deduplicates users by email address (MongoDB users matched to existing Portal users by email; unmatched users get new Portal accounts with a forced password reset).
   - Inserts into PostgreSQL within transactions, with idempotent upsert logic for re-runnability.
   - Logs every skip, merge, and conflict for audit.

3. **Staged rollout**:
   - **Phase 1**: Run ETL in dry-run mode, validate row counts and referential integrity.
   - **Phase 2**: Run ETL for real against a staging PostgreSQL instance. Run the full test suite against it.
   - **Phase 3**: Production cutover. Run ETL, switch application to PostgreSQL, verify.
   - **Phase 4**: Keep MongoDB in read-only mode for 30 days as a safety net. Decommission after 30 days with no issues.

4. **User deduplication**: Email address is the merge key. When a MongoDB user's email matches an existing Portal user, the accounts are merged: the Portal account is authoritative for auth credentials and permissions, and the MongoDB account's social data (posts, messages, followers) is associated with the Portal user ID.

## Consequences

### Positive

- Single database technology to operate, monitor, back up, and tune.
- All data benefits from PostgreSQL's ACID transactions, foreign key constraints, and CHECK constraints.
- Full-text search via `to_tsvector`/`plainto_tsquery` with GIN indexes replaces any MongoDB text index usage, with better ranking and language support.
- Alembic provides versioned, reviewable, reversible schema migrations for all tables.
- The existing async SQLAlchemy infrastructure (connection pooling, session management, tenant isolation) covers all data access patterns.
- Test infrastructure (async test sessions, factories, fixtures) works for all data immediately.

### Negative

- One-time migration effort: ETL script development, testing, and validation (~1-2 weeks).
- MongoDB's flexible schema allowed some documents to have inconsistent shapes; these need manual review and normalization during mapping.
- 30-day dual-database retention period increases hosting costs temporarily.
- Any MongoDB-specific query patterns (aggregation pipelines, `$lookup`) must be rewritten as SQL joins or CTEs.

### Risks

- **Data loss during ETL**: Malformed MongoDB documents or edge cases in the transform logic could silently drop records. **Mitigation:** Dry-run mode with row-count validation before any production write; full audit log of every skip, merge, and conflict.
- **User deduplication conflicts**: Two MongoDB accounts mapped to the same email, or a MongoDB account whose email does not exist in the Portal. **Mitigation:** ETL script handles all three cases explicitly (merge, create-new, conflict-report); conflicts require manual review before cutover.
- **30-day MongoDB retention cost**: Two live databases during the retention window. **Mitigation:** The cost is bounded and time-limited; MongoDB instance is set to read-only immediately after cutover.

## Alternatives Considered

### Keep MongoDB for Social Features

- **Pros**: No migration effort. MongoDB's document model is a natural fit for posts and messages (nested comments, variable metadata). Existing Mongoose schemas work as-is.
- **Cons**: Two databases to operate, back up, and monitor. Cross-database joins are impossible; any query spanning user auth (PostgreSQL) and social data (MongoDB) requires application-level joins. No foreign key constraints between social data and user records. No Alembic migrations for schema changes. The 0-test MongoDB codebase remains untestable without significant investment. Doubles the infrastructure attack surface.
- **Rejected because**: The operational burden of two databases and the inability to enforce referential integrity across them outweigh the migration effort.

### Migrate to MongoDB (Drop PostgreSQL)

- **Pros**: MongoDB's document model handles social features naturally.
- **Cons**: Loses ACID transactions for billing and compliance data. Loses Alembic migration tooling. Loses GIN-indexed FTS. Loses 1,400+ tests that depend on SQLAlchemy models and PostgreSQL behavior. Loses foreign key constraints that enforce data integrity for safety-critical features (risk assessments linked to users, COPPA consent records). Would require rewriting the entire AI Portal data layer.
- **Rejected because**: PostgreSQL's guarantees are essential for billing, compliance, and child safety data. Rewriting the proven data layer is an unacceptable risk.

### Use Both with a Sync Layer

- **Pros**: No migration needed. Each database handles what it's best at.
- **Cons**: Data synchronization between two databases is a source of subtle bugs (eventual consistency, failed syncs, ordering issues). Adds operational complexity (sync monitoring, conflict resolution). Does not reduce the number of technologies to maintain. Still no referential integrity across boundaries.
- **Rejected because**: Sync layers introduce more problems than they solve at this scale. The simplicity of one database outweighs any theoretical performance benefit of polyglot persistence.

## Related ADRs

- [ADR-005](005-platform-unification.md) — Platform unification (this migration is a prerequisite step in the consolidation plan)
- [ADR-010](010-clean-break-no-data-migration.md) — Clean break / no data migration (supersedes this ADR if the decision is made to not carry legacy data forward)
