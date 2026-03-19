# ADR-004: Mobile App Greenfield with Expo SDK 52+

**Status:** Accepted
**Date:** 2026-03-17
**Deciders:** Engineering Team

## Context

The existing Bhapi App mobile codebase (in `bhapi-inc/bhapi-app`) is built on React Native 0.64 (released March 2021). It has the following characteristics:

- **React Native 0.64**: Five major versions behind current (0.76+). Missing the New Architecture (Fabric renderer, TurboModules, JSI), Hermes as default engine, and numerous security patches.
- **No Expo**: Uses bare React Native CLI workflow with manual native module linking.
- **0 tests**: No unit, integration, or E2E tests of any kind.
- **localStorage for tokens**: Authentication tokens are stored in AsyncStorage (backed by localStorage on web, SharedPreferences/NSUserDefaults on native), which is unencrypted and vulnerable to XSS on web and trivially readable on rooted/jailbroken devices.
- **No TypeScript**: Entire codebase is plain JavaScript with no type checking.

The unified Bhapi Platform needs a mobile app that supports the AI Portal's safety features, the new social module, and meets the security bar required for a child safety product (COPPA compliance, encrypted credential storage).

## Decision

Greenfield the mobile app using Expo SDK 52+ with React Native 0.76+, rather than incrementally upgrading the existing React Native 0.64 codebase.

### Technology choices:

- **Framework**: Expo SDK 52+ (managed workflow with `expo-dev-client` for custom native modules when needed).
- **Runtime**: React Native 0.76+ with New Architecture enabled (Fabric, TurboModules).
- **Language**: TypeScript (strict mode).
- **Navigation**: Expo Router (file-based routing, consistent with Next.js patterns used in the web portal).
- **State/data**: TanStack Query (React Query) for server state (matching the web portal), Zustand for local state.
- **Auth token storage**: `expo-secure-store` (Keychain on iOS, EncryptedSharedPreferences on Android). Eliminates the localStorage XSS vulnerability.
- **Testing**: Jest + React Native Testing Library (unit/integration), Maestro (E2E).
- **CI**: GitHub Actions with EAS Build for native binaries.

### What gets carried forward from the old codebase:

- UI/UX patterns and screen designs (visual reference only, not code).
- API contract knowledge (endpoint shapes, auth flows).
- Nothing else. No code, no dependencies, no configuration.

## Consequences

### Positive

- Modern, secure foundation from day one. `expo-secure-store` fixes the critical token storage vulnerability.
- TypeScript catches entire classes of bugs at compile time that the untyped JS codebase could not.
- Expo's managed workflow dramatically simplifies native builds, OTA updates, and app store submissions.
- File-based routing (Expo Router) matches the Next.js pattern used in the web portal, reducing cognitive load for developers working across platforms.
- TanStack Query for data fetching matches the web portal, enabling shared API hooks or at minimum shared patterns.
- New Architecture (Fabric + TurboModules) provides better performance, smaller bridge overhead, and synchronous native module access.
- Test infrastructure is built in from the start, not bolted on after the fact.
- EAS Build handles iOS and Android builds in the cloud without requiring local Xcode/Android Studio setup.

### Negative

- The old mobile app's functionality must be rebuilt from scratch. Screens, navigation, and integrations are reimplemented.
- Team must learn Expo-specific patterns if not already familiar.
- Expo's managed workflow has some limitations for custom native modules (mitigated by `expo-dev-client` and config plugins).
- Two mobile codebases exist temporarily during the transition period until the old app is archived.

### Risks

- **App store review delays**: New apps require initial App Store / Google Play review, which can take 1-7 days. **Mitigation:** Submit for review early; use EAS Update (OTA) for bug fixes that do not require native changes.
- **Expo SDK version lag behind React Native**: Expo SDK releases trail React Native by weeks to months. **Mitigation:** Expo SDK 52 is current and stable; the managed workflow is the intended path.
- **Custom native module gaps**: Some device capabilities may not have Expo config plugins yet. **Mitigation:** `expo-dev-client` allows ejecting individual modules without leaving the managed workflow entirely.

## Alternatives Considered

### Incremental Upgrade (RN 0.64 to 0.76)

- **Estimated path**: 0.64 -> 0.66 -> 0.68 -> 0.71 -> 0.73 -> 0.76 (4-5 intermediate upgrades).
- **Estimated time**: 8-12 weeks, based on community reports of 1-3 weeks per major version jump, with significant time spent resolving native dependency conflicts.
- **Pros**: Preserves existing screens and navigation logic. No "rewrite" stigma.
- **Cons**: Each upgrade risks breaking native modules that may be unmaintained. The codebase still has 0 tests after the upgrade, meaning each version bump is done blind with no regression safety net. Still no TypeScript. Still no Expo (would need to be added separately after reaching 0.76, which is another multi-week effort). The localStorage token vulnerability persists unless separately addressed. At the end of 8-12 weeks, you have a 0.76 app with 0 tests, no types, and no Expo -- and then you still need to add all of those things.
- **Rejected because**: Similar calendar time to a greenfield, but produces an inferior result. The upgrade effort is high-risk (no tests to catch regressions) and the end state still requires significant additional work to reach parity with what a greenfield delivers on day one.

### Flutter

- **Pros**: Single codebase for iOS, Android, and web. Strong typing (Dart). Good performance (compiled to native ARM). Growing ecosystem.
- **Cons**: The entire web portal is React/Next.js and the team's expertise is in React. Choosing Flutter means learning Dart, a different component model, and different state management patterns. No code sharing between web and mobile. The API client layer must be rewritten in Dart. Flutter's web output is canvas-based, not DOM-based, which has SEO and accessibility limitations.
- **Rejected because**: The team is React-native (pun intended). The web portal is React. Choosing Flutter fragments the tech stack and eliminates any possibility of shared code or patterns between web and mobile.

### Progressive Web App (PWA)

- **Pros**: Single codebase (the existing Next.js portal). No app store submission. Instant updates.
- **Cons**: No access to Keychain/EncryptedSharedPreferences (tokens remain in localStorage). Push notifications are limited on iOS (no background push until iOS 16.4, still limited). No access to platform-specific parental control APIs. App store presence matters for consumer trust, especially for a child safety product. PWA install rates are significantly lower than native app downloads.
- **Rejected because**: The security requirements (encrypted token storage) and platform integration needs (parental controls, push notifications) require native capabilities that PWAs cannot provide.

## Related ADRs

- [ADR-006](006-two-app-mobile-strategy.md) — Two-app mobile strategy (builds on this decision; defines the Safety and Social app split)
