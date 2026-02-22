"use client";

import { useState } from "react";
import {
  Bell,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  Filter,
  Loader2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import {
  useAlerts,
  useMarkAlertActioned,
  useMarkAllAlertsRead,
} from "@/hooks/use-alerts";
import type { Alert, AlertSeverity } from "@/types";

const severityIcons: Record<AlertSeverity, typeof Info> = {
  info: Info,
  warning: AlertTriangle,
  error: AlertCircle,
  critical: AlertTriangle,
};

const severityStyles: Record<
  AlertSeverity,
  { border: string; bg: string; iconColor: string; badge: string }
> = {
  info: {
    border: "border-l-blue-500",
    bg: "bg-blue-50",
    iconColor: "text-blue-500",
    badge: "bg-blue-100 text-blue-700",
  },
  warning: {
    border: "border-l-amber-500",
    bg: "bg-amber-50",
    iconColor: "text-amber-500",
    badge: "bg-amber-100 text-amber-700",
  },
  error: {
    border: "border-l-orange-500",
    bg: "bg-orange-50",
    iconColor: "text-orange-500",
    badge: "bg-orange-100 text-orange-700",
  },
  critical: {
    border: "border-l-red-700",
    bg: "bg-red-100",
    iconColor: "text-red-700",
    badge: "bg-red-200 text-red-800",
  },
};

export default function AlertsPage() {
  const [filterSeverity, setFilterSeverity] = useState<string>("all");
  const [filterType, setFilterType] = useState<string>("all");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const {
    data: alertsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useAlerts({
    page,
    page_size: pageSize,
    severity: filterSeverity !== "all" ? filterSeverity : undefined,
    type: filterType !== "all" ? filterType : undefined,
  });

  const markActionedMutation = useMarkAlertActioned();
  const markAllReadMutation = useMarkAllAlertsRead();

  const alerts = alertsData?.items ?? [];
  const totalPages = alertsData?.total_pages ?? 1;
  const totalAlerts = alertsData?.total ?? 0;
  const unreadCount = alerts.filter((a) => !a.read).length;

  function handleMarkAllRead() {
    markAllReadMutation.mutate();
  }

  function handleAcknowledge(alertId: string) {
    markActionedMutation.mutate(alertId);
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading alerts...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load alerts
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
          <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
          <p className="mt-1 text-sm text-gray-500">
            {unreadCount > 0
              ? `${unreadCount} unread alert${unreadCount > 1 ? "s" : ""}`
              : "All caught up"}
            {totalAlerts > 0 && (
              <span className="ml-1 text-gray-400">
                ({totalAlerts} total)
              </span>
            )}
          </p>
        </div>
        {unreadCount > 0 && (
          <Button
            variant="secondary"
            size="sm"
            onClick={handleMarkAllRead}
            isLoading={markAllReadMutation.isPending}
          >
            <CheckCircle2 className="h-4 w-4" />
            Mark all read
          </Button>
        )}
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Filter className="h-4 w-4 text-gray-400" />
        <select
          value={filterSeverity}
          onChange={(e) => {
            setFilterSeverity(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="all">All severities</option>
          <option value="critical">Critical</option>
          <option value="error">Error</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
        <select
          value={filterType}
          onChange={(e) => {
            setFilterType(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="all">All types</option>
          <option value="risk">Risk</option>
          <option value="spend">Spend</option>
          <option value="member">Member</option>
          <option value="system">System</option>
        </select>
      </div>

      {/* Alert List */}
      <div className="space-y-3">
        {alerts.map((alert) => (
          <AlertCard
            key={alert.id}
            alert={alert}
            onAcknowledge={handleAcknowledge}
            isAcknowledging={
              markActionedMutation.isPending &&
              markActionedMutation.variables === alert.id
            }
          />
        ))}

        {alerts.length === 0 && (
          <div className="py-12 text-center">
            <Bell className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-sm text-gray-500">
              No alerts match your filters
            </p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Showing {alerts.length} of {totalAlerts} alerts
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
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function AlertCard({
  alert,
  onAcknowledge,
  isAcknowledging,
}: {
  alert: Alert;
  onAcknowledge: (id: string) => void;
  isAcknowledging: boolean;
}) {
  const style = severityStyles[alert.severity] || severityStyles.info;
  const SeverityIcon = severityIcons[alert.severity] || Info;
  const timeLabel = formatRelativeTime(alert.created_at);

  return (
    <div
      className={`rounded-r-xl border-l-4 ${style.border} ${
        alert.read ? "bg-white" : style.bg
      } p-4 shadow-sm ring-1 ring-gray-200`}
    >
      <div className="flex items-start gap-3">
        <SeverityIcon
          className={`mt-0.5 h-5 w-5 flex-shrink-0 ${style.iconColor}`}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <h3
                  className={`text-sm font-semibold ${
                    alert.read ? "text-gray-700" : "text-gray-900"
                  }`}
                >
                  {alert.title}
                </h3>
                {!alert.read && (
                  <span className="inline-block h-2 w-2 rounded-full bg-primary" />
                )}
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${style.badge}`}
                >
                  {alert.severity}
                </span>
              </div>
              <div className="mt-0.5 flex items-center gap-2">
                {alert.member_name && (
                  <span className="text-xs text-gray-400">
                    Member: {alert.member_name}
                  </span>
                )}
                <span className="text-xs capitalize text-gray-400">
                  {alert.type}
                </span>
              </div>
            </div>
            <span className="flex-shrink-0 text-xs text-gray-400">
              {timeLabel}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-600">{alert.message}</p>
          {!alert.actioned && (
            <div className="mt-3">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onAcknowledge(alert.id)}
                isLoading={isAcknowledging}
              >
                Acknowledge
              </Button>
            </div>
          )}
          {alert.actioned && (
            <div className="mt-2 flex items-center gap-1 text-xs text-green-600">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Acknowledged
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatRelativeTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60_000);
    const diffHours = Math.floor(diffMs / 3_600_000);
    const diffDays = Math.floor(diffMs / 86_400_000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24)
      return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    if (diffDays < 7)
      return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
    return date.toLocaleDateString();
  } catch {
    return timestamp;
  }
}
