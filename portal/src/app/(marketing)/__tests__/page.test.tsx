import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// Mock next/link
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/",
}));

// Mock BhapiLogo
vi.mock("@/components/BhapiLogo", () => ({
  BhapiLogo: ({ className }: { className?: string }) => (
    <img src="/logo.png" alt="Bhapi" className={className} />
  ),
}));

// Mock use-social-proof
vi.mock("@/hooks/use-social-proof", () => ({
  useSocialProof: () => ({
    data: { familyCount: 12000, schoolCount: 340, countriesCount: 28 },
    isLoading: false,
    isError: false,
  }),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// ─── Landing Page ────────────────────────────────────────────────────────────

import LandingPage from "../../page";

describe("LandingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders hero headline "Safe AI. Safe Social."', () => {
    render(<LandingPage />, { wrapper: createWrapper() });
    expect(screen.getByText(/Safe AI\./i)).toBeInTheDocument();
    expect(screen.getByText(/Safe Social\./i)).toBeInTheDocument();
  });

  it("renders hero subtitle about monitoring AI interactions", () => {
    render(<LandingPage />, { wrapper: createWrapper() });
    expect(
      screen.getByText(/Monitor your child's AI interactions/i)
    ).toBeInTheDocument();
  });

  it("renders Start Free CTA linking to /register", () => {
    render(<LandingPage />, { wrapper: createWrapper() });
    const startLinks = screen.getAllByRole("link", { name: /Start Free/i });
    expect(startLinks.length).toBeGreaterThanOrEqual(1);
    expect(startLinks[0]).toHaveAttribute("href", "/register");
  });

  it("hero shows only Start Free CTA (no Book a Demo)", () => {
    render(<LandingPage />, { wrapper: createWrapper() });
    expect(
      screen.queryByRole("link", { name: /Book a Demo/i })
    ).not.toBeInTheDocument();
  });

  it("does not render app store badges (hidden until apps published)", () => {
    render(<LandingPage />, { wrapper: createWrapper() });
    expect(
      screen.queryByAltText(/Download on the App Store/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByAltText(/Get it on Google Play/i)
    ).not.toBeInTheDocument();
  });

  it("renders audience tabs: Families, Schools, Partners", () => {
    render(<LandingPage />, { wrapper: createWrapper() });
    expect(screen.getByRole("tab", { name: /Families/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Schools/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Partners/i })).toBeInTheDocument();
  });

  it("shows Families tab content by default", () => {
    render(<LandingPage />, { wrapper: createWrapper() });
    expect(screen.getByText(/AI Usage Monitoring/i)).toBeInTheDocument();
    // Use heading query to find the specific feature card heading (not the footer/subtitle text)
    expect(screen.getByRole("heading", { name: /Safe Social Network/i })).toBeInTheDocument();
  });

  it("switches to Schools tab content when Schools tab is clicked", () => {
    render(<LandingPage />, { wrapper: createWrapper() });
    const schoolsTab = screen.getByRole("tab", { name: /Schools/i });
    fireEvent.click(schoolsTab);
    expect(
      screen.getByText(/District-wide Deployment/i)
    ).toBeInTheDocument();
  });

  it("switches to Partners tab content when Partners tab is clicked", () => {
    render(<LandingPage />, { wrapper: createWrapper() });
    const partnersTab = screen.getByRole("tab", { name: /Partners/i });
    fireEvent.click(partnersTab);
    // Revenue Share should appear as a feature card heading after switching to Partners tab
    expect(screen.getByRole("heading", { name: /Revenue Share/i })).toBeInTheDocument();
  });

  it("renders social proof numbers", () => {
    render(<LandingPage />, { wrapper: createWrapper() });
    // Families protected count
    expect(screen.getByText(/12,000\+/)).toBeInTheDocument();
  });
});

// ─── Families Page ───────────────────────────────────────────────────────────

import FamiliesPage from "../families/page";

describe("FamiliesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the families hero heading", () => {
    render(<FamiliesPage />, { wrapper: createWrapper() });
    expect(
      screen.getByText(/safest way for your family to use AI/i)
    ).toBeInTheDocument();
  });

  it("renders the Free plan card", () => {
    render(<FamiliesPage />, { wrapper: createWrapper() });
    expect(screen.getByText("Free")).toBeInTheDocument();
    expect(screen.getByText("$0")).toBeInTheDocument();
  });

  it("renders the Family plan at $9.99/mo", () => {
    render(<FamiliesPage />, { wrapper: createWrapper() });
    expect(screen.getByText("$9.99")).toBeInTheDocument();
  });

  it("renders the Family+ plan at $19.99/mo", () => {
    render(<FamiliesPage />, { wrapper: createWrapper() });
    expect(screen.getByText("$19.99")).toBeInTheDocument();
  });

  it("renders testimonial cards", () => {
    render(<FamiliesPage />, { wrapper: createWrapper() });
    expect(screen.getByText(/Sarah M\./i)).toBeInTheDocument();
    expect(screen.getByText(/James T\./i)).toBeInTheDocument();
    expect(screen.getByText(/Priya K\./i)).toBeInTheDocument();
  });

  it('renders "Start Your Free Trial" CTA', () => {
    render(<FamiliesPage />, { wrapper: createWrapper() });
    const ctas = screen.getAllByText(/Start Your Free Trial/i);
    expect(ctas.length).toBeGreaterThanOrEqual(1);
  });
});

