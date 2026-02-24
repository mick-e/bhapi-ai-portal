import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import type { Alert, PaginatedResponse } from "@/types";

vi.mock("@/lib/api-client", () => ({
  alertsApi: {
    list: vi.fn(),
    markRead: vi.fn(),
    markActioned: vi.fn(),
    markAllRead: vi.fn(),
  },
  riskApi: {
    list: vi.fn(),
    acknowledge: vi.fn(),
  },
}));

import { alertsApi } from "@/lib/api-client";
import { useAlerts, alertKeys, riskKeys } from "../use-alerts";

const mockAlerts: PaginatedResponse<Alert> = {
  items: [
    {
      id: "1",
      group_id: "g1",
      type: "risk",
      severity: "critical",
      title: "Test Alert",
      message: "Test message",
      read: false,
      actioned: false,
      created_at: new Date().toISOString(),
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
}

describe("useAlerts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches alerts", async () => {
    vi.mocked(alertsApi.list).mockResolvedValueOnce(mockAlerts);

    const { result } = renderHook(() => useAlerts(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.items[0].title).toBe("Test Alert");
  });

  it("passes filter params to API", async () => {
    vi.mocked(alertsApi.list).mockResolvedValueOnce(mockAlerts);

    renderHook(
      () => useAlerts({ severity: "critical", page: 2, page_size: 10 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() =>
      expect(alertsApi.list).toHaveBeenCalledWith({
        severity: "critical",
        page: 2,
        page_size: 10,
      })
    );
  });
});

describe("alertKeys", () => {
  it("produces correct query keys", () => {
    expect(alertKeys.all).toEqual(["alerts"]);
    expect(alertKeys.lists()).toEqual(["alerts", "list"]);
    expect(alertKeys.list({ severity: "critical" })).toEqual([
      "alerts",
      "list",
      { severity: "critical" },
    ]);
  });
});

describe("riskKeys", () => {
  it("produces correct query keys", () => {
    expect(riskKeys.all).toEqual(["risk"]);
    expect(riskKeys.lists()).toEqual(["risk", "list"]);
  });
});
