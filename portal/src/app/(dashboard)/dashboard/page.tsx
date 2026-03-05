"use client";

import { useState } from "react";
import {
  Users,
  Activity,
  AlertTriangle,
  CreditCard,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  Loader2,
  RefreshCw,
  Plus,
} from "lucide-react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useDashboardSummary } from "@/hooks/use-dashboard";
import { useAuth } from "@/hooks/use-auth";
import { groupsApi } from "@/lib/api-client";
import type { Alert, CaptureEvent } from "@/types";

function CreateGroupPrompt() {
  const { user } = useAuth();
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const groupType = user?.account_type || "family";

  async function handleCreate() {
    if (!name.trim()) {
      setError("Please enter a group name.");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await groupsApi.create({ name: name.trim(), type: groupType });
      // Reload the page to pick up the new group context
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create group.");
      setCreating(false);
    }
  }

  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="mx-auto w-full max-w-md rounded-xl bg-white p-8 shadow-sm ring-1 ring-gray-200">
        <div className="text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary-100">
            <Plus className="h-7 w-7 text-primary-600" />
          </div>
          <h2 className="mt-4 text-xl font-bold text-gray-900">
            Create your first group
          </h2>
          <p className="mt-2 text-sm text-gray-500">
            Set up your {groupType} group to start monitoring AI usage and keeping everyone safe.
          </p>
        </div>

        <div className="mt-6 space-y-4">
          {error && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">
              {error}
            </div>
          )}
          <div>
            <label htmlFor="group-name" className="block text-sm font-medium text-gray-700">
              Group name
            </label>
            <input
              id="group-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={groupType === "family" ? "The Smith Family" : groupType === "school" ? "Oakwood Academy" : "My Club"}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            />
          </div>
          <Button
            onClick={handleCreate}
            isLoading={creating}
            className="w-full"
          >
            Create {groupType.charAt(0).toUpperCase() + groupType.slice(1)} Group
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading, isError, error, refetch } = useDashboardSummary();

  // If user has no group, show onboarding
  const noGroup = !user?.group_id;

  if (isLoading && !noGroup) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading dashboard...</span>
      </div>
    );
  }

  // Show create group prompt if user has no group or if the error is about missing group
  if (noGroup || (isError && (error as Error)?.message?.includes("No group found"))) {
    return <CreateGroupPrompt />;
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load dashboard
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

  const summary = data!;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Overview of your group&apos;s AI activity and safety
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          title="Active Members"
          value={String(summary.active_members)}
          subtitle={`of ${summary.total_members} total`}
          icon={<Users className="h-5 w-5 text-primary" />}
          trend={{
            direction: "up",
            label: `${summary.total_members} registered`,
          }}
        />
        <SummaryCard
          title="AI Interactions"
          value={String(summary.interactions_today)}
          subtitle="today"
          icon={<Activity className="h-5 w-5 text-green-600" />}
          trend={{
            direction: "up",
            label: summary.interactions_trend || "tracking",
          }}
        />
        <SummaryCard
          title="Active Alerts"
          value={String(summary.alert_summary.unread_count)}
          subtitle={
            summary.alert_summary.critical_count > 0
              ? `${summary.alert_summary.critical_count} critical`
              : "none critical"
          }
          icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
          trend={{
            direction: summary.risk_summary.trend === "increasing" ? "up" : "down",
            label: `risk ${summary.risk_summary.trend}`,
          }}
        />
        <SummaryCard
          title="Spend Today"
          value={`$${summary.spend_summary.today_usd.toFixed(2)}`}
          subtitle={`$${summary.spend_summary.budget_usd.toFixed(0)} budget`}
          icon={<CreditCard className="h-5 w-5 text-accent" />}
          trend={{
            direction: "up",
            label: `${summary.spend_summary.budget_used_percentage.toFixed(1)}% of budget`,
          }}
        />
      </div>

      {/* Recent Activity and Alerts */}
      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Activity */}
        <Card
          title="Recent Activity"
          description="Latest AI interactions across your group"
          footer={
            <Link
              href="/activity"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary-700 hover:text-primary-800"
            >
              View all activity
              <ArrowRight className="h-4 w-4" />
            </Link>
          }
        >
          {summary.recent_activity.length === 0 ? (
            <div className="py-6 text-center">
              <Activity className="mx-auto h-8 w-8 text-gray-300" />
              <p className="mt-2 text-sm text-gray-500">No recent activity</p>
            </div>
          ) : (
            <div className="space-y-4">
              {summary.recent_activity.slice(0, 5).map((event) => (
                <ActivityItem key={event.id} event={event} />
              ))}
            </div>
          )}
        </Card>

        {/* Alert Summary */}
        <Card
          title="Alert Summary"
          description="Safety alerts requiring attention"
          footer={
            <Link
              href="/alerts"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary-700 hover:text-primary-800"
            >
              View all alerts
              <ArrowRight className="h-4 w-4" />
            </Link>
          }
        >
          {summary.alert_summary.recent.length === 0 ? (
            <div className="py-6 text-center">
              <AlertTriangle className="mx-auto h-8 w-8 text-gray-300" />
              <p className="mt-2 text-sm text-gray-500">No active alerts</p>
            </div>
          ) : (
            <div className="space-y-4">
              {summary.alert_summary.recent.slice(0, 3).map((alert) => (
                <AlertItem key={alert.id} alert={alert} />
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Spend Summary */}
      <div className="mt-6">
        <Card
          title="Spend Summary"
          description="API costs for the current billing period"
          footer={
            <Link
              href="/spend"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary-700 hover:text-primary-800"
            >
              View spend details
              <ArrowRight className="h-4 w-4" />
            </Link>
          }
        >
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            <div>
              <p className="text-sm text-gray-500">This month</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                ${summary.spend_summary.month_usd.toFixed(2)}
              </p>
              <p className="mt-1 text-xs text-gray-400">
                of ${summary.spend_summary.budget_usd.toFixed(2)} budget
              </p>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{
                    width: `${Math.min(summary.spend_summary.budget_used_percentage, 100)}%`,
                  }}
                />
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-500">Top provider</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                {summary.spend_summary.top_provider || "N/A"}
              </p>
              <p className="mt-1 text-xs text-gray-400">
                ${summary.spend_summary.top_provider_cost_usd.toFixed(2)} (
                {summary.spend_summary.top_provider_percentage.toFixed(0)}%)
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Top user</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">
                {summary.spend_summary.top_member || "N/A"}
              </p>
              <p className="mt-1 text-xs text-gray-400">
                ${summary.spend_summary.top_member_cost_usd.toFixed(2)} (
                {summary.spend_summary.top_member_percentage.toFixed(0)}%)
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function SummaryCard({
  title,
  value,
  subtitle,
  icon,
  trend,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
  trend: { direction: "up" | "down"; label: string };
}) {
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-500">{title}</span>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-50">
          {icon}
        </div>
      </div>
      <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
      <div className="mt-1 flex items-center gap-2">
        <span className="text-sm text-gray-400">{subtitle}</span>
      </div>
      <div className="mt-2 flex items-center gap-1">
        {trend.direction === "up" ? (
          <TrendingUp className="h-3.5 w-3.5 text-green-500" />
        ) : (
          <TrendingDown className="h-3.5 w-3.5 text-green-500" />
        )}
        <span className="text-xs text-gray-500">{trend.label}</span>
      </div>
    </div>
  );
}

function ActivityItem({ event }: { event: CaptureEvent }) {
  const riskColors = {
    low: "bg-green-100 text-green-700",
    medium: "bg-amber-100 text-amber-700",
    high: "bg-red-100 text-red-700",
    critical: "bg-red-200 text-red-800",
  };

  const timeLabel = formatRelativeTime(event.timestamp);

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary">
          {event.member_name.charAt(0)}
        </div>
        <div>
          <p className="text-sm font-medium text-gray-900">
            {event.member_name}
          </p>
          <p className="text-xs text-gray-500">
            {event.provider} / {event.model}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColors[event.risk_level]}`}
        >
          {event.risk_level}
        </span>
        <span className="text-xs text-gray-400">{timeLabel}</span>
      </div>
    </div>
  );
}

function AlertItem({ alert }: { alert: Alert }) {
  const severityStyles: Record<string, string> = {
    critical: "border-l-red-500 bg-red-50",
    error: "border-l-red-500 bg-red-50",
    warning: "border-l-amber-500 bg-amber-50",
    info: "border-l-blue-500 bg-blue-50",
  };

  const style = severityStyles[alert.severity] || severityStyles.info;
  const timeLabel = formatRelativeTime(alert.created_at);

  return (
    <div className={`rounded-r-lg border-l-4 p-3 ${style}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold text-gray-900">{alert.title}</p>
          <p className="mt-0.5 text-xs text-gray-600">{alert.message}</p>
        </div>
        <span className="flex-shrink-0 text-xs text-gray-400">{timeLabel}</span>
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
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
    return date.toLocaleDateString();
  } catch {
    return timestamp;
  }
}
