# shared-native — Integration Test Plan

Native modules can't be exercised in Jest/CI. These are manual device tests.

## iOS PermissionKit (Task 28)

**Device requirements:** Physical iPhone running iOS 26+ with a child Apple ID configured under Screen Time.

### TC-iOS-1 — approved path
1. Launch Safety app with child account signed in
2. From the Social app, trigger a contact-request flow that calls `requestParentApproval("Add new friend: Alex", childAccountId)`
3. Parent receives the iOS system prompt
4. Parent taps **Approve**
5. Expect: TS promise resolves with `{ status: 'approved' }`

### TC-iOS-2 — denied path
Same as TC-iOS-1 but parent taps **Deny**.
Expect: `{ status: 'denied' }`

### TC-iOS-3 — timeout
Same as TC-iOS-1 but parent ignores for 5 minutes (PermissionKit default timeout).
Expect: `{ status: 'timeout' }`

### TC-iOS-4 — framework unavailable
On an iOS 25 or older device, `isPermissionKitAvailable()` returns false and `requestParentApproval` returns `{ status: 'unsupported', reason: 'pre_ios26_or_framework_missing' }`.

## Android Digital Wellbeing (Task 29)

**Device requirements:** Physical Android device, Android 9+ (API 28).

### TC-Android-1 — permission not granted (first run)
1. Fresh install; grant nothing
2. Safety app screen-time screen shows permission CTA
3. Tap **Open Settings** → call lands user in `ACTION_USAGE_ACCESS_SETTINGS`
4. User grants Bhapi Safety access
5. Return to app — `getDailyAppUsage()` resolves with a non-empty list

### TC-Android-2 — permission granted
With the special permission granted:
- `isDigitalWellbeingAvailable()` returns true
- `getDailyAppUsage()` resolves with recent-use rows
- Total foreground time across all entries roughly matches Android Digital Wellbeing's own dashboard

### TC-Android-3 — permission revoked mid-session
User revokes permission in Settings while app is backgrounded.
- On resume, `getDailyAppUsage()` returns `[]`
- App surfaces the re-grant CTA

## Platform fallback tests (cross-platform)

### TC-FB-1 — iOS-only function on Android
`requestParentApproval(...)` on an Android device returns `{ status: 'unsupported', reason: 'platform=android' }`.

### TC-FB-2 — Android-only function on iOS
`getDailyAppUsage()` on iOS returns `[]`.

## Sign-off

Each TC should be executed on the target device matrix and recorded in
the Phase 4 release notes before the Phase 4 Launch Excellence gate closes.
