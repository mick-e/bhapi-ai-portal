"use client";

import { useState } from "react";
import {
  FileBarChart,
  Download,
  Calendar,
  Shield,
  TrendingUp,
  Users,
  Loader2,
  AlertTriangle,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  X,
  Clock,
  CheckCircle2,
  XCircle,
  Mail,
  Heart,
  TrendingDown,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  useReports,
  useCreateReport,
  useDownloadReport,
  useReportSchedules,
  useUpdateReportSchedule,
} from "@/hooks/use-reports";
import { useFamilyWeeklyReport, useSendFamilyReport } from "@/hooks/use-family-report";
import type {
  Report,
  ReportType,
  ReportFormat,
  ReportStatus,
  ReportSchedule,
  ReportScheduleConfig,
} from "@/types";

const typeIcons: Record<ReportType, typeof Shield> = {
  safety: Shield,
  spend: TrendingUp,
  activity: Users,
  compliance: FileBarChart,
};

const typeColors: Record<ReportType, string> = {
  safety: "bg-red-50 text-red-600",
  spend: "bg-green-50 text-green-600",
  activity: "bg-blue-50 text-blue-600",
  compliance: "bg-purple-50 text-purple-600",
};

const statusConfig: Record<
  ReportStatus,
  { icon: typeof CheckCircle2; label: string; color: string }
> = {
  ready: {
    icon: CheckCircle2,
    label: "Ready",
    color: "text-green-600",
  },
  generating: {
    icon: Clock,
    label: "Generating",
    color: "text-amber-600",
  },
  failed: {
    icon: XCircle,
    label: "Failed",
    color: "text-red-600",
  },
};

