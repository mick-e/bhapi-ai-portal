import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type {
  SchoolDevice,
  DeploymentStatus,
  SchoolPolicy,
  PaginatedDevices,
} from "@/hooks/use-school-admin";

// ─── Mocks ──────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/school-admin",
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const mockAddToast = vi.fn();
vi.mock("@/contexts/ToastContext", () => ({
  useToast: () => ({
    addToast: mockAddToast,
    removeToast: vi.fn(),
    toasts: [],
  }),
}));

// ─── Test Data ──────────────────────────────────────────────────────────────

const mockDevices: SchoolDevice[] = [
  {
    id: "dev-1",
    device_id: "CHROMEBOOK-001",
    device_name: "Lab Computer 01",
    os: "chromeos",
    status: "active",
    last_sync: "2026-03-20T10:00:00Z",
    assigned_to: "Room 101",
    extension_version: "2.1.0",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "dev-2",
    device_id: "LAPTOP-002",
    device_name: "Teacher Laptop",
    os: "windows",
    status: "inactive",
    last_sync: null,
    assigned_to: null,
    extension_version: null,
    created_at: "2026-02-01T00:00:00Z",
  },
  {
    id: "dev-3",
    device_id: "TABLET-003",
    device_name: "Student iPad",
    os: "ipados",
    status: "pending",
    last_sync: null,
    assigned_to: "Alice",
    extension_version: null,
    created_at: "2026-03-01T00:00:00Z",
  },
  {
    id: "dev-4",
    device_id: "PHONE-004",
    device_name: "Admin Phone",
    os: "android",
    status: "error",
    last_sync: "2026-03-19T08:00:00Z",
    assigned_to: "IT Admin",
    extension_version: "2.0.5",
    created_at: "2026-03-10T00:00:00Z",
  },
];

const mockDevicesResponse: PaginatedDevices = {
  items: mockDevices,
  total: 4,
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
    description: "Block all AI tools during exam periods",
    policy_type: "acceptable_use",
    enforcement_level: "block",
    active: true,
    created_at: "2026-01-15T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: "pol-2",
    name: "Data Privacy Policy",
    description: "Restrict data sharing with AI platforms",
    policy_type: "data_handling",
    enforcement_level: "warn",
    active: true,
    created_at: "2026-02-01T00:00:00Z",
    updated_at: "2026-02-15T00:00:00Z",
  },
  {
    id: "pol-3",
    name: "Cost Monitoring",
    description: "Track and alert on API costs",
    policy_type: "cost_control",
    enforcement_level: "audit",
    active: false,
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
];

// ─── Hook Mocks ─────────────────────────────────────────────────────────────

const mockMutate = vi.fn();

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      email: "admin@school.com",
      display_name: "School Admin",
      account_type: "school",
      group_id: "school-1",
      role: "owner",
    },
    isLoading: false,
    isAuthenticated: true,
  }),
}));

let mockDevicesQueryOverride: Partial<ReturnType<typeof import("@/hooks/use-school-admin").useSchoolDevices>> = {};
let mockDeploymentQueryOverride: Partial<ReturnType<typeof import("@/hooks/use-school-admin").useDeploymentStatus>> = {};
let mockPoliciesQueryOverride: Partial<ReturnType<typeof import("@/hooks/use-school-admin").useSchoolPolicies>> = {};

vi.mock("@/hooks/use-school-admin", () => ({
  useSchoolDevices: () => ({
    data: mockDevicesResponse,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...mockDevicesQueryOverride,
  }),
  useDeploymentStatus: () => ({
    data: mockDeployment,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...mockDeploymentQueryOverride,
  }),
  useSchoolPolicies: () => ({
    data: mockPolicies,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...mockPoliciesQueryOverride,
  }),
  useAddDevice: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
  usePushPolicy: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
  schoolAdminKeys: {
    all: ["school-admin"],
    devices: (id: string) => ["school-admin", "devices", id],
    deployment: (id: string) => ["school-admin", "deployment", id],
    policies: (id: string) => ["school-admin", "policies", id],
  },
}));

import SchoolAdminPage from "../page";

