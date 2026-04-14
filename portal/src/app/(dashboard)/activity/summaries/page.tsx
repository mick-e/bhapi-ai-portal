"use client";

import { useState } from "react";
import {
  MessageSquare,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useTranslations } from "@/contexts/LocaleContext";
import { useSummaries } from "@/hooks/use-summaries";
import { useAuth } from "@/hooks/use-auth";
import { apiFetch } from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";
import type { ConversationSummary, GroupMember, PaginatedResponse } from "@/types";
import Link from "next/link";

const TONE_COLORS: Record<string, string> = {
  neutral: "bg-gray-100 text-gray-700",
  positive: "bg-green-100 text-green-700",
  concerned: "bg-amber-100 text-amber-700",
  distressed: "bg-red-100 text-red-700",
};

const PLATFORM_LABELS: Record<string, string> = {
  chatgpt: "ChatGPT",
  gemini: "Gemini",
  copilot: "Copilot",
  claude: "Claude",
  grok: "Grok",
};

function SummaryCard({ summary }: { summary: ConversationSummary }) {
  const [expanded, setExpanded] = useState(false);
  const t = useTranslations("activitySummaries");

  return (
    <div
      className={`rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200 ${
        summary.action_needed ? "border-l-4 border-l-amber-400" : ""
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-100">
            <MessageSquare className="h-4 w-4 text-primary-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-gray-900">
                {PLATFORM_LABELS[summary.platform] || summary.platform}
              </span>
              <span
                className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                  TONE_COLORS[summary.emotional_tone] || TONE_COLORS.neutral
                }`}
              >
                {summary.emotional_tone}
              </span>
              {summary.action_needed && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                  <AlertTriangle className="h-3 w-3" />
                  {t("actionNeeded")}
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-gray-500">{summary.date}</p>
          </div>
        </div>
      </div>

      {/* Topics */}
      {summary.topics.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {summary.topics.map((topic, i) => (
            <span
              key={i}
              className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600"
            >
              {topic}
            </span>
          ))}
        </div>
      )}

      {/* Summary text */}
      <p className="mt-3 text-sm text-gray-700">{summary.summary_text}</p>

      {/* Risk flags */}
      {summary.risk_flags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {summary.risk_flags.map((flag, i) => (
            <span
              key={i}
              className="rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-700"
            >
              {flag}
            </span>
          ))}
        </div>
      )}

      {/* Action reason */}
      {summary.action_needed && summary.action_reason && (
        <div className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {summary.action_reason}
        </div>
      )}

      {/* Expandable quotes */}
      {summary.key_quotes.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="inline-flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-700"
          >
            {expanded ? (
              <>
                <ChevronUp className="h-3.5 w-3.5" />
                {t("hideQuotes")}
              </>
            ) : (
              <>
                <ChevronDown className="h-3.5 w-3.5" />
                {summary.key_quotes.length === 1
                  ? t("showQuoteOne")
                  : t("showQuotesMany").replace("{count}", String(summary.key_quotes.length))}
              </>
            )}
          </button>
          {expanded && (
            <div className="mt-2 space-y-2">
              {summary.key_quotes.map((quote, i) => (
                <blockquote
                  key={i}
                  className="border-l-2 border-gray-300 pl-3 text-sm italic text-gray-600"
                >
                  &ldquo;{quote}&rdquo;
                </blockquote>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SummariesPage() {
  const t = useTranslations("activitySummaries");
  const { user } = useAuth();
  const groupId = user?.group_id || "";

  const [selectedMember, setSelectedMember] = useState<string>("");
  const [dateFilter, setDateFilter] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [page, setPage] = useState(1);

  // Fetch members for filter dropdown
  const { data: membersData } = useQuery<PaginatedResponse<GroupMember>>({
    queryKey: ["members", groupId],
    queryFn: () =>
      apiFetch(`/api/v1/groups/${groupId}/members?page_size=100`),
    enabled: !!groupId,
  });

  const members = membersData?.items ?? [];

  // Auto-select first member if none selected
  const effectiveMemberId = selectedMember || members[0]?.id || "";

  const { data, isLoading, isError, error, refetch } = useSummaries({
    member_id: effectiveMemberId,
    start_date: dateFilter,
    end_date: dateFilter,
    page,
    page_size: 20,
  });

  const summaries = data?.items ?? [];
  const totalPages = data?.total_pages ?? 1;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {t("title")}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {t("subtitle")}
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-center gap-4">
        <div>
          <label
            htmlFor="date-filter"
            className="block text-xs font-medium text-gray-500"
          >
            {t("dateLabel")}
          </label>
          <input
            id="date-filter"
            type="date"
            value={dateFilter}
            onChange={(e) => {
              setDateFilter(e.target.value);
              setPage(1);
            }}
            className="mt-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>

        <div>
          <label
            htmlFor="member-filter"
            className="block text-xs font-medium text-gray-500"
          >
            {t("memberLabel")}
          </label>
          <select
            id="member-filter"
            value={selectedMember}
            onChange={(e) => {
              setSelectedMember(e.target.value);
              setPage(1);
            }}
            className="mt-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="">{t("allMembers")}</option>
            {members.map((m) => (
              <option key={m.id} value={m.id}>
                {m.display_name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-end">
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
            {t("refresh")}
          </Button>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex h-48 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-sm text-gray-500">
            {t("loading")}
          </span>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="flex h-48 flex-col items-center justify-center text-center">
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
      )}

      {/* Empty state */}
      {!isLoading && !isError && summaries.length === 0 && (
        <div className="flex h-48 flex-col items-center justify-center text-center">
          <MessageSquare className="h-10 w-10 text-gray-300" />
          <p className="mt-3 text-sm font-medium text-gray-900">
            {t("emptyTitle")}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {t("emptyDescription")}
          </p>
          <Link
            href="/settings"
            className="mt-3 text-sm font-medium text-primary-700 hover:text-primary-800"
          >
            {t("goToSettings")}
          </Link>
        </div>
      )}

      {/* Summary cards */}
      {!isLoading && !isError && summaries.length > 0 && (
        <>
          <div className="space-y-4">
            {summaries.map((summary) => (
              <SummaryCard key={summary.id} summary={summary} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-3">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                {t("previous")}
              </Button>
              <span className="text-sm text-gray-500">
                {t("pageOf").replace("{page}", String(page)).replace("{total}", String(totalPages))}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
              >
                {t("next")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
