import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  analyticsApi: {
    academicReport: vi.fn(),
  },
}));

import { analyticsApi } from "@/lib/api-client";
import { useAcademicReport, academicKeys } from "../use-academic";
import type { AcademicReport } from "@/types";

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

describe("useAcademicReport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches academic report for a member", async () => {
    const mockReport = {
      member_id: "m1",
      total_sessions: 10,
      academic_percentage: 65,
      categories: [],
    };
    vi.mocked(analyticsApi.academicReport).mockResolvedValueOnce(mockReport as unknown as AcademicReport);

    const { result } = renderHook(
      () => useAcademicReport("g1", "m1"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockReport);
    expect(analyticsApi.academicReport).toHaveBeenCalledWith(
      "g1", "m1", undefined, undefined
    );
  });

  it("does not fetch when groupId is null", () => {
    renderHook(() => useAcademicReport(null, "m1"), {
      wrapper: createWrapper(),
    });

    expect(analyticsApi.academicReport).not.toHaveBeenCalled();
  });

  it("does not fetch when memberId is null", () => {
    renderHook(() => useAcademicReport("g1", null), {
      wrapper: createWrapper(),
    });

    expect(analyticsApi.academicReport).not.toHaveBeenCalled();
  });

  it("passes date range parameters", async () => {
    vi.mocked(analyticsApi.academicReport).mockResolvedValueOnce({} as AcademicReport);

    renderHook(
      () => useAcademicReport("g1", "m1", "2026-03-01", "2026-03-10"),
      { wrapper: createWrapper() }
    );

    await waitFor(() =>
      expect(analyticsApi.academicReport).toHaveBeenCalledWith(
        "g1", "m1", "2026-03-01", "2026-03-10"
      )
    );
  });

  it("returns error state on failure", async () => {
    vi.mocked(analyticsApi.academicReport).mockRejectedValueOnce(
      new Error("Server error")
    );

    const { result } = renderHook(
      () => useAcademicReport("g1", "m1"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("academicKeys", () => {
  it("produces correct query keys", () => {
    expect(academicKeys.all).toEqual(["academic"]);
    expect(academicKeys.report("g1", "m1")).toEqual([
      "academic", "report", "g1", "m1", undefined, undefined,
    ]);
    expect(academicKeys.report("g1", "m1", "2026-03-01", "2026-03-10")).toEqual([
      "academic", "report", "g1", "m1", "2026-03-01", "2026-03-10",
    ]);
  });
});
