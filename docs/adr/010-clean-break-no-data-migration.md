# ADR-010: Clean Break — No MongoDB Data Migration

## Status: Accepted

## Date: 2026-03-19

## Context

The legacy bhapi.com platform runs on three repositories in the `bhapi-inc` GitHub organization:

| Repository | Stack | Tests | Known Issues |
|-----------|-------|-------|-------------|
| `bhapi-api` | Node.js/Express + MongoDB | 0 | 18 Snyk security vulnerabilities |
| `bhapi-app` | React Native 0.64.2 | 0 | 3 major versions behind current |
| `bhapi-web` | React (Create React App) | 0 | CRA deprecated, no maintenance |

The AI Portal (this repository) runs on PostgreSQL with FastAPI/SQLAlchemy, has 1,578+ passing tests, and is actively maintained.

The question is whether to migrate data from the legacy MongoDB database into the new PostgreSQL database.

### Evidence of negligible active usage

- **App Store ratings/reviews:** ~0 recent reviews across iOS and Android.
- **Legacy API:** No monitoring or analytics to confirm active usage (the API has 0 tests and no observability).
- **Security posture:** 18 known Snyk vulnerabilities in `bhapi-api`. Migrating data from a system with known security vulnerabilities into a children's safety platform introduces risk.
- **Data quality:** No validation layer in the legacy API (0 tests = 0 schema enforcement). MongoDB documents may contain inconsistent, incomplete, or malformed data.

### Migration cost estimate

Even if migration were desirable, the effort would be significant:

1. **Schema mapping:** MongoDB schemaless documents to PostgreSQL typed columns. Every field must be manually mapped and validated.
2. **Data cleaning:** Without tests or validation in the legacy system, every document must be individually verified.
3. **User deduplication:** Users may exist in both systems (by email). Merge logic for overlapping accounts.
4. **Password migration:** Legacy password hashing algorithm must be identified and either migrated or users forced to reset.
5. **Referential integrity:** MongoDB has no foreign keys. PostgreSQL does. Orphaned references must be resolved.
6. **Testing:** The migration itself needs comprehensive testing — but the source system has 0 tests to validate against.

Estimated effort: 2-4 weeks for a migration that benefits approximately 0 active users.

## Decision

No data migration from MongoDB to PostgreSQL. Clean start.

### Specific actions:

1. **No ETL scripts.** No migration tooling will be built.
2. **Legacy repos archived.** All three `bhapi-inc` repositories are archived on GitHub as read-only reference per ADR-005.
3. **New App Store listing.** The Bhapi Social app uses `com.bhapi.social` (new bundle ID), not the existing `com.bhapi` bundle. No connection to the legacy app listing.
4. **New user accounts.** All users create fresh accounts on the new platform. There is no "import my old data" flow.
5. **Legacy data retained.** The MongoDB database is not deleted. It remains accessible (read-only) in case any historical reference is needed. No SLA on its availability.
6. **Feature reference.** Legacy code serves as functional reference for social features (ADR-002). The code is consulted for feature parity; the data is not migrated.

## Consequences

**Positive:**

- No migration complexity. Zero risk of importing malformed, unvalidated, or security-compromised data into the new platform.
- Clean security posture. The new platform starts with a known-good, empty database. No inherited vulnerabilities from the legacy system's 18 Snyk issues.
- Simpler architecture. No ETL pipeline, no dual-database read period, no migration rollback plan.
- Faster time to market. 2-4 weeks of migration effort redirected to building new features.
- No legacy schema debt. PostgreSQL schema is designed for current requirements, not constrained by MongoDB document shapes.

**Negative:**

- Any existing users lose their data. Based on evidence (~0 active users), this affects approximately nobody. However, if users do exist, the loss is total — there is no partial migration.
- The decision is irreversible in practice. Once legacy repos are archived and the MongoDB instance is decommissioned, migration becomes impossible. (Mitigated by keeping MongoDB read-only, not deleting it.)

**Risks:**

- Legacy users exist and complain. **Mitigation:** Update the legacy app's README and App Store description to point to the new Bhapi platform. Include a migration notice in the legacy web app's landing page. Provide a support email for any users who need assistance.
- Legal obligation to retain legacy data (e.g., GDPR data subject requests for data created on the old platform). **Mitigation:** Keep the MongoDB instance in read-only mode for 12 months after archival. Process any data subject requests manually against the legacy database during this period.
- Team sentiment: "we should migrate just in case." **Mitigation:** This ADR documents the evidence-based rationale. The burden of proof is on migration advocates to identify specific active users who would benefit.

## Alternatives Considered

### Full Data Migration (ETL from MongoDB to PostgreSQL)

- **Pros:** No data loss for any users, however few. Continuity of service.
- **Cons:** 2-4 weeks of effort for ~0 users. Imports unvalidated data from a system with 18 security vulnerabilities and 0 tests. Creates pressure to maintain backward compatibility with legacy data shapes. Migration bugs could corrupt the new database.
- **Rejected because:** The cost-benefit ratio is negative. The effort is significant, the benefit is negligible, and the risk of importing bad data is real.

### Selective Migration (Users Only, No Content)

- **Pros:** Lighter than full migration. Users can log in with existing credentials.
- **Cons:** Still requires password hash migration, email deduplication, and schema mapping for user records. Users log in but find no data — arguably worse UX than creating a fresh account. Still imports data from an unvalidated source.
- **Rejected because:** A "you can log in but everything is empty" experience is worse than a clean "create a new account" experience.

### Offer Self-Service Data Export from Legacy

- **Pros:** Users who care can export their own data. Platform is not responsible for migration quality.
- **Cons:** Requires building an export feature in the legacy app (which has 0 tests and 18 vulnerabilities). Requires building an import feature in the new app. Two features for ~0 users.
- **Rejected because:** Building new features in a legacy system with 18 security vulnerabilities is not justifiable.

## Related ADRs

- [ADR-003](003-mongodb-to-postgresql.md) — PostgreSQL as the single database (this ADR clarifies: no data comes from MongoDB)
- [ADR-005](005-platform-unification.md) — Archive legacy repositories
