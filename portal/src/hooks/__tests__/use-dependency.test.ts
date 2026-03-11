import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from "@/lib/api-client";
import {
  useDependencyScore,
  useDependencyHistory,
  dependencyKeys,
} from "../use-dependency";

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

describe("useDependencyScore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches dependency score for a member", async () => {
    const mockScore = {
      member_id: "m1",
      score: 42,
      level: "moderate",
      factors: [],
    };
    vi.mocked(apiFetch).mockResolvedValueOnce(mockScore);

    const { result } = renderHook(
      () => useDependencyScore("m1", 30),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockScore);
    expect(apiFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/risk/dependency-score")
    );
  });

  it("does not fetch when memberId is empty", () => {
    renderHook(() => useDependencyScore(""), {
      wrapper: createWrapper(),
    });

    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("returns error state on failure", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(
      () => useDependencyScore("m1"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeTruthy();
  });
});

describe("useDependencyHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches dependency history", async () => {
    const mockHistory = {
      member_id: "m1",
      entries: [{ date: "2026-03-10", score: 40 }],
    };
    vi.mocked(apiFetch).mockResolvedValueOnce(mockHistory);

    const { result } = renderHook(
      () => useDependencyHistory("m1", 90),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockHistory);
    expect(apiFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/risk/dependency-score/history")
    );
  });
});

describe("dependencyKeys", () => {
  it("produces correct query keys", () => {
    expect(dependencyKeys.all).toEqual(["dependency"]);
    expect(dependencyKeys.score("m1", 30)).toEqual([
      "dependency", "score", "m1", 30,
    ]);
    expect(dependencyKeys.history("m1", 90)).toEqual([
      "dependency", "history", "m1", 90,
    ]);
  });
});
