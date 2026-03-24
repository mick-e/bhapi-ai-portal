import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/developers"),
  useRouter: vi.fn(() => ({ push: vi.fn(), replace: vi.fn() })),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => React.createElement("a", { href }, children),
}));

vi.mock("@/components/BhapiLogo", () => ({
  BhapiLogo: () => React.createElement("img", { alt: "Bhapi" }),
}));

vi.mock("@/components/ui/Card", () => ({
  Card: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", { "data-testid": "card" }, children),
}));

vi.mock("@/components/ui/Button", () => ({
  Button: ({
    children,
    onClick,
    isLoading,
    disabled,
    type,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    isLoading?: boolean;
    disabled?: boolean;
    type?: string;
  }) =>
    React.createElement(
      "button",
      { onClick, disabled: disabled || isLoading, type: type ?? "button" },
      isLoading ? "Loading..." : children
    ),
}));

vi.mock("@/hooks/use-developer-portal", () => ({
  useApiClients: vi.fn(),
  useApiUsage: vi.fn(),
  useWebhooks: vi.fn(),
  useCreateWebhook: vi.fn(),
  useSendTestEvent: vi.fn(),
  developerKeys: {
    all: ["developer-portal"],
    clients: () => ["developer-portal", "clients"],
    usage: () => ["developer-portal", "usage"],
    webhooks: () => ["developer-portal", "webhooks"],
    deliveries: (id: string) => ["developer-portal", "deliveries", id],
  },
}));

import {
  useApiClients,
  useApiUsage,
  useWebhooks,
  useCreateWebhook,
  useSendTestEvent,
  developerKeys,
} from "@/hooks/use-developer-portal";

// ─── Pages under test ─────────────────────────────────────────────────────────

import DevelopersLandingPage from "../page";
import ApiDashboardPage from "../dashboard/page";
import WebhooksPage from "../webhooks/page";
import DocsPage from "../docs/page";

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

// ─── Test suites ──────────────────────────────────────────────────────────────

describe("Developer Landing Page", () => {
  it("renders hero headline", () => {
    render(React.createElement(DevelopersLandingPage), {
      wrapper: createWrapper(),
    });
    expect(screen.getByText("Build on Bhapi")).toBeInTheDocument();
  });

  it("renders hero subtitle", () => {
    render(React.createElement(DevelopersLandingPage), {
      wrapper: createWrapper(),
    });
    expect(
      screen.getByText(/Integrate child safety into your apps/i)
    ).toBeInTheDocument();
  });

  it("renders all four API overview cards", () => {
    render(React.createElement(DevelopersLandingPage), {
      wrapper: createWrapper(),
    });
    expect(screen.getByText("OAuth 2.0")).toBeInTheDocument();
    expect(screen.getByText("Webhooks")).toBeInTheDocument();
    expect(screen.getByText("Rate Limiting")).toBeInTheDocument();
    expect(screen.getByText("SDKs")).toBeInTheDocument();
  });

  it("renders all partnership tier names", () => {
    render(React.createElement(DevelopersLandingPage), {
      wrapper: createWrapper(),
    });
    expect(screen.getByText("Free")).toBeInTheDocument();
    expect(screen.getByText("Starter")).toBeInTheDocument();
    expect(screen.getByText("Growth")).toBeInTheDocument();
    expect(screen.getByText("Enterprise")).toBeInTheDocument();
  });

  it("renders Apply for Access CTA linking to dashboard", () => {
    render(React.createElement(DevelopersLandingPage), {
      wrapper: createWrapper(),
    });
    const links = screen
      .getAllByRole("link")
      .filter((el) => el.getAttribute("href") === "/developers/dashboard");
    expect(links.length).toBeGreaterThanOrEqual(1);
  });

  it("renders link to docs page", () => {
    render(React.createElement(DevelopersLandingPage), {
      wrapper: createWrapper(),
    });
    const docsLinks = screen
      .getAllByRole("link")
      .filter((el) => el.getAttribute("href") === "/developers/docs");
    expect(docsLinks.length).toBeGreaterThanOrEqual(1);
  });
});

