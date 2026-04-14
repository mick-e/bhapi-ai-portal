"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  Shield,
  Clock,
  BookOpen,
  Trophy,
  AlertCircle,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Star,
  Award,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useTranslations } from "@/contexts/LocaleContext";
import { useChildDashboard } from "@/hooks/use-privacy";

export default function MyDashboardPage() {
  return (
    <Suspense
      fallback={<MyDashboardLoading />}
    >
      <MyDashboardContent />
    </Suspense>
  );
}

function MyDashboardLoading() {
  const t = useTranslations("myDashboard");
  return (
    <div className="flex h-64 items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <span className="ml-3 text-sm text-gray-500">{t("loading")}</span>
    </div>
  );
}

function MyDashboardContent() {
  const t = useTranslations("myDashboard");
  const searchParams = useSearchParams();
  const memberId = searchParams.get("id") || "";

  const {
    data: dashboard,
    isLoading,
    isError,
    error,
    refetch,
  } = useChildDashboard(memberId);

  if (!memberId) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">{t("noMemberIdTitle")}</p>
        <p className="mt-1 text-sm text-gray-500">
          {t("noMemberIdDescription")}
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

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          {t("errorTitle")}
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || t("errorFallback")}
        </p>
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={() => refetch()}
        >
          <RefreshCw className="h-4 w-4" />
          {t("tryAgain")}
        </Button>
      </div>
    );
  }

  if (!dashboard) return null;

  const sections = dashboard.sections || [];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
        <p className="mt-1 text-sm text-gray-500">
          {t("subtitle")}
        </p>
      </div>

      {/* Stats Overview */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {sections.includes("safety_score") && dashboard.safety_score !== undefined && (
          <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-50">
                <Shield className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">{t("safetyScore")}</p>
                <p className="text-lg font-bold text-gray-900">{dashboard.safety_score}</p>
              </div>
            </div>
            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className={`h-full rounded-full transition-all ${
                  dashboard.safety_score >= 80
                    ? "bg-green-500"
                    : dashboard.safety_score >= 50
                      ? "bg-amber-500"
                      : "bg-red-500"
                }`}
                style={{ width: `${Math.min(100, dashboard.safety_score)}%` }}
              />
            </div>
          </div>
        )}

        {sections.includes("time_usage") && dashboard.sessions_today !== undefined && (
          <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50">
                <Clock className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">{t("sessionsToday")}</p>
                <p className="text-lg font-bold text-gray-900">
                  {dashboard.sessions_today}
                </p>
              </div>
            </div>
          </div>
        )}

        {sections.includes("rewards") && dashboard.rewards && (
          <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50">
                <Trophy className="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">{t("rewardsEarned")}</p>
                <p className="text-lg font-bold text-gray-900">
                  {dashboard.rewards.items.length}
                </p>
              </div>
            </div>
          </div>
        )}

        {sections.includes("rewards") && dashboard.rewards && (
          <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-50">
                <Clock className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-xs text-gray-500">{t("extraTimeEarned")}</p>
                <p className="text-lg font-bold text-gray-900">
                  {t("minutes").replace("{min}", String(dashboard.rewards.extra_time_minutes))}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Literacy Progress */}
        {sections.includes("literacy") && dashboard.literacy && (
          <Card title={t("literacyTitle")}>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-primary" />
                  <span className="text-sm font-medium text-gray-700">
                    {t("level")}: {dashboard.literacy.current_level}
                  </span>
                </div>
                <span className="rounded-full bg-primary-50 px-3 py-1 text-xs font-semibold text-primary">
                  {t("modulesCompleted").replace("{count}", String(dashboard.literacy.modules_completed))}
                </span>
              </div>
              <div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>{t("score")}</span>
                  <span>{dashboard.literacy.total_score.toFixed(0)}%</span>
                </div>
                <div className="mt-1 h-2.5 w-full overflow-hidden rounded-full bg-gray-100">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{
                      width: `${Math.min(100, dashboard.literacy.total_score)}%`,
                    }}
                  />
                </div>
              </div>
              <p className="text-sm text-gray-500">
                {t("literacyHint")}
              </p>
            </div>
          </Card>
        )}

        {/* My Rewards */}
        {sections.includes("rewards") && dashboard.rewards && (
          <Card title={t("myRewards")}>
            {dashboard.rewards.items.length === 0 ? (
              <div className="py-6 text-center">
                <Trophy className="mx-auto h-10 w-10 text-gray-300" />
                <p className="mt-2 text-sm text-gray-500">
                  {t("noRewards")}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {dashboard.rewards.items.map((reward) => (
                  <div
                    key={reward.id}
                    className="flex items-center justify-between rounded-lg border border-gray-100 p-3"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex h-8 w-8 items-center justify-center rounded-full ${
                          reward.reward_type === "badge"
                            ? "bg-amber-100"
                            : "bg-green-100"
                        }`}
                      >
                        {reward.reward_type === "badge" ? (
                          <Award className="h-4 w-4 text-amber-600" />
                        ) : (
                          <Clock className="h-4 w-4 text-green-600" />
                        )}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {reward.trigger_description}
                        </p>
                        <p className="text-xs text-gray-500">
                          {reward.reward_type === "extra_time"
                            ? t("plusMinutes").replace("{value}", String(reward.value))
                            : t("badgeEarned")}
                        </p>
                      </div>
                    </div>
                    {reward.redeemed && (
                      <span className="text-xs text-gray-400">{t("used")}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}
      </div>

      {/* I Need Help Button */}
      <div className="mt-8 flex justify-center">
        <button
          onClick={() => {
            if (typeof window !== "undefined") {
              window.alert(t("needHelpAlert"));
            }
          }}
          className="flex items-center gap-2 rounded-xl border-2 border-red-200 bg-red-50 px-6 py-3 text-sm font-semibold text-red-700 transition-colors hover:bg-red-100"
        >
          <AlertCircle className="h-5 w-5" />
          {t("needHelp")}
        </button>
      </div>
    </div>
  );
}
