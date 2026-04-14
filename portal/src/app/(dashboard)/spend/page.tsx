"use client";

import { useState } from "react";
import {
  CreditCard,
  TrendingUp,
  DollarSign,
  Users,
  AlertTriangle,
  Loader2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Settings2,
  X,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useSpendSummary, useSpendRecords, useCreateBudgetThreshold } from "@/hooks/use-spend";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/contexts/ToastContext";
import { useTranslations } from "@/contexts/LocaleContext";
import type { SpendRecord } from "@/types";

export default function SpendPage() {
  const t = useTranslations("spend");
  const [period, setPeriod] = useState<"day" | "week" | "month">("month");
  const [recordsPage, setRecordsPage] = useState(1);
  const [showBudgetModal, setShowBudgetModal] = useState(false);
  const recordsPageSize = 20;

  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
    error: summaryErr,
    refetch: refetchSummary,
  } = useSpendSummary(period);

  const {
    data: recordsData,
    isLoading: recordsLoading,
  } = useSpendRecords({ page: recordsPage, page_size: recordsPageSize });

  const records = recordsData?.items ?? [];
  const recordsTotalPages = recordsData?.total_pages ?? 1;
  const recordsTotal = recordsData?.total ?? 0;

  if (summaryLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">{t("loading")}</span>
      </div>
    );
  }

  if (summaryError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          {t("failedToLoad")}
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(summaryErr as Error)?.message || t("somethingWentWrong")}
        </p>
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={() => refetchSummary()}
        >
          <RefreshCw className="h-4 w-4" />
          {t("tryAgain")}
        </Button>
      </div>
    );
  }

  const s = summary!;

  return (
    <div>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {t("description")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={period}
            onChange={(e) =>
              setPeriod(e.target.value as "day" | "week" | "month")
            }
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="day">{t("periodToday")}</option>
            <option value="week">{t("periodThisWeek")}</option>
            <option value="month">{t("periodThisMonth")}</option>
          </select>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowBudgetModal(true)}
          >
            <Settings2 className="h-4 w-4" />
            {t("setBudget")}
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={period === "day" ? "Today" : period === "week" ? "This Week" : "This Month"}
          value={`$${s.total_cost_usd.toFixed(2)}`}
          subtitle={`of $${s.budget_usd.toFixed(2)} budget`}
          icon={<DollarSign className="h-5 w-5 text-primary" />}
        />
        <StatCard
          label="Daily Average"
          value={`$${s.avg_daily_cost_usd.toFixed(2)}`}
          subtitle="per day"
          icon={<TrendingUp className="h-5 w-5 text-green-600" />}
        />
        <StatCard
          label="Active Spenders"
          value={String(s.active_spenders)}
          subtitle={`of ${s.total_members} members`}
          icon={<Users className="h-5 w-5 text-accent" />}
        />
        <StatCard
          label="Over Budget"
          value={String(s.over_budget_count)}
          subtitle={s.over_budget_count === 1 ? "member exceeded limit" : "members exceeded limit"}
          icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
        />
      </div>

      {/* Budget Progress */}
      <Card
        title="Budget Progress"
        description={s.period_label || `Current ${period} period`}
      >
        <div className="space-y-6">
          <div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Group Total</span>
              <span className="font-medium text-gray-900">
                ${s.total_cost_usd.toFixed(2)} / ${s.budget_usd.toFixed(2)}
              </span>
            </div>
            <div className="mt-2 h-3 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className={`h-full rounded-full transition-all ${
                  s.budget_used_percentage >= 100
                    ? "bg-red-500"
                    : s.budget_used_percentage >= 80
                      ? "bg-amber-500"
                      : "bg-primary"
                }`}
                style={{ width: `${Math.min(s.budget_used_percentage, 100)}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-gray-400">
              {s.budget_used_percentage.toFixed(1)}% used, $
              {s.budget_remaining_usd.toFixed(2)} remaining
            </p>
          </div>
        </div>
      </Card>

      {/* Provider & Member Breakdown */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="By Provider">
          {s.provider_breakdown.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-500">
              No provider data yet
            </p>
          ) : (
            <div className="space-y-4">
              {s.provider_breakdown.map((p) => (
                <ProviderRow
                  key={p.provider}
                  name={p.provider}
                  amount={p.cost_usd}
                  percentage={p.percentage}
                  requests={p.request_count}
                />
              ))}
            </div>
          )}
        </Card>

        <Card title="By Member">
          {s.member_breakdown.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-500">
              No member spend data yet
            </p>
          ) : (
            <div className="space-y-4">
              {s.member_breakdown.map((m) => (
                <MemberSpendRow
                  key={m.member_id}
                  name={m.member_name}
                  amount={m.cost_usd}
                  limit={m.limit_usd}
                />
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Spend Records Table */}
      <div className="mt-6">
        <Card title="Spend Records" description="Individual API usage entries">
          {recordsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : records.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-500">
              No spend records yet
            </p>
          ) : (
            <>
              <div className="-mx-6 -my-4 overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Member
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Provider
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        Model
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                        Tokens
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                        Cost
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                        Time
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {records.map((record) => (
                      <SpendRecordRow key={record.id} record={record} />
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Records Pagination */}
              {recordsTotalPages > 1 && (
                <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-4">
                  <p className="text-sm text-gray-500">
                    Showing {records.length} of {recordsTotal} records
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={recordsPage <= 1}
                      onClick={() =>
                        setRecordsPage((p) => Math.max(1, p - 1))
                      }
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-sm text-gray-600">
                      {recordsPage} / {recordsTotalPages}
                    </span>
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={recordsPage >= recordsTotalPages}
                      onClick={() => setRecordsPage((p) => p + 1)}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
      </div>

      {showBudgetModal && (
        <SetBudgetModal
          currentBudget={s.budget_usd}
          onClose={() => setShowBudgetModal(false)}
        />
      )}
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function SetBudgetModal({
  currentBudget,
  onClose,
}: {
  currentBudget: number;
  onClose: () => void;
}) {
  const { user } = useAuth();
  const { addToast } = useToast();
  const createThreshold = useCreateBudgetThreshold();
  const [amount, setAmount] = useState(currentBudget > 0 ? String(currentBudget) : "");
  const [thresholdType, setThresholdType] = useState<"soft" | "hard">("soft");
  const [notifyAt, setNotifyAt] = useState("50,80,100");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const parsedAmount = parseFloat(amount);
    if (!parsedAmount || parsedAmount <= 0) {
      addToast("Please enter a valid budget amount", "error");
      return;
    }

    const notifyValues = notifyAt
      .split(",")
      .map((v) => parseInt(v.trim()))
      .filter((v) => !isNaN(v) && v > 0 && v <= 100);

    createThreshold.mutate(
      {
        group_id: user!.group_id!,
        type: thresholdType,
        amount: parsedAmount,
        notify_at: notifyValues.length > 0 ? notifyValues : [50, 80, 100],
      },
      {
        onSuccess: () => {
          addToast("Budget threshold saved", "success");
          onClose();
        },
        onError: (err) =>
          addToast((err as Error).message || "Failed to save budget", "error"),
      }
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Set Budget Threshold</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label htmlFor="budget-amount" className="block text-sm font-medium text-gray-700">
              Monthly Budget (USD)
            </label>
            <div className="relative mt-1">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
              <input
                id="budget-amount"
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="100.00"
                className="block w-full rounded-lg border border-gray-300 py-2 pl-7 pr-3 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            </div>
          </div>

          <div>
            <label htmlFor="threshold-type" className="block text-sm font-medium text-gray-700">
              Threshold Type
            </label>
            <select
              id="threshold-type"
              value={thresholdType}
              onChange={(e) => setThresholdType(e.target.value as "soft" | "hard")}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value="soft">Soft limit (notify only)</option>
              <option value="hard">Hard limit (block usage)</option>
            </select>
          </div>

          <div>
            <label htmlFor="notify-at" className="block text-sm font-medium text-gray-700">
              Alert at percentages
            </label>
            <input
              id="notify-at"
              type="text"
              value={notifyAt}
              onChange={(e) => setNotifyAt(e.target.value)}
              placeholder="50,80,100"
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
            <p className="mt-1 text-xs text-gray-400">
              Comma-separated percentages (e.g. 50, 80, 100)
            </p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button variant="secondary" size="sm" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button size="sm" type="submit" isLoading={createThreshold.isPending}>
              Save Budget
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  subtitle,
  icon,
}: {
  label: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-500">{label}</span>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-50">
          {icon}
        </div>
      </div>
      <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
      <p className="mt-1 text-xs text-gray-400">{subtitle}</p>
    </div>
  );
}

function ProviderRow({
  name,
  amount,
  percentage,
  requests,
}: {
  name: string;
  amount: number;
  percentage: number;
  requests: number;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-gray-900">{name}</span>
        <span className="text-gray-600">
          ${amount.toFixed(2)} ({percentage.toFixed(0)}%)
        </span>
      </div>
      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-primary"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="mt-1 text-xs text-gray-400">
        {requests.toLocaleString()} requests
      </p>
    </div>
  );
}

function MemberSpendRow({
  name,
  amount,
  limit,
}: {
  name: string;
  amount: number;
  limit: number;
}) {
  const percentage = limit > 0 ? Math.round((amount / limit) * 100) : 0;
  const isOverBudget = percentage >= 100;

  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary">
            {name.charAt(0).toUpperCase()}
          </div>
          <span className="font-medium text-gray-900">{name}</span>
        </div>
        <span
          className={`text-sm ${
            isOverBudget ? "font-semibold text-red-600" : "text-gray-600"
          }`}
        >
          ${amount.toFixed(2)} / ${limit.toFixed(2)}
        </span>
      </div>
      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full transition-all ${
            isOverBudget
              ? "bg-red-500"
              : percentage >= 80
                ? "bg-amber-500"
                : "bg-primary"
          }`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}

function SpendRecordRow({ record }: { record: SpendRecord }) {
  const timeLabel = formatRelativeTime(record.timestamp);

  return (
    <tr className="hover:bg-gray-50">
      <td className="whitespace-nowrap px-6 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-[10px] font-semibold text-primary">
            {record.member_name.charAt(0).toUpperCase()}
          </div>
          <span className="text-sm text-gray-900">{record.member_name}</span>
        </div>
      </td>
      <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-600">
        {record.provider}
      </td>
      <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-600">
        {record.model}
      </td>
      <td className="whitespace-nowrap px-6 py-3 text-right text-sm text-gray-600">
        {record.token_count.toLocaleString()}
      </td>
      <td className="whitespace-nowrap px-6 py-3 text-right text-sm font-medium text-gray-900">
        ${record.cost_usd.toFixed(3)}
      </td>
      <td className="whitespace-nowrap px-6 py-3 text-right text-xs text-gray-400">
        {timeLabel}
      </td>
    </tr>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────────────

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
    if (diffHours < 24)
      return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    if (diffDays < 7)
      return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
    return date.toLocaleDateString();
  } catch {
    return timestamp;
  }
}
