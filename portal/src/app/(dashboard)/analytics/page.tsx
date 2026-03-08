"use client";

import { useState } from "react";
import {
  BarChart3,
  Loader2,
  AlertTriangle,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus,
  Activity,
  ShieldAlert,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/use-auth";
import {
  useTrends,
  useUsagePatterns,
  useMemberBaselines,
} from "@/hooks/use-analytics";

function TrendIcon({ direction }: { direction: string }) {
  if (direction === "up") return <TrendingUp className="h-5 w-5 text-red-500" />;
  if (direction === "down") return <TrendingDown className="h-5 w-5 text-green-500" />;
  return <Minus className="h-5 w-5 text-gray-400" />;
}

export default function AnalyticsPage() {
  const { user } = useAuth();
  const groupId = user?.group_id || null;
  const [days, setDays] = useState(7);

  const {
    data: trends,
    isLoading: trendsLoading,
    isError: trendsError,
    error: trendsErr,
    refetch: refetchTrends,
  } = useTrends(groupId, days);

  const {
    data: usage,
    isLoading: usageLoading,
  } = useUsagePatterns(groupId, days);

  const {
    data: baselines,
    isLoading: baselinesLoading,
  } = useMemberBaselines(groupId);

  const isLoading = trendsLoading || usageLoading || baselinesLoading;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading analytics...</span>
      </div>
    );
  }

  if (trendsError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load analytics
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(trendsErr as Error)?.message || "Something went wrong"}
        </p>
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={() => refetchTrends()}
        >
          <RefreshCw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="mt-1 text-sm text-gray-500">
            Activity trends, usage patterns, and member baselines
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          aria-label="Time period"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
        </select>
      </div>

      {/* Trend Cards */}
      {trends && (
        <div className="mb-6 grid gap-4 sm:grid-cols-2">
          <Card>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
                  <Activity className="h-5 w-5 text-primary-600" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase">
                    Activity Trend
                  </p>
                  <p className="text-lg font-bold text-gray-900">
                    {trends.activity.current_avg.toFixed(1)}
                    <span className="ml-1 text-sm font-normal text-gray-400">
                      avg/day
                    </span>
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <TrendIcon direction={trends.activity.direction} />
                <span className="text-xs text-gray-500 capitalize">
                  {trends.activity.direction}
                </span>
              </div>
            </div>
            <p className="mt-2 text-xs text-gray-400">
              Previous period: {trends.activity.previous_avg.toFixed(1)} avg/day
            </p>
          </Card>

          <Card>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50">
                  <ShieldAlert className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase">
                    Risk Events
                  </p>
                  <p className="text-lg font-bold text-gray-900">
                    {trends.risk_events.current_count}
                    <span className="ml-1 text-sm font-normal text-gray-400">
                      events
                    </span>
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <TrendIcon direction={trends.risk_events.direction} />
                <span className="text-xs text-gray-500 capitalize">
                  {trends.risk_events.direction}
                </span>
              </div>
            </div>
            <p className="mt-2 text-xs text-gray-400">
              Previous period: {trends.risk_events.previous_count} events
            </p>
          </Card>
        </div>
      )}

      {/* Usage by Platform */}
      {usage && (
        <Card
          title="Usage by Platform"
          description={`${usage.total_events} total events in the selected period`}
          className="mb-6"
        >
          {Object.keys(usage.by_platform).length === 0 ? (
            <p className="text-sm text-gray-500">No platform data available</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(usage.by_platform)
                .sort(([, a], [, b]) => b - a)
                .map(([platform, count]) => {
                  const percentage =
                    usage.total_events > 0
                      ? (count / usage.total_events) * 100
                      : 0;
                  return (
                    <div key={platform}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-gray-700 capitalize">
                          {platform}
                        </span>
                        <span className="text-gray-500">
                          {count} ({percentage.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="mt-1 h-2 w-full rounded-full bg-gray-100">
                        <div
                          className="h-2 rounded-full bg-primary-500"
                          style={{ width: `${Math.min(percentage, 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </Card>
      )}

      {/* Member Baselines */}
      <Card
        title="Member Baselines"
        description="Average daily activity per member over the last 30 days"
      >
        {(!baselines || baselines.length === 0) ? (
          <div className="py-8 text-center">
            <BarChart3 className="mx-auto h-10 w-10 text-gray-300" />
            <p className="mt-3 text-sm text-gray-500">
              No member baseline data available
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-4 py-3 text-left font-medium text-gray-500">
                    Member
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">
                    Primary Platform
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">
                    Total Events
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">
                    Avg Daily
                  </th>
                </tr>
              </thead>
              <tbody>
                {baselines.map((member) => (
                  <tr
                    key={member.member_id}
                    className="border-b border-gray-50 last:border-0"
                  >
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {member.member_name}
                    </td>
                    <td className="px-4 py-3 text-gray-600 capitalize">
                      {member.primary_platform}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {member.total_events}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {member.avg_daily.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
