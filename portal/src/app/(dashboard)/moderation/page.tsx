"use client";

import { AlertTriangle, Clock, Inbox, CheckCircle, Loader2, RefreshCw } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { useModerationSla } from "@/hooks/use-moderation-sla";

// SLA targets (must match backend constants)
const PRE_PUBLISH_SLA_MS = 2_000;   // <2s for pre-publish (under 13)
const POST_PUBLISH_SLA_MS = 60_000; // <60s for post-publish (13-15)

function formatMs(ms: number): string {
  if (ms === 0) return "—";
  if (ms < 1_000) return `${ms.toFixed(0)} ms`;
  return `${(ms / 1_000).toFixed(2)} s`;
}

function formatAge(seconds: number): string {
  if (seconds === 0) return "—";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3_600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const h = Math.floor(seconds / 3_600);
  const m = Math.floor((seconds % 3_600) / 60);
  return `${h}h ${m}m`;
}

interface MetricCardProps {
  title: string;
  value: string;
  label: string;
  warn?: boolean;
  icon: React.ReactNode;
}

function MetricCard({ title, value, label, warn, icon }: MetricCardProps) {
  return (
    <Card
      className={warn ? "ring-amber-400 ring-2" : undefined}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{title}</p>
          <p className={`mt-1 text-2xl font-bold ${warn ? "text-amber-600" : "text-gray-900"}`}>
            {value}
          </p>
          <p className="mt-0.5 text-xs text-gray-400">{label}</p>
        </div>
        <span className={`rounded-lg p-2 ${warn ? "bg-amber-50 text-amber-500" : "bg-gray-50 text-gray-400"}`}>
          {icon}
        </span>
      </div>
      {warn && (
        <div className="mt-3 flex items-center gap-1 text-xs font-medium text-amber-600">
          <AlertTriangle className="h-3 w-3" />
          SLA threshold breached
        </div>
      )}
    </Card>
  );
}

export default function ModerationSLAPage() {
  const { data, isLoading, isError, dataUpdatedAt } = useModerationSla();

  const lastUpdated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : null;

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Moderation SLA Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            Live pipeline performance — auto-refreshes every 10 seconds
          </p>
        </div>
        {lastUpdated && (
          <div className="flex items-center gap-1.5 text-xs text-gray-400">
            <RefreshCw className="h-3.5 w-3.5" />
            Updated {lastUpdated}
          </div>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {/* Error state */}
      {isError && !isLoading && (
        <Card>
          <div className="py-12 text-center">
            <AlertTriangle className="mx-auto h-10 w-10 text-amber-400" />
            <p className="mt-3 text-sm font-medium text-gray-700">
              Unable to load SLA metrics
            </p>
            <p className="mt-1 text-xs text-gray-400">
              Check your connection and refresh.
            </p>
          </div>
        </Card>
      )}

      {data && (
        <>
          {/* SLA breach alert banner */}
          {data.sla_breach_count_24h > 0 && (
            <div className="mb-6 flex items-center gap-3 rounded-lg bg-amber-50 px-4 py-3 ring-1 ring-amber-200">
              <AlertTriangle className="h-5 w-5 flex-shrink-0 text-amber-500" />
              <p className="text-sm font-medium text-amber-700">
                {data.sla_breach_count_24h} SLA breach{data.sla_breach_count_24h !== 1 ? "es" : ""} in the last 24 hours.
                Review the queue to resolve pending items.
              </p>
            </div>
          )}

          {/* Pre-publish pipeline section */}
          <section aria-labelledby="pre-publish-heading" className="mb-8">
            <h2 id="pre-publish-heading" className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Pre-publish pipeline — under 13 (target: &lt;2 s)
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                title="P50 latency"
                value={formatMs(data.pre_publish_p50_ms)}
                label="Median processing time"
                warn={data.pre_publish_p50_ms > PRE_PUBLISH_SLA_MS}
                icon={<Clock className="h-5 w-5" />}
              />
              <MetricCard
                title="P95 latency"
                value={formatMs(data.pre_publish_p95_ms)}
                label="95th-percentile processing time"
                warn={data.pre_publish_p95_ms > PRE_PUBLISH_SLA_MS}
                icon={<Clock className="h-5 w-5" />}
              />
              <MetricCard
                title="Queue depth"
                value={String(data.queue_depth)}
                label="Pending items in queue"
                warn={data.queue_depth > 50}
                icon={<Inbox className="h-5 w-5" />}
              />
              <MetricCard
                title="Oldest pending"
                value={formatAge(data.oldest_pending_age_seconds)}
                label="Age of oldest pending item"
                warn={data.oldest_pending_age_seconds > PRE_PUBLISH_SLA_MS / 1_000}
                icon={<Clock className="h-5 w-5" />}
              />
            </div>
          </section>

          {/* Post-publish pipeline section */}
          <section aria-labelledby="post-publish-heading" className="mb-8">
            <h2 id="post-publish-heading" className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Post-publish pipeline — ages 13-15 (target: &lt;60 s)
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                title="P50 latency"
                value={formatMs(data.post_publish_p50_ms)}
                label="Median takedown time"
                warn={data.post_publish_p50_ms > POST_PUBLISH_SLA_MS}
                icon={<Clock className="h-5 w-5" />}
              />
              <MetricCard
                title="P95 latency"
                value={formatMs(data.post_publish_p95_ms)}
                label="95th-percentile takedown time"
                warn={data.post_publish_p95_ms > POST_PUBLISH_SLA_MS}
                icon={<Clock className="h-5 w-5" />}
              />
              <MetricCard
                title="SLA breaches (24h)"
                value={String(data.sla_breach_count_24h)}
                label="Items that exceeded SLA target"
                warn={data.sla_breach_count_24h > 0}
                icon={<AlertTriangle className="h-5 w-5" />}
              />
              <MetricCard
                title="Total reviewed (24h)"
                value={String(data.total_reviewed_24h)}
                label="Decisions made in last 24 hours"
                icon={<CheckCircle className="h-5 w-5" />}
              />
            </div>
          </section>
        </>
      )}
    </div>
  );
}
