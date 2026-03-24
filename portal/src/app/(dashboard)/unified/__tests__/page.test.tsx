import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LocaleProvider } from "@/contexts/LocaleContext";
import type {
  RiskScoreSummary,
  AIActivitySummary,
  SocialSummary,
  ScreenTimeSummary,
  LocationSummary,
  ActionCenter,
} from "@/hooks/use-unified-dashboard";
import type { GroupMember } from "@/types";

// ─── Navigation mocks ────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/unified",
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

// ─── Fixture data ─────────────────────────────────────────────────────────────

const mockRiskScore: RiskScoreSummary = {
  score: 45,
  trend: "stable",
  confidence: "high",
  factors: ["Emotional language detected", "Unusual session length", "New platform"],
};

const mockAIActivity: AIActivitySummary = {
  events_today: 12,
  top_platforms: ["ChatGPT", "Claude"],
  recent_events: [],
};

const mockSocial: SocialSummary = {
  posts_today: 3,
  comments_today: 7,
  friend_requests_pending: 2,
};

const mockScreenTime: ScreenTimeSummary = {
  total_minutes_today: 135,
  top_categories: [
    { category: "Social Media", minutes: 60 },
    { category: "AI Tools", minutes: 45 },
    { category: "Gaming", minutes: 30 },
  ],
};

const mockLocation: LocationSummary = {
  last_known_location: "Home",
  geofence_status: "inside",
  last_updated: "2026-03-24T10:00:00Z",
};

const mockActionCenter: ActionCenter = {
  pending_approvals: 2,
  unread_alerts: 5,
  pending_extension_requests: 1,
};

const mockMembers: GroupMember[] = [
  {
    id: "m1",
    group_id: "g1",
    user_id: "u2",
    display_name: "Alice",
    email: "alice@example.com",
    role: "member",
    status: "active",
    joined_at: "2026-01-01T00:00:00Z",
  },
];

// ─── Hook mocks ───────────────────────────────────────────────────────────────

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      email: "parent@example.com",
      display_name: "Parent",
      account_type: "family",
      group_id: "g1",
      role: "owner",
    },
    isLoading: false,
    isAuthenticated: true,
  }),
}));

