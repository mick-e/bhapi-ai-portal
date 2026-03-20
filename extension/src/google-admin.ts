/**
 * Google Admin MDM deployment support for Bhapi extension.
 *
 * Detects managed Chrome browser environments and applies
 * enterprise policies pushed via Google Admin Console.
 */

export interface ManagedPolicy {
  contentFiltering?: boolean;
  safeSearch?: boolean;
  monitoringLevel?: "basic" | "standard" | "strict";
  blockedCategories?: string[];
  allowedDomains?: string[];
}

export interface ManagedInstallState {
  isManaged: boolean;
  schoolId?: string;
  deviceId?: string;
  policy?: ManagedPolicy;
}

const DEFAULT_STATE: ManagedInstallState = {
  isManaged: false,
};

/**
 * Check if the extension is running in a managed Chrome environment.
 */
export async function detectManagedEnvironment(): Promise<ManagedInstallState> {
  try {
    if (
      typeof chrome === "undefined" ||
      !chrome.storage ||
      !chrome.storage.managed
    ) {
      return DEFAULT_STATE;
    }

    return new Promise((resolve) => {
      chrome.storage.managed.get(null, (items) => {
        if (chrome.runtime.lastError || !items || Object.keys(items).length === 0) {
          resolve(DEFAULT_STATE);
          return;
        }

        resolve({
          isManaged: true,
          schoolId: items.schoolId ?? undefined,
          deviceId: items.deviceId ?? undefined,
          policy: {
            contentFiltering: items.contentFiltering ?? true,
            safeSearch: items.safeSearch ?? true,
            monitoringLevel: items.monitoringLevel ?? "standard",
            blockedCategories: items.blockedCategories ?? [],
            allowedDomains: items.allowedDomains ?? [],
          },
        });
      });
    });
  } catch {
    return DEFAULT_STATE;
  }
}

/**
 * Apply managed policy settings to extension behaviour.
 */
export function applyManagedPolicy(policy: ManagedPolicy): void {
  if (typeof chrome === "undefined" || !chrome.storage || !chrome.storage.local) {
    return;
  }

  chrome.storage.local.set({
    "bhapi_managed_policy": policy,
    "bhapi_managed_at": new Date().toISOString(),
  });
}

/**
 * Report deployment status back to the Bhapi API.
 */
export async function reportDeploymentStatus(
  apiBase: string,
  schoolId: string,
  deviceId: string,
  status: "deployed" | "pending" | "error",
): Promise<boolean> {
  try {
    const response = await fetch(
      `${apiBase}/api/v1/integrations/google-admin/devices/${schoolId}/${deviceId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      },
    );
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Listen for managed policy changes and re-apply.
 */
export function watchPolicyChanges(
  callback: (policy: ManagedPolicy) => void,
): void {
  if (
    typeof chrome === "undefined" ||
    !chrome.storage ||
    !chrome.storage.onChanged
  ) {
    return;
  }

  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName !== "managed") return;

    const policy: ManagedPolicy = {};
    if (changes.contentFiltering) policy.contentFiltering = changes.contentFiltering.newValue;
    if (changes.safeSearch) policy.safeSearch = changes.safeSearch.newValue;
    if (changes.monitoringLevel) policy.monitoringLevel = changes.monitoringLevel.newValue;
    if (changes.blockedCategories) policy.blockedCategories = changes.blockedCategories.newValue;
    if (changes.allowedDomains) policy.allowedDomains = changes.allowedDomains.newValue;

    if (Object.keys(policy).length > 0) {
      callback(policy);
    }
  });
}
