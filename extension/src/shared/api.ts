/**
 * Bhapi AI Safety Monitor — API Client
 *
 * Communicates with the Bhapi capture gateway.  All outbound requests
 * are HMAC-signed so the server can verify authenticity.
 *
 * Chrome: uses `chrome.storage.local` for configuration.
 * Firefox: the same API is available as `browser.storage.local`
 *          (or via the webextension-polyfill shim).
 */

import { signPayload } from "./crypto";
import { CaptureEvent, ExtensionConfig, DEFAULT_CONFIG } from "./types";

// ---------------------------------------------------------------------------
// Config helpers
// ---------------------------------------------------------------------------

/**
 * Retrieve the extension configuration from chrome.storage.local.
 * Returns DEFAULT_CONFIG values for any keys that are missing.
 */
export async function getConfig(): Promise<ExtensionConfig> {
  return new Promise((resolve) => {
    // chrome.storage.local.get accepts an object of defaults
    chrome.storage.local.get(DEFAULT_CONFIG, (items) => {
      resolve(items as ExtensionConfig);
    });
  });
}

/**
 * Persist a partial config update to chrome.storage.local.
 */
export async function saveConfig(partial: Partial<ExtensionConfig>): Promise<void> {
  return new Promise((resolve) => {
    chrome.storage.local.set(partial, () => {
      resolve();
    });
  });
}

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

interface ApiResponse<T = unknown> {
  ok: boolean;
  status: number;
  data: T | null;
  error: string | null;
}

/**
 * Make a signed request to the capture gateway.
 */
async function signedFetch<T = unknown>(
  config: ExtensionConfig,
  method: string,
  path: string,
  body?: unknown,
): Promise<ApiResponse<T>> {
  const url = `${config.apiUrl}${path}`;
  const timestamp = new Date().toISOString();
  const bodyString = body ? JSON.stringify(body) : "";

  // Build the string-to-sign: METHOD\nPATH\nTIMESTAMP\nBODY
  const stringToSign = [method, path, timestamp, bodyString].join("\n");

  let signature = "";
  if (config.signingSecret) {
    signature = await signPayload(stringToSign, config.signingSecret);
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Bhapi-Timestamp": timestamp,
    "X-Bhapi-Group": config.groupId,
    "X-Bhapi-Member": config.memberId,
  };

  if (signature) {
    headers["X-Bhapi-Signature"] = signature;
  }

  try {
    const response = await fetch(url, {
      method,
      headers,
      body: bodyString || undefined,
    });

    let data: T | null = null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = (await response.json()) as T;
    }

    return {
      ok: response.ok,
      status: response.status,
      data,
      error: response.ok ? null : `HTTP ${response.status}`,
    };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      data: null,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

// ---------------------------------------------------------------------------
// Public API methods
// ---------------------------------------------------------------------------

/**
 * Send a capture event to the Bhapi gateway.
 *
 * POST /api/v1/capture/events
 */
export async function sendEvent(event: CaptureEvent): Promise<ApiResponse> {
  const config = await getConfig();
  if (!config.apiUrl) {
    return { ok: false, status: 0, data: null, error: "API URL not configured" };
  }
  return signedFetch(config, "POST", "/api/v1/capture/events", event);
}

/**
 * Check the health of the capture gateway.
 *
 * GET /api/v1/capture/health
 */
export async function checkStatus(): Promise<ApiResponse<{ status: string }>> {
  const config = await getConfig();
  if (!config.apiUrl) {
    return { ok: false, status: 0, data: null, error: "API URL not configured" };
  }
  return signedFetch<{ status: string }>(config, "GET", "/api/v1/capture/health");
}

/**
 * Exchange a setup code for a signing secret and group/member IDs.
 *
 * POST /api/v1/capture/pair
 */
export async function pairWithSetupCode(
  apiUrl: string,
  setupCode: string,
): Promise<ApiResponse<{ groupId: string; memberId: string; signingSecret: string }>> {
  const tempConfig: ExtensionConfig = {
    ...DEFAULT_CONFIG,
    apiUrl,
  };

  try {
    const url = `${apiUrl}/api/v1/capture/pair`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ setupCode }),
    });

    let data = null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await response.json();
    }

    if (response.ok && data) {
      // Persist the received credentials
      await saveConfig({
        apiUrl,
        groupId: data.groupId,
        memberId: data.memberId,
        signingSecret: data.signingSecret,
        setupCode,
        enabled: true,
      });
    }

    return {
      ok: response.ok,
      status: response.status,
      data,
      error: response.ok ? null : `HTTP ${response.status}`,
    };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      data: null,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
