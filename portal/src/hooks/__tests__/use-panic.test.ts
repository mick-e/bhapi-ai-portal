import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import type { PaginatedResponse } from "@/types";

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from "@/lib/api-client";
import {
  usePanicReports,
  useCreatePanicReport,
  useRespondToPanic,
  useQuickResponses,
  panicKeys,
} from "../use-panic";

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

const mockPanicReports: PaginatedResponse<{
  id: string;
  group_id: string;
  member_id: string;
  message: string;
  status: string;
}> = {
  items: [
    {
      id: "p1",
      group_id: "g1",
      member_id: "m1",
      message: "I need help",
      status: "pending",
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

describe("usePanicReports", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches panic reports for a group", async () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockPanicReports);

    const { result } = renderHook(
      () => usePanicReports("g1"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toHaveLength(1);
    expect(api.get).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/alerts/panic")
    );
  });

  it("does not fetch when groupId is null", () => {
    renderHook(() => usePanicReports(null), {
      wrapper: createWrapper(),
    });

    expect(api.get).not.toHaveBeenCalled();
  });

  it("returns error state on failure", async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(
      () => usePanicReports("g1"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useCreatePanicReport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates a panic report", async () => {
    const mockResult = { id: "p2", group_id: "g1", member_id: "m1", message: "Help!", status: "pending" };
    vi.mocked(api.post).mockResolvedValueOnce(mockResult);

    const { result } = renderHook(() => useCreatePanicReport(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ group_id: "g1", member_id: "m1", message: "Help!" } as never);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.post).toHaveBeenCalledWith(
      "/api/v1/alerts/panic",
      expect.objectContaining({ message: "Help!" })
    );
  });
});

describe("useRespondToPanic", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("responds to a panic report", async () => {
    const mockResult = { id: "p1", status: "responded" };
    vi.mocked(api.post).mockResolvedValueOnce(mockResult);

    const { result } = renderHook(() => useRespondToPanic(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ reportId: "p1", response: "On my way", groupId: "g1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.post).toHaveBeenCalledWith(
      "/api/v1/alerts/panic/p1/respond",
      { response: "On my way" }
    );
  });
});

describe("useQuickResponses", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches quick responses", async () => {
    const mockResponses = { responses: ["I'm on my way", "Call me"] };
    vi.mocked(api.get).mockResolvedValueOnce(mockResponses);

    const { result } = renderHook(() => useQuickResponses(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.responses).toHaveLength(2);
  });
});

describe("panicKeys", () => {
  it("produces correct query keys", () => {
    expect(panicKeys.all).toEqual(["panic"]);
    expect(panicKeys.list("g1")).toEqual(["panic", "list", "g1"]);
    expect(panicKeys.quickResponses).toEqual(["panic", "quick-responses"]);
  });
});
