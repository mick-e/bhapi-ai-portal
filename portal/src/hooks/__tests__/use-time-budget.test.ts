import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/lib/api-client";
import {
  useTimeBudget,
  useTimeBudgetHistory,
  useBedtimeMode,
  useUpdateTimeBudget,
  useUpdateBedtime,
  useDeleteBedtime,
  timeBudgetKeys,
} from "../use-time-budget";

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

describe("useTimeBudget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches time budget for a member", async () => {
    const mockBudget = {
      member_id: "m1",
      daily_minutes: 120,
      remaining_minutes: 60,
      enabled: true,
    };
    vi.mocked(api.get).mockResolvedValueOnce(mockBudget);

    const { result } = renderHook(
      () => useTimeBudget("g1", "m1"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockBudget);
    expect(api.get).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/blocking/time-budget/m1")
    );
  });

  it("does not fetch when groupId is null", () => {
    renderHook(() => useTimeBudget(null, "m1"), {
      wrapper: createWrapper(),
    });

    expect(api.get).not.toHaveBeenCalled();
  });

  it("returns error state on failure", async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(
      () => useTimeBudget("g1", "m1"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeTruthy();
  });
});

describe("useTimeBudgetHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches usage history", async () => {
    const mockHistory = [
      { date: "2026-03-10", minutes_used: 90 },
      { date: "2026-03-09", minutes_used: 45 },
    ];
    vi.mocked(api.get).mockResolvedValueOnce(mockHistory);

    const { result } = renderHook(
      () => useTimeBudgetHistory("g1", "m1", 7),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(2);
    expect(api.get).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/blocking/time-budget/m1/history")
    );
  });
});

describe("useBedtimeMode", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches bedtime config", async () => {
    const mockBedtime = {
      member_id: "m1",
      enabled: true,
      start_time: "21:00",
      end_time: "07:00",
    };
    vi.mocked(api.get).mockResolvedValueOnce(mockBedtime);

    const { result } = renderHook(
      () => useBedtimeMode("g1", "m1"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockBedtime);
    expect(api.get).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/blocking/bedtime/m1")
    );
  });
});

describe("useUpdateTimeBudget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("updates time budget via PUT", async () => {
    const mockResult = { member_id: "m1", daily_minutes: 90, enabled: true };
    vi.mocked(api.put).mockResolvedValueOnce(mockResult);

    const { result } = renderHook(() => useUpdateTimeBudget(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      groupId: "g1",
      memberId: "m1",
      data: { weekday_minutes: 90, weekend_minutes: 90 },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.put).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/blocking/time-budget/m1"),
      { weekday_minutes: 90, weekend_minutes: 90 }
    );
  });
});

describe("useUpdateBedtime", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("updates bedtime config via PUT", async () => {
    const mockResult = { member_id: "m1", enabled: true, start_time: "22:00", end_time: "07:00" };
    vi.mocked(api.put).mockResolvedValueOnce(mockResult);

    const { result } = renderHook(() => useUpdateBedtime(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      groupId: "g1",
      memberId: "m1",
      data: { start_hour: 22, end_hour: 7 },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.put).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/blocking/bedtime/m1"),
      { start_hour: 22, end_hour: 7 }
    );
  });
});

describe("useDeleteBedtime", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("deletes bedtime config", async () => {
    vi.mocked(api.delete).mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useDeleteBedtime(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ groupId: "g1", memberId: "m1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.delete).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/blocking/bedtime/m1")
    );
  });
});

describe("timeBudgetKeys", () => {
  it("produces correct query keys", () => {
    expect(timeBudgetKeys.all).toEqual(["time-budget"]);
    expect(timeBudgetKeys.budget("g1", "m1")).toEqual([
      "time-budget", "budget", "g1", "m1",
    ]);
    expect(timeBudgetKeys.history("g1", "m1")).toEqual([
      "time-budget", "history", "g1", "m1",
    ]);
    expect(timeBudgetKeys.bedtime("g1", "m1")).toEqual([
      "time-budget", "bedtime", "g1", "m1",
    ]);
  });
});
