/**
 * Bhapi shared-native — cross-platform bridge for native OS APIs.
 *
 * Phase 4 Task 28 (iOS PermissionKit) + Task 29 (Android Digital Wellbeing).
 *
 * All functions degrade gracefully: on unsupported platforms they return a
 * well-formed `unsupported` result rather than throwing, so callers don't
 * need platform guards at every call site.
 *
 * **Testing:** Native modules can't be exercised in Jest/CI. Integration
 * tests require a physical iOS 26 device (PermissionKit) or an Android
 * device with `PACKAGE_USAGE_STATS` granted in Settings. See
 * `__tests__/integration.md` for manual test plans.
 */

import { NativeModules, Platform } from 'react-native';

// ---------------------------------------------------------------------------
// iOS PermissionKit (Task 28, R-23)
// ---------------------------------------------------------------------------

export interface ParentApprovalResult {
  status: 'approved' | 'denied' | 'timeout' | 'unsupported';
  /** Reason the OS gave us, if any (diagnostic only). */
  reason?: string;
}

/**
 * Ask the OS to request parental approval via iOS 26 PermissionKit.
 *
 * Falls back to `{ status: 'unsupported' }` on Android, web, or pre-iOS 26.
 * Callers should then route to the in-app parental approval flow.
 */
export async function requestParentApproval(
  reason: string,
  childAccountId: string,
): Promise<ParentApprovalResult> {
  if (Platform.OS !== 'ios') return { status: 'unsupported', reason: `platform=${Platform.OS}` };
  const { PermissionKitBridge } = NativeModules;
  if (!PermissionKitBridge) {
    return { status: 'unsupported', reason: 'bridge_missing' };
  }
  try {
    const result = await PermissionKitBridge.requestParentApproval(reason, childAccountId);
    return { status: result.status as ParentApprovalResult['status'] };
  } catch (e) {
    return { status: 'unsupported', reason: String(e) };
  }
}

/**
 * True if PermissionKit is available on this device (iOS 26+ with the
 * framework linked). Callers use this to decide whether to surface the
 * system flow or skip straight to the in-app flow.
 */
export function isPermissionKitAvailable(): boolean {
  return Platform.OS === 'ios' && Boolean(NativeModules.PermissionKitBridge);
}

// ---------------------------------------------------------------------------
// Android Digital Wellbeing (Task 29, P4-NAT1)
// ---------------------------------------------------------------------------

export interface AppUsageEntry {
  packageName: string;
  /** Total foreground time in milliseconds over the last 24h. */
  totalTimeMs: number;
  /** Unix ms timestamp of last foreground usage. */
  lastTimeUsed: number;
}

/**
 * Fetch the last 24h of per-app foreground time via Android's
 * `UsageStatsManager`. Requires the special `PACKAGE_USAGE_STATS`
 * permission (grantable only from system Settings — use
 * `openUsageStatsSettings()` to direct the user there).
 *
 * Returns `[]` on iOS, unsupported platforms, or permission-denied.
 * The caller can distinguish by also checking
 * `isDigitalWellbeingAvailable()` before calling.
 */
export async function getDailyAppUsage(): Promise<AppUsageEntry[]> {
  if (Platform.OS !== 'android') return [];
  const { DigitalWellbeingBridge } = NativeModules;
  if (!DigitalWellbeingBridge) return [];
  try {
    return await DigitalWellbeingBridge.getDailyAppUsage();
  } catch {
    return [];
  }
}

/**
 * Open the system Settings screen where the user can grant
 * `PACKAGE_USAGE_STATS`. Resolves when the Intent fires — not when the
 * user actually grants the permission (Android doesn't give us a
 * callback for that).
 */
export async function openUsageStatsSettings(): Promise<void> {
  if (Platform.OS !== 'android') return;
  const { DigitalWellbeingBridge } = NativeModules;
  if (!DigitalWellbeingBridge) return;
  try {
    await DigitalWellbeingBridge.openUsageStatsSettings();
  } catch {
    /* swallow — no recovery action available here */
  }
}

export function isDigitalWellbeingAvailable(): boolean {
  return Platform.OS === 'android' && Boolean(NativeModules.DigitalWellbeingBridge);
}
