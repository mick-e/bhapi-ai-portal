import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from "@/lib/api-client";
import {
  useSchoolDevices,
  useDeploymentStatus,
  useSchoolPolicies,
  useAddDevice,
  usePushPolicy,
  useUpdatePolicy,
  useDeletePolicy,
  schoolAdminKeys,
  type PaginatedDevices,
  type DeploymentStatus,
  type SchoolPolicy,
  type SchoolDevice,
} from "../use-school-admin";

const mockDevicesResponse: PaginatedDevices = {
  items: [
    {
      id: "dev-1",
      device_id: "CB-001",
      device_name: "Lab PC 01",
      os: "chromeos",
      status: "active",
      last_sync: "2026-03-20T10:00:00Z",
      assigned_to: "Room 101",
      extension_version: "2.1.0",
      created_at: "2026-01-01T00:00:00Z",
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockDeployment: DeploymentStatus = {
  total_devices: 50,
  active_devices: 35,
  pending_devices: 8,
  inactive_devices: 5,
  error_devices: 2,
  last_updated: "2026-03-20T12:00:00Z",
  extension_coverage_percent: 70,
};

const mockPolicies: SchoolPolicy[] = [
  {
    id: "pol-1",
    name: "No AI During Exams",
    description: "Block all AI tools",
    policy_type: "acceptable_use",
    enforcement_level: "block",
    active: true,
    created_at: "2026-01-15T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
];

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

describe("schoolAdminKeys", () => {
  it("produces correct query keys", () => {
    expect(schoolAdminKeys.all).toEqual(["school-admin"]);
    expect(schoolAdminKeys.devices("s1")).toEqual([
      "school-admin",
      "devices",
      "s1",
      undefined,
    ]);
    expect(schoolAdminKeys.devices("s1", { status: "active" })).toEqual([
      "school-admin",
      "devices",
      "s1",
      { status: "active" },
    ]);
    expect(schoolAdminKeys.deployment("s1")).toEqual([
      "school-admin",
      "deployment",
      "s1",
    ]);
    expect(schoolAdminKeys.policies("s1")).toEqual([
      "school-admin",
      "policies",
      "s1",
    ]);
  });
});

describe("useSchoolDevices", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches devices for a school", async () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockDevicesResponse);

    const { result } = renderHook(() => useSchoolDevices("school-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.items[0].device_name).toBe("Lab PC 01");
  });

  it("does not fetch when schoolId is null", () => {
    const { result } = renderHook(() => useSchoolDevices(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(api.get).not.toHaveBeenCalled();
  });

  it("passes filter params in URL", async () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockDevicesResponse);

    renderHook(
      () =>
        useSchoolDevices("school-1", { status: "active", search: "lab" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(api.get).toHaveBeenCalled());
    const url = vi.mocked(api.get).mock.calls[0][0];
    expect(url).toContain("status=active");
    expect(url).toContain("search=lab");
  });
});

describe("useDeploymentStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches deployment status", async () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockDeployment);

    const { result } = renderHook(() => useDeploymentStatus("school-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.total_devices).toBe(50);
    expect(result.current.data?.extension_coverage_percent).toBe(70);
  });

  it("does not fetch when schoolId is null", () => {
    const { result } = renderHook(() => useDeploymentStatus(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useSchoolPolicies", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches school policies", async () => {
    vi.mocked(api.get).mockResolvedValueOnce(mockPolicies);

    const { result } = renderHook(() => useSchoolPolicies("school-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].name).toBe("No AI During Exams");
  });

  it("does not fetch when schoolId is null", () => {
    const { result } = renderHook(() => useSchoolPolicies(null), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
  });
});

describe("useAddDevice", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls post with correct URL and data", async () => {
    const newDevice: SchoolDevice = {
      id: "dev-new",
      device_id: "AUTO-001",
      device_name: "New Device",
      os: "windows",
      status: "pending",
      last_sync: null,
      assigned_to: null,
      extension_version: null,
      created_at: new Date().toISOString(),
    };
    vi.mocked(api.post).mockResolvedValueOnce(newDevice);

    const { result } = renderHook(() => useAddDevice("school-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ device_name: "New Device", os: "windows" });

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(vi.mocked(api.post).mock.calls[0][0]).toContain(
      "/api/v1/integrations/google-admin/schools/school-1/devices"
    );
  });
});

describe("usePushPolicy", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls post with correct URL and data", async () => {
    const newPolicy: SchoolPolicy = {
      id: "pol-new",
      name: "Test Policy",
      description: "Test",
      policy_type: "acceptable_use",
      enforcement_level: "warn",
      active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    vi.mocked(api.post).mockResolvedValueOnce(newPolicy);

    const { result } = renderHook(() => usePushPolicy("school-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      name: "Test Policy",
      description: "Test",
      policy_type: "acceptable_use",
      enforcement_level: "warn",
    });

    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(vi.mocked(api.post).mock.calls[0][0]).toContain(
      "/api/v1/integrations/google-admin/schools/school-1/policy"
    );
  });
});

describe("useUpdatePolicy", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls patch with correct URL", async () => {
    vi.mocked(api.patch).mockResolvedValueOnce(mockPolicies[0]);

    const { result } = renderHook(() => useUpdatePolicy("school-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      policyId: "pol-1",
      data: { active: false },
    });

    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    expect(vi.mocked(api.patch).mock.calls[0][0]).toBe(
      "/api/v1/governance/policies/pol-1"
    );
  });
});

describe("useDeletePolicy", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls delete with correct URL", async () => {
    vi.mocked(api.delete).mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useDeletePolicy("school-1"), {
      wrapper: createWrapper(),
    });

    result.current.mutate("pol-1");

    await waitFor(() => expect(api.delete).toHaveBeenCalled());
    expect(vi.mocked(api.delete).mock.calls[0][0]).toBe(
      "/api/v1/governance/policies/pol-1"
    );
  });
});
