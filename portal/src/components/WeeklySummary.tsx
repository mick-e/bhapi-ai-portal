"use client";
import React from "react";
import { useRouter } from "next/navigation";
import { useDashboardSummary } from "@/hooks/use-dashboard";

interface SummaryCardProps {
  label: string;
  value: string | number;
  sub?: string;
  onClick?: () => void;
}

function SummaryCard({ label, value, sub, onClick }: SummaryCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex flex-1 flex-col rounded-xl bg-white p-4 text-left shadow-sm ring-1 ring-gray-100 transition hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:cursor-default"
      disabled={!onClick}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
    </button>
  );
}

/**
 * Three-card weekly summary: AI Sessions, Risk Events, AI Spend.
 * Links to /analytics for details.
 */
export function WeeklySummary() {
  const router = useRouter();
  const { data, isLoading } = useDashboardSummary();

  if (isLoading || !data) {
    return (
      <div className="flex gap-3">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-20 flex-1 animate-pulse rounded-xl bg-gray-100"
          />
        ))}
      </div>
    );
  }

  const sessions = data.interactions_today ?? 0;
  const riskEvents = data.risk_summary.total_events_today ?? 0;
  const spendToday = data.spend_summary.today_usd ?? 0;
  const spendFormatted =
    spendToday < 0.01 ? "—" : `$${spendToday.toFixed(2)}`;

  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold text-gray-700">This Week</h2>
      <div className="flex gap-3">
        <SummaryCard
          label="AI Sessions"
          value={sessions}
          sub="today"
          onClick={() => router.push("/activity")}
        />
        <SummaryCard
          label="Risk Events"
          value={riskEvents}
          sub={
            data.risk_summary.trend === "increasing"
              ? "trending up"
              : data.risk_summary.trend === "decreasing"
              ? "trending down"
              : "stable"
          }
          onClick={() => router.push("/risk")}
        />
        <SummaryCard
          label="AI Spend"
          value={spendFormatted}
          sub="today"
          onClick={() => router.push("/analytics")}
        />
      </div>
    </div>
  );
}
