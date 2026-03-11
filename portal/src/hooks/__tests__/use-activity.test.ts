import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import type { PaginatedResponse } from "@/types";

vi.mock("@/lib/api-client", () => ({
  activityApi: {
    list: vi.fn(),
    get: vi.fn(),
  },
}));

import { activityApi } from "@/lib/api-client";
import {
  useActivity,
  useActivityEvent,
  activityKeys,
} from "../use-activity";

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

const mockEvents: PaginatedResponse<{
  id: string;
  platform: string;
  event_type: string;
}> = {
  items: [
    { id: "e1", platform: "chatgpt", event_type: "message" },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

describe("useActivity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches activity events", async () => {
    vi.mocked(activityApi.list).mockResolvedValueOnce(mockEvents);

    const { result } = renderHook(() => useActivity(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toHaveLength(1);
    expect(activityApi.list).toHaveBeenCalledWith(undefined);
  });

  it("passes filter params to API", async () => {
    vi.mocked(activityApi.list).mockResolvedValueOnce(mockEvents);

    const params = { member_id: "m1", provider: "chatgpt", page: 2 };
    renderHook(() => useActivity(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(activityApi.list).toHaveBeenCalledWith(params)
    );
  });

  it("returns error state on failure", async () => {
    vi.mocked(activityApi.list).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useActivity(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useActivityEvent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches a single event by ID", async () => {
    const mockEvent = { id: "e1", platform: "chatgpt", content: "Hello" };
    vi.mocked(activityApi.get).mockResolvedValueOnce(mockEvent);

    const { result } = renderHook(() => useActivityEvent("e1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockEvent);
    expect(activityApi.get).toHaveBeenCalledWith("e1");
  });

  it("does not fetch when eventId is empty", () => {
    renderHook(() => useActivityEvent(""), {
      wrapper: createWrapper(),
    });

    expect(activityApi.get).not.toHaveBeenCalled();
  });
});

describe("activityKeys", () => {
  it("produces correct query keys", () => {
    expect(activityKeys.all).toEqual(["activity"]);
    expect(activityKeys.lists()).toEqual(["activity", "list"]);
    expect(activityKeys.detail("e1")).toEqual(["activity", "detail", "e1"]);
  });
});
