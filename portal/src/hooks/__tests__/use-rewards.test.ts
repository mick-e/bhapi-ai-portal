import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  rewardsApi: {
    list: vi.fn(),
    checkTriggers: vi.fn(),
  },
  deviceApi: {
    getSessionSummary: vi.fn(),
  },
}));

vi.mock("@/hooks/use-auth", () => ({
  useAuth: vi.fn(() => ({
    user: { group_id: "g1", id: "u1", email: "test@example.com" },
    isAuthenticated: true,
  })),
}));

import { rewardsApi, deviceApi } from "@/lib/api-client";
import {
  useRewards,
  useCheckRewards,
  useDeviceSummary,
  rewardKeys,
  deviceKeys,
} from "../use-rewards";

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

describe("useRewards", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches rewards for a member", async () => {
    const mockRewards = [
      { id: "r1", title: "Safety Star", badge_type: "star", earned_at: "2026-03-10T00:00:00Z" },
    ];
    vi.mocked(rewardsApi.list).mockResolvedValueOnce(mockRewards);

    const { result } = renderHook(() => useRewards("m1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(rewardsApi.list).toHaveBeenCalledWith("g1", "m1");
  });

  it("does not fetch when memberId is empty", () => {
    renderHook(() => useRewards(""), {
      wrapper: createWrapper(),
    });

    expect(rewardsApi.list).not.toHaveBeenCalled();
  });

  it("returns error state on failure", async () => {
    vi.mocked(rewardsApi.list).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useRewards("m1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useCheckRewards", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("triggers reward check for a member", async () => {
    const mockResult = [{ id: "r2", title: "New Badge" }];
    vi.mocked(rewardsApi.checkTriggers).mockResolvedValueOnce(mockResult);

    const { result } = renderHook(() => useCheckRewards(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("m1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(rewardsApi.checkTriggers).toHaveBeenCalledWith("g1", "m1");
  });
});

describe("useDeviceSummary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches device session summary", async () => {
    const mockSummary = {
      member_id: "m1",
      total_sessions: 5,
      total_minutes: 120,
      devices: [],
    };
    vi.mocked(deviceApi.getSessionSummary).mockResolvedValueOnce(mockSummary);

    const { result } = renderHook(() => useDeviceSummary("m1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockSummary);
    expect(deviceApi.getSessionSummary).toHaveBeenCalledWith("m1", undefined);
  });

  it("passes date parameter", async () => {
    vi.mocked(deviceApi.getSessionSummary).mockResolvedValueOnce({});

    renderHook(() => useDeviceSummary("m1", "2026-03-10"), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(deviceApi.getSessionSummary).toHaveBeenCalledWith("m1", "2026-03-10")
    );
  });
});

describe("rewardKeys", () => {
  it("produces correct query keys", () => {
    expect(rewardKeys.all).toEqual(["rewards"]);
    expect(rewardKeys.list("g1", "m1")).toEqual(["rewards", "list", "g1", "m1"]);
  });
});

describe("deviceKeys", () => {
  it("produces correct query keys", () => {
    expect(deviceKeys.all).toEqual(["devices"]);
    expect(deviceKeys.summary("m1", "2026-03-10")).toEqual([
      "devices", "summary", "m1", "2026-03-10",
    ]);
  });
});
