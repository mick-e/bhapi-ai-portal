import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAlertStream } from "../use-alert-stream";

class MockEventSource {
  url: string;
  withCredentials: boolean;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  listeners: Record<string, ((event: { data: string }) => void)[]> = {};
  closed = false;

  constructor(url: string, options?: { withCredentials?: boolean }) {
    this.url = url;
    this.withCredentials = options?.withCredentials ?? false;
    MockEventSource.instances.push(this);
  }

  addEventListener(event: string, handler: (event: { data: string }) => void) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(handler);
  }

  close() {
    this.closed = true;
  }

  // Test helpers
  simulateOpen() {
    this.onopen?.();
  }

  simulateEvent(type: string, data: unknown) {
    const handlers = this.listeners[type] || [];
    handlers.forEach((h) => h({ data: JSON.stringify(data) }));
  }

  simulateError() {
    this.onerror?.();
  }

  static instances: MockEventSource[] = [];
  static reset() {
    MockEventSource.instances = [];
  }
}

describe("useAlertStream", () => {
  beforeEach(() => {
    MockEventSource.reset();
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("connects to the alert stream", () => {
    renderHook(() =>
      useAlertStream({ groupId: "g1" })
    );

    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toContain("/api/v1/alerts/stream?group_id=g1");
  });

  it("reports connected state after open", () => {
    const { result } = renderHook(() =>
      useAlertStream({ groupId: "g1" })
    );

    expect(result.current.connected).toBe(false);

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    expect(result.current.connected).toBe(true);
  });

  it("receives new_alert events", () => {
    const onAlert = vi.fn();
    const { result } = renderHook(() =>
      useAlertStream({ groupId: "g1", onAlert })
    );

    const alertData = {
      id: "a1",
      group_id: "g1",
      severity: "critical",
      title: "Test Alert",
      created_at: "2026-03-11T00:00:00Z",
    };

    act(() => {
      MockEventSource.instances[0].simulateEvent("new_alert", alertData);
    });

    expect(onAlert).toHaveBeenCalledWith(alertData);
    expect(result.current.lastEvent).toEqual(alertData);
  });

  it("does not connect when disabled", () => {
    renderHook(() =>
      useAlertStream({ groupId: "g1", enabled: false })
    );

    expect(MockEventSource.instances).toHaveLength(0);
  });

  it("does not connect when groupId is empty", () => {
    renderHook(() =>
      useAlertStream({ groupId: "" })
    );

    expect(MockEventSource.instances).toHaveLength(0);
  });

  it("closes connection on unmount", () => {
    const { unmount } = renderHook(() =>
      useAlertStream({ groupId: "g1" })
    );

    const es = MockEventSource.instances[0];
    unmount();

    expect(es.closed).toBe(true);
  });
});
