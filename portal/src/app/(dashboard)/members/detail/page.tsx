"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Activity,
  CreditCard,
  Clock,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Ban,
  ShieldCheck,
  Heart,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronDown,
  ChevronUp,
  Info,
  Timer,
  Moon,
  Monitor,
  Trophy,
  Award,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useMember } from "@/hooks/use-members";
import { useActivity } from "@/hooks/use-activity";
import { useRiskEvents } from "@/hooks/use-alerts";
import { useSpendRecords } from "@/hooks/use-spend";
import { useBlockCheck, useCreateBlockRule, useRevokeBlockRule } from "@/hooks/use-blocking";
import { useDependencyScore, useDependencyHistory } from "@/hooks/use-dependency";
import { useSummaries } from "@/hooks/use-summaries";
import { useTimeBudget, useUpdateTimeBudget, useTimeBudgetHistory } from "@/hooks/use-time-budget";
import { useBedtimeMode, useUpdateBedtime, useDeleteBedtime } from "@/hooks/use-time-budget";
import { useAuth } from "@/hooks/use-auth";
import { useDeviceSummary, useRewards } from "@/hooks/use-rewards";
import { apiFetch, integrationsApi } from "@/lib/api-client";
import { useToast } from "@/contexts/ToastContext";
import { useTranslations } from "@/contexts/LocaleContext";