// ─── Helpers ────────────────────────────────────────────────────────────────

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("SchoolAdminPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDevicesQueryOverride = {};
    mockDeploymentQueryOverride = {};
    mockPoliciesQueryOverride = {};
  });

  // ── Page Rendering ──────────────────────────────────────────────────────

  it("renders the page heading", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByText("School IT Admin")).toBeInTheDocument();
  });

  it("renders the page description", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(
      screen.getByText("Manage devices, monitor deployment, and configure policies")
    ).toBeInTheDocument();
  });

  it("renders tab buttons", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByRole("tab", { name: /Devices/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Deployment/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Policies/i })).toBeInTheDocument();
  });

  it("defaults to devices tab", () => {
    renderWithProviders(<SchoolAdminPage />);
    const devicesTab = screen.getByRole("tab", { name: /Devices/i });
    expect(devicesTab).toHaveAttribute("aria-selected", "true");
  });

  // ── Device Table ────────────────────────────────────────────────────────

  it("renders device table with mock data", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByText("Lab Computer 01")).toBeInTheDocument();
    expect(screen.getByText("Teacher Laptop")).toBeInTheDocument();
    expect(screen.getByText("Student iPad")).toBeInTheDocument();
    expect(screen.getByText("Admin Phone")).toBeInTheDocument();
  });

  it("shows device IDs in table", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByText("CHROMEBOOK-001")).toBeInTheDocument();
    expect(screen.getByText("LAPTOP-002")).toBeInTheDocument();
  });

  it("shows device status badges", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByText("active")).toBeInTheDocument();
    expect(screen.getByText("inactive")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("error")).toBeInTheDocument();
  });

  it("shows assigned to or Unassigned", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByText("Room 101")).toBeInTheDocument();
    expect(screen.getAllByText("Unassigned").length).toBeGreaterThanOrEqual(1);
  });

  it("shows last sync date or Never", () => {
    renderWithProviders(<SchoolAdminPage />);
    const neverCells = screen.getAllByText("Never");
    expect(neverCells.length).toBeGreaterThanOrEqual(1);
  });

  it("renders table headers", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByText("Device")).toBeInTheDocument();
    expect(screen.getByText("OS")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Last Sync")).toBeInTheDocument();
    expect(screen.getByText("Assigned To")).toBeInTheDocument();
  });

  // ── Device Filters ──────────────────────────────────────────────────────

  it("has a search input for devices", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByPlaceholderText("Search devices...")).toBeInTheDocument();
  });

  it("has a status filter dropdown", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByLabelText("Filter by status")).toBeInTheDocument();
  });

  it("filters devices by search text", () => {
    renderWithProviders(<SchoolAdminPage />);
    const searchInput = screen.getByPlaceholderText("Search devices...");
    fireEvent.change(searchInput, { target: { value: "Lab" } });
    expect(screen.getByText("Lab Computer 01")).toBeInTheDocument();
    expect(screen.queryByText("Teacher Laptop")).not.toBeInTheDocument();
  });

  it("filters devices by status", () => {
    renderWithProviders(<SchoolAdminPage />);
    const statusSelect = screen.getByLabelText("Filter by status");
    fireEvent.change(statusSelect, { target: { value: "active" } });
    expect(screen.getByText("Lab Computer 01")).toBeInTheDocument();
    expect(screen.queryByText("Teacher Laptop")).not.toBeInTheDocument();
  });

  it("shows empty message when no devices match filter", () => {
    renderWithProviders(<SchoolAdminPage />);
    const searchInput = screen.getByPlaceholderText("Search devices...");
    fireEvent.change(searchInput, { target: { value: "nonexistent-xyz" } });
    expect(screen.getByText("No devices match your filters")).toBeInTheDocument();
  });

  // ── Device Actions ──────────────────────────────────────────────────────

  it("has an Add Device button", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByText("Add Device")).toBeInTheDocument();
  });

  it("has an Export CSV button", () => {
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByText("Export CSV")).toBeInTheDocument();
  });

  it("opens Add Device modal on button click", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByText("Add Device"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Register a new device for your school")).toBeInTheDocument();
  });

  it("shows device form fields in Add Device modal", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByText("Add Device"));
    expect(screen.getByLabelText("Device name")).toBeInTheDocument();
    expect(screen.getByLabelText("Operating system")).toBeInTheDocument();
    expect(screen.getByLabelText("Assigned to (optional)")).toBeInTheDocument();
  });

  it("closes Add Device modal on Cancel", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByText("Add Device"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  // ── Loading States ────────────────────────────────────────────────────

  it("shows loading spinner for devices", () => {
    mockDevicesQueryOverride = { isLoading: true, data: undefined };
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByText("Loading devices...")).toBeInTheDocument();
  });

  it("shows error state for devices", () => {
    mockDevicesQueryOverride = { isError: true, isLoading: false, data: undefined };
    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByText("Failed to load devices")).toBeInTheDocument();
  });

  // ── Deployment Tab ──────────────────────────────────────────────────────

  it("switches to deployment tab", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Deployment/i }));
    expect(screen.getByText("Total Devices")).toBeInTheDocument();
  });

  it("shows deployment status cards", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Deployment/i }));
    // Labels and numbers may appear in both cards and summary rows
    expect(screen.getByText("Total Devices")).toBeInTheDocument();
    expect(screen.getAllByText("Active").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pending").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Errors").length).toBeGreaterThan(0);
  });

  it("shows extension coverage progress bar", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Deployment/i }));
    expect(screen.getByText("Extension Coverage")).toBeInTheDocument();
    expect(screen.getByText("70%")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows deployment breakdown", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Deployment/i }));
    expect(screen.getByText("Deployment Breakdown")).toBeInTheDocument();
  });

  it("shows loading state for deployment", () => {
    mockDeploymentQueryOverride = { isLoading: true, data: undefined };
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Deployment/i }));
    expect(screen.getByText("Loading deployment status...")).toBeInTheDocument();
  });

  it("shows error state for deployment", () => {
    mockDeploymentQueryOverride = { isError: true, isLoading: false, data: undefined };
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Deployment/i }));
    expect(screen.getByText("Failed to load deployment status")).toBeInTheDocument();
  });

  // ── Policies Tab ────────────────────────────────────────────────────────

  it("switches to policies tab", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Policies/i }));
    expect(screen.getByText("No AI During Exams")).toBeInTheDocument();
  });

  it("renders all policy cards", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Policies/i }));
    expect(screen.getByText("No AI During Exams")).toBeInTheDocument();
    expect(screen.getByText("Data Privacy Policy")).toBeInTheDocument();
    expect(screen.getByText("Cost Monitoring")).toBeInTheDocument();
  });

  it("shows policy enforcement badges", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Policies/i }));
    expect(screen.getByText("block")).toBeInTheDocument();
    expect(screen.getByText("warn")).toBeInTheDocument();
    expect(screen.getByText("audit")).toBeInTheDocument();
  });

  it("shows policy active/inactive status", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Policies/i }));
    const activeBadges = screen.getAllByText("Active");
    const inactiveBadge = screen.getByText("Inactive");
    expect(activeBadges.length).toBe(2);
    expect(inactiveBadge).toBeInTheDocument();
  });

  it("shows Create Policy button in policies tab", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Policies/i }));
    expect(screen.getByText("Create Policy")).toBeInTheDocument();
  });

  it("opens Create Policy modal on button click", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Policies/i }));
    fireEvent.click(screen.getByText("Create Policy"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Define a new AI usage policy for your school")).toBeInTheDocument();
  });

  it("shows policy form fields in Create Policy modal", () => {
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Policies/i }));
    fireEvent.click(screen.getByText("Create Policy"));
    expect(screen.getByLabelText("Policy name")).toBeInTheDocument();
    expect(screen.getByLabelText("Description")).toBeInTheDocument();
    expect(screen.getByLabelText("Policy type")).toBeInTheDocument();
    expect(screen.getByLabelText("Enforcement level")).toBeInTheDocument();
  });

  it("shows loading state for policies", () => {
    mockPoliciesQueryOverride = { isLoading: true, data: undefined };
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Policies/i }));
    expect(screen.getByText("Loading policies...")).toBeInTheDocument();
  });

  it("shows empty state when no policies", () => {
    mockPoliciesQueryOverride = { data: [], isLoading: false };
    renderWithProviders(<SchoolAdminPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Policies/i }));
    expect(
      screen.getByText("No policies created yet. Create your first AI usage policy to get started.")
    ).toBeInTheDocument();
  });

  // ── Empty Device State ────────────────────────────────────────────────

  it("shows empty state when no devices", () => {
    mockDevicesQueryOverride = {
      data: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 },
      isLoading: false,
    };
    renderWithProviders(<SchoolAdminPage />);
    expect(
      screen.getByText("No devices registered yet. Add your first device to get started.")
    ).toBeInTheDocument();
  });
});

// ─── No Group Tests ─────────────────────────────────────────────────────────

describe("SchoolAdminPage - no group", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDevicesQueryOverride = {};
    mockDeploymentQueryOverride = {};
    mockPoliciesQueryOverride = {};
  });

  it("shows no school group message when user has no group_id", async () => {
    // We need to re-mock useAuth to return null group_id
    const useAuthMock = await import("@/hooks/use-auth");
    vi.spyOn(useAuthMock, "useAuth").mockReturnValue({
      user: {
        id: "u1",
        email: "test@school.com",
        display_name: "Test",
        account_type: "school",
        group_id: null,
        role: "owner",
      },
      isLoading: false,
      isAuthenticated: true,
    } as ReturnType<typeof useAuthMock.useAuth>);

    renderWithProviders(<SchoolAdminPage />);
    expect(screen.getByText("No school group found")).toBeInTheDocument();
  });
});
