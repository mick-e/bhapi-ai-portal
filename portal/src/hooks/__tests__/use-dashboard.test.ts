import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// Mock the api-client
vi.mock("@/lib/api-client", () => ({
  dashboardApi: {
    getSummary: vi.fn(),
  },
}));

import { dashboardApi } from "@/lib/api-client";
import { useDashboardSummary, dashboardKeys } from "../use-dashboard";
import type { DashboardData } from "@/types";

const mockData: DashboardData = {
  active_members: 2,
  total_members: 4,
  interactions_today: 10,
  interactions_trend: "tracking",
  recent_activity: [],
  alert_summary: { unread_count: 0, critical_count: 0, recent: [] },
  spend_summary: {
    today_usd: 0,
    month_usd: 0,
    budget_usd: 0,
    budget_used_percentage: 0,
    top_provider: "",
    top_provider_cost_usd: 0,
    top_provider_percentage: 0,
    top_member: "",
    top_member_cost_usd: 0,
    top_member_percentage: 0,
  },
  risk_summary: {
    total_events_today: 0,
    high_severity_count: 0,
    trend: "stable",
  },
  activity_trend: [],
  risk_breakdown: [],
  spend_trend: [],
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

describe("useDashboardSummary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches dashboard data", async () => {
    vi.mocked(dashboardApi.getSummary).mockResolvedValueOnce(mockData);

    const { result } = renderHook(() => useDashboardSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(dashboardApi.getSummary).toHaveBeenCalledTimes(1);
  });

  it("returns error state on failure", async () => {
    vi.mocked(dashboardApi.getSummary).mockRejectedValueOnce(
      new Error("Network error")
    );

    const { result } = renderHook(() => useDashboardSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeTruthy();
  });
});

describe("dashboardKeys", () => {
  it("produces correct query keys", () => {
    expect(dashboardKeys.all).toEqual(["dashboard"]);
    expect(dashboardKeys.summary()).toEqual(["dashboard", "summary"]);
  });
});
