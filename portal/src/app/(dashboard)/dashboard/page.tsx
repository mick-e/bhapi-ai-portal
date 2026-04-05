"use client";
import React from "react";
import { useSafetyScore } from "@/hooks/use-safety-score";
import { SafetyScoreCard } from "@/components/SafetyScoreCard";
import { ActionsNeeded } from "@/components/ActionsNeeded";
import { WeeklySummary } from "@/components/WeeklySummary";
import { EmptyState } from "@/components/ui/EmptyState";

export default function DashboardPage() {
  const { data: score, isLoading } = useSafetyScore();

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <div className="h-24 animate-pulse rounded-xl bg-gray-100" />
        <div className="h-32 animate-pulse rounded-xl bg-gray-100" />
        <div className="h-24 animate-pulse rounded-xl bg-gray-100" />
      </div>
    );
  }

  if (!score || score.children_monitored === 0) {
    return (
      <div className="p-6">
        <EmptyState
          title="Welcome to Bhapi"
          message="Add your first child to start monitoring AI usage and keep your family safe."
          actionLabel="Add a child"
          onAction={() => (window.location.href = "/members")}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <SafetyScoreCard data={score} />
      <ActionsNeeded />
      <WeeklySummary />
      {/* Trust: What we collect */}
      <div className="rounded-lg bg-blue-50 px-4 py-3 ring-1 ring-blue-100">
        <p className="text-sm font-medium text-blue-800">What we monitor</p>
        <p className="mt-1 text-xs text-blue-600">
          AI conversation metadata (platforms, duration, risk signals). We never read message content unless flagged for safety.{" "}
          <a href="/settings/privacy" className="underline">Manage privacy settings</a>
        </p>
      </div>
    </div>
  );
}