vi.mock("@/hooks/use-members", () => ({
  useMembers: () => ({
    data: { items: mockMembers, total: 1, page: 1, page_size: 20, total_pages: 1 },
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/hooks/use-unified-dashboard", () => ({
  useUnifiedDashboard: () => ({
    data: {
      childId: "m1",
      riskScore: mockRiskScore,
      aiActivity: mockAIActivity,
      social: mockSocial,
      screenTime: mockScreenTime,
      location: mockLocation,
      actionCenter: mockActionCenter,
    },
    isLoading: false,
    isError: false,
    errors: [],
    refetchAll: vi.fn(),
  }),
  unifiedDashboardKeys: {
    all: ["unified-dashboard"],
    child: (id: string) => ["unified-dashboard", id],
    riskScore: (id: string) => ["unified-dashboard", id, "risk-score"],
    aiActivity: (id: string) => ["unified-dashboard", id, "ai-activity"],
    social: (id: string) => ["unified-dashboard", id, "social"],
    screenTime: (id: string) => ["unified-dashboard", id, "screen-time"],
    location: (id: string) => ["unified-dashboard", id, "location"],
    actionCenter: (id: string) => ["unified-dashboard", id, "action-center"],
  },
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────

import UnifiedDashboardPage, {
  RiskScoreSection,
  AIActivitySection,
  SocialActivitySection,
  ScreenTimeSection,
  LocationSection,
  ActionCenterSection,
} from "../page";

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <LocaleProvider>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </LocaleProvider>
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("UnifiedDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page title", () => {
    renderWithProviders(<UnifiedDashboardPage />);
    expect(screen.getByText("Unified Dashboard")).toBeInTheDocument();
  });

  it("renders the page subtitle", () => {
    renderWithProviders(<UnifiedDashboardPage />);
    expect(
      screen.getByText(/Complete view of your child/i)
    ).toBeInTheDocument();
  });

  it("shows the risk score section heading", () => {
    renderWithProviders(<UnifiedDashboardPage />);
    expect(screen.getByText("Risk Score")).toBeInTheDocument();
  });

  it("shows the AI Activity section heading", () => {
    renderWithProviders(<UnifiedDashboardPage />);
    expect(screen.getByText("AI Activity")).toBeInTheDocument();
  });

  it("shows the Social Activity section heading", () => {
    renderWithProviders(<UnifiedDashboardPage />);
    expect(screen.getByText("Social Activity")).toBeInTheDocument();
  });

  it("shows the Screen Time section heading", () => {
    renderWithProviders(<UnifiedDashboardPage />);
    expect(screen.getByText("Screen Time")).toBeInTheDocument();
  });

  it("shows the Location section heading", () => {
    renderWithProviders(<UnifiedDashboardPage />);
    expect(screen.getByText("Location")).toBeInTheDocument();
  });

  it("shows the Action Center section heading", () => {
    renderWithProviders(<UnifiedDashboardPage />);
    expect(screen.getByText("Action Center")).toBeInTheDocument();
  });

  it("shows the refresh button", () => {
    renderWithProviders(<UnifiedDashboardPage />);
    expect(screen.getByRole("button", { name: /refresh/i })).toBeInTheDocument();
  });

  it("shows child selector with child name", () => {
    renderWithProviders(<UnifiedDashboardPage />);
    expect(screen.getByDisplayValue("Alice")).toBeInTheDocument();
  });
});

describe("RiskScoreSection", () => {
  it("renders score number", () => {
    renderWithProviders(<RiskScoreSection data={mockRiskScore} />);
    expect(screen.getByText("45")).toBeInTheDocument();
  });

  it("renders confidence badge", () => {
    renderWithProviders(<RiskScoreSection data={mockRiskScore} />);
    expect(screen.getByText(/High confidence/i)).toBeInTheDocument();
  });

  it("renders top factors", () => {
    renderWithProviders(<RiskScoreSection data={mockRiskScore} />);
    expect(screen.getByText("Emotional language detected")).toBeInTheDocument();
  });

  it("renders fallback when no data", () => {
    renderWithProviders(<RiskScoreSection data={null} />);
    expect(screen.getByText(/No risk data/i)).toBeInTheDocument();
  });
});

describe("AIActivitySection", () => {
  it("shows event count", () => {
    renderWithProviders(<AIActivitySection data={mockAIActivity} />);
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("shows top platforms", () => {
    renderWithProviders(<AIActivitySection data={mockAIActivity} />);
    expect(screen.getByText("ChatGPT")).toBeInTheDocument();
    expect(screen.getByText("Claude")).toBeInTheDocument();
  });

  it("shows fallback when no data", () => {
    renderWithProviders(<AIActivitySection data={null} />);
    expect(screen.getByText(/No activity data/i)).toBeInTheDocument();
  });
});

describe("SocialActivitySection", () => {
  it("shows post count", () => {
    renderWithProviders(<SocialActivitySection data={mockSocial} />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("shows pending friend requests", () => {
    renderWithProviders(<SocialActivitySection data={mockSocial} />);
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});

describe("ScreenTimeSection", () => {
  it("shows total formatted time", () => {
    // 135 min = 2h 15m
    renderWithProviders(<ScreenTimeSection data={mockScreenTime} />);
    expect(screen.getByText(/2h 15m/i)).toBeInTheDocument();
  });

  it("shows top category", () => {
    renderWithProviders(<ScreenTimeSection data={mockScreenTime} />);
    expect(screen.getByText("Social Media")).toBeInTheDocument();
  });
});

describe("LocationSection", () => {
  it("shows last known location", () => {
    renderWithProviders(<LocationSection data={mockLocation} />);
    expect(screen.getByText("Home")).toBeInTheDocument();
  });

  it("shows inside safe zone badge", () => {
    renderWithProviders(<LocationSection data={mockLocation} />);
    expect(screen.getByText(/Inside safe zone/i)).toBeInTheDocument();
  });
});

describe("ActionCenterSection", () => {
  it("shows pending approvals count", () => {
    renderWithProviders(<ActionCenterSection data={mockActionCenter} />);
    expect(screen.getByText("Pending approvals")).toBeInTheDocument();
  });

  it("shows unread alerts count", () => {
    renderWithProviders(<ActionCenterSection data={mockActionCenter} />);
    expect(screen.getByText("Unread alerts")).toBeInTheDocument();
  });

  it("shows extension requests", () => {
    renderWithProviders(<ActionCenterSection data={mockActionCenter} />);
    expect(screen.getByText("Extension requests")).toBeInTheDocument();
  });
});

describe("Hook exports exist", () => {
  it("useUnifiedDashboard is exported from the hook module", async () => {
    const mod = await import("@/hooks/use-unified-dashboard");
    expect(typeof mod.useUnifiedDashboard).toBe("function");
  });

  it("unifiedDashboardKeys is exported", async () => {
    const mod = await import("@/hooks/use-unified-dashboard");
    expect(mod.unifiedDashboardKeys).toBeDefined();
    expect(Array.isArray(mod.unifiedDashboardKeys.all)).toBe(true);
  });
});