export default function MemberDetailPage() {
  return (
    <Suspense fallback={<div className="flex h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /><span className="ml-3 text-sm text-gray-500">Loading member...</span></div>}>
      <MemberDetailContent />
    </Suspense>
  );
}

function MemberDetailContent() {
  const t = useTranslations("memberDetail");
  const searchParams = useSearchParams();
  const memberId = searchParams.get("id") || "";
  const { user } = useAuth();
  const { addToast } = useToast();
  const groupId = user?.group_id || "";

  const {
    data: member,
    isLoading,
    isError,
    error,
    refetch,
  } = useMember(memberId);

  const { data: activityData } = useActivity({
    member_id: memberId,
    page_size: 5,
  });

  const { data: riskData } = useRiskEvents({
    member_id: memberId,
    page_size: 5,
  });

  const { data: spendData } = useSpendRecords({
    member_id: memberId,
    page_size: 5,
  });

  const { data: safetyScore } = useQuery<{
    score: number;
    trend: string;
    top_categories: string[];
    risk_count_by_severity: Record<string, number>;
    member_id: string;
    group_id: string;
  }>({
    queryKey: ["safety-score", "member", memberId],
    queryFn: () =>
      apiFetch(`/api/v1/risk/score?member_id=${memberId}`),
    enabled: !!memberId,
    refetchInterval: 60_000,
  });

  const { data: blockStatus } = useBlockCheck(groupId || null, memberId);
  const createBlock = useCreateBlockRule();
  const revokeBlock = useRevokeBlockRule();
  const { data: dependencyData } = useDependencyScore(memberId);
  const { data: dependencyHistory } = useDependencyHistory(memberId);
  const { data: summariesData } = useSummaries({
    member_id: memberId,
    page_size: 5,
  });
  const { data: timeBudget } = useTimeBudget(groupId || null, memberId);
  const { data: usageHistory } = useTimeBudgetHistory(groupId || null, memberId);
  const updateTimeBudget = useUpdateTimeBudget();
  const { data: bedtimeConfig } = useBedtimeMode(groupId || null, memberId);
  const updateBedtime = useUpdateBedtime();
  const deleteBedtime = useDeleteBedtime();
  const { data: deviceSummary } = useDeviceSummary(memberId);
  const { data: rewards } = useRewards(memberId);
  const [ageVerifying, setAgeVerifying] = useState(false);
  const [depLearnMore, setDepLearnMore] = useState(false);
  const [editingBudget, setEditingBudget] = useState(false);
  const [weekdayMin, setWeekdayMin] = useState(60);
  const [weekendMin, setWeekendMin] = useState(120);
  const [bedStart, setBedStart] = useState(21);
  const [bedEnd, setBedEnd] = useState(7);

  if (!memberId) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">{t("noMemberSelected")}</p>
        <Link href="/members" className="mt-2 text-sm text-primary-700 hover:underline">
          {t("backToMembers")}
        </Link>
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
        <p className="mt-3 text-sm font-medium text-gray-900">{t("failedToLoad")}</p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || t("somethingWentWrong")}
        </p>
        <Button variant="secondary" size="sm" className="mt-4" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
          {t("tryAgain")}
        </Button>
      </div>
    );
  }

  if (!member) return null;

  const recentActivity = activityData?.items ?? [];
  const recentRisks = riskData?.items ?? [];
  const recentSpend = spendData?.items ?? [];
  const totalSpend = recentSpend.reduce((sum, r) => sum + r.cost_usd, 0);

  const riskColors: Record<string, string> = {
    low: "bg-green-100 text-green-700",
    medium: "bg-amber-100 text-amber-700",
    high: "bg-red-100 text-red-700",
    critical: "bg-red-200 text-red-800",
  };

  const statusColors: Record<string, string> = {
    active: "bg-green-100 text-green-700",
    invited: "bg-amber-100 text-amber-700",
    suspended: "bg-red-100 text-red-700",
  };

  return (
    <div>
      <Link
        href="/members"
        className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("backToMembers")}
      </Link>

      {/* Member header */}
      <div className="mb-8 flex items-center gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-100 text-lg font-bold text-primary">
          {member.display_name.charAt(0).toUpperCase()}
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{member.display_name}</h1>
          <div className="mt-1 flex items-center gap-3">
            <span className="text-sm text-gray-500">{member.email}</span>
            <span className="text-sm capitalize text-gray-500">{member.role}</span>
            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[member.status]}`}>
              {member.status}
            </span>
            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${riskColors[member.risk_level || "low"]}`}>
              {member.risk_level || "low"} {t("risk")}
            </span>
          </div>
        </div>
      </div>

      {/* Stats cards */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-4">
        <StatCard icon={<Activity className="h-5 w-5 text-primary" />} label={t("totalActivity")} value={String(activityData?.total ?? 0)} />
        <StatCard icon={<AlertTriangle className="h-5 w-5 text-amber-500" />} label={t("riskEvents")} value={String(riskData?.total ?? 0)} />
        <StatCard icon={<CreditCard className="h-5 w-5 text-accent" />} label={t("totalSpend")} value={`$${totalSpend.toFixed(2)}`} />
        <StatCard icon={<Clock className="h-5 w-5 text-gray-500" />} label={t("lastActive")} value={member.last_active ? formatRelativeTime(member.last_active) : t("never")} />
      </div>

      {/* Safety Score Gauge */}
      {safetyScore && (
        <div className="mb-8">
          <Card title={t("safetyScore")}>
            <div className="flex items-center gap-8">
              <CircularScoreGauge score={safetyScore.score} />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">{t("trend")}:</span>
                  <span className={`text-sm font-semibold ${
                    safetyScore.trend === "improving"
                      ? "text-green-600"
                      : safetyScore.trend === "declining"
                        ? "text-red-600"
                        : "text-gray-500"
                  }`}>
                    {safetyScore.trend.charAt(0).toUpperCase() + safetyScore.trend.slice(1)}
                  </span>
                </div>
                {safetyScore.top_categories.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-medium text-gray-500">{t("topRiskCategories")}</p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {safetyScore.top_categories.map((cat) => (
                        <span
                          key={cat}
                          className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600"
                        >
                          {cat.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <div className="mt-3 grid grid-cols-4 gap-2">
                  {(["critical", "high", "medium", "low"] as const).map((sev) => (
                    <div key={sev} className="text-center">
                      <p className="text-lg font-bold text-gray-900">
                        {safetyScore.risk_count_by_severity[sev] ?? 0}
                      </p>
                      <p className="text-xs capitalize text-gray-500">{sev}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Age Verification & Blocking Controls */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card title={t("ageVerification")}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">
                {member.date_of_birth ? `${t("dob")}: ${member.date_of_birth}` : t("dobNotVerified")}
              </p>
              {member.age_verified && (
                <p className="mt-1 flex items-center gap-1 text-xs text-green-600">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  {t("verified")}
                </p>
              )}
            </div>
            {!member.age_verified && (
              <Button
                size="sm"
                variant="secondary"
                isLoading={ageVerifying}
                onClick={async () => {
                  setAgeVerifying(true);
                  try {
                    await integrationsApi.startAgeVerification(groupId, memberId);
                    addToast(t("ageVerifStarted"), "success");
                  } catch {
                    addToast(t("failedStartVerif"), "error");
                  } finally {
                    setAgeVerifying(false);
                  }
                }}
              >
                <ShieldCheck className="h-4 w-4" />
                {t("verifyAge")}
              </Button>
            )}
          </div>
        </Card>

        <Card title={t("blockingControls")}>
          <div className="flex items-center justify-between">
            <div>
              {blockStatus?.blocked ? (
                <p className="flex items-center gap-1.5 text-sm font-medium text-red-600">
                  <Ban className="h-4 w-4" />
                  {t("aiAccessBlocked")} ({blockStatus.rules?.length || 0} {(blockStatus.rules?.length || 0) !== 1 ? t("activeRulesPlural") : t("activeRuleSingle")})
                </p>
              ) : (
                <p className="text-sm text-gray-600">{t("aiAccessAllowed")}</p>
              )}
            </div>
            {blockStatus?.blocked ? (
              <Button
                size="sm"
                variant="secondary"
                isLoading={revokeBlock.isPending}
                onClick={() => {
                  const rule = blockStatus.rules?.[0];
                  if (rule) {
                    revokeBlock.mutate(
                      { ruleId: rule.id, groupId },
                      {
                        onSuccess: () => addToast(t("blockRevoked"), "success"),
                        onError: () => addToast(t("failedRevoke"), "error"),
                      }
                    );
                  }
                }}
              >
                {t("unblock")}
              </Button>
            ) : (
              <Button
                size="sm"
                variant="secondary"
                isLoading={createBlock.isPending}
                onClick={() => {
                  createBlock.mutate(
                    { group_id: groupId, member_id: memberId, reason: "Manual block from member page" },
                    {
                      onSuccess: () => addToast(t("memberBlocked"), "success"),
                      onError: () => addToast(t("failedBlockMember"), "error"),
                    }
                  );
                }}
              >
                <Ban className="h-4 w-4" />
                {t("blockAccess")}
              </Button>
            )}
          </div>
        </Card>
      </div>

      {/* Emotional Dependency */}
      {dependencyData && dependencyData.score > 0 && (
        <div className="mb-8">
          <Card title="Emotional Dependency">
            <div className="flex items-start gap-8">
              <DependencyGauge score={dependencyData.score} />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">Trend:</span>
                  <span className={`inline-flex items-center gap-1 text-sm font-semibold ${
                    dependencyData.trend === "improving"
                      ? "text-green-600"
                      : dependencyData.trend === "worsening"
                        ? "text-red-600"
                        : "text-gray-500"
                  }`}>
                    {dependencyData.trend === "improving" && <TrendingDown className="h-4 w-4" />}
                    {dependencyData.trend === "worsening" && <TrendingUp className="h-4 w-4" />}
                    {dependencyData.trend === "stable" && <Minus className="h-4 w-4" />}
                    {dependencyData.trend.charAt(0).toUpperCase() + dependencyData.trend.slice(1)}
                  </span>
                </div>

                {dependencyData.risk_factors.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-medium text-gray-500">Risk factors</p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {dependencyData.risk_factors.map((factor, i) => (
                        <span
                          key={i}
                          className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700"
                        >
                          {factor}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {Object.keys(dependencyData.platform_breakdown).length > 0 && (
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {Object.entries(dependencyData.platform_breakdown).map(([platform, count]) => (
                      <div key={platform} className="text-center">
                        <p className="text-lg font-bold text-gray-900">{count}</p>
                        <p className="text-xs capitalize text-gray-500">{platform}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Weekly history sparkline */}
                {dependencyHistory && dependencyHistory.history.length > 1 && (
                  <div className="mt-4">
                    <p className="text-xs font-medium text-gray-500">Weekly trend</p>
                    <DependencySparkline history={dependencyHistory.history} />
                  </div>
                )}

                {/* Learn More expandable */}
                <button
                  onClick={() => setDepLearnMore(!depLearnMore)}
                  className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary-700 hover:text-primary-800"
                >
                  <Info className="h-4 w-4" />
                  {depLearnMore ? "Show less" : "Learn more"}
                  {depLearnMore ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                </button>
                {depLearnMore && (
                  <div className="mt-3 rounded-lg bg-gray-50 p-4 text-sm text-gray-600">
                    <p className="font-medium text-gray-800">What is emotional dependency?</p>
                    <p className="mt-1">
                      AI companion platforms can form strong emotional bonds with children.
                      While some interaction is normal, excessive reliance may indicate
                      your child is substituting AI relationships for real human connection.
                    </p>
                    <p className="mt-2 font-medium text-gray-800">What you can do</p>
                    <ul className="mt-1 list-inside list-disc space-y-1">
                      <li>Talk openly about the difference between AI and human friendships</li>
                      <li>Encourage in-person social activities and hobbies</li>
                      <li>Set healthy time limits for companion AI platforms</li>
                      <li>Monitor late-night usage patterns</li>
                      <li>Seek professional guidance if scores remain high</li>
                    </ul>
                    <p className="mt-3 italic text-gray-500">
                      {dependencyData.recommendation}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* AI Screen Time & Bedtime */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card title={t("aiScreenTime")}>
          <div className="flex items-center gap-4">
            <TimerGauge
              minutesUsed={timeBudget?.minutes_used ?? 0}
              budgetMinutes={timeBudget?.budget_minutes ?? 0}
            />
            <div className="flex-1">
              {timeBudget?.enabled ? (
                <>
                  <p className="text-sm text-gray-600">
                    {timeBudget.minutes_used} / {timeBudget.budget_minutes} {t("minToday")}
                  </p>
                  {timeBudget.exceeded && (
                    <p className="mt-1 text-xs font-medium text-red-600">{t("budgetExceeded")}</p>
                  )}
                  {timeBudget.warn && !timeBudget.exceeded && (
                    <p className="mt-1 text-xs font-medium text-amber-600">{t("approachingLimit")}</p>
                  )}
                  <p className="mt-1 text-xs text-gray-400">
                    {t("weekday")}: {timeBudget.weekday_minutes}m &middot; {t("weekend")}: {timeBudget.weekend_minutes}m
                  </p>
                </>
              ) : (
                <p className="text-sm text-gray-500">{t("noTimeBudget")}</p>
              )}
            </div>
          </div>

          {/* 7-day usage bar chart */}
          {usageHistory && usageHistory.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-xs font-medium text-gray-500">{t("last7Days")}</p>
              <div className="flex items-end gap-1" style={{ height: 60 }}>
                {[...usageHistory].reverse().map((day) => {
                  const maxMin = Math.max(...usageHistory.map((d) => d.budget_minutes || 60));
                  const pct = maxMin > 0 ? Math.min(100, (day.minutes_used / maxMin) * 100) : 0;
                  return (
                    <div
                      key={day.date}
                      className={`flex-1 rounded-t ${day.exceeded ? "bg-red-400" : "bg-primary"}`}
                      style={{ height: `${Math.max(4, pct)}%` }}
                      title={`${day.date}: ${day.minutes_used}/${day.budget_minutes} min`}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {/* Edit budget */}
          {editingBudget ? (
            <div className="mt-4 space-y-2">
              <div className="flex gap-2">
                <label className="text-xs text-gray-500">
                  {t("weekdayMin")}
                  <input
                    type="number"
                    min={0}
                    value={weekdayMin}
                    onChange={(e) => setWeekdayMin(Number(e.target.value))}
                    className="mt-0.5 block w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                </label>
                <label className="text-xs text-gray-500">
                  {t("weekendMin")}
                  <input
                    type="number"
                    min={0}
                    value={weekendMin}
                    onChange={(e) => setWeekendMin(Number(e.target.value))}
                    className="mt-0.5 block w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                </label>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  isLoading={updateTimeBudget.isPending}
                  onClick={() => {
                    updateTimeBudget.mutate(
                      {
                        groupId: groupId!,
                        memberId,
                        data: {
                          weekday_minutes: weekdayMin,
                          weekend_minutes: weekendMin,
                        },
                      },
                      {
                        onSuccess: () => {
                          addToast(t("screenTimeUpdated"), "success");
                          setEditingBudget(false);
                        },
                        onError: () => addToast(t("failedUpdate"), "error"),
                      }
                    );
                  }}
                >
                  {t("save")}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setEditingBudget(false)}>
                  {t("cancel")}
                </Button>
              </div>
            </div>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              className="mt-3"
              onClick={() => {
                setWeekdayMin(timeBudget?.weekday_minutes ?? 60);
                setWeekendMin(timeBudget?.weekend_minutes ?? 120);
                setEditingBudget(true);
              }}
            >
              <Timer className="h-4 w-4" />
              {timeBudget?.enabled ? t("editBudget") : t("setBudget")}
            </Button>
          )}
        </Card>

        <Card title={t("bedtimeMode")}>
          <div className="flex items-center gap-3">
            <Moon className="h-5 w-5 text-indigo-500" />
            <div className="flex-1">
              {bedtimeConfig?.enabled ? (
                <>
                  <p className="text-sm font-medium text-gray-700">
                    {t("active")}: {bedtimeConfig.start_hour}:00 &ndash; {bedtimeConfig.end_hour}:00
                  </p>
                  <p className="mt-0.5 text-xs text-gray-400">
                    {t("aiBlockedDuring")}
                  </p>
                </>
              ) : (
                <p className="text-sm text-gray-500">{t("bedtimeNotActive")}</p>
              )}
            </div>
          </div>

          <div className="mt-4 space-y-2">
            <div className="flex gap-2">
              <label className="text-xs text-gray-500">
                {t("startHour")}
                <select
                  value={bedStart}
                  onChange={(e) => setBedStart(Number(e.target.value))}
                  className="mt-0.5 block w-full rounded border border-gray-300 px-2 py-1 text-sm"
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>{i}:00</option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-gray-500">
                {t("endHour")}
                <select
                  value={bedEnd}
                  onChange={(e) => setBedEnd(Number(e.target.value))}
                  className="mt-0.5 block w-full rounded border border-gray-300 px-2 py-1 text-sm"
                >
                  {Array.from({ length: 24 }, (_, i) => (
                    <option key={i} value={i}>{i}:00</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                isLoading={updateBedtime.isPending}
                onClick={() => {
                  updateBedtime.mutate(
                    {
                      groupId: groupId!,
                      memberId,
                      data: { start_hour: bedStart, end_hour: bedEnd },
                    },
                    {
                      onSuccess: () => addToast(t("bedtimeUpdated"), "success"),
                      onError: () => addToast(t("failedSetBedtime"), "error"),
                    }
                  );
                }}
              >
                {bedtimeConfig?.enabled ? t("updateBedtime") : t("enableBedtime")}
              </Button>
              {bedtimeConfig?.enabled && (
                <Button
                  variant="ghost"
                  size="sm"
                  isLoading={deleteBedtime.isPending}
                  onClick={() => {
                    deleteBedtime.mutate(
                      { groupId: groupId!, memberId },
                      {
                        onSuccess: () => addToast(t("bedtimeDisabled"), "success"),
                        onError: () => addToast(t("failedDisable"), "error"),
                      }
                    );
                  }}
                >
                  {t("disable")}
                </Button>
              )}
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title={t("recentActivity")}>
          {recentActivity.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-500">{t("noActivityYet")}</p>
          ) : (
            <div className="space-y-3">
              {recentActivity.map((event) => (
                <div key={event.id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-900">{event.provider} / {event.model}</p>
                    <p className="text-xs text-gray-500 truncate max-w-[250px]">{event.prompt_preview}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColors[event.risk_level]}`}>{event.risk_level}</span>
                    <span className="text-xs text-gray-400">{formatRelativeTime(event.timestamp)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title={t("riskEvents")}>
          {recentRisks.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-500">{t("noRiskEvents")}</p>
          ) : (
            <div className="space-y-3">
              {recentRisks.map((risk) => (
                <div key={risk.id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{risk.category}</p>
                    <p className="text-xs text-gray-500 truncate max-w-[250px]">{risk.description}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColors[risk.severity]}`}>{risk.severity}</span>
                    {risk.acknowledged && <span className="text-xs text-green-600">{t("ack")}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Recent Summaries */}
      <div className="mt-6">
        <Card
          title={t("recentSummaries")}
          footer={
            <Link
              href={`/activity/summaries?member_id=${memberId}`}
              className="inline-flex items-center gap-1 text-sm font-medium text-primary-700 hover:text-primary-800"
            >
              {t("viewAllSummaries")}
            </Link>
          }
        >
          {(!summariesData || summariesData.items.length === 0) ? (
            <p className="py-4 text-center text-sm text-gray-500">{t("noSummariesYet")}</p>
          ) : (
            <div className="space-y-3">
              {summariesData.items.slice(0, 5).map((summary) => (
                <div
                  key={summary.id}
                  className={`rounded-lg p-3 ${summary.action_needed ? "border-l-4 border-l-amber-400 bg-amber-50" : "bg-gray-50"}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">{summary.platform}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        summary.emotional_tone === "positive" ? "bg-green-100 text-green-700" :
                        summary.emotional_tone === "concerned" ? "bg-amber-100 text-amber-700" :
                        summary.emotional_tone === "distressed" ? "bg-red-100 text-red-700" :
                        "bg-gray-100 text-gray-700"
                      }`}>
                        {summary.emotional_tone}
                      </span>
                    </div>
                    <span className="text-xs text-gray-400">{summary.date}</span>
                  </div>
                  <p className="mt-1 text-xs text-gray-600 line-clamp-2">{summary.summary_text}</p>
                  {summary.risk_flags.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {summary.risk_flags.map((flag, i) => (
                        <span key={i} className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-700">{flag}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="mt-6">
        <Card title={t("recentSpend")}>
          {recentSpend.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-500">{t("noSpendRecords")}</p>
          ) : (
            <div className="-mx-6 -my-4 overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">{t("colProvider")}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">{t("colModel")}</th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">{t("colTokens")}</th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">{t("colCost")}</th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">{t("colTime")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {recentSpend.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-600">{record.provider}</td>
                      <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-600">{record.model}</td>
                      <td className="whitespace-nowrap px-6 py-3 text-right text-sm text-gray-600">{record.token_count.toLocaleString()}</td>
                      <td className="whitespace-nowrap px-6 py-3 text-right text-sm font-medium text-gray-900">${record.cost_usd.toFixed(3)}</td>
                      <td className="whitespace-nowrap px-6 py-3 text-right text-xs text-gray-400">{formatRelativeTime(record.timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      {/* Devices Section (F12) */}
      <div className="mt-6">
        <Card title={t("devices")}>
          {!deviceSummary ? (
            <p className="py-4 text-center text-sm text-gray-500">{t("noDeviceData")}</p>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <Monitor className="h-5 w-5 text-gray-500" />
                  <div>
                    <p className="text-xs text-gray-500">{t("totalTime")}</p>
                    <p className="text-lg font-bold text-gray-900">{deviceSummary.total_minutes} min</p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-500">{t("sessions")}</p>
                  <p className="text-lg font-bold text-gray-900">{deviceSummary.session_count}</p>
                </div>
              </div>

              {deviceSummary.device_breakdown.length > 0 && (
                <div>
                  <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">{t("byDevice")}</h4>
                  <div className="space-y-2">
                    {deviceSummary.device_breakdown.map((dev) => (
                      <div key={dev.device_id} className="flex items-center justify-between rounded-lg border border-gray-100 p-3">
                        <div className="flex items-center gap-2">
                          <Monitor className="h-4 w-4 text-gray-400" />
                          <span className="text-sm text-gray-700">{dev.device_name}</span>
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                          <span className="text-gray-500">{dev.minutes} min</span>
                          <span className="text-gray-400">{dev.sessions} {t("sessionsLower")}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {deviceSummary.platform_breakdown.length > 0 && (
                <div>
                  <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">{t("byPlatform")}</h4>
                  <div className="flex flex-wrap gap-2">
                    {deviceSummary.platform_breakdown.map((plat) => (
                      <div key={plat.platform} className="rounded-lg bg-gray-50 px-3 py-2">
                        <p className="text-sm font-medium text-gray-700 capitalize">{plat.platform}</p>
                        <p className="text-xs text-gray-500">{plat.minutes} min / {plat.sessions} {t("sessionsLower")}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Rewards Section (F14) */}
      <div className="mt-6">
        <Card title={t("rewards")}>
          {!rewards || rewards.length === 0 ? (
            <div className="py-6 text-center">
              <Trophy className="mx-auto h-10 w-10 text-gray-300" />
              <p className="mt-2 text-sm text-gray-500">{t("noRewardsYet")}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {rewards.map((reward) => (
                <div key={reward.id} className="flex items-center justify-between rounded-lg border border-gray-100 p-3">
                  <div className="flex items-center gap-3">
                    <div className={`flex h-9 w-9 items-center justify-center rounded-full ${
                      reward.reward_type === "badge" ? "bg-amber-100" : "bg-green-100"
                    }`}>
                      {reward.reward_type === "badge" ? (
                        <Award className="h-4 w-4 text-amber-600" />
                      ) : (
                        <Clock className="h-4 w-4 text-green-600" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{reward.trigger_description}</p>
                      <p className="text-xs text-gray-500">
                        {reward.reward_type === "extra_time"
                          ? `+${reward.value} ${t("minutesExtra")}`
                          : `${t("badgeTier")} ${reward.value}`}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-400">
                      {new Date(reward.earned_at).toLocaleDateString()}
                    </p>
                    {reward.redeemed && (
                      <span className="text-xs text-gray-400">{t("redeemed")}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function CircularScoreGauge({ score }: { score: number }) {
  const radius = 50;
  const stroke = 8;
  const normalizedRadius = radius - stroke / 2;
  const circumference = 2 * Math.PI * normalizedRadius;
  const progress = Math.max(0, Math.min(100, score));
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  const color =
    score >= 80 ? "#16a34a" : score >= 50 ? "#d97706" : "#dc2626";
  const bgLabel =
    score >= 80 ? "Safe" : score >= 50 ? "Caution" : "At Risk";

  return (
    <div className="relative flex flex-shrink-0 flex-col items-center">
      <svg width={radius * 2} height={radius * 2}>
        <circle
          cx={radius}
          cy={radius}
          r={normalizedRadius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={stroke}
        />
        <circle
          cx={radius}
          cy={radius}
          r={normalizedRadius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          transform={`rotate(-90 ${radius} ${radius})`}
          style={{ transition: "stroke-dashoffset 0.5s ease" }}
        />
        <text
          x={radius}
          y={radius - 6}
          textAnchor="middle"
          dominantBaseline="central"
          className="text-2xl font-bold"
          fill={color}
        >
          {score.toFixed(0)}
        </text>
        <text
          x={radius}
          y={radius + 14}
          textAnchor="middle"
          dominantBaseline="central"
          className="text-xs"
          fill="#6b7280"
        >
          {bgLabel}
        </text>
      </svg>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-50">{icon}</div>
        <div>
          <p className="text-xs text-gray-500">{label}</p>
          <p className="text-lg font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}

function TimerGauge({ minutesUsed, budgetMinutes }: { minutesUsed: number; budgetMinutes: number }) {
  const radius = 36;
  const stroke = 6;
  const normalizedRadius = radius - stroke / 2;
  const circumference = 2 * Math.PI * normalizedRadius;
  const pct = budgetMinutes > 0 ? Math.min(100, (minutesUsed / budgetMinutes) * 100) : 0;
  const offset = circumference - (pct / 100) * circumference;
  const color = pct >= 100 ? "#dc2626" : pct >= 75 ? "#d97706" : "#0d9488";

  return (
    <div className="flex flex-shrink-0 flex-col items-center">
      <svg width={radius * 2} height={radius * 2}>
        <circle cx={radius} cy={radius} r={normalizedRadius} fill="none" stroke="#e5e7eb" strokeWidth={stroke} />
        <circle
          cx={radius} cy={radius} r={normalizedRadius} fill="none"
          stroke={color} strokeWidth={stroke}
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${radius} ${radius})`}
          style={{ transition: "stroke-dashoffset 0.5s ease" }}
        />
        <text x={radius} y={radius - 4} textAnchor="middle" dominantBaseline="central" className="text-sm font-bold" fill={color}>
          {Math.round(pct)}%
        </text>
        <text x={radius} y={radius + 10} textAnchor="middle" dominantBaseline="central" className="text-[9px]" fill="#6b7280">
          used
        </text>
      </svg>
    </div>
  );
}

function DependencyGauge({ score }: { score: number }) {
  const radius = 50;
  const stroke = 8;
  const normalizedRadius = radius - stroke / 2;
  const circumference = 2 * Math.PI * normalizedRadius;
  const progress = Math.max(0, Math.min(100, score));
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  // Green 0-40, Amber 41-60, Red 61-100
  const color =
    score <= 40 ? "#16a34a" : score <= 60 ? "#d97706" : "#dc2626";
  const label =
    score <= 40 ? "Low" : score <= 60 ? "Moderate" : "High";

  return (
    <div className="relative flex flex-shrink-0 flex-col items-center">
      <svg width={radius * 2} height={radius * 2}>
        <circle
          cx={radius}
          cy={radius}
          r={normalizedRadius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={stroke}
        />
        <circle
          cx={radius}
          cy={radius}
          r={normalizedRadius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          transform={`rotate(-90 ${radius} ${radius})`}
          style={{ transition: "stroke-dashoffset 0.5s ease" }}
        />
        <text
          x={radius}
          y={radius - 6}
          textAnchor="middle"
          dominantBaseline="central"
          className="text-2xl font-bold"
          fill={color}
        >
          {score}
        </text>
        <text
          x={radius}
          y={radius + 14}
          textAnchor="middle"
          dominantBaseline="central"
          className="text-xs"
          fill="#6b7280"
        >
          {label}
        </text>
      </svg>
      <div className="mt-1 flex items-center gap-1 text-xs text-gray-400">
        <Heart className="h-3 w-3" />
        Dependency
      </div>
    </div>
  );
}

function DependencySparkline({ history }: { history: { week_start: string; week_end: string; score: number }[] }) {
  if (history.length < 2) return null;

  const maxScore = Math.max(...history.map((h) => h.score), 100);
  const width = 200;
  const height = 40;
  const padding = 4;
  const drawWidth = width - padding * 2;
  const drawHeight = height - padding * 2;

  const points = history.map((h, i) => {
    const x = padding + (i / (history.length - 1)) * drawWidth;
    const y = padding + drawHeight - (h.score / maxScore) * drawHeight;
    return `${x},${y}`;
  });

  return (
    <svg width={width} height={height} className="mt-1">
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke="#d97706"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {history.map((h, i) => {
        const x = padding + (i / (history.length - 1)) * drawWidth;
        const y = padding + drawHeight - (h.score / maxScore) * drawHeight;
        return (
          <circle key={i} cx={x} cy={y} r={2} fill="#d97706" />
        );
      })}
    </svg>
  );
}

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
