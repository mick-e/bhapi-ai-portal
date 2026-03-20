/**
 * School policy enforcement via Chrome managed storage.
 * Reads admin-configured settings from chrome.storage.managed,
 * which is populated by the school's Google Admin Console policy.
 *
 * This enables IT admins to centrally configure the extension
 * for all Chromebooks in the school without end-user interaction.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SchoolPolicy {
  /** Monitoring intensity level. */
  monitoringLevel: "standard" | "enhanced" | "maximum";
  /** Unique school identifier in Bhapi. */
  schoolId: string;
  /** Human-readable school name. */
  schoolName: string;
  /** List of AI platform identifiers to monitor. Empty means monitor all. */
  enabledPlatforms: string[];
  /** If true, block AI platforms not listed in enabledPlatforms. */
  blockUnmonitored: boolean;
  /** If true, only monitor during school hours. */
  schoolHoursOnly: boolean;
  /** School day start time in HH:MM format (24h). */
  schoolHoursStart: string;
  /** School day end time in HH:MM format (24h). */
  schoolHoursEnd: string;
  /** IANA timezone for the school (e.g. "America/New_York"). */
  schoolTimezone: string;
  /** Optional custom API endpoint for this school. */
  reportingEndpoint: string;
}

/** Default policy applied when no managed storage is configured. */
export const DEFAULT_POLICY: SchoolPolicy = {
  monitoringLevel: "standard",
  schoolId: "",
  schoolName: "",
  enabledPlatforms: [],
  blockUnmonitored: false,
  schoolHoursOnly: false,
  schoolHoursStart: "08:00",
  schoolHoursEnd: "15:00",
  schoolTimezone: "America/New_York",
  reportingEndpoint: "",
};

// ---------------------------------------------------------------------------
// Policy Manager
// ---------------------------------------------------------------------------

export class SchoolPolicyManager {
  private policy: SchoolPolicy | null = null;

  /**
   * Load the school policy from Chrome managed storage.
   * Falls back to DEFAULT_POLICY if managed storage is not configured
   * or is unavailable (e.g. non-Chrome browsers).
   */
  async loadPolicy(): Promise<SchoolPolicy | null> {
    try {
      if (
        typeof chrome === "undefined" ||
        !chrome.storage ||
        !chrome.storage.managed
      ) {
        this.policy = { ...DEFAULT_POLICY };
        return this.policy;
      }

      const managed = await new Promise<Record<string, unknown>>(
        (resolve) => {
          chrome.storage.managed.get(undefined, (items) => {
            // chrome.runtime.lastError is set when managed storage is
            // not configured (no policy JSON deployed by admin)
            if ((chrome.runtime as any).lastError) {
              resolve({});
            } else {
              resolve((items || {}) as Record<string, unknown>);
            }
          });
        },
      );

      if (Object.keys(managed).length === 0) {
        this.policy = { ...DEFAULT_POLICY };
        return this.policy;
      }

      this.policy = {
        monitoringLevel: this.validateMonitoringLevel(
          managed.monitoringLevel as string,
        ),
        schoolId: (managed.schoolId as string) || DEFAULT_POLICY.schoolId,
        schoolName:
          (managed.schoolName as string) || DEFAULT_POLICY.schoolName,
        enabledPlatforms: Array.isArray(managed.enabledPlatforms)
          ? (managed.enabledPlatforms as string[])
          : DEFAULT_POLICY.enabledPlatforms,
        blockUnmonitored:
          typeof managed.blockUnmonitored === "boolean"
            ? managed.blockUnmonitored
            : DEFAULT_POLICY.blockUnmonitored,
        schoolHoursOnly:
          typeof managed.schoolHoursOnly === "boolean"
            ? managed.schoolHoursOnly
            : DEFAULT_POLICY.schoolHoursOnly,
        schoolHoursStart:
          (managed.schoolHoursStart as string) ||
          DEFAULT_POLICY.schoolHoursStart,
        schoolHoursEnd:
          (managed.schoolHoursEnd as string) || DEFAULT_POLICY.schoolHoursEnd,
        schoolTimezone:
          (managed.schoolTimezone as string) || DEFAULT_POLICY.schoolTimezone,
        reportingEndpoint:
          (managed.reportingEndpoint as string) ||
          DEFAULT_POLICY.reportingEndpoint,
      };

      return this.policy;
    } catch {
      this.policy = { ...DEFAULT_POLICY };
      return this.policy;
    }
  }

