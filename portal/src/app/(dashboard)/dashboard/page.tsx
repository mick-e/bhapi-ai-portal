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
    </div>
  );
}