export default function ReportsPage() {
  const [filterType, setFilterType] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showScheduleSection, setShowScheduleSection] = useState(false);
  const pageSize = 20;

  const {
    data: reportsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useReports({
    page,
    page_size: pageSize,
    type: filterType !== "all" ? filterType : undefined,
  });

  const downloadMutation = useDownloadReport();

  const reports = reportsData?.items ?? [];
  const totalPages = reportsData?.total_pages ?? 1;
  const totalReports = reportsData?.total ?? 0;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading reports...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load reports
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || "Something went wrong"}
        </p>
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={() => refetch()}
        >
          <RefreshCw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
          <p className="mt-1 text-sm text-gray-500">
            Generated reports on AI usage, safety, and compliance
            {totalReports > 0 && (
              <span className="ml-1 text-gray-400">
                ({totalReports} total)
              </span>
            )}
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <FileBarChart className="h-4 w-4" />
          Generate Report
        </Button>
      </div>

      {/* Quick Stats */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
              <FileBarChart className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalReports}</p>
              <p className="text-sm text-gray-500">Reports generated</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50">
              <Calendar className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {reports.filter((r) => r.status === "ready").length}
              </p>
              <p className="text-sm text-gray-500">Available for download</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50">
              <Download className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">PDF / CSV</p>
              <p className="text-sm text-gray-500">Export formats</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="mb-6 flex items-center gap-3">
        <span className="text-sm text-gray-500">Filter by type:</span>
        <select
          value={filterType}
          onChange={(e) => {
            setFilterType(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="all">All types</option>
          <option value="safety">Safety</option>
          <option value="spend">Spend</option>
          <option value="activity">Activity</option>
          <option value="compliance">Compliance</option>
        </select>
      </div>

      {/* Reports List */}
      <div className="space-y-4">
        {reports.map((report) => (
          <ReportCard
            key={report.id}
            report={report}
            onDownload={() => downloadMutation.mutate(report.id)}
            isDownloading={
              downloadMutation.isPending &&
              downloadMutation.variables === report.id
            }
          />
        ))}

        {reports.length === 0 && (
          <div className="py-12 text-center">
            <FileBarChart className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-sm text-gray-500">
              {filterType !== "all"
                ? "No reports match your filter"
                : "No reports generated yet"}
            </p>
            <Button
              variant="secondary"
              size="sm"
              className="mt-4"
              onClick={() => setShowCreateModal(true)}
            >
              Generate your first report
            </Button>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Showing {reports.length} of {totalReports} reports
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <span className="text-sm text-gray-600">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Schedule Configuration */}
      {showScheduleSection && <ScheduleSection />}

      {!showScheduleSection && (
        <div className="mt-6">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowScheduleSection(true)}
          >
            <Calendar className="h-4 w-4" />
            Configure Scheduled Reports
          </Button>
        </div>
      )}

      {/* Weekly Family Report Section */}
      <WeeklyFamilyReportSection />

      {/* Create Report Modal */}
      {showCreateModal && (
        <CreateReportModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function ReportCard({
  report,
  onDownload,
  isDownloading,
}: {
  report: Report;
  onDownload: () => void;
  isDownloading: boolean;
}) {
  const TypeIcon = typeIcons[report.type] || FileBarChart;
  const colorClass = typeColors[report.type] || "bg-gray-50 text-gray-600";
  const status = statusConfig[report.status] || statusConfig.ready;
  const StatusIcon = status.icon;

  return (
    <Card>
      <div className="flex items-start gap-4">
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${colorClass}`}
        >
          <TypeIcon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">
                {report.title}
              </h3>
              <p className="mt-0.5 text-xs text-gray-400">
                Period: {formatDateRange(report.period_start, report.period_end)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className={`flex items-center gap-1 text-xs ${status.color}`}>
                <StatusIcon className="h-3.5 w-3.5" />
                {status.label}
              </div>
              {report.status === "ready" && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={onDownload}
                  isLoading={isDownloading}
                >
                  <Download className="h-3.5 w-3.5" />
                  Download
                </Button>
              )}
              {report.status === "generating" && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
                  Processing
                </span>
              )}
            </div>
          </div>
          <p className="mt-1 text-sm text-gray-600">{report.description}</p>
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
            <span className="capitalize">{report.type}</span>
            <span className="uppercase">{report.format}</span>
            {report.generated_at && (
              <span>Generated: {formatDate(report.generated_at)}</span>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

function CreateReportModal({ onClose }: { onClose: () => void }) {
  const [reportType, setReportType] = useState<ReportType>("safety");
  const [format, setFormat] = useState<ReportFormat>("pdf");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");

  const createMutation = useCreateReport();

  function handleCreate() {
    if (!periodStart || !periodEnd) return;
    createMutation.mutate(
      {
        type: reportType,
        format,
        period_start: periodStart,
        period_end: periodEnd,
      },
      {
        onSuccess: () => {
          onClose();
        },
      }
    );
  }

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">
              Generate Report
            </h2>
            <button
              onClick={onClose}
              className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Create a new report for your group
          </p>

          {createMutation.isError && (
            <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
              {(createMutation.error as Error)?.message ||
                "Failed to create report"}
            </div>
          )}

          <div className="mt-4 space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Report type
              </label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value as ReportType)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                <option value="safety">Safety Summary</option>
                <option value="spend">Spend Report</option>
                <option value="activity">Activity Report</option>
                <option value="compliance">Compliance Report</option>
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Format
              </label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value as ReportFormat)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                <option value="pdf">PDF</option>
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
              </select>
            </div>
            <Input
              label="Period start"
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
            />
            <Input
              label="Period end"
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
            />
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                onClose();
                createMutation.reset();
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              isLoading={createMutation.isPending}
              disabled={!periodStart || !periodEnd}
            >
              Generate
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}

function ScheduleSection() {
  const { data: schedules, isLoading } = useReportSchedules();
  const updateSchedule = useUpdateReportSchedule();

  const reportTypes: ReportType[] = ["safety", "spend", "activity", "compliance"];
  const scheduleOptions: { value: ReportSchedule; label: string }[] = [
    { value: "none", label: "None" },
    { value: "daily", label: "Daily" },
    { value: "weekly", label: "Weekly" },
    { value: "monthly", label: "Monthly" },
  ];

  function getCurrentSchedule(type: ReportType): ReportScheduleConfig {
    const existing = schedules?.find((s) => s.type === type);
    return existing || { type, schedule: "none", format: "pdf", recipients: [] };
  }

  function handleScheduleChange(type: ReportType, schedule: ReportSchedule) {
    const current = getCurrentSchedule(type);
    updateSchedule.mutate({ ...current, schedule });
  }

  function handleFormatChange(type: ReportType, format: ReportFormat) {
    const current = getCurrentSchedule(type);
    updateSchedule.mutate({ ...current, format });
  }

  return (
    <div className="mt-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Scheduled Reports
        </h2>
        <p className="text-sm text-gray-500">
          Automatically generate and email reports on a schedule
        </p>
      </div>
      {isLoading ? (
        <div className="flex h-24 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {reportTypes.map((type) => {
            const config = getCurrentSchedule(type);
            const TypeIcon = typeIcons[type] || FileBarChart;
            const colorClass =
              typeColors[type] || "bg-gray-50 text-gray-600";

            return (
              <Card key={type}>
                <div className="flex items-start gap-3">
                  <div
                    className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${colorClass}`}
                  >
                    <TypeIcon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 space-y-3">
                    <h3 className="text-sm font-semibold capitalize text-gray-900">
                      {type} Report
                    </h3>
                    <div className="flex items-center gap-2">
                      <label className="text-xs text-gray-500">Schedule:</label>
                      <select
                        value={config.schedule}
                        onChange={(e) =>
                          handleScheduleChange(
                            type,
                            e.target.value as ReportSchedule
                          )
                        }
                        className="rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none"
                      >
                        {scheduleOptions.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    {config.schedule !== "none" && (
                      <div className="flex items-center gap-2">
                        <label className="text-xs text-gray-500">Format:</label>
                        <select
                          value={config.format}
                          onChange={(e) =>
                            handleFormatChange(
                              type,
                              e.target.value as ReportFormat
                            )
                          }
                          className="rounded border border-gray-300 px-2 py-1 text-xs focus:border-primary focus:outline-none"
                        >
                          <option value="pdf">PDF</option>
                          <option value="csv">CSV</option>
                          <option value="json">JSON</option>
                        </select>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Weekly Family Report Section ────────────────────────────────────────────

function WeeklyFamilyReportSection() {
  const { data: report, isLoading, isError } = useFamilyWeeklyReport();
  const sendReport = useSendFamilyReport();

  if (isLoading) {
    return (
      <div className="mt-8">
        <Card title="Weekly Family Safety Report">
          <div className="flex h-24 items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="ml-2 text-sm text-gray-500">Loading weekly report...</span>
          </div>
        </Card>
      </div>
    );
  }

  if (isError || !report) {
    return (
      <div className="mt-8">
        <Card title="Weekly Family Safety Report">
          <p className="text-sm text-gray-500">
            No weekly report data available yet. Reports are generated once you have activity data.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="mt-8 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Weekly Family Safety Report
        </h2>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => sendReport.mutate()}
          isLoading={sendReport.isPending}
        >
          <Mail className="h-4 w-4" />
          Email Report
        </Button>
      </div>

      {/* Safety score */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50">
              <Heart className="h-5 w-5 text-teal-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {report.family_safety_score}
              </p>
              <p className="text-sm text-gray-500">Family Safety Score</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
              <Users className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {report.member_count}
              </p>
              <p className="text-sm text-gray-500">Family Members</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {report.action_items.unresolved_alerts}
              </p>
              <p className="text-sm text-gray-500">Unresolved Alerts</p>
            </div>
          </div>
        </div>
      </div>

      {/* Per-member breakdown */}
      <Card title="Member Breakdown">
        <div className="space-y-3">
          {report.members.map((m) => (
            <div
              key={m.member_id}
              className="flex items-center justify-between rounded-lg border border-gray-100 p-3"
            >
              <div>
                <p className="text-sm font-medium text-gray-900">{m.display_name}</p>
                <p className="mt-0.5 text-xs text-gray-500">
                  {m.platforms_used.length > 0
                    ? `Platforms: ${m.platforms_used.join(", ")}`
                    : "No AI usage this week"}
                </p>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="text-center">
                  <p className="font-semibold text-gray-900">{m.safety_score}</p>
                  <p className="text-xs text-gray-500">Safety</p>
                </div>
                <div className="text-center">
                  <p className="font-semibold text-gray-900">{m.events_this_week}</p>
                  <p className="text-xs text-gray-500">Events</p>
                </div>
                <div className="text-center">
                  <p className={`font-semibold ${m.risk_count > 0 ? "text-red-600" : "text-green-600"}`}>
                    {m.risk_count}
                  </p>
                  <p className="text-xs text-gray-500">Risks</p>
                </div>
                <div className="text-center">
                  {m.week_change > 0 ? (
                    <p className="text-xs text-amber-600">
                      <TrendingUp className="inline h-3 w-3" /> +{m.week_change}
                    </p>
                  ) : m.week_change < 0 ? (
                    <p className="text-xs text-green-600">
                      <TrendingDown className="inline h-3 w-3" /> {m.week_change}
                    </p>
                  ) : (
                    <p className="text-xs text-gray-400">--</p>
                  )}
                  <p className="text-xs text-gray-500">Change</p>
                </div>
              </div>
            </div>
          ))}
          {report.members.length === 0 && (
            <p className="text-sm text-gray-500">No member data available.</p>
          )}
        </div>
      </Card>

      {/* Highlights */}
      {(report.highlights.safest_member || report.highlights.most_improved) && (
        <Card title="Highlights">
          <div className="flex flex-wrap gap-4">
            {report.highlights.safest_member && (
              <div className="flex items-center gap-2 rounded-lg bg-green-50 px-4 py-2">
                <Shield className="h-4 w-4 text-green-600" />
                <span className="text-sm text-green-800">
                  Safest member: <strong>{report.highlights.safest_member}</strong>
                </span>
              </div>
            )}
            {report.highlights.most_improved && (
              <div className="flex items-center gap-2 rounded-lg bg-blue-50 px-4 py-2">
                <TrendingUp className="h-4 w-4 text-blue-600" />
                <span className="text-sm text-blue-800">
                  Most improved: <strong>{report.highlights.most_improved}</strong>
                </span>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatDateRange(start: string, end: string): string {
  try {
    const s = new Date(start);
    const e = new Date(end);
    const opts: Intl.DateTimeFormatOptions = {
      day: "numeric",
      month: "short",
      year: "numeric",
    };
    return `${s.toLocaleDateString("en-GB", opts)} - ${e.toLocaleDateString("en-GB", opts)}`;
  } catch {
    return `${start} - ${end}`;
  }
}

function formatDate(timestamp: string): string {
  try {
    const d = new Date(timestamp);
    return d.toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return timestamp;
  }
}
