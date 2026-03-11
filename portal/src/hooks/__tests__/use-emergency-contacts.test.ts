import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  emergencyContactsApi: {
    list: vi.fn(),
    add: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
  },
}));

vi.mock("@/hooks/use-auth", () => ({
  useAuth: vi.fn(() => ({
    user: { group_id: "g1", id: "u1", email: "test@example.com" },
    isAuthenticated: true,
  })),
}));

import { emergencyContactsApi } from "@/lib/api-client";
import {
  useEmergencyContacts,
  useAddEmergencyContact,
  useUpdateEmergencyContact,
  useRemoveEmergencyContact,
  emergencyContactKeys,
} from "../use-emergency-contacts";

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

describe("useEmergencyContacts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches emergency contacts for the user's group", async () => {
    const mockContacts = [
      {
        id: "ec1",
        group_id: "g1",
        name: "Jane Doe",
        relationship: "grandmother",
        phone: "+1234567890",
        email: null,
        notify_on: ["panic"],
        consent_given: true,
        consent_given_at: "2026-03-01T00:00:00Z",
        created_at: "2026-03-01T00:00:00Z",
      },
    ];
    vi.mocked(emergencyContactsApi.list).mockResolvedValueOnce(mockContacts);

    const { result } = renderHook(() => useEmergencyContacts(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].name).toBe("Jane Doe");
    expect(emergencyContactsApi.list).toHaveBeenCalledWith("g1");
  });

  it("returns error state on failure", async () => {
    vi.mocked(emergencyContactsApi.list).mockRejectedValueOnce(
      new Error("Network error")
    );

    const { result } = renderHook(() => useEmergencyContacts(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useAddEmergencyContact", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("adds an emergency contact", async () => {
    const mockResult = {
      id: "ec2",
      group_id: "g1",
      name: "John Doe",
      relationship: "uncle",
      phone: "+9876543210",
    };
    vi.mocked(emergencyContactsApi.add).mockResolvedValueOnce(mockResult);

    const { result } = renderHook(() => useAddEmergencyContact(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      name: "John Doe",
      relationship: "uncle",
      phone: "+9876543210",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(emergencyContactsApi.add).toHaveBeenCalledWith(
      "g1",
      expect.objectContaining({ name: "John Doe" })
    );
  });
});

describe("useRemoveEmergencyContact", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("removes an emergency contact", async () => {
    vi.mocked(emergencyContactsApi.remove).mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useRemoveEmergencyContact(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("ec1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(emergencyContactsApi.remove).toHaveBeenCalledWith("g1", "ec1");
  });
});

describe("emergencyContactKeys", () => {
  it("produces correct query keys", () => {
    expect(emergencyContactKeys.all).toEqual(["emergency-contacts"]);
    expect(emergencyContactKeys.list("g1")).toEqual([
      "emergency-contacts", "list", "g1",
    ]);
  });
});
