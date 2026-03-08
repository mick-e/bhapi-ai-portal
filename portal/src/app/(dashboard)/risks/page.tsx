"use client";

import { useState } from "react";
import {
  ShieldAlert,
  Filter,
  Loader2,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { DateRangeFilter } from "@/components/DateRangeFilter";
import { useRiskEvents, useAcknowledgeRisk } from "@/hooks/use-alerts";
import { useToast } from "@/contexts/ToastContext";
import { useAuth } from "@/hooks/use-auth";
import type { RiskEvent, RiskSeverity } from "@/types";

const severityStyles: Record<
  RiskSeverity,
  { border: string; bg: string; badge: string }
> = {
  low: {
    border: "border-l-blue-500",
    bg: "bg-blue-50",
    badge: "bg-blue-100 text-blue-700",
  },
  medium: {
    border: "border-l-amber-500",
    bg: "bg-amber-50",
    badge: "bg-amber-100 text-amber-700",
  },
  high: {
    border: "border-l-orange-500",
    bg: "bg-orange-50",
    badge: "bg-orange-100 text-orange-700",
  },
  critical: {
    border: "border-l-red-700",
    bg: "bg-red-100",
    badge: "bg-red-200 text-red-800",
  },
};

const categories = [
  "all",
  "SELF_HARM",
  "VIOLENCE",
  "ACADEMIC_DISHONESTY",
  "BULLYING",
  "PII_EXPOSURE",
  "SEXUAL_CONTENT",
  "SUBSTANCE_ABUSE",
];

export default function RisksPage() {
  const [filterSeverity, setFilterSeverity] = useState<string>("all");
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [filterAck, setFilterAck] = useState<string>("all");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { user } = useAuth();
  const { addToast } = useToast();
  const acknowledgeMutation = useAcknowledgeRisk();

  const {
    data: riskData,
    isLoading,
    isError,
    error,
    refetch,
  } = useRiskEvents({
    page,
    page_size: pageSize,
    severity: filterSeverity !== "all" ? filterSeverity : undefined,
    category: filterCategory !== "all" ? filterCategory : undefined,
    resolved: filterAck === "all" ? undefined : filterAck === "acknowledged",
  });

  const events = riskData?.items ?? [];
  const totalPages = riskData?.total_pages ?? 1;
  const totalEvents = riskData?.total ?? 0;

  function handleAcknowledge(eventId: string) {
    acknowledgeMutation.mutate(
      { event_id: eventId, notes: undefined },
      {
        onSuccess: () => addToast("Risk event acknowledged", "success"),
        onError: (err) =>
          addToast((err as Error).message || "Failed to acknowledge", "error"),
      }
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">
          Loading risk events...
        </span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load risk events
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
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Risk Events</h1>
        <p className="mt-1 text-sm text-gray-500">
          Safety events detected by the risk pipeline
          {totalEvents > 0 && (
            <span className="ml-1 text-gray-400">
              ({totalEvents} total)
            </span>
          )}
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:flex-wrap">
        <Filter className="h-4 w-4 text-gray-400" />
        <select
          value={filterSeverity}
          onChange={(e) => {
            setFilterSeverity(e.target.value);
            setPage(1);
          }}
          aria-label="Filter by severity"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="all">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          value={filterCategory}
          onChange={(e) => {
            setFilterCategory(e.target.value);
            setPage(1);
          }}
          aria-label="Filter by category"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat === "all" ? "All categories" : cat.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <select
          value={filterAck}
          onChange={(e) => {
            setFilterAck(e.target.value);
            setPage(1);
          }}
          aria-label="Filter by status"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="all">All statuses</option>
          <option value="unacknowledged">Unacknowledged</option>
          <option value="acknowledged">Acknowledged</option>
        </select>
      </div>

      {/* Risk Event List */}
      <div className="space-y-3">
        {events.map((event) => (
          <RiskEventCard
            key={event.id}
            event={event}
            onAcknowledge={handleAcknowledge}
            isAcknowledging={
              acknowledgeMutation.isPending &&
              acknowledgeMutation.variables?.event_id === event.id
            }
          />
        ))}

        {events.length === 0 && (
          <div className="py-12 text-center">
            <ShieldAlert className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-sm text-gray-500">
              No risk events match your filters
            </p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Showing {events.length} of {totalEvents} events
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

function RiskEventCard({
  event,
  onAcknowledge,
  isAcknowledging,
}: {
  event: RiskEvent;
  onAcknowledge: (id: string) => void;
  isAcknowledging: boolean;
}) {
  const style = severityStyles[event.severity] || severityStyles.low;
  const timeLabel = formatRelativeTime(event.timestamp);

  return (
    <div
      className={`rounded-r-xl border-l-4 ${style.border} ${
        event.acknowledged ? "bg-white" : style.bg
      } p-4 shadow-sm ring-1 ring-gray-200`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-900 capitalize">
              {event.category.replace(/_/g, " ").toLowerCase()}
            </span>
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${style.badge}`}
            >
              {event.severity}
            </span>
            {event.acknowledged && (
              <span className="flex items-center gap-1 text-xs text-green-600">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Acknowledged
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-600">{event.description}</p>
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
            <span>Member: {event.member_name}</span>
            <span>{timeLabel}</span>
          </div>
        </div>

        <div className="flex-shrink-0">
          {!event.acknowledged && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onAcknowledge(event.id)}
              isLoading={isAcknowledging}
            >
              Acknowledge
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

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
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
    return date.toLocaleDateString();
  } catch {
    return timestamp;
  }
}
