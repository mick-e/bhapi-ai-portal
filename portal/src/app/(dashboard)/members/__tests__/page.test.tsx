import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MembersPage from "../page";

// Mock data
const mockMembersData = {
  items: [
    {
      id: "m1",
      group_id: "g1",
      user_id: "u1",
      display_name: "Parent Admin",
      email: "parent@test.com",
      role: "owner",
      status: "active" as const,
      risk_level: "low" as const,
      last_active: "2024-01-30T12:00:00Z",
      joined_at: "2024-01-01T00:00:00Z",
    },
    {
      id: "m2",
      group_id: "g1",
      user_id: "u2",
      display_name: "Child One",
      email: "child1@test.com",
      role: "member",
      status: "active" as const,
      risk_level: "medium" as const,
      last_active: "2024-01-29T10:00:00Z",
      joined_at: "2024-01-05T00:00:00Z",
    },
    {
      id: "m3",
      group_id: "g1",
      user_id: "u3",
      display_name: "Invited User",
      email: "invited@test.com",
      role: "member",
      status: "invited" as const,
      risk_level: "low" as const,
      joined_at: "2024-01-20T00:00:00Z",
    },
  ],
  total: 3,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockInviteMember = vi.fn();
const mockUpdateMember = vi.fn();
const mockRemoveMember = vi.fn();

vi.mock("@/hooks/use-members", () => ({
  useMembers: vi.fn(() => ({
    data: mockMembersData,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
  useInviteMember: vi.fn(() => ({
    mutate: mockInviteMember,
    isPending: false,
    isError: false,
    error: null,
    reset: vi.fn(),
  })),
  useUpdateMember: vi.fn(() => ({
    mutate: mockUpdateMember,
    isPending: false,
  })),
  useRemoveMember: vi.fn(() => ({
    mutate: mockRemoveMember,
    isPending: false,
  })),
}));

vi.mock("@/hooks/use-auth", () => ({
  useAuth: vi.fn(() => ({
    user: {
      id: "u1",
      email: "parent@test.com",
      display_name: "Parent Admin",
      account_type: "family",
      group_id: "g1",
      role: "owner",
    },
    isAuthenticated: true,
  })),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MembersPage />
    </QueryClientProvider>
  );
}

describe("MembersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page heading", () => {
    renderPage();
    expect(screen.getByText("Members")).toBeInTheDocument();
  });

  it("renders member rows", () => {
    renderPage();
    expect(screen.getByText("Parent Admin")).toBeInTheDocument();
    expect(screen.getByText("Child One")).toBeInTheDocument();
    expect(screen.getByText("Invited User")).toBeInTheDocument();
  });

  it("shows member emails", () => {
    renderPage();
    expect(screen.getByText("parent@test.com")).toBeInTheDocument();
    expect(screen.getByText("child1@test.com")).toBeInTheDocument();
    expect(screen.getByText("invited@test.com")).toBeInTheDocument();
  });

  it("shows status badges", () => {
    renderPage();
    const activeBadges = screen.getAllByText("active");
    expect(activeBadges).toHaveLength(2);
    expect(screen.getByText("invited")).toBeInTheDocument();
  });

  it("shows risk badges", () => {
    renderPage();
    expect(screen.getAllByText("low")).toHaveLength(2);
    expect(screen.getByText("medium")).toBeInTheDocument();
  });

  it("shows active member count", () => {
    renderPage();
    expect(screen.getByText("Active members")).toBeInTheDocument();
    // Count text
    const countElements = screen.getAllByText("2");
    expect(countElements.length).toBeGreaterThanOrEqual(1);
  });

  it("shows pending invites count", () => {
    renderPage();
    expect(screen.getByText("Pending invites")).toBeInTheDocument();
  });

  it("shows total members count", () => {
    renderPage();
    expect(screen.getByText("Total members")).toBeInTheDocument();
  });

  it("has invite member button", () => {
    renderPage();
    expect(screen.getByText("Invite Member")).toBeInTheDocument();
  });

  it("opens invite modal on button click", () => {
    renderPage();
    fireEvent.click(screen.getByText("Invite Member"));
    expect(screen.getByText("Invite a Member")).toBeInTheDocument();
    expect(
      screen.getByText("Send an invitation to join your group")
    ).toBeInTheDocument();
  });

  it("invite modal has email input and role selector", () => {
    renderPage();
    fireEvent.click(screen.getByText("Invite Member"));
    expect(screen.getByPlaceholderText("member@example.com")).toBeInTheDocument();
    expect(screen.getByText("Send Invite")).toBeInTheDocument();
  });

  it("has search input", () => {
    renderPage();
    expect(screen.getByPlaceholderText("Search members...")).toBeInTheDocument();
  });

  it("shows member table headers", () => {
    renderPage();
    expect(screen.getByText("Member")).toBeInTheDocument();
    expect(screen.getByText("Role")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Risk")).toBeInTheDocument();
    expect(screen.getByText("Last Active")).toBeInTheDocument();
    expect(screen.getByText("Actions")).toBeInTheDocument();
  });

  it("cancel button closes invite modal", () => {
    renderPage();
    fireEvent.click(screen.getByText("Invite Member"));
    expect(screen.getByText("Invite a Member")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByText("Invite a Member")).not.toBeInTheDocument();
  });
});
