import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

vi.mock("@/hooks/use-auth", () => ({
  useAuth: vi.fn(() => ({
    user: { group_id: "g1", id: "u1", email: "test@example.com" },
    isAuthenticated: true,
  })),
}));

import { api } from "@/lib/api-client";
import {
  useAgreementTemplates,
  useActiveAgreement,
  useCreateAgreement,
  useSignAgreement,
  useReviewAgreement,
  agreementKeys,
} from "../use-agreement";

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

describe("useAgreementTemplates", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches agreement templates", async () => {
    const mockTemplates = {
      balanced: {
        title: "Balanced Family",
        rules: [{ category: "time", text: "Limit screen time" }],
      },
    };
    vi.mocked(api.get).mockResolvedValueOnce(mockTemplates);

    const { result } = renderHook(() => useAgreementTemplates(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockTemplates);
    expect(api.get).toHaveBeenCalledWith("/api/v1/groups/agreement-templates");
  });

  it("returns error state on failure", async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useAgreementTemplates(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useActiveAgreement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches the active agreement for the user's group", async () => {
    const mockAgreement = {
      id: "a1",
      group_id: "g1",
      template_id: "balanced",
      rules: [],
      signatures: [],
    };
    vi.mocked(api.get).mockResolvedValueOnce(mockAgreement);

    const { result } = renderHook(() => useActiveAgreement(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockAgreement);
    expect(api.get).toHaveBeenCalledWith("/api/v1/groups/g1/agreement");
  });
});

describe("useCreateAgreement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates an agreement from a template", async () => {
    const mockResult = { id: "a1", group_id: "g1", template_id: "balanced" };
    vi.mocked(api.post).mockResolvedValueOnce(mockResult);

    const { result } = renderHook(() => useCreateAgreement(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ template_id: "balanced" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.post).toHaveBeenCalledWith(
      "/api/v1/groups/g1/agreement",
      { template_id: "balanced" }
    );
  });
});

describe("useSignAgreement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("signs the agreement", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ id: "a1" });

    const { result } = renderHook(() => useSignAgreement(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ member_id: "m1", name: "Alice" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.post).toHaveBeenCalledWith(
      "/api/v1/groups/g1/agreement/sign",
      { member_id: "m1", name: "Alice" }
    );
  });
});

describe("useReviewAgreement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("marks agreement for review", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ id: "a1" });

    const { result } = renderHook(() => useReviewAgreement(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.post).toHaveBeenCalledWith("/api/v1/groups/g1/agreement/review");
  });
});

describe("agreementKeys", () => {
  it("produces correct query keys", () => {
    expect(agreementKeys.all).toEqual(["agreement"]);
    expect(agreementKeys.templates()).toEqual(["agreement", "templates"]);
    expect(agreementKeys.active("g1")).toEqual(["agreement", "active", "g1"]);
  });
});