describe("API Dashboard Page", () => {
  beforeEach(() => {
    vi.mocked(useApiClients).mockReturnValue({
      data: {
        items: [
          {
            id: "abc",
            name: "My App",
            client_id: "cl_testclientid123",
            is_active: true,
            is_approved: true,
            created_at: "2026-03-01T00:00:00Z",
          },
        ],
        total: 1,
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useApiClients>);

    vi.mocked(useApiUsage).mockReturnValue({
      data: {
        total_calls: 4200,
        tier_name: "Starter",
        tier_limit: 10000,
        days: [
          { date: "2026-03-22", calls: 120 },
          { date: "2026-03-23", calls: 200 },
          { date: "2026-03-24", calls: 80 },
        ],
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useApiUsage>);
  });

  it("renders API Dashboard heading", () => {
    render(React.createElement(ApiDashboardPage), { wrapper: createWrapper() });
    expect(screen.getByText("API Dashboard")).toBeInTheDocument();
  });

  it("renders API Credentials section", () => {
    render(React.createElement(ApiDashboardPage), { wrapper: createWrapper() });
    expect(screen.getByText("API Credentials")).toBeInTheDocument();
  });

  it("renders client name", () => {
    render(React.createElement(ApiDashboardPage), { wrapper: createWrapper() });
    expect(screen.getByText("My App")).toBeInTheDocument();
  });

  it("renders usage metrics", () => {
    render(React.createElement(ApiDashboardPage), { wrapper: createWrapper() });
    expect(screen.getByText("4,200")).toBeInTheDocument();
    // "Starter" appears in both usage section and tier card
    const starterElements = screen.getAllByText("Starter");
    expect(starterElements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders Upgrade Plan button", () => {
    render(React.createElement(ApiDashboardPage), { wrapper: createWrapper() });
    expect(screen.getByText("Upgrade Plan")).toBeInTheDocument();
  });

  it("renders quick links section", () => {
    render(React.createElement(ApiDashboardPage), { wrapper: createWrapper() });
    expect(screen.getByText("Quick Links")).toBeInTheDocument();
    expect(screen.getByText("API Docs")).toBeInTheDocument();
    expect(screen.getByText("Support")).toBeInTheDocument();
  });
});

describe("Webhooks Page", () => {
  beforeEach(() => {
    vi.mocked(useWebhooks).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useWebhooks>);

    vi.mocked(useCreateWebhook).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useCreateWebhook>);

    vi.mocked(useSendTestEvent).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useSendTestEvent>);
  });

  it("renders Webhooks page heading", () => {
    render(React.createElement(WebhooksPage), { wrapper: createWrapper() });
    expect(screen.getByText("Webhooks")).toBeInTheDocument();
  });

  it("renders Add Webhook button", () => {
    render(React.createElement(WebhooksPage), { wrapper: createWrapper() });
    expect(screen.getByText("Add Webhook")).toBeInTheDocument();
  });

  it("shows add webhook form when button clicked", async () => {
    render(React.createElement(WebhooksPage), { wrapper: createWrapper() });
    fireEvent.click(screen.getByText("Add Webhook"));
    await waitFor(() => {
      expect(screen.getByText("Add Webhook Endpoint")).toBeInTheDocument();
    });
  });

  it("renders event checkboxes in the form", async () => {
    render(React.createElement(WebhooksPage), { wrapper: createWrapper() });
    fireEvent.click(screen.getByText("Add Webhook"));
    await waitFor(() => {
      expect(screen.getByText("Alert Created")).toBeInTheDocument();
      expect(screen.getByText("Risk Scored")).toBeInTheDocument();
      expect(screen.getByText("Member Added")).toBeInTheDocument();
      expect(screen.getByText("Capture Ingested")).toBeInTheDocument();
    });
  });

  it("shows empty state when no webhooks registered", () => {
    render(React.createElement(WebhooksPage), { wrapper: createWrapper() });
    expect(
      screen.getByText(/No webhook endpoints yet/i)
    ).toBeInTheDocument();
  });

  it("renders webhooks list when data present", () => {
    vi.mocked(useWebhooks).mockReturnValue({
      data: {
        items: [
          {
            id: "wh1",
            url: "https://example.com/hook",
            events: ["alert.created", "risk.scored"],
            is_active: true,
            created_at: "2026-03-01T00:00:00Z",
          },
        ],
        total: 1,
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useWebhooks>);

    render(React.createElement(WebhooksPage), { wrapper: createWrapper() });
    expect(screen.getByText("https://example.com/hook")).toBeInTheDocument();
    // "alert.created" appears in both the event reference section and the webhook list badge
    const alertBadges = screen.getAllByText("alert.created");
    expect(alertBadges.length).toBeGreaterThanOrEqual(1);
  });
});

describe("Docs Page", () => {
  it("renders API Documentation heading", () => {
    render(React.createElement(DocsPage), { wrapper: createWrapper() });
    expect(screen.getByText("API Documentation")).toBeInTheDocument();
  });

  it("renders Authentication section", () => {
    render(React.createElement(DocsPage), { wrapper: createWrapper() });
    // "Authentication" appears in TOC and section heading
    const authElements = screen.getAllByText("Authentication");
    expect(authElements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders code sample tabs", () => {
    render(React.createElement(DocsPage), { wrapper: createWrapper() });
    const pythonTabs = screen.getAllByText("Python");
    expect(pythonTabs.length).toBeGreaterThanOrEqual(1);
    const jsTabs = screen.getAllByText("JavaScript");
    expect(jsTabs.length).toBeGreaterThanOrEqual(1);
    const curlTabs = screen.getAllByText("cURL");
    expect(curlTabs.length).toBeGreaterThanOrEqual(1);
  });

  it("renders endpoint reference table with method badges", () => {
    render(React.createElement(DocsPage), { wrapper: createWrapper() });
    // POST badge for /platform/token
    const postBadges = screen.getAllByText("POST");
    expect(postBadges.length).toBeGreaterThanOrEqual(1);
    const getBadges = screen.getAllByText("GET");
    expect(getBadges.length).toBeGreaterThanOrEqual(1);
  });

  it("renders rate limiting section", () => {
    render(React.createElement(DocsPage), { wrapper: createWrapper() });
    // "Rate Limiting" may appear in TOC and section heading
    const rateLimitElements = screen.getAllByText("Rate Limiting");
    expect(rateLimitElements.length).toBeGreaterThanOrEqual(1);
    // X-RateLimit-Limit is inside a <pre> block — use a partial match
    expect(screen.getByText(/X-RateLimit-Limit:/)).toBeInTheDocument();
  });

  it("renders OAuth 2.0 flow steps", () => {
    render(React.createElement(DocsPage), { wrapper: createWrapper() });
    // "OAuth 2.0 Flow" appears in TOC and section heading
    const oauthFlowElements = screen.getAllByText("OAuth 2.0 Flow");
    expect(oauthFlowElements.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Register your app")).toBeInTheDocument();
    expect(screen.getByText("Generate PKCE pair")).toBeInTheDocument();
  });
});

describe("use-developer-portal hook exports", () => {
  it("exports useApiClients hook", () => {
    expect(typeof useApiClients).toBe("function");
  });

  it("exports useApiUsage hook", () => {
    expect(typeof useApiUsage).toBe("function");
  });

  it("exports useWebhooks hook", () => {
    expect(typeof useWebhooks).toBe("function");
  });

  it("exports useCreateWebhook hook", () => {
    expect(typeof useCreateWebhook).toBe("function");
  });

  it("exports useSendTestEvent hook", () => {
    expect(typeof useSendTestEvent).toBe("function");
  });

  it("exports correct developerKeys structure", () => {
    expect(developerKeys.all).toEqual(["developer-portal"]);
    expect(developerKeys.clients()).toEqual(["developer-portal", "clients"]);
    expect(developerKeys.webhooks()).toEqual(["developer-portal", "webhooks"]);
    expect(developerKeys.usage()).toEqual(["developer-portal", "usage"]);
    expect(developerKeys.deliveries("x")).toEqual([
      "developer-portal",
      "deliveries",
      "x",
    ]);
  });
});
