"use client";
import React from "react";
import type { SafetyScore } from "@/hooks/use-safety-score";

function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 50) return "text-amber-600";
  return "text-red-600";
}

function scoreMessage(score: number, alerts: number): string {
  if (alerts === 0) return "Your family is safe — no alerts this week";
  if (alerts === 1) return "1 item needs your attention";
  return `${alerts} items need your attention`;
}

function scoreBg(score: number): string {
  if (score >= 80) return "bg-green-50 ring-green-200";
  if (score >= 50) return "bg-amber-50 ring-amber-200";
  return "bg-red-50 ring-red-200";
}

export function SafetyScoreCard({ data }: { data: SafetyScore }) {
  return (
    <div className={`rounded-xl p-6 ring-1 ${scoreBg(data.score)}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">Family Safety</p>
          <p className="mt-1 text-lg font-medium text-gray-900">
            {scoreMessage(data.score, data.active_alerts)}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {data.children_monitored}{" "}
            {data.children_monitored === 1 ? "child" : "children"} monitored
          </p>
        </div>
        <div className={`text-4xl font-bold ${scoreColor(data.score)}`}>
          {data.score}
        </div>
      </div>
    </div>
  );
}
