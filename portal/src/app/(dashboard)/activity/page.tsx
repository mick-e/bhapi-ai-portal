"use client";

import { useState } from "react";
import {
  Activity,
  Search,
  Filter,
  MessageSquare,
  Code,
  Image,
  FileText,
  Loader2,
  AlertTriangle,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useActivity } from "@/hooks/use-activity";
import type { CaptureEvent, EventType } from "@/types";

const typeIcons: Record<EventType, typeof MessageSquare> = {
  chat: MessageSquare,
  code: Code,
  image: Image,
  document: FileText,
};

const typeLabels: Record<EventType, string> = {
  chat: "Chat",
  code: "Code generation",
  image: "Image analysis",
  document: "Document",
};

export default function ActivityPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterRisk, setFilterRisk] = useState<string>("all");
  const [filterProvider, setFilterProvider] = useState<string>("all");
  const [filterType, setFilterType] = useState<string>("all");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const {
    data: activityData,
    isLoading,
    isError,
    error,
    refetch,
  } = useActivity({
    page,
    page_size: pageSize,
    risk_level: filterRisk !== "all" ? filterRisk : undefined,
    provider: filterProvider !== "all" ? filterProvider : undefined,
    event_type: filterType !== "all" ? filterType : undefined,
    search: searchQuery || undefined,
  });

  const events = activityData?.items ?? [];
  const totalPages = activityData?.total_pages ?? 1;
  const totalEvents = activityData?.total ?? 0;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading activity...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load activity
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
        <h1 className="text-2xl font-bold text-gray-900">Activity</h1>
        <p className="mt-1 text-sm text-gray-500">
          Timeline of all AI interactions across your group
          {totalEvents > 0 && (
            <span className="ml-1 text-gray-400">
              ({totalEvents.toLocaleString()} total)
            </span>
          )}
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search activity..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            aria-label="Search activity"
            className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="h-4 w-4 text-gray-400" />
          <select
            value={filterRisk}
            onChange={(e) => {
              setFilterRisk(e.target.value);
              setPage(1);
            }}
            aria-label="Filter by risk level"
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">All risk levels</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <select
            value={filterProvider}
            onChange={(e) => {
              setFilterProvider(e.target.value);
              setPage(1);
            }}
            aria-label="Filter by provider"
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">All providers</option>
            <option value="OpenAI">OpenAI</option>
            <option value="Anthropic">Anthropic</option>
            <option value="Google">Google</option>
            <option value="Microsoft">Microsoft</option>
            <option value="xAI">xAI</option>
          </select>
          <select
            value={filterType}
            onChange={(e) => {
              setFilterType(e.target.value);
              setPage(1);
            }}
            aria-label="Filter by event type"
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">All types</option>
            <option value="chat">Chat</option>
            <option value="code">Code</option>
            <option value="image">Image</option>
            <option value="document">Document</option>
          </select>
        </div>
      </div>

      {/* Activity Timeline */}
      <div className="space-y-4">
        {events.map((event) => (
          <ActivityCard key={event.id} event={event} />
        ))}

        {events.length === 0 && (
          <div className="py-12 text-center">
            <Activity className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-sm text-gray-500">
              {searchQuery ||
              filterRisk !== "all" ||
              filterProvider !== "all" ||
              filterType !== "all"
                ? "No activity matches your filters"
                : "No activity recorded yet"}
            </p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Showing {events.length} of {totalEvents.toLocaleString()} events
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

function ActivityCard({ event }: { event: CaptureEvent }) {
  const TypeIcon =
    typeIcons[(event.event_type as EventType) || "chat"] ?? MessageSquare;
  const timeLabel = formatRelativeTime(event.timestamp);

  return (
    <Card>
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100">
          <TypeIcon className="h-5 w-5 text-gray-600" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-[10px] font-semibold text-primary">
                {event.member_name.charAt(0).toUpperCase()}
              </div>
              <span className="text-sm font-semibold text-gray-900">
                {event.member_name}
              </span>
              <span className="text-xs text-gray-400">
                {event.provider} / {event.model}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <RiskBadge level={event.risk_level} />
              <span className="text-xs text-gray-400">{timeLabel}</span>
            </div>
          </div>
          <p className="mt-1 truncate text-sm text-gray-600">
            {event.prompt_preview}
          </p>
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
            <span className="capitalize">
              {typeLabels[(event.event_type as EventType) || "chat"] || event.event_type}
            </span>
            <span>{event.token_count.toLocaleString()} tokens</span>
            <span>${event.cost_usd.toFixed(3)}</span>
            {event.flagged && (
              <span className="font-medium text-red-500">Flagged</span>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

function RiskBadge({
  level,
}: {
  level: "low" | "medium" | "high" | "critical";
}) {
  const styles = {
    low: "bg-green-100 text-green-700",
    medium: "bg-amber-100 text-amber-700",
    high: "bg-red-100 text-red-700",
    critical: "bg-red-200 text-red-800",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${styles[level]}`}
    >
      {level}
    </span>
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
