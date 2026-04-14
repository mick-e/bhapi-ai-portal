"use client";
import React from "react";
import { useSafetyScore } from "@/hooks/use-safety-score";
import { SafetyScoreCard } from "@/components/SafetyScoreCard";
import { ActionsNeeded } from "@/components/ActionsNeeded";
import { WeeklySummary } from "@/components/WeeklySummary";
import { EmptyState } from "@/components/ui/EmptyState";
import { useTranslations } from "@/contexts/LocaleContext";

export default function DashboardPage() {
  const { data: score, isLoading } = useSafetyScore();
  const t = useTranslations("dashboard");

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
          title={t("welcomeEmpty")}
          message={t("welcomeEmptyMessage")}
          actionLabel={t("addChild")}
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
        <p className="text-sm font-medium text-blue-800">{t("whatWeMonitor")}</p>
        <p className="mt-1 text-xs text-blue-600">
          {t("whatWeMonitorDesc")}{" "}
          <a href="/settings/privacy" className="underline">{t("managePrivacy")}</a>
        </p>
      </div>
    </div>
  );
}
