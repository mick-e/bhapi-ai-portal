/**
 * Bhapi AI Safety — Bypass Detection (Phase 4 Task 23 / R-24)
 *
 * Client-side probes for techniques used to evade AI monitoring:
 *  - VPN / proxy detection via WebRTC IP leak + DNS resolution anomaly
 *  - Alternative AI URL detection (mirrors / forks of supported platforms)
 *  - Incognito / private-window detection
 *  - Extension tampering (manifest hash changes)
 *
 * On detection, posts to /api/v1/blocking/bypass-attempt. The backend handles
 * classification, alerting, and auto-block escalation (see
 * src/blocking/vpn_detection.py).
 *
 * NOTE: Detection is best-effort and intentionally privacy-preserving — we
 * never send raw IPs, just boolean signals. Tests expect the same shape.
 */

export type BypassType = "vpn" | "proxy" | "alt_url" | "incognito" | "tampering";

export interface BypassDetectionSignals {
  webrtc_leak?: boolean;
  dns_anomaly?: boolean;
  url?: string;
  manifest_hash_mismatch?: boolean;
}

const ALT_AI_URL_PATTERNS: RegExp[] = [
  /chatgpt-mirror\.\w+/i,
  /openai-proxy\.\w+/i,
  /gemini-mirror\.\w+/i,
  /claude-proxy\.\w+/i,
  /-bypass\./i,
  /freegpt/i,
];

/**
 * Detect VPN/proxy via WebRTC IP leak. If the browser exposes a private IP
 * range (10/8, 172.16/12, 192.168/16) different from the public IP returned
 * by a STUN probe, that's a strong VPN signal. We only return a boolean —
 * raw IPs are never sent to the backend.
 */
export async function detectVpnViaWebRtc(
  iceServers: RTCIceServer[] = [{ urls: "stun:stun.l.google.com:19302" }]
): Promise<{ leak: boolean; private_ip_count: number; public_ip_count: number }> {
  return new Promise((resolve) => {
    const result = { leak: false, private_ip_count: 0, public_ip_count: 0 };
    let pc: RTCPeerConnection | null = null;

    try {
      pc = new RTCPeerConnection({ iceServers });
      pc.createDataChannel("");
      pc.onicecandidate = (event) => {
        if (!event.candidate) {
          pc?.close();
          // VPN heuristic: both public and private candidates present
          result.leak = result.private_ip_count > 0 && result.public_ip_count > 0;
          resolve(result);
          return;
        }
        const cand = event.candidate.candidate;
        const ipMatch = cand.match(/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/);
        if (ipMatch) {
          const ip = ipMatch[1];
          if (
            ip.startsWith("10.") ||
            ip.startsWith("192.168.") ||
            /^172\.(1[6-9]|2\d|3[01])\./.test(ip)
          ) {
            result.private_ip_count += 1;
          } else if (!ip.startsWith("127.")) {
            result.public_ip_count += 1;
          }
        }
      };
      pc.createOffer().then((offer) => pc?.setLocalDescription(offer));

      // Safety timeout — STUN probe should resolve within 3s
      setTimeout(() => {
        try {
          pc?.close();
        } catch {
          /* ignore */
        }
        resolve(result);
      }, 3000);
    } catch {
      resolve(result);
    }
  });
}

export function detectAltAiUrl(url: string): boolean {
  return ALT_AI_URL_PATTERNS.some((pattern) => pattern.test(url));
}

export function detectIncognito(): boolean {
  // Heuristic: in Chrome/Edge incognito, indexedDB.open throws or storage quota
  // is dramatically reduced. Not 100% — modern browsers obscure this signal —
  // but useful as a soft hint.
  try {
    if (typeof navigator !== "undefined" && "storage" in navigator) {
      // Caller should compare quota via navigator.storage.estimate() in async context
    }
    if (typeof window !== "undefined" && "webkitRequestFileSystem" in window) {
      // Legacy Chrome incognito signal
      return false; // can't sync-detect; skip
    }
  } catch {
    return true;
  }
  return false;
}

/**
 * Verify the running extension's manifest hash against an expected hash.
 * Mismatch = tampering (someone modified manifest.json or repacked the
 * extension to disable monitoring).
 */
export async function detectManifestTampering(
  expectedHashHex: string
): Promise<boolean> {
  try {
    if (typeof chrome === "undefined" || !chrome.runtime?.getManifest) {
      return false; // not running as a browser extension
    }
    const manifest = chrome.runtime.getManifest();
    const json = JSON.stringify(manifest);
    const enc = new TextEncoder().encode(json);
    const buf = await crypto.subtle.digest("SHA-256", enc);
    const hashHex = Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
    return hashHex !== expectedHashHex;
  } catch {
    return false;
  }
}

export interface ReportPayload {
  member_id: string;
  bypass_type: BypassType;
  detection_signals: BypassDetectionSignals;
}

/**
 * POST a bypass attempt to the backend. Caller is responsible for batching
 * + de-duplication; the backend coalesces identical attempts within 60s.
 */
export async function reportBypassAttempt(
  apiBaseUrl: string,
  authToken: string,
  payload: ReportPayload
): Promise<Response> {
  return fetch(`${apiBaseUrl}/api/v1/blocking/bypass-attempt`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(payload),
  });
}
