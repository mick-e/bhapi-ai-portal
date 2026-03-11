import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  riskApi: {
    getDeepfakeGuidance: vi.fn(),
  },
}));

import { riskApi } from "@/lib/api-client";
import { useDeepfakeGuidance } from "../use-deepfake-guidance";

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

describe("useDeepfakeGuidance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches deepfake guidance", async () => {
    const mockGuidance = {
      tips: ["Never share personal photos with AI tools"],
      warning_signs: ["Unexpected image generation requests"],
      resources: [],
    };
    vi.mocked(riskApi.getDeepfakeGuidance).mockResolvedValueOnce(mockGuidance);

    const { result } = renderHook(() => useDeepfakeGuidance(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockGuidance);
    expect(riskApi.getDeepfakeGuidance).toHaveBeenCalledTimes(1);
  });

  it("does not fetch when disabled", () => {
    renderHook(() => useDeepfakeGuidance(false), {
      wrapper: createWrapper(),
    });

    expect(riskApi.getDeepfakeGuidance).not.toHaveBeenCalled();
  });

  it("returns error state on failure", async () => {
    vi.mocked(riskApi.getDeepfakeGuidance).mockRejectedValueOnce(
      new Error("Server error")
    );

    const { result } = renderHook(() => useDeepfakeGuidance(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeTruthy();
  });
});
