import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Alert, PaginatedResponse } from "@/types";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/alerts",
}));

// Mock next/link
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

const mockAlerts: Alert[] = [
  {
    id: "alert-1",
    group_id: "group-1",
    type: "risk",
    severity: "critical",
    title: "Self-harm content detected",
    message: "Detected self-harm related content on ChatGPT",
    member_name: "Alice",
    read: false,
    actioned: false,
    related_member_id: "member-1",
    related_event_id: "event-1",
    created_at: new Date().toISOString(),
  },
  {
    id: "alert-2",
    group_id: "group-1",
    type: "risk",
    severity: "warning",
    title: "PII shared",
    message: "Email address shared with AI platform",
    member_name: "Bob",
    read: true,
    actioned: false,
    related_member_id: "member-2",
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "alert-3",
    group_id: "group-1",
    type: "spend",
    severity: "info",
    title: "Budget threshold reached",
    message: "Monthly spend reached 80% of budget",
    read: true,
    actioned: true,
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
];

const mockAlertsResponse: PaginatedResponse<Alert> = {
  items: mockAlerts,
  total: 3,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockMutate = vi.fn();

vi.mock("@/hooks/use-alerts", () => ({
  alertKeys: {
    all: ["alerts"],
    lists: () => ["alerts", "list"],
    list: (p?: unknown) => ["alerts", "list", p],
  },
  riskKeys: {
    all: ["risk"],
    lists: () => ["risk", "list"],
    list: (p?: unknown) => ["risk", "list", p],
  },
  useAlerts: () => ({
    data: mockAlertsResponse,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
  useMarkAlertActioned: () => ({
    mutate: mockMutate,
    isPending: false,
    variables: null,
  }),
  useMarkAllAlertsRead: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

import AlertsPage from "../page";

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("AlertsPage", () => {
  it("renders the alerts heading", () => {
    renderWithProviders(<AlertsPage />);
    expect(screen.getByText("Alerts")).toBeInTheDocument();
  });

  it("shows unread count when there are unread alerts", () => {
    renderWithProviders(<AlertsPage />);
    expect(screen.getByText(/1 unread alert/)).toBeInTheDocument();
  });

  it("renders all alert cards", () => {
    renderWithProviders(<AlertsPage />);
    expect(
      screen.getByText("Self-harm content detected")
    ).toBeInTheDocument();
    expect(screen.getByText("PII shared")).toBeInTheDocument();
    expect(
      screen.getByText("Budget threshold reached")
    ).toBeInTheDocument();
  });

  it("shows severity badges", () => {
    renderWithProviders(<AlertsPage />);
    expect(screen.getByText("critical")).toBeInTheDocument();
    expect(screen.getByText("warning")).toBeInTheDocument();
    expect(screen.getByText("info")).toBeInTheDocument();
  });

  it("shows member names on alerts", () => {
    renderWithProviders(<AlertsPage />);
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
    expect(screen.getByText(/Bob/)).toBeInTheDocument();
  });

  it("shows acknowledge button for unactioned alerts", () => {
    renderWithProviders(<AlertsPage />);
    const ackButtons = screen.getAllByText("Acknowledge");
    // alert-1 and alert-2 are unactioned
    expect(ackButtons).toHaveLength(2);
  });

  it("shows acknowledged status for actioned alerts", () => {
    renderWithProviders(<AlertsPage />);
    expect(screen.getByText("Acknowledged")).toBeInTheDocument();
  });

  it("has severity and type filter dropdowns", () => {
    renderWithProviders(<AlertsPage />);
    expect(screen.getByText("All severities")).toBeInTheDocument();
    expect(screen.getByText("All types")).toBeInTheDocument();
  });

  it("shows mark all read button when unread alerts exist", () => {
    renderWithProviders(<AlertsPage />);
    expect(screen.getByText("Mark all read")).toBeInTheDocument();
  });
});
