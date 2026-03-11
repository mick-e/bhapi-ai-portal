import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ReportsPage from "../page";

// Mock hooks
const mockReportsData = {
  items: [
    {
      id: "r1",
      group_id: "g1",
      title: "Safety Report - January",
      description: "Monthly safety summary",
      type: "safety" as const,
      status: "ready" as const,
      format: "pdf" as const,
      period_start: "2024-01-01",
      period_end: "2024-01-31",
      generated_at: "2024-01-31T12:00:00Z",
      created_at: "2024-01-31T12:00:00Z",
    },
    {
      id: "r2",
      group_id: "g1",
      title: "Spend Report - January",
      description: "Monthly spend breakdown",
      type: "spend" as const,
      status: "generating" as const,
      format: "csv" as const,
      period_start: "2024-01-01",
      period_end: "2024-01-31",
      created_at: "2024-01-31T13:00:00Z",
    },
    {
      id: "r3",
      group_id: "g1",
      title: "Activity Report",
      description: "Weekly activity summary",
      type: "activity" as const,
      status: "ready" as const,
      format: "pdf" as const,
      period_start: "2024-01-22",
      period_end: "2024-01-28",
      generated_at: "2024-01-28T18:00:00Z",
      created_at: "2024-01-28T18:00:00Z",
    },
  ],
  total: 3,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockDownload = vi.fn();
const mockCreateReport = vi.fn();

vi.mock("@/hooks/use-reports", () => ({
  useReports: vi.fn(() => ({
    data: mockReportsData,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
  useCreateReport: vi.fn(() => ({
    mutate: mockCreateReport,
    isPending: false,
    isError: false,
    error: null,
    reset: vi.fn(),
  })),
  useDownloadReport: vi.fn(() => ({
    mutate: mockDownload,
    isPending: false,
    variables: null,
  })),
  useReportSchedules: vi.fn(() => ({
    data: [],
    isLoading: false,
  })),
  useUpdateReportSchedule: vi.fn(() => ({
    mutate: vi.fn(),
  })),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page heading", () => {
    renderWithProviders(<ReportsPage />);
    expect(screen.getByText("Reports")).toBeInTheDocument();
  });

  it("shows total report count", () => {
    renderWithProviders(<ReportsPage />);
    expect(screen.getByText("(3 total)")).toBeInTheDocument();
  });

  it("renders all report cards", () => {
    renderWithProviders(<ReportsPage />);
    expect(
      screen.getByText("Safety Report - January")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Spend Report - January")
    ).toBeInTheDocument();
    expect(screen.getByText("Activity Report")).toBeInTheDocument();
  });

  it("shows status badges", () => {
    renderWithProviders(<ReportsPage />);
    expect(screen.getAllByText("Ready")).toHaveLength(2);
    expect(screen.getByText("Processing")).toBeInTheDocument();
  });

  it("shows download buttons for ready reports", () => {
    renderWithProviders(<ReportsPage />);
    const downloadButtons = screen.getAllByText("Download");
    expect(downloadButtons).toHaveLength(2); // Only 2 ready reports
  });

  it("calls download on button click", () => {
    renderWithProviders(<ReportsPage />);
    const downloadButtons = screen.getAllByText("Download");
    fireEvent.click(downloadButtons[0]);
    expect(mockDownload).toHaveBeenCalledWith("r1");
  });

  it("shows generate report button", () => {
    renderWithProviders(<ReportsPage />);
    expect(screen.getByText("Generate Report")).toBeInTheDocument();
  });

  it("opens create modal on button click", () => {
    renderWithProviders(<ReportsPage />);
    // Click the main "Generate Report" button
    const buttons = screen.getAllByText("Generate Report");
    fireEvent.click(buttons[0]);
    expect(
      screen.getByText("Create a new report for your group")
    ).toBeInTheDocument();
  });

  it("shows type filter dropdown", () => {
    renderWithProviders(<ReportsPage />);
    expect(screen.getByText("Filter by type:")).toBeInTheDocument();
    expect(screen.getByDisplayValue("All types")).toBeInTheDocument();
  });

  it("shows quick stats cards", () => {
    renderWithProviders(<ReportsPage />);
    expect(screen.getByText("Reports generated")).toBeInTheDocument();
    expect(screen.getByText("Available for download")).toBeInTheDocument();
    expect(screen.getByText("PDF / CSV")).toBeInTheDocument();
  });

  it("shows configure schedule button", () => {
    renderWithProviders(<ReportsPage />);
    expect(
      screen.getByText("Configure Scheduled Reports")
    ).toBeInTheDocument();
  });

  it("opens schedule section on button click", () => {
    renderWithProviders(<ReportsPage />);
    fireEvent.click(screen.getByText("Configure Scheduled Reports"));
    expect(screen.getByText("Scheduled Reports")).toBeInTheDocument();
  });
});
