import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  blockingApi: {
    list: vi.fn(),
    check: vi.fn(),
    create: vi.fn(),
    revoke: vi.fn(),
    pendingApprovals: vi.fn(),
    effectiveness: vi.fn(),
    approveUnblock: vi.fn(),
    denyUnblock: vi.fn(),
  },
}));

import { blockingApi } from "@/lib/api-client";
import {
  useBlockRules,
  useBlockCheck,
  useCreateBlockRule,
  useRevokeBlockRule,
  usePendingApprovals,
  useBlockEffectiveness,
  useApproveUnblock,
  useDenyUnblock,
  blockingKeys,
} from "../use-blocking";

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

describe("useBlockRules", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches block rules for a group", async () => {
    const mockRules = [
      { id: "br1", group_id: "g1", member_id: "m1", platforms: ["chatgpt"], active: true },
    ];
    vi.mocked(blockingApi.list).mockResolvedValueOnce(mockRules);

    const { result } = renderHook(() => useBlockRules("g1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(blockingApi.list).toHaveBeenCalledWith("g1");
  });

  it("does not fetch when groupId is null", () => {
    renderHook(() => useBlockRules(null), {
      wrapper: createWrapper(),
    });

    expect(blockingApi.list).not.toHaveBeenCalled();
  });
});

describe("useBlockCheck", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("checks block status for a member", async () => {
    const mockStatus = { blocked: false, rules: [] };
    vi.mocked(blockingApi.check).mockResolvedValueOnce(mockStatus);

    const { result } = renderHook(() => useBlockCheck("g1", "m1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(blockingApi.check).toHaveBeenCalledWith("g1", "m1");
  });
});

describe("useCreateBlockRule", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates a block rule", async () => {
    const mockRule = { id: "br2", group_id: "g1", member_id: "m1" };
    vi.mocked(blockingApi.create).mockResolvedValueOnce(mockRule);

    const { result } = renderHook(() => useCreateBlockRule(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      group_id: "g1",
      member_id: "m1",
      platforms: ["chatgpt"],
      reason: "Testing",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(blockingApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ group_id: "g1", member_id: "m1" })
    );
  });
});

describe("useRevokeBlockRule", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("revokes a block rule", async () => {
    vi.mocked(blockingApi.revoke).mockResolvedValueOnce({ id: "br1", active: false });

    const { result } = renderHook(() => useRevokeBlockRule(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ ruleId: "br1", groupId: "g1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(blockingApi.revoke).toHaveBeenCalledWith("br1");
  });
});

describe("usePendingApprovals", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches pending approvals", async () => {
    const mockApprovals = [{ id: "a1", status: "pending" }];
    vi.mocked(blockingApi.pendingApprovals).mockResolvedValueOnce(mockApprovals);

    const { result } = renderHook(() => usePendingApprovals("g1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
  });
});

describe("useBlockEffectiveness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches block effectiveness stats", async () => {
    const mockStats = { total_blocks: 5, bypass_attempts: 1 };
    vi.mocked(blockingApi.effectiveness).mockResolvedValueOnce(mockStats);

    const { result } = renderHook(() => useBlockEffectiveness("g1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(blockingApi.effectiveness).toHaveBeenCalledWith("g1");
  });
});

describe("useApproveUnblock", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("approves an unblock request", async () => {
    vi.mocked(blockingApi.approveUnblock).mockResolvedValueOnce({ id: "a1", status: "approved" });

    const { result } = renderHook(() => useApproveUnblock(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ approvalId: "a1", groupId: "g1", decision_note: "OK" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(blockingApi.approveUnblock).toHaveBeenCalledWith("a1", { decision_note: "OK" });
  });
});

describe("useDenyUnblock", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("denies an unblock request", async () => {
    vi.mocked(blockingApi.denyUnblock).mockResolvedValueOnce({ id: "a1", status: "denied" });

    const { result } = renderHook(() => useDenyUnblock(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ approvalId: "a1", groupId: "g1" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(blockingApi.denyUnblock).toHaveBeenCalledWith("a1", { decision_note: undefined });
  });
});

describe("blockingKeys", () => {
  it("produces correct query keys", () => {
    expect(blockingKeys.all).toEqual(["blocking"]);
    expect(blockingKeys.rules("g1")).toEqual(["blocking", "rules", "g1"]);
    expect(blockingKeys.check("g1", "m1")).toEqual(["blocking", "check", "g1", "m1"]);
    expect(blockingKeys.pendingApprovals("g1")).toEqual(["blocking", "pending-approvals", "g1"]);
    expect(blockingKeys.effectiveness("g1")).toEqual(["blocking", "effectiveness", "g1"]);
  });
});
