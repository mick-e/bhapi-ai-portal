/**
 * Tests for SchoolPolicyManager — Chrome managed storage policy enforcement.
 * Mocks chrome.storage.managed and Intl APIs.
 */

import { SchoolPolicyManager, DEFAULT_POLICY, SchoolPolicy } from "../src/school-policy";

// ---------------------------------------------------------------------------
// Chrome API mock setup
// ---------------------------------------------------------------------------

function setupChromeMock(managedData: Record<string, unknown> | null = null) {
  const chromeObj = {
    storage: {
      managed: {
        get: jest.fn((_keys: unknown, callback: (items: Record<string, unknown>) => void) => {
          if (managedData === null) {
            // Simulate no managed policy
            (chromeObj.runtime as any).lastError = { message: "No managed storage" };
            callback({});
          } else {
            (chromeObj.runtime as any).lastError = null;
            callback(managedData);
          }
        }),
      },
    },
    runtime: {
      lastError: null as { message: string } | null,
    },
  };

  (globalThis as any).chrome = chromeObj;
  return chromeObj;
}

function clearChromeMock() {
  delete (globalThis as any).chrome;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SchoolPolicyManager", () => {
  let manager: SchoolPolicyManager;

  beforeEach(() => {
    manager = new SchoolPolicyManager();
  });

  afterEach(() => {
    clearChromeMock();
  });

  // 1
  test("loadPolicy reads from managed storage", async () => {
    setupChromeMock({
      monitoringLevel: "enhanced",
      schoolId: "school-123",
      schoolName: "Test Academy",
      enabledPlatforms: ["chatgpt", "claude"],
      blockUnmonitored: true,
      schoolHoursOnly: true,
      schoolHoursStart: "09:00",
      schoolHoursEnd: "14:30",
      schoolTimezone: "America/Chicago",
      reportingEndpoint: "https://school.bhapi.ai/api",
    });

    const policy = await manager.loadPolicy();

    expect(policy).not.toBeNull();
    expect(policy!.monitoringLevel).toBe("enhanced");
    expect(policy!.schoolId).toBe("school-123");
    expect(policy!.schoolName).toBe("Test Academy");
    expect(policy!.enabledPlatforms).toEqual(["chatgpt", "claude"]);
    expect(policy!.blockUnmonitored).toBe(true);
    expect(policy!.schoolHoursOnly).toBe(true);
    expect(policy!.schoolHoursStart).toBe("09:00");
    expect(policy!.schoolHoursEnd).toBe("14:30");
    expect(policy!.schoolTimezone).toBe("America/Chicago");
    expect(policy!.reportingEndpoint).toBe("https://school.bhapi.ai/api");
  });

  // 2
  test("loadPolicy returns default policy when managed storage not configured", async () => {
    setupChromeMock(null); // No managed policy

    const policy = await manager.loadPolicy();

    expect(policy).toEqual(DEFAULT_POLICY);
  });

  // 3
  test("loadPolicy returns default policy when managed storage is empty", async () => {
    setupChromeMock({});

    const policy = await manager.loadPolicy();

    expect(policy).toEqual(DEFAULT_POLICY);
  });

  // 4
  test("loadPolicy returns default policy when chrome API unavailable", async () => {
    // Do not set up chrome mock — simulates non-Chrome browser
    clearChromeMock();

    const policy = await manager.loadPolicy();

    expect(policy).toEqual(DEFAULT_POLICY);
  });

  // 5
  test("getPolicy returns null before loadPolicy is called", () => {
    expect(manager.getPolicy()).toBeNull();
  });

  // 6
  test("getPolicy returns loaded policy after loadPolicy", async () => {
    setupChromeMock({ monitoringLevel: "maximum", schoolId: "s1" });
    await manager.loadPolicy();

    const policy = manager.getPolicy();
    expect(policy).not.toBeNull();
    expect(policy!.monitoringLevel).toBe("maximum");
  });

  // 7
  test("isMonitoringActive returns true when schoolHoursOnly is false", async () => {
    setupChromeMock({
      schoolHoursOnly: false,
    });
    await manager.loadPolicy();

    // Should be active regardless of time
    expect(manager.isMonitoringActive(new Date("2026-03-20T23:00:00"))).toBe(true);
    expect(manager.isMonitoringActive(new Date("2026-03-20T03:00:00"))).toBe(true);
  });

  // 8
  test("isMonitoringActive checks school hours when schoolHoursOnly is true", async () => {
    setupChromeMock({
      schoolHoursOnly: true,
      schoolHoursStart: "08:00",
      schoolHoursEnd: "15:00",
      schoolTimezone: "UTC",
    });
    await manager.loadPolicy();

    // During school hours on a weekday (Wednesday)
    const duringHours = new Date("2026-03-18T10:00:00Z"); // Wednesday
    expect(manager.isMonitoringActive(duringHours)).toBe(true);

    // Before school hours on a weekday
    const beforeHours = new Date("2026-03-18T06:00:00Z"); // Wednesday 6am
    expect(manager.isMonitoringActive(beforeHours)).toBe(false);

    // After school hours on a weekday
    const afterHours = new Date("2026-03-18T16:00:00Z"); // Wednesday 4pm
    expect(manager.isMonitoringActive(afterHours)).toBe(false);
  });

  // 9
  test("isMonitoringActive returns false on weekends when schoolHoursOnly", async () => {
    setupChromeMock({
      schoolHoursOnly: true,
      schoolHoursStart: "08:00",
      schoolHoursEnd: "15:00",
      schoolTimezone: "UTC",
    });
    await manager.loadPolicy();

    // Saturday at 10am — within hours but weekend
    const saturday = new Date("2026-03-21T10:00:00Z"); // Saturday
    expect(manager.isMonitoringActive(saturday)).toBe(false);

    // Sunday at 10am
    const sunday = new Date("2026-03-22T10:00:00Z"); // Sunday
    expect(manager.isMonitoringActive(sunday)).toBe(false);
  });

  // 10
  test("shouldMonitorPlatform returns true when enabledPlatforms is empty", async () => {
    setupChromeMock({ enabledPlatforms: [] });
    await manager.loadPolicy();

    expect(manager.shouldMonitorPlatform("chatgpt")).toBe(true);
    expect(manager.shouldMonitorPlatform("claude")).toBe(true);
    expect(manager.shouldMonitorPlatform("unknown-platform")).toBe(true);
  });

  // 11
  test("shouldMonitorPlatform checks enabledPlatforms list", async () => {
    setupChromeMock({
      enabledPlatforms: ["chatgpt", "claude", "gemini"],
    });
    await manager.loadPolicy();

    expect(manager.shouldMonitorPlatform("chatgpt")).toBe(true);
    expect(manager.shouldMonitorPlatform("claude")).toBe(true);
    expect(manager.shouldMonitorPlatform("grok")).toBe(false);
    expect(manager.shouldMonitorPlatform("characterai")).toBe(false);
  });

  // 12
  test("shouldBlockPlatform returns false when blockUnmonitored is false", async () => {
    setupChromeMock({
      blockUnmonitored: false,
      enabledPlatforms: ["chatgpt"],
    });
    await manager.loadPolicy();

    expect(manager.shouldBlockPlatform("grok")).toBe(false);
    expect(manager.shouldBlockPlatform("claude")).toBe(false);
  });

  // 13
  test("shouldBlockPlatform blocks platforms not in enabledPlatforms", async () => {
    setupChromeMock({
      blockUnmonitored: true,
      enabledPlatforms: ["chatgpt", "claude"],
    });
    await manager.loadPolicy();

    expect(manager.shouldBlockPlatform("chatgpt")).toBe(false); // In list — don't block
    expect(manager.shouldBlockPlatform("claude")).toBe(false);   // In list — don't block
    expect(manager.shouldBlockPlatform("grok")).toBe(true);      // Not in list — block
    expect(manager.shouldBlockPlatform("characterai")).toBe(true);
  });

  // 14
  test("shouldBlockPlatform returns false when enabledPlatforms is empty", async () => {
    setupChromeMock({
      blockUnmonitored: true,
      enabledPlatforms: [],
    });
    await manager.loadPolicy();

    // Empty list means "monitor all" — nothing to block
    expect(manager.shouldBlockPlatform("chatgpt")).toBe(false);
    expect(manager.shouldBlockPlatform("unknown")).toBe(false);
  });

  // 15
  test("getMonitoringLevel returns correct level", async () => {
    setupChromeMock({ monitoringLevel: "maximum" });
    await manager.loadPolicy();
    expect(manager.getMonitoringLevel()).toBe("maximum");
  });

  // 16
  test("getMonitoringLevel defaults to standard for invalid values", async () => {
    setupChromeMock({ monitoringLevel: "invalid-level" });
    await manager.loadPolicy();
    expect(manager.getMonitoringLevel()).toBe("standard");
  });

  // 17
  test("getMonitoringLevel returns standard when no policy loaded", () => {
    expect(manager.getMonitoringLevel()).toBe("standard");
  });

  // 18
  test("isMonitoringActive returns true when no policy loaded", () => {
    expect(manager.isMonitoringActive()).toBe(true);
  });

  // 19
  test("shouldMonitorPlatform returns true when no policy loaded", () => {
    expect(manager.shouldMonitorPlatform("chatgpt")).toBe(true);
  });

  // 20
  test("shouldBlockPlatform returns false when no policy loaded", () => {
    expect(manager.shouldBlockPlatform("chatgpt")).toBe(false);
  });

  // 21
  test("loadPolicy handles partial managed data with defaults", async () => {
    setupChromeMock({
      schoolId: "partial-school",
      // Everything else should fall back to defaults
    });
    await manager.loadPolicy();

    const policy = manager.getPolicy()!;
    expect(policy.schoolId).toBe("partial-school");
    expect(policy.monitoringLevel).toBe("standard");
    expect(policy.schoolHoursOnly).toBe(false);
    expect(policy.blockUnmonitored).toBe(false);
    expect(policy.enabledPlatforms).toEqual([]);
    expect(policy.schoolTimezone).toBe("America/New_York");
  });

  // 22
  test("getReportingEndpoint returns configured endpoint", async () => {
    setupChromeMock({ reportingEndpoint: "https://custom.api.com" });
    await manager.loadPolicy();
    expect(manager.getReportingEndpoint()).toBe("https://custom.api.com");
  });

  // 23
  test("getReportingEndpoint returns empty string when not configured", async () => {
    setupChromeMock({});
    await manager.loadPolicy();
    expect(manager.getReportingEndpoint()).toBe("");
  });
});
