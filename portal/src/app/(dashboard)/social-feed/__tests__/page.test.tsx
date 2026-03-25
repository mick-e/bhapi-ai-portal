import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SocialFeedPage from "../page";

// ─── Mock data ────────────────────────────────────────────────────────────────

const mockChildren = {
  items: [
    {
      id: "child-1",
      group_id: "g1",
      user_id: "u2",
      display_name: "Emma",
      email: "emma@test.com",
      role: "member",
      status: "active" as const,
      joined_at: "2024-01-01T00:00:00Z",
    },
    {
      id: "child-2",
      group_id: "g1",
      user_id: "u3",
      display_name: "Liam",
      email: "liam@test.com",
      role: "member",
      status: "active" as const,
      joined_at: "2024-01-05T00:00:00Z",
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockFeed = {
  items: [
    {
      id: "post-1",
      author_id: "child-1",
      author_name: "Emma",
      content: "Had a great day at school today!",
      media_count: 0,
      has_image: false,
      has_video: false,
      moderation_status: "approved" as const,
      like_count: 5,
      comment_count: 2,
      created_at: "2024-01-30T10:00:00Z",
    },
    {
      id: "post-2",
      author_id: "child-1",
      author_name: "Emma",
      content: "Check out this cool artwork I made",
      media_count: 1,
      has_image: true,
      has_video: false,
      moderation_status: "pending" as const,
      like_count: 12,
      comment_count: 4,
      created_at: "2024-01-29T15:00:00Z",
    },
    {
      id: "post-3",
      author_id: "child-1",
      author_name: "Emma",
      content: "This post was removed",
      media_count: 0,
      has_image: false,
      has_video: false,
      moderation_status: "rejected" as const,
      like_count: 0,
      comment_count: 0,
      created_at: "2024-01-28T09:00:00Z",
    },
  ],
  total: 3,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockContacts = {
  items: [
    {
      id: "c1",
      contact_id: "u10",
      contact_name: "Alice",
      status: "approved" as const,
      requested_at: "2024-01-10T00:00:00Z",
      approved_at: "2024-01-11T00:00:00Z",
    },
    {
      id: "c2",
      contact_id: "u11",
      contact_name: "Bob",
      status: "pending" as const,
      requested_at: "2024-01-28T00:00:00Z",
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockProfile = {
  id: "child-1",
  display_name: "Emma",
  follower_count: 8,
  following_count: 6,
  post_count: 3,
  total_likes_received: 17,
  total_comments_received: 6,
  joined_at: "2024-01-01T00:00:00Z",
};

// ─── Mocks ────────────────────────────────────────────────────────────────────

const mockFlagPost = vi.fn();

vi.mock("@/hooks/use-members", () => ({
  useMembers: vi.fn(() => ({
    data: mockChildren,
    isLoading: false,
    isError: false,
  })),
}));

vi.mock("@/hooks/use-social-monitor", () => ({
  useChildFeed: vi.fn(() => ({
    data: mockFeed,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
  useChildContacts: vi.fn(() => ({
    data: mockContacts,
    isLoading: false,
    isError: false,
  })),
  useChildProfile: vi.fn(() => ({
    data: mockProfile,
    isLoading: false,
    isError: false,
  })),
  useFlagPost: vi.fn(() => ({
    mutate: mockFlagPost,
    isPending: false,
  })),
  socialMonitorKeys: {
    all: ["social-monitor"],
    feed: (id: string) => ["social-monitor", "feed", id],
    contacts: (id: string) => ["social-monitor", "contacts", id],
    profile: (id: string) => ["social-monitor", "profile", id],
  },
}));

vi.mock("@/contexts/ToastContext", () => ({
  useToast: vi.fn(() => ({
    addToast: vi.fn(),
    removeToast: vi.fn(),
    toasts: [],
  })),
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("SocialFeedPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page title", () => {
    renderWithProviders(<SocialFeedPage />);
    expect(screen.getByText("Social Feed Monitor")).toBeInTheDocument();
  });

  it("renders the page description", () => {
    renderWithProviders(<SocialFeedPage />);
    expect(
      screen.getByText(
        "Review your child's social posts, contacts, and activity"
      )
    ).toBeInTheDocument();
  });

  it("shows child selector dropdown with correct children", () => {
    renderWithProviders(<SocialFeedPage />);
    const selector = screen.getByRole("combobox", { name: /select child/i });
    expect(selector).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Emma" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Liam" })).toBeInTheDocument();
  });

  it("renders the feed section heading", () => {
    renderWithProviders(<SocialFeedPage />);
    expect(screen.getByText("Recent Posts")).toBeInTheDocument();
  });

  it("renders the contacts section heading", () => {
    renderWithProviders(<SocialFeedPage />);
    expect(screen.getByText("Contacts")).toBeInTheDocument();
  });

  it("renders post content in the feed", () => {
    renderWithProviders(<SocialFeedPage />);
    expect(
      screen.getByText("Had a great day at school today!")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Check out this cool artwork I made")
    ).toBeInTheDocument();
  });

  it("shows approved moderation badge (green)", () => {
    renderWithProviders(<SocialFeedPage />);
    const badges = screen.getAllByText("approved");
    expect(badges.length).toBeGreaterThanOrEqual(1);
    expect(badges[0]).toHaveClass("bg-green-100");
  });

  it("shows pending moderation badge (amber)", () => {
    renderWithProviders(<SocialFeedPage />);
    const badge = screen.getByText("pending");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("bg-amber-100");
  });

  it("shows rejected moderation badge (red)", () => {
    renderWithProviders(<SocialFeedPage />);
    const badge = screen.getByText("rejected");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("bg-red-100");
  });

  it("renders a flag button for each post", () => {
    renderWithProviders(<SocialFeedPage />);
    const flagButtons = screen.getAllByRole("button", { name: /flag post/i });
    expect(flagButtons).toHaveLength(mockFeed.items.length);
  });

  it("opens flag confirmation modal when flag button is clicked", () => {
    renderWithProviders(<SocialFeedPage />);
    const flagButtons = screen.getAllByRole("button", { name: /flag post/i });
    fireEvent.click(flagButtons[0]);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Flag this post")).toBeInTheDocument();
  });

  it("cancel button in flag modal closes the modal", () => {
    renderWithProviders(<SocialFeedPage />);
    const flagButtons = screen.getAllByRole("button", { name: /flag post/i });
    fireEvent.click(flagButtons[0]);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows approved contacts list", () => {
    renderWithProviders(<SocialFeedPage />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("shows pending contact requests", () => {
    renderWithProviders(<SocialFeedPage />);
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("Awaiting approval")).toBeInTheDocument();
  });

  it("displays activity stats — total posts", () => {
    renderWithProviders(<SocialFeedPage />);
    expect(screen.getByText("Total posts")).toBeInTheDocument();
  });

  it("displays activity stats — total likes received", () => {
    renderWithProviders(<SocialFeedPage />);
    expect(screen.getByText("Total likes received")).toBeInTheDocument();
  });

  it("displays activity stats — total comments received", () => {
    renderWithProviders(<SocialFeedPage />);
    expect(screen.getByText("Total comments received")).toBeInTheDocument();
  });

  it("shows image media indicator for posts with images", () => {
    renderWithProviders(<SocialFeedPage />);
    expect(screen.getByText("Image")).toBeInTheDocument();
  });
});

// ─── Hook export tests ────────────────────────────────────────────────────────

describe("use-social-monitor hook exports", () => {
  it("exports useChildFeed", async () => {
    const mod = await import("@/hooks/use-social-monitor");
    expect(typeof mod.useChildFeed).toBe("function");
  });

  it("exports useChildContacts", async () => {
    const mod = await import("@/hooks/use-social-monitor");
    expect(typeof mod.useChildContacts).toBe("function");
  });

  it("exports useChildProfile", async () => {
    const mod = await import("@/hooks/use-social-monitor");
    expect(typeof mod.useChildProfile).toBe("function");
  });

  it("exports useFlagPost", async () => {
    const mod = await import("@/hooks/use-social-monitor");
    expect(typeof mod.useFlagPost).toBe("function");
  });

  it("exports socialMonitorKeys", async () => {
    const mod = await import("@/hooks/use-social-monitor");
    expect(mod.socialMonitorKeys).toBeDefined();
    expect(Array.isArray(mod.socialMonitorKeys.all)).toBe(true);
  });
});
