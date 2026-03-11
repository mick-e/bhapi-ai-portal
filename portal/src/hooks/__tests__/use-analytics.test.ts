import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  analyticsApi: {
    trends: vi.fn(),
    usagePatterns: vi.fn(),
    memberBaselines: vi.fn(),
    anomalies: vi.fn(),
    peerComparison: vi.fn(),
  },
}));

import { analyticsApi } from "@/lib/api-client";
import {
  useTrends,
  useUsagePatterns,
  useMemberBaselines,
  useAnomalies,
  usePeerComparison,
  analyticsKeys,
} from "../use-analytics";

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

describe("useTrends", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches trend data for a group", async () => {
    const mockTrends = { dates: ["2026-03-10"], counts: [5] };
    vi.mocked(analyticsApi.trends).mockResolvedValueOnce(mockTrends);

    const { result } = renderHook(() => useTrends("g1", 7), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockTrends);
    expect(analyticsApi.trends).toHaveBeenCalledWith("g1", 7);
  });

  it("does not fetch when groupId is null", () => {
    renderHook(() => useTrends(null), {
      wrapper: createWrapper(),
    });

    expect(analyticsApi.trends).not.toHaveBeenCalled();
  });

  it("returns error state on failure", async () => {
    vi.mocked(analyticsApi.trends).mockRejectedValueOnce(new Error("Error"));

    const { result } = renderHook(() => useTrends("g1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useUsagePatterns", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches usage patterns", async () => {
    const mockPatterns = { peak_hours: [14, 15, 16], platforms: {} };
    vi.mocked(analyticsApi.usagePatterns).mockResolvedValueOnce(mockPatterns);

    const { result } = renderHook(() => useUsagePatterns("g1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(analyticsApi.usagePatterns).toHaveBeenCalledWith("g1", 7);
  });
});

describe("useMemberBaselines", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches member baselines", async () => {
    const mockBaselines = [
      { member_id: "m1", avg_daily_events: 5, std_deviation: 2 },
    ];
    vi.mocked(analyticsApi.memberBaselines).mockResolvedValueOnce(mockBaselines);

    const { result } = renderHook(() => useMemberBaselines("g1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(analyticsApi.memberBaselines).toHaveBeenCalledWith("g1", 30);
  });
});

describe("useAnomalies", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches anomalies", async () => {
    const mockAnomalies = { anomalies: [], total: 0 };
    vi.mocked(analyticsApi.anomalies).mockResolvedValueOnce(mockAnomalies);

    const { result } = renderHook(() => useAnomalies("g1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(analyticsApi.anomalies).toHaveBeenCalledWith("g1");
  });
});

describe("usePeerComparison", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches peer comparison data", async () => {
    const mockComparison = { group_percentile: 75, peer_avg: 50 };
    vi.mocked(analyticsApi.peerComparison).mockResolvedValueOnce(mockComparison);

    const { result } = renderHook(() => usePeerComparison("g1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(analyticsApi.peerComparison).toHaveBeenCalledWith("g1", 30);
  });
});

describe("analyticsKeys", () => {
  it("produces correct query keys", () => {
    expect(analyticsKeys.all).toEqual(["analytics"]);
    expect(analyticsKeys.trends("g1", 7)).toEqual(["analytics", "trends", "g1", 7]);
    expect(analyticsKeys.usage("g1", 7)).toEqual(["analytics", "usage", "g1", 7]);
    expect(analyticsKeys.baselines("g1", 30)).toEqual(["analytics", "baselines", "g1", 30]);
    expect(analyticsKeys.anomalies("g1")).toEqual(["analytics", "anomalies", "g1"]);
    expect(analyticsKeys.peerComparison("g1", 30)).toEqual([
      "analytics", "peer-comparison", "g1", 30,
    ]);
  });
});
