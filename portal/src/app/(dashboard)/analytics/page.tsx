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
  Users,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useTranslations } from "@/contexts/LocaleContext";
import { useAuth } from "@/hooks/use-auth";
import {
  useAnomalies,
  useMemberBaselines,
  usePeerComparison,
  useTrends,
  useUsagePatterns,
} from "@/hooks/use-analytics";

function TrendIcon({ direction }: { direction: string }) {
  if (direction === "up") return <TrendingUp className="h-5 w-5 text-red-500" />;
  if (direction === "down") return <TrendingDown className="h-5 w-5 text-green-500" />;
  return <Minus className="h-5 w-5 text-gray-400" />;
}

function usageLevelColor(level: string): string {
  switch (level) {
    case "very_high":
      return "bg-red-500";
    case "high":
      return "bg-amber-500";
    case "moderate":
      return "bg-primary-500";
    default:
      return "bg-gray-400";
  }
}

function useUsageLevelLabel() {
  const t = useTranslations("analytics");
  return (level: string): string => {
    switch (level) {
      case "very_high":
        return t("levelVeryHigh");
      case "high":
        return t("levelHigh");
      case "moderate":
        return t("levelModerate");
      default:
        return t("levelLow");
    }
  };
}

export default function AnalyticsPage() {
  const t = useTranslations("analytics");
  const usageLevelLabel = useUsageLevelLabel();
  const { user } = useAuth();
  const groupId = user?.group_id || null;
  const [days, setDays] = useState(7);
  const [tab, setTab] = useState<"overview" | "peer">("overview");

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

  const {
    data: anomalyData,
    isLoading: anomaliesLoading,
  } = useAnomalies(groupId);

  const {
    data: peerData,
    isLoading: peerLoading,
  } = usePeerComparison(groupId, days);

  const isLoading = trendsLoading || usageLoading || baselinesLoading || anomaliesLoading || peerLoading;

  if (!groupId) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <BarChart3 className="h-10 w-10 text-gray-300" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          {t("noGroupTitle")}
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {t("noGroupDescription")}
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">{t("loading")}</span>
      </div>
    );
  }

  if (trendsError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          {t("errorTitle")}
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(trendsErr as Error)?.message || t("errorFallback")}
        </p>
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={() => refetchTrends()}
        >
          <RefreshCw className="h-4 w-4" />
          {t("tryAgain")}
        </Button>
      </div>
    );
  }

  const anomalies = anomalyData?.anomalies ?? [];

  return (
    <div>
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {t("subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg border border-gray-300">
            <button
              onClick={() => setTab("overview")}
              className={`px-3 py-2 text-sm font-medium rounded-l-lg ${
                tab === "overview"
                  ? "bg-primary-50 text-primary-700 border-primary"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              {t("overview")}
            </button>
            <button
              onClick={() => setTab("peer")}
              className={`px-3 py-2 text-sm font-medium rounded-r-lg border-l border-gray-300 ${
                tab === "peer"
                  ? "bg-primary-50 text-primary-700 border-primary"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              {t("peerComparison")}
            </button>
          </div>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            aria-label={t("timePeriod")}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value={7}>{t("last7Days")}</option>
            <option value={14}>{t("last14Days")}</option>
            <option value={30}>{t("last30Days")}</option>
          </select>
        </div>
      </div>

      {/* Anomaly Alerts */}
      {anomalies.length > 0 && (
        <div className="mb-6 space-y-3">
          {anomalies.map((anomaly) => (
            <div
              key={anomaly.member_id}
              className={`flex items-start gap-3 rounded-lg border p-4 ${
                anomaly.severity === "critical"
                  ? "border-red-200 bg-red-50"
                  : "border-amber-200 bg-amber-50"
              }`}
            >
              <AlertTriangle
                className={`mt-0.5 h-5 w-5 flex-shrink-0 ${
                  anomaly.severity === "critical"
                    ? "text-red-600"
                    : "text-amber-600"
                }`}
              />
              <div className="flex-1">
                <p
                  className={`text-sm font-medium ${
                    anomaly.severity === "critical"
                      ? "text-red-900"
                      : "text-amber-900"
                  }`}
                >
                  {t("anomalyDetected").replace("{name}", anomaly.member_name)}
                </p>
                <p
                  className={`mt-1 text-sm ${
                    anomaly.severity === "critical"
                      ? "text-red-700"
                      : "text-amber-700"
                  }`}
                >
                  Recent average is {(anomaly.recent_daily_avg ?? 0).toFixed(1)} events/day
                  ({(anomaly.standard_deviations ?? 0).toFixed(1)} standard deviations{" "}
                  {anomaly.direction} baseline of{" "}
                  {(anomaly.baseline_daily_avg ?? 0).toFixed(1)} events/day)
                </p>
              </div>
              <span
                className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                  anomaly.severity === "critical"
                    ? "bg-red-100 text-red-700"
                    : "bg-amber-100 text-amber-700"
                }`}
              >
                {anomaly.severity}
              </span>
            </div>
          ))}
        </div>
      )}

      {tab === "overview" && (
        <>
          {/* Trend Cards */}
          {trends?.activity && trends?.risk_events && (() => {
            // Backend returns data_points array — compute averages from them
            const activityPoints = trends.activity.data_points ?? [];
            const riskPoints = trends.risk_events.data_points ?? [];
            const activityTotal = activityPoints.reduce((s, p) => s + p.value, 0);
            const riskTotal = riskPoints.reduce((s, p) => s + p.value, 0);
            const activityAvg = activityPoints.length > 0 ? activityTotal / activityPoints.length : 0;

            return (
            <div className="mb-6 grid gap-4 sm:grid-cols-2">
              <Card>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
                      <Activity className="h-5 w-5 text-primary-600" />
                    </div>
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase">
                        {t("activityTrend")}
                      </p>
                      <p className="text-lg font-bold text-gray-900">
                        {activityAvg.toFixed(1)}
                        <span className="ml-1 text-sm font-normal text-gray-400">
                          {t("avgPerDay")}
                        </span>
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <TrendIcon direction={trends.activity.direction ?? "stable"} />
                    <span className="text-xs text-gray-500 capitalize">
                      {trends.activity.direction ?? "stable"}
                    </span>
                  </div>
                </div>
                <p className="mt-2 text-xs text-gray-400">
                  {t("daysOfDataTotal")
                    .replace("{days}", String(activityPoints.length))
                    .replace("{total}", String(activityTotal))}
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
                        {t("riskEvents")}
                      </p>
                      <p className="text-lg font-bold text-gray-900">
                        {riskTotal}
                        <span className="ml-1 text-sm font-normal text-gray-400">
                          {t("events")}
                        </span>
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <TrendIcon direction={trends.risk_events.direction ?? "stable"} />
                    <span className="text-xs text-gray-500 capitalize">
                      {trends.risk_events.direction ?? "stable"}
                    </span>
                  </div>
                </div>
                <p className="mt-2 text-xs text-gray-400">
                  {t("daysOfData").replace("{days}", String(riskPoints.length))}
                </p>
              </Card>
            </div>
            );
          })()}

          {/* Usage by Platform */}
          {usage?.by_platform && (() => {
            const totalEvents = Object.values(usage.by_platform).reduce((s, v) => s + v, 0);
            return (
            <Card
              title={t("usageByPlatform")}
              description={t("totalEventsPeriod").replace("{total}", String(totalEvents))}
              className="mb-6"
            >
              {Object.keys(usage.by_platform).length === 0 ? (
                <p className="text-sm text-gray-500">{t("noPlatformData")}</p>
              ) : (
                <div className="space-y-3">
                  {Object.entries(usage.by_platform)
                    .sort(([, a], [, b]) => b - a)
                    .map(([platform, count]) => {
                      const percentage =
                        totalEvents > 0
                          ? (count / totalEvents) * 100
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
            );
          })()}

          {/* Member Baselines */}
          <Card
            title={t("memberBaselines")}
            description={t("memberBaselinesDescription")}
          >
            {(!baselines || baselines.length === 0) ? (
              <div className="py-8 text-center">
                <BarChart3 className="mx-auto h-10 w-10 text-gray-300" />
                <p className="mt-3 text-sm text-gray-500">
                  {t("noBaselineData")}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="px-4 py-3 text-left font-medium text-gray-500">
                        {t("member")}
                      </th>
                      <th className="px-4 py-3 text-left font-medium text-gray-500">
                        {t("primaryPlatform")}
                      </th>
                      <th className="px-4 py-3 text-right font-medium text-gray-500">
                        {t("totalEvents")}
                      </th>
                      <th className="px-4 py-3 text-right font-medium text-gray-500">
                        {t("avgDaily")}
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
                          {member.primary_platform ?? t("none")}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-600">
                          {member.total_events ?? 0}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-600">
                          {(member.avg_daily_events ?? 0).toFixed(1)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}

      {tab === "peer" && (
        <Card
          title={t("peerComparison")}
          description={t("peerComparisonDescription")}
        >
          {(!peerData?.members || peerData.members.length === 0) ? (
            <div className="py-8 text-center">
              <Users className="mx-auto h-10 w-10 text-gray-300" />
              <p className="mt-3 text-sm text-gray-500">
                {t("noPeerData")}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {peerData.members.map((member) => (
                <div key={member.member_id}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-gray-900">
                      {member.member_name}
                    </span>
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          member.usage_level === "very_high"
                            ? "bg-red-100 text-red-700"
                            : member.usage_level === "high"
                              ? "bg-amber-100 text-amber-700"
                              : member.usage_level === "moderate"
                                ? "bg-primary-100 text-primary-700"
                                : "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {usageLevelLabel(member.usage_level)}
                      </span>
                      <span className="text-gray-500">
                        {t("eventCount").replace("{count}", String(member.event_count))}
                      </span>
                    </div>
                  </div>
                  <div className="mt-1.5 flex items-center gap-3">
                    <div className="h-2.5 flex-1 rounded-full bg-gray-100">
                      <div
                        className={`h-2.5 rounded-full ${usageLevelColor(member.usage_level)}`}
                        style={{ width: `${Math.min(member.percentile, 100)}%` }}
                      />
                    </div>
                    <span className="w-12 text-right text-xs font-medium text-gray-500">
                      {member.percentile.toFixed(0)}th
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