// ─── Schools Page ────────────────────────────────────────────────────────────

import SchoolsPage from "../schools/page";

describe("SchoolsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the schools hero heading", () => {
    render(<SchoolsPage />, { wrapper: createWrapper() });
    expect(
      screen.getByText(/District-wide AI safety/i)
    ).toBeInTheDocument();
  });

  it("renders COPPA 2026 compliance badge", () => {
    render(<SchoolsPage />, { wrapper: createWrapper() });
    expect(screen.getByText("COPPA 2026")).toBeInTheDocument();
  });

  it("renders GDPR compliance badge", () => {
    render(<SchoolsPage />, { wrapper: createWrapper() });
    expect(screen.getByText("GDPR")).toBeInTheDocument();
  });

  it("renders FERPA compliance badge", () => {
    render(<SchoolsPage />, { wrapper: createWrapper() });
    expect(screen.getByText("FERPA")).toBeInTheDocument();
  });

  it("renders SOC 2 in-progress badge", () => {
    render(<SchoolsPage />, { wrapper: createWrapper() });
    expect(screen.getByText("SOC 2 Type II")).toBeInTheDocument();
  });

  it("renders per-seat pricing tiers", () => {
    render(<SchoolsPage />, { wrapper: createWrapper() });
    expect(screen.getByText(/1 – 499 students/i)).toBeInTheDocument();
    expect(screen.getByText(/500 – 2,499 students/i)).toBeInTheDocument();
    expect(screen.getByText(/2,500\+ students/i)).toBeInTheDocument();
  });

  it("renders Request a Demo CTA", () => {
    render(<SchoolsPage />, { wrapper: createWrapper() });
    const demoLinks = screen.getAllByRole("link", { name: /Request a Demo/i });
    expect(demoLinks.length).toBeGreaterThanOrEqual(1);
  });
});

// ─── Pricing Page ────────────────────────────────────────────────────────────

import PricingPage from "../pricing/page";

describe("PricingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the pricing page heading", () => {
    render(<PricingPage />, { wrapper: createWrapper() });
    expect(
      screen.getByText(/Simple, transparent pricing/i)
    ).toBeInTheDocument();
  });

  it("renders all five tier columns: Free, Family, Family+, School, Enterprise", () => {
    render(<PricingPage />, { wrapper: createWrapper() });
    expect(screen.getByText("Free")).toBeInTheDocument();
    expect(screen.getByText("Family")).toBeInTheDocument();
    expect(screen.getByText("Family+")).toBeInTheDocument();
    expect(screen.getByText("School")).toBeInTheDocument();
    expect(screen.getByText("Enterprise")).toBeInTheDocument();
  });

  it("renders feature matrix rows", () => {
    render(<PricingPage />, { wrapper: createWrapper() });
    expect(
      screen.getByText(/Children \/ Students/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/AI monitoring/i)).toBeInTheDocument();
    expect(screen.getByText(/Safe social network/i)).toBeInTheDocument();
    expect(screen.getByText(/SIS integration/i)).toBeInTheDocument();
  });

  it("renders FAQ accordion with at least one question", () => {
    render(<PricingPage />, { wrapper: createWrapper() });
    expect(
      screen.getByText(/Is there a free trial/i)
    ).toBeInTheDocument();
  });

  it("expands FAQ answer when question is clicked", () => {
    render(<PricingPage />, { wrapper: createWrapper() });
    const question = screen.getByText(/Is there a free trial/i);
    fireEvent.click(question);
    expect(
      screen.getByText(/All paid plans include a 14-day free trial/i)
    ).toBeInTheDocument();
  });
});

// ─── Social Proof Hook ───────────────────────────────────────────────────────

describe("useSocialProof hook module", () => {
  it("exports useSocialProof function", async () => {
    const mod = await import("@/hooks/use-social-proof");
    expect(typeof mod.useSocialProof).toBe("function");
  });
});
