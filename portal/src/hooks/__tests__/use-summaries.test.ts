import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import type { PaginatedResponse } from "@/types";

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn(),
  api: {
    post: vi.fn(),
  },
}));

import { apiFetch, api } from "@/lib/api-client";
import {
  useSummaries,
  useSummary,
  useTriggerSummarization,
  summaryKeys,
} from "../use-summaries";

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

describe("useSummaries", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches conversation summaries for a member", async () => {
    const mockData: PaginatedResponse<{ id: string; summary: string }> = {
      items: [{ id: "s1", summary: "Chat about homework" }],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    };
    vi.mocked(apiFetch).mockResolvedValueOnce(mockData);

    const { result } = renderHook(
      () => useSummaries({ member_id: "m1" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toHaveLength(1);
    expect(apiFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/capture/summaries")
    );
  });

  it("does not fetch when member_id is missing", () => {
    renderHook(() => useSummaries({}), {
      wrapper: createWrapper(),
    });

    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("returns error state on failure", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("Server error"));

    const { result } = renderHook(
      () => useSummaries({ member_id: "m1" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useSummary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches a single summary by ID", async () => {
    const mockSummary = { id: "s1", summary: "Detailed conversation" };
    vi.mocked(apiFetch).mockResolvedValueOnce(mockSummary);

    const { result } = renderHook(() => useSummary("s1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockSummary);
    expect(apiFetch).toHaveBeenCalledWith("/api/v1/capture/summaries/s1");
  });

  it("does not fetch when summaryId is empty", () => {
    renderHook(() => useSummary(""), {
      wrapper: createWrapper(),
    });

    expect(apiFetch).not.toHaveBeenCalled();
  });
});

describe("useTriggerSummarization", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("triggers summarization for an event", async () => {
    const mockResult = { id: "s2", summary: "New summary" };
    vi.mocked(api.post).mockResolvedValueOnce(mockResult);

    const { result } = renderHook(() => useTriggerSummarization(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ event_id: "e1", member_age: 12 });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.post).toHaveBeenCalledWith(
      "/api/v1/capture/summarize",
      { event_id: "e1", member_age: 12 }
    );
  });
});

describe("summaryKeys", () => {
  it("produces correct query keys", () => {
    expect(summaryKeys.all).toEqual(["summaries"]);
    expect(summaryKeys.lists()).toEqual(["summaries", "list"]);
    expect(summaryKeys.detail("s1")).toEqual(["summaries", "detail", "s1"]);
  });
});
