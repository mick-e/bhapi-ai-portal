import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  familyReportApi: {
    getWeekly: vi.fn(),
    send: vi.fn(),
  },
}));

import { familyReportApi } from "@/lib/api-client";
import {
  useFamilyWeeklyReport,
  useSendFamilyReport,
  familyReportKeys,
} from "../use-family-report";

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

describe("useFamilyWeeklyReport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches the weekly family report", async () => {
    const mockReport = {
      group_id: "g1",
      group_name: "Smith Family",
      generated_at: "2026-03-11T00:00:00Z",
      period_start: "2026-03-04",
      period_end: "2026-03-10",
      family_safety_score: 85,
      member_count: 3,
      members: [],
      highlights: { safest_member: null, most_improved: null },
      action_items: { unresolved_alerts: 2 },
    };
    vi.mocked(familyReportApi.getWeekly).mockResolvedValueOnce(mockReport);

    const { result } = renderHook(() => useFamilyWeeklyReport(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.family_safety_score).toBe(85);
    expect(familyReportApi.getWeekly).toHaveBeenCalledTimes(1);
  });

  it("returns error state on failure", async () => {
    vi.mocked(familyReportApi.getWeekly).mockRejectedValueOnce(
      new Error("Server error")
    );

    const { result } = renderHook(() => useFamilyWeeklyReport(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useSendFamilyReport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends the weekly report", async () => {
    vi.mocked(familyReportApi.send).mockResolvedValueOnce({ sent: true });

    const { result } = renderHook(() => useSendFamilyReport(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(familyReportApi.send).toHaveBeenCalledTimes(1);
  });
});

describe("familyReportKeys", () => {
  it("produces correct query keys", () => {
    expect(familyReportKeys.all).toEqual(["family-report"]);
    expect(familyReportKeys.weekly()).toEqual(["family-report", "weekly"]);
  });
});
