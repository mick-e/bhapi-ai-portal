/**
 * Bhapi AI Safety Monitor — AI Platform Detector
 *
 * Identifies which AI platform the user is currently on based on the
 * page URL.  Returns null for unsupported / unrecognised URLs.
 */

import { PlatformType } from "../shared/types";

/** URL pattern rules for each supported AI platform. */
const PLATFORM_PATTERNS: ReadonlyArray<{
  platform: PlatformType;
  /** One or more hostname substrings to match. */
  hostnames: string[];
  /** Optional path prefix that must also match. */
  pathPrefix?: string;
}> = [
  {
    platform: "chatgpt",
    hostnames: ["chatgpt.com"],
  },
  {
    platform: "gemini",
    hostnames: ["gemini.google.com"],
  },
  {
    platform: "copilot",
    hostnames: ["copilot.microsoft.com"],
  },
  {
    platform: "claude",
    hostnames: ["claude.ai"],
  },
  {
    platform: "grok",
    hostnames: ["grok.com"],
  },
  {
    // Grok is also accessible at x.com/i/grok
    platform: "grok",
    hostnames: ["x.com"],
    pathPrefix: "/i/grok",
  },
];

/**
 * Detect which AI platform the given URL belongs to.
 *
 * @param url - A fully qualified URL string (e.g. window.location.href).
 * @returns The PlatformType if recognised, or null otherwise.
 */
export function detectPlatform(url: string): PlatformType | null {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }

  const hostname = parsed.hostname.toLowerCase();
  const pathname = parsed.pathname.toLowerCase();

  for (const rule of PLATFORM_PATTERNS) {
    const hostnameMatch = rule.hostnames.some(
      (h) => hostname === h || hostname.endsWith(`.${h}`),
    );
    if (!hostnameMatch) continue;

    if (rule.pathPrefix) {
      if (pathname.startsWith(rule.pathPrefix.toLowerCase())) {
        return rule.platform;
      }
      // Hostname matched but path did not — continue checking other rules
      continue;
    }

    return rule.platform;
  }

  return null;
}
