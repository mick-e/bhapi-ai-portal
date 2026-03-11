"use client";

import { Suspense, useState, useMemo } from "react";
import {
  BookOpen,
  Loader2,
  AlertTriangle,
  RefreshCw,
  GraduationCap,
  PenTool,
  HelpCircle,
  Clock,
  Lightbulb,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/use-auth";
import { useAcademicReport } from "@/hooks/use-academic";
import { useMemberBaselines } from "@/hooks/use-analytics";
import type { AcademicReport, DailyBreakdownItem } from "@/types";

type Period = "this_week" | "last_week" | "this_month";

function getDateRange(period: Period): { start: string; end: string } {
  const now = new Date();
  const today = now.toISOString().split("T")[0];

  if (period === "this_week") {
    const day = now.getDay();
    const diff = day === 0 ? 6 : day - 1; // Monday start
    const monday = new Date(now);
    monday.setDate(now.getDate() - diff);
    return { start: monday.toISOString().split("T")[0], end: today };
  }

  if (period === "last_week") {
    const day = now.getDay();
    const diff = day === 0 ? 6 : day - 1;
    const thisMonday = new Date(now);
    thisMonday.setDate(now.getDate() - diff);
    const lastSunday = new Date(thisMonday);
    lastSunday.setDate(thisMonday.getDate() - 1);
    const lastMonday = new Date(lastSunday);
    lastMonday.setDate(lastSunday.getDate() - 6);
    return {
      start: lastMonday.toISOString().split("T")[0],
      end: lastSunday.toISOString().split("T")[0],
    };
  }

  // this_month
  const firstOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  return { start: firstOfMonth.toISOString().split("T")[0], end: today };
}

function DonutChart({
  learning,
  doing,
  unclassified,
}: {
  learning: number;
  doing: number;
  unclassified: number;
}) {
  const total = learning + doing + unclassified;
  if (total === 0) {
    return (
      <div className="flex h-40 w-40 items-center justify-center rounded-full border-8 border-gray-200">
        <span className="text-sm text-gray-400">No data</span>
      </div>
    );
  }

  const learningPct = (learning / total) * 100;
  const doingPct = (doing / total) * 100;

  // CSS conic-gradient donut
  const gradient = `conic-gradient(
    #22c55e 0% ${learningPct}%,
    #f59e0b ${learningPct}% ${learningPct + doingPct}%,
    #d1d5db ${learningPct + doingPct}% 100%
  )`;

  return (
    <div className="relative flex items-center justify-center">
      <div
        className="h-40 w-40 rounded-full"
        style={{ background: gradient }}
      />
      <div className="absolute flex h-24 w-24 flex-col items-center justify-center rounded-full bg-white">
        <span className="text-xl font-bold text-gray-900">{total}</span>
        <span className="text-xs text-gray-500">sessions</span>
      </div>
    </div>
  );
}

function StackedBar({ items }: { items: DailyBreakdownItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-gray-400">No daily data available</p>;
  }

  const maxTotal = Math.max(
    ...items.map((d) => d.learning + d.doing + d.unclassified),
    1
  );

  return (
    <div className="space-y-2">
      {items.map((day) => {
        const total = day.learning + day.doing + day.unclassified;
        const pctL = total > 0 ? (day.learning / maxTotal) * 100 : 0;
        const pctD = total > 0 ? (day.doing / maxTotal) * 100 : 0;
        const pctU = total > 0 ? (day.unclassified / maxTotal) * 100 : 0;
        const label = day.date.slice(5); // MM-DD

        return (
          <div key={day.date} className="flex items-center gap-3">
            <span className="w-14 text-xs text-gray-500">{label}</span>
            <div className="flex h-5 flex-1 overflow-hidden rounded-full bg-gray-100">
              {pctL > 0 && (
                <div
                  className="bg-green-500"
                  style={{ width: `${pctL}%` }}
                  title={`Learning: ${day.learning}`}
                />
              )}
              {pctD > 0 && (
                <div
                  className="bg-amber-500"
                  style={{ width: `${pctD}%` }}
                  title={`Doing: ${day.doing}`}
                />
              )}
              {pctU > 0 && (
                <div
                  className="bg-gray-300"
                  style={{ width: `${pctU}%` }}
                  title={`Unclassified: ${day.unclassified}`}
                />
              )}
            </div>
            <span className="w-8 text-right text-xs text-gray-400">
              {total}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function AcademicDashboardContent() {
  const { user } = useAuth();
  const groupId = user?.group_id || null;
  const [period, setPeriod] = useState<Period>("this_week");
  const [selectedMember, setSelectedMember] = useState<string>("");

  const { data: baselines } = useMemberBaselines(groupId);

  const members = useMemo(() => baselines || [], [baselines]);

  // Auto-select first member
  const memberId = selectedMember || members[0]?.member_id || null;

  const { start, end } = getDateRange(period);

  const {
    data: report,
    isLoading,
    isError,
    error,
    refetch,
  } = useAcademicReport(groupId, memberId, start, end);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">
          Loading academic report...
        </span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load academic report
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
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Academic Integrity
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Understand how your child uses AI for learning vs. task completion
          </p>
        </div>
        <div className="flex items-center gap-3">
          {members.length > 0 && (
            <select
              value={memberId || ""}
              onChange={(e) => setSelectedMember(e.target.value)}
              aria-label="Select member"
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              {members.map((m) => (
                <option key={m.member_id} value={m.member_id}>
                  {m.member_name}
                </option>
              ))}
            </select>
          )}
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as Period)}
            aria-label="Time period"
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="this_week">This week</option>
            <option value="last_week">Last week</option>
            <option value="this_month">This month</option>
          </select>
        </div>
      </div>

      {!report || report.total_ai_sessions === 0 ? (
        <div className="py-12 text-center">
          <BookOpen className="mx-auto h-12 w-12 text-gray-300" />
          <p className="mt-4 text-sm text-gray-500">
            No AI sessions found for this period
          </p>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="mb-6 grid gap-4 sm:grid-cols-4">
            <Card>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
                  <BookOpen className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase">
                    Total Sessions
                  </p>
                  <p className="text-lg font-bold text-gray-900">
                    {report.total_ai_sessions}
                  </p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50">
                  <GraduationCap className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase">
                    Learning
                  </p>
                  <p className="text-lg font-bold text-green-700">
                    {report.learning_count}
                  </p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50">
                  <PenTool className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase">
                    Task Completion
                  </p>
                  <p className="text-lg font-bold text-amber-700">
                    {report.doing_count}
                  </p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50">
                  <Clock className="h-5 w-5 text-teal-600" />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase">
                    Study Hours
                  </p>
                  <p className="text-lg font-bold text-teal-700">
                    {report.study_hour_sessions}
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* Charts Row */}
          <div className="mb-6 grid gap-6 lg:grid-cols-2">
            {/* Donut Chart */}
            <Card
              title="Learning vs. Doing"
              description="How your child uses AI tools"
            >
              <div className="flex flex-col items-center gap-6 sm:flex-row">
                <DonutChart
                  learning={report.learning_count}
                  doing={report.doing_count}
                  unclassified={report.unclassified_count}
                />
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-full bg-green-500" />
                    <span className="text-sm text-gray-700">
                      Learning ({report.learning_count})
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-full bg-amber-500" />
                    <span className="text-sm text-gray-700">
                      Task Completion ({report.doing_count})
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded-full bg-gray-300" />
                    <span className="text-sm text-gray-700">
                      Unclassified ({report.unclassified_count})
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-medium text-gray-900">
                    Learning Ratio:{" "}
                    <span className="text-green-700">
                      {(report.learning_ratio * 100).toFixed(0)}%
                    </span>
                  </p>
                </div>
              </div>
            </Card>

            {/* Daily Breakdown */}
            <Card
              title="Daily Breakdown"
              description="Stacked view of daily AI usage"
            >
              <StackedBar items={report.daily_breakdown} />
            </Card>
          </div>

          {/* Recommendation */}
          {report.recommendation && (
            <Card className="border-l-4 border-l-primary-500">
              <div className="flex items-start gap-3">
                <Lightbulb className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary-600" />
                <div>
                  <p className="text-sm font-semibold text-gray-900">
                    Recommendation
                  </p>
                  <p className="mt-1 text-sm text-gray-600">
                    {report.recommendation}
                  </p>
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

export default function AcademicPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <AcademicDashboardContent />
    </Suspense>
  );
}
