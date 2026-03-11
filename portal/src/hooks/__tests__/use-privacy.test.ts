import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  privacyApi: {
    getVisibility: vi.fn(),
    setVisibility: vi.fn(),
    getSelfView: vi.fn(),
    setSelfView: vi.fn(),
    getChildDashboard: vi.fn(),
  },
}));

vi.mock("@/hooks/use-auth", () => ({
  useAuth: vi.fn(() => ({
    user: { group_id: "g1", id: "u1", email: "test@example.com" },
    isAuthenticated: true,
  })),
}));

import { privacyApi } from "@/lib/api-client";
import {
  useVisibility,
  useSetVisibility,
  useSelfView,
  useSetSelfView,
  useChildDashboard,
  privacyKeys,
} from "../use-privacy";

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

describe("useVisibility", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches visibility settings for a member", async () => {
    const mockVisibility = {
      member_id: "m1",
      activity_visible: true,
      risk_visible: true,
      spend_visible: false,
    };
    vi.mocked(privacyApi.getVisibility).mockResolvedValueOnce(mockVisibility);

    const { result } = renderHook(() => useVisibility("m1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockVisibility);
    expect(privacyApi.getVisibility).toHaveBeenCalledWith("g1", "m1");
  });

  it("does not fetch when memberId is empty", () => {
    renderHook(() => useVisibility(""), {
      wrapper: createWrapper(),
    });

    expect(privacyApi.getVisibility).not.toHaveBeenCalled();
  });

  it("returns error state on failure", async () => {
    vi.mocked(privacyApi.getVisibility).mockRejectedValueOnce(
      new Error("Network error")
    );

    const { result } = renderHook(() => useVisibility("m1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useSetVisibility", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("updates visibility settings", async () => {
    const mockResult = { member_id: "m1", activity_visible: false };
    vi.mocked(privacyApi.setVisibility).mockResolvedValueOnce(mockResult);

    const { result } = renderHook(() => useSetVisibility(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      memberId: "m1",
      data: { activity_visible: false } as never,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(privacyApi.setVisibility).toHaveBeenCalledWith(
      "g1",
      "m1",
      expect.objectContaining({ activity_visible: false })
    );
  });
});

describe("useSelfView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches child self-view config", async () => {
    const mockSelfView = {
      member_id: "m1",
      can_see_activity: true,
      can_see_scores: false,
    };
    vi.mocked(privacyApi.getSelfView).mockResolvedValueOnce(mockSelfView);

    const { result } = renderHook(() => useSelfView("m1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(privacyApi.getSelfView).toHaveBeenCalledWith("g1", "m1");
  });
});

describe("useChildDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches child dashboard data", async () => {
    const mockDashboard = {
      member_id: "m1",
      safety_score: 90,
      recent_activity: [],
    };
    vi.mocked(privacyApi.getChildDashboard).mockResolvedValueOnce(mockDashboard);

    const { result } = renderHook(() => useChildDashboard("m1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(privacyApi.getChildDashboard).toHaveBeenCalledWith("m1");
  });

  it("does not fetch when memberId is empty", () => {
    renderHook(() => useChildDashboard(""), {
      wrapper: createWrapper(),
    });

    expect(privacyApi.getChildDashboard).not.toHaveBeenCalled();
  });
});

describe("privacyKeys", () => {
  it("produces correct query keys", () => {
    expect(privacyKeys.all).toEqual(["privacy"]);
    expect(privacyKeys.visibility("g1", "m1")).toEqual([
      "privacy", "visibility", "g1", "m1",
    ]);
    expect(privacyKeys.selfView("g1", "m1")).toEqual([
      "privacy", "self-view", "g1", "m1",
    ]);
    expect(privacyKeys.childDashboard("m1")).toEqual([
      "privacy", "child-dashboard", "m1",
    ]);
  });
});
