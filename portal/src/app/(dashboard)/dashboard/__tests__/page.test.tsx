import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { DashboardData } from "@/types";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/dashboard",
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

const mockDashboardData: DashboardData = {
  active_members: 3,
  total_members: 5,
  interactions_today: 42,
  interactions_trend: "+12% this week",
  recent_activity: [],
  alert_summary: {
    unread_count: 2,
    critical_count: 1,
    recent: [],
  },
  spend_summary: {
    today_usd: 1.5,
    month_usd: 25.0,
    budget_usd: 100.0,
    budget_used_percentage: 25.0,
    top_provider: "OpenAI",
    top_provider_cost_usd: 20.0,
    top_provider_percentage: 80.0,
    top_member: "Alice",
    top_member_cost_usd: 15.0,
    top_member_percentage: 60.0,
  },
  risk_summary: {
    total_events_today: 5,
    high_severity_count: 1,
    trend: "stable",
  },
  activity_trend: [],
  risk_breakdown: [],
  spend_trend: [],
};

// Mock the auth hook
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      email: "test@example.com",
      display_name: "Test User",
      account_type: "family",
      group_id: "g1",
      role: "owner",
    },
    isLoading: false,
    isAuthenticated: true,
    error: null,
    login: vi.fn(),
    loginWithOAuth: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
  }),
}));

// Mock the dashboard hook
vi.mock("@/hooks/use-dashboard", () => ({
  dashboardKeys: { all: ["dashboard"], summary: () => ["dashboard", "summary"] },
  useDashboardSummary: () => ({
    data: mockDashboardData,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

import DashboardPage from "../page";

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the dashboard heading", () => {
    renderWithProviders(<DashboardPage />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("shows summary cards with data", () => {
    renderWithProviders(<DashboardPage />);
    expect(screen.getByText("Active Members")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("$1.50")).toBeInTheDocument();
  });

  it("shows recent activity and alert sections", () => {
    renderWithProviders(<DashboardPage />);
    expect(screen.getByText("Recent Activity")).toBeInTheDocument();
    expect(screen.getByText("Alert Summary")).toBeInTheDocument();
    expect(screen.getByText("Spend Summary")).toBeInTheDocument();
  });
});
