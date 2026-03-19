# ADR-006: Two-App Mobile Strategy

## Status: Accepted

## Date: 2026-03-19

## Context

The Bhapi Platform needs mobile presence for two distinct audiences: parents (monitoring dashboard, alerts, child activity review) and children aged 5-15 (safe social feed, messaging, creative tools).

A single app with role switching creates several problems:

1. **UX complexity.** Parents need data-dense dashboards; children need playful, age-appropriate interfaces. Cramming both into one app forces compromises for both audiences.
2. **App Store review complications.** Apple and Google have separate review guidelines for children's apps (Apple Kids Category, Google Designed for Families) versus monitoring/parental control tools. A single app that is both a children's social network and a parental monitoring tool will face contradictory review requirements.
3. **Privacy isolation.** Children should never see monitoring data. Parents should never accidentally post to the social feed. Separate apps enforce this boundary architecturally.

## Decision

Build two separate Expo apps in a Turborepo monorepo:

### Bhapi Safety (`com.bhapi.safety`)
- **Audience:** Parents and guardians
- **Purpose:** Monitoring dashboard, real-time alerts, child activity timeline, spend tracking, content review, blocking controls
- **App Store category:** Utilities / Parental Controls

### Bhapi Social (`com.bhapi.social`)
- **Audience:** Children aged 5-15
- **Purpose:** Safe social feed, messaging, creative tools, AI literacy modules
- **App Store category:** Social Networking (Kids Category on Apple)
- **Age tiers:** Three tiers per ADR-009 (Young 5-9, Pre-teen 10-12, Teen 13-15)

### Shared Packages (6)

| Package | Purpose |
|---------|---------|
| `shared-ui` | Design tokens, base components (Button, Card, Avatar) |
| `shared-auth` | JWT handling, session management, biometric auth |
| `shared-api` | API client, React Query hooks, WebSocket connection |
| `shared-i18n` | Translation infrastructure, 6 languages (EN, FR, ES, DE, PT-BR, IT) |
| `shared-config` | Environment config, feature flags, age tier definitions |
| `shared-types` | TypeScript types shared between apps |

### Monorepo Structure
```
apps/
  safety/          # Parent app (Expo)
  social/          # Child app (Expo)
packages/
  shared-ui/
  shared-auth/
  shared-api/
  shared-i18n/
  shared-config/
  shared-types/
```

## Consequences

**Positive:**

- Separate App Store listings allow targeted metadata, screenshots, and descriptions for each audience.
- Separate review processes: the children's app can comply with Kids Category requirements without conflicting with parental control tool guidelines.
- Age-appropriate UX per audience without compromise. The child app can use playful design; the parent app can use data-dense layouts.
- Independent release cycles. A bug fix in the parent app does not require re-reviewing the children's app.
- Shared packages eliminate code duplication while maintaining app separation.

**Negative:**

- Two apps to maintain, test, and release. CI pipeline complexity increases (two build targets per platform = 4 builds).
- Two CI pipelines (though Turborepo caching mitigates build time).
- Potential user confusion: parents need to install Safety, children need Social. Mitigated by cross-linking in App Store descriptions and in-app prompts.
- Shared package versioning requires discipline to avoid breaking changes.

**Risks:**

- App Store rejection for either app. **Mitigation:** Pre-submit consultation with Apple (App Store Connect) and Google (Designed for Families pre-launch checklist). Build compliance into the development process, not as an afterthought.
- Children installing the parent app or vice versa. **Mitigation:** Age gate on Social app launch; Safety app requires parent account login.

## Alternatives Considered

### Single App with Role Switching

- **Pros:** One codebase, one App Store listing, simpler deployment.
- **Cons:** Contradictory App Store review requirements. UX compromise for both audiences. Risk of children accessing monitoring data through role switching bugs. Apple may reject a Kids Category app that contains parental monitoring features.
- **Rejected because:** App Store compliance risk is too high for a children's safety platform.

### Native Apps (Swift/Kotlin) Instead of Expo

- **Pros:** Maximum platform integration, best performance.
- **Cons:** Doubles development effort (two languages, two codebases per app = 4 codebases). The team's primary expertise is TypeScript/React. Per ADR-004, Expo provides sufficient native capability.
- **Rejected because:** ADR-004 already decided on Expo. Two Expo apps are manageable; four native codebases are not.

## Related ADRs

- [ADR-004](004-mobile-tech-choices.md) — Mobile technology choices (Expo SDK 52+)
- [ADR-005](005-platform-unification.md) — Platform unification (single repository strategy)
- [ADR-009](009-age-tier-permission-model.md) — Age tier permission model (defines the three tiers used in Social app)