  /**
   * Return the currently loaded policy, or null if not yet loaded.
   */
  getPolicy(): SchoolPolicy | null {
    return this.policy;
  }

  /**
   * Check whether monitoring should be active right now.
   * If schoolHoursOnly is false, monitoring is always active.
   * Otherwise, checks if the current time falls within school hours
   * in the school's timezone.
   */
  isMonitoringActive(now?: Date): boolean {
    if (!this.policy) return true;
    if (!this.policy.schoolHoursOnly) return true;

    const currentTime = now || new Date();

    try {
      // Get the current time in the school's timezone
      const formatter = new Intl.DateTimeFormat("en-US", {
        timeZone: this.policy.schoolTimezone,
        hour: "numeric",
        minute: "numeric",
        hour12: false,
      });

      const parts = formatter.formatToParts(currentTime);
      const hourPart = parts.find((p) => p.type === "hour");
      const minutePart = parts.find((p) => p.type === "minute");

      if (!hourPart || !minutePart) return true;

      const currentHour = parseInt(hourPart.value, 10);
      const currentMinute = parseInt(minutePart.value, 10);
      const currentMinutes = currentHour * 60 + currentMinute;

      const [startH, startM] = this.policy.schoolHoursStart
        .split(":")
        .map(Number);
      const [endH, endM] = this.policy.schoolHoursEnd.split(":").map(Number);

      const startMinutes = startH * 60 + startM;
      const endMinutes = endH * 60 + endM;

      // Also check it's a weekday (Mon-Fri)
      const dayFormatter = new Intl.DateTimeFormat("en-US", {
        timeZone: this.policy.schoolTimezone,
        weekday: "short",
      });
      const dayOfWeek = dayFormatter.format(currentTime);
      const isWeekday = !["Sat", "Sun"].includes(dayOfWeek);

      if (!isWeekday) return false;

      return currentMinutes >= startMinutes && currentMinutes < endMinutes;
    } catch {
      // If timezone handling fails, default to active
      return true;
    }
  }

  /**
   * Check if a given platform should be monitored.
   * If enabledPlatforms is empty, all platforms are monitored.
   */
  shouldMonitorPlatform(platform: string): boolean {
    if (!this.policy) return true;
    if (this.policy.enabledPlatforms.length === 0) return true;
    return this.policy.enabledPlatforms.includes(platform);
  }

  /**
   * Check if a given platform should be blocked.
   * Only blocks when blockUnmonitored is true AND the platform
   * is not in the enabledPlatforms list (and the list is non-empty).
   */
  shouldBlockPlatform(platform: string): boolean {
    if (!this.policy) return false;
    if (!this.policy.blockUnmonitored) return false;
    if (this.policy.enabledPlatforms.length === 0) return false;
    return !this.policy.enabledPlatforms.includes(platform);
  }

  /**
   * Get the current monitoring level.
   */
  getMonitoringLevel(): string {
    return this.policy?.monitoringLevel ?? "standard";
  }

  /**
   * Get the school's custom reporting endpoint, if configured.
   */
  getReportingEndpoint(): string {
    return this.policy?.reportingEndpoint ?? "";
  }

  /**
   * Validate and normalise the monitoring level string.
   */
  private validateMonitoringLevel(
    level: string | undefined,
  ): "standard" | "enhanced" | "maximum" {
    if (level === "enhanced" || level === "maximum") return level;
    return "standard";
  }
}

/** Singleton instance for use across the extension. */
export const policyManager = new SchoolPolicyManager();
