"use client";

import { useState } from "react";
import {
  Bell,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  ShieldAlert,
  MessageCircle,
  ChevronDown,
  ChevronUp,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Tabs } from "@/components/ui/Tabs";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { OnboardingCard } from "@/components/ui/OnboardingCard";
import {
  useAlerts,
  useMarkAlertActioned,
  useMarkAllAlertsRead,
  useSnoozeAlert,
} from "@/hooks/use-alerts";
import { usePanicReports, useRespondToPanic, useQuickResponses } from "@/hooks/use-panic";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/contexts/ToastContext";
import { useTranslations } from "@/contexts/LocaleContext";
import type { Alert, AlertSeverity, PanicReport } from "@/types";

// ─── Calm language maps ────────────────────────────────────────────────────

const CALM_MESSAGES: Record<string, (memberName: string) => string> = {
  risk: (name) => `Something needs your attention regarding ${name}`,
  spend: (name) => `${name}'s AI usage changed significantly this week`,
  member: (name) => `${name} may need your attention`,
  system: (name) => `Something needs your attention regarding ${name}`,
};

const SUGGESTED_ACTIONS: Record<string, string> = {
  risk: "Review the details and talk with your child",
  spend: "Check in about their AI usage habits",
  member: "Have a calm conversation about what happened",
  system: "Review the details and take action if needed",
};

const SEVERITY_BADGE_VARIANT: Record<AlertSeverity, "error" | "warning" | "info" | "neutral"> = {
  critical: "error",
  error: "error",
  warning: "warning",
  info: "info",
};

const SEVERITY_LABEL: Record<AlertSeverity, string> = {
  critical: "Urgent",
  error: "Important",
  warning: "Heads up",
  info: "Note",
};

// ─── Page ──────────────────────────────────────────────────────────────────

export default function AlertsPage() {
  const t = useTranslations("alerts");
  const { user } = useAuth();
  const groupId = user?.group_id || null;
  const [activeTab, setActiveTab] = useState<"active" | "handled">("active");

  const {
    data: alertsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useAlerts({ page_size: 100 });

  const { addToast } = useToast();
  const markActionedMutation = useMarkAlertActioned();
  const markAllReadMutation = useMarkAllAlertsRead();
  const snoozeMutation = useSnoozeAlert();

  const allAlerts = alertsData?.items ?? [];
  const activeAlerts = allAlerts.filter((a) => !a.actioned);
  const handledAlerts = allAlerts.filter((a) => a.actioned);
  const displayedAlerts = activeTab === "active" ? activeAlerts : handledAlerts;

  // Group by member_name
  const grouped = displayedAlerts.reduce<Record<string, Alert[]>>((acc, alert) => {
    const key = alert.member_name || "General";
    if (!acc[key]) acc[key] = [];
    acc[key].push(alert);
    return acc;
  }, {});

  function handleMarkAllRead() {
    markAllReadMutation.mutate(undefined, {
      onSuccess: () => addToast("All alerts marked as read", "success"),
      onError: (err) => addToast((err as Error).message || "Failed to mark alerts read", "error"),
    });
  }

  function handleAcknowledge(alertId: string) {
    markActionedMutation.mutate(alertId, {
      onSuccess: () => addToast("Marked as handled", "success"),
      onError: (err) => addToast((err as Error).message || "Failed to handle alert", "error"),
    });
  }

  function handleSnooze(alertId: string) {
    snoozeMutation.mutate(
      { alertId, hours: 24 },
      {
        onSuccess: () => addToast("Alert snoozed for 24 hours", "success"),
        onError: (err) => addToast((err as Error).message || "Failed to snooze alert", "error"),
      }
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

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
          <p className="mt-1 text-sm text-gray-500">{t("thingsNeedAttention")}</p>
        </div>
        {activeAlerts.filter((a) => !a.read).length > 0 && (
          <Button
            variant="secondary"
            size="sm"
            onClick={handleMarkAllRead}
            isLoading={markAllReadMutation.isPending}
          >
            <CheckCircle2 className="h-4 w-4" />
            {t("markAllRead")}
          </Button>
        )}
      </div>

      <OnboardingCard
        id="alerts-intro"
        icon={Bell}
        title="Your Safety Inbox"
        description="Alerts appear here when we detect something that needs your attention. We group them by child and suggest actions — no jargon, just clear next steps."
      />

      {/* Tabs */}
      <Tabs
        tabs={[
          { key: "active", label: t("tabActive"), count: activeAlerts.length },
          { key: "handled", label: t("tabHandled"), count: handledAlerts.length },
        ]}
        active={activeTab}
        onChange={(key) => setActiveTab(key as "active" | "handled")}
        className="mb-6"
      />

      {/* Content */}
      {displayedAlerts.length === 0 ? (
        activeTab === "active" ? (
          <EmptyState
            icon={<Bell className="h-12 w-12" />}
            title={t("allClear")}
            message={t("allClearMessage")}
          />
        ) : (
          <EmptyState
            icon={<CheckCircle2 className="h-12 w-12" />}
            title={t("noHandledYet")}
            message={t("noHandledYetMessage")}
          />
        )
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([memberName, memberAlerts]) => (
            <ChildAlertGroup
              key={memberName}
              memberName={memberName}
              alerts={memberAlerts}
              onAcknowledge={handleAcknowledge}
              onSnooze={handleSnooze}
              isHandled={activeTab === "handled"}
              markActionedVariables={markActionedMutation.variables}
              isMarkingActioned={markActionedMutation.isPending}
              isSnoozePending={snoozeMutation.isPending}
              snoozeVariables={snoozeMutation.variables}
            />
          ))}
        </div>
      )}

      {/* Panic Reports Section */}
      <PanicReportsSection groupId={groupId} />
    </div>
  );
}

// ─── Child Alert Group ────────────────────────────────────────────────────

function ChildAlertGroup({
  memberName,
  alerts,
  onAcknowledge,
  onSnooze,
  isHandled,
  markActionedVariables,
  isMarkingActioned,
  isSnoozePending,
  snoozeVariables,
}: {
  memberName: string;
  alerts: Alert[];
  onAcknowledge: (id: string) => void;
  onSnooze: (id: string) => void;
  isHandled: boolean;
  markActionedVariables?: string;
  isMarkingActioned: boolean;
  isSnoozePending: boolean;
  snoozeVariables?: { alertId: string; hours: number };
}) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
      {/* Group header */}
      <button
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
            <User className="h-4 w-4 text-primary" />
          </div>
          <span className="text-sm font-semibold text-gray-900">{memberName}</span>
          <Badge variant={isHandled ? "success" : "warning"}>
            {alerts.length} {alerts.length === 1 ? "alert" : "alerts"}
          </Badge>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        )}
      </button>

      {/* Alert list */}
      {expanded && (
        <div className="divide-y divide-gray-100 border-t border-gray-100">
          {alerts.map((alert) => (
            <CalmAlertRow
              key={alert.id}
              alert={alert}
              memberName={memberName}
              onAcknowledge={onAcknowledge}
              onSnooze={onSnooze}
              isHandled={isHandled}
              isAcknowledging={isMarkingActioned && markActionedVariables === alert.id}
              isSnoozingThis={isSnoozePending && snoozeVariables?.alertId === alert.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Calm Alert Row ────────────────────────────────────────────────────────

function CalmAlertRow({
  alert,
  memberName,
  onAcknowledge,
  onSnooze,
  isHandled,
  isAcknowledging,
  isSnoozingThis,
}: {
  alert: Alert;
  memberName: string;
  onAcknowledge: (id: string) => void;
  onSnooze: (id: string) => void;
  isHandled: boolean;
  isAcknowledging: boolean;
  isSnoozingThis: boolean;
}) {
  const calmMessage =
    (CALM_MESSAGES[alert.type] ?? CALM_MESSAGES.system)(memberName);
  const suggestion =
    SUGGESTED_ACTIONS[alert.type] ?? SUGGESTED_ACTIONS.system;
  const badgeVariant = SEVERITY_BADGE_VARIANT[alert.severity] ?? "neutral";
  const severityLabel = SEVERITY_LABEL[alert.severity] ?? alert.severity;
  const timeLabel = formatRelativeTime(alert.created_at);
  const isSnoozed = alert.snoozed_until && new Date(alert.snoozed_until) > new Date();

  return (
    <div className={`px-4 py-4 ${isSnoozed ? "opacity-60" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={badgeVariant}>{severityLabel}</Badge>
            {isSnoozed && <Badge variant="neutral">Snoozed</Badge>}
            {!alert.read && (
              <span className="inline-block h-2 w-2 rounded-full bg-primary" aria-label="Unread" />
            )}
          </div>
          <p className="mt-1.5 text-sm font-medium text-gray-900">{calmMessage}</p>
          <p className="mt-0.5 text-xs text-gray-500">{suggestion}</p>
        </div>
        <span className="flex-shrink-0 text-xs text-gray-400">{timeLabel}</span>
      </div>

      {/* Action buttons */}
      {!isHandled && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => onAcknowledge(alert.id)}
            isLoading={isAcknowledging}
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            Mark as handled
          </Button>
          {!isSnoozed && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onSnooze(alert.id)}
              isLoading={isSnoozingThis}
            >
              Snooze 24h
            </Button>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              const params = new URLSearchParams({
                id: alert.id,
                child: alert.member_name || '',
              });
              window.location.href = `/activity?${params.toString()}`;
            }}
          >
            View details
          </Button>
        </div>
      )}

      {isHandled && (
        <div className="mt-2 flex items-center gap-1 text-xs text-green-600">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Handled
        </div>
      )}
    </div>
  );
}

// ─── Panic Reports Section ─────────────────────────────────────────────────

function PanicReportsSection({ groupId }: { groupId: string | null }) {
  const { data: panicData } = usePanicReports(groupId);
  const { data: quickResponseData } = useQuickResponses();
  const respondMutation = useRespondToPanic();
  const { addToast } = useToast();

  const reports = panicData?.items ?? [];
  const quickResponses = quickResponseData?.responses ?? [];

  if (reports.length === 0) return null;

  function handleRespond(reportId: string, response: string) {
    if (!groupId) return;
    respondMutation.mutate(
      { reportId, response, groupId },
      {
        onSuccess: () => addToast("Response sent", "success"),
        onError: (err) => addToast((err as Error).message || "Failed to respond", "error"),
      }
    );
  }

  return (
    <div className="mt-8">
      <div className="mb-4 flex items-center gap-2">
        <ShieldAlert className="h-5 w-5 text-red-600" />
        <h2 className="text-lg font-bold text-gray-900">Panic Reports</h2>
        <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700">
          {reports.filter((r: PanicReport) => !r.resolved).length} unresolved
        </span>
      </div>

      <div className="space-y-3">
        {reports.map((report: PanicReport) => (
          <div
            key={report.id}
            className={`rounded-xl border-l-4 p-4 shadow-sm ring-1 ring-gray-200 ${
              report.resolved
                ? "border-l-gray-300 bg-white"
                : "border-l-red-600 bg-red-50"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <ShieldAlert
                    className={`h-4 w-4 ${
                      report.resolved ? "text-gray-400" : "text-red-600"
                    }`}
                  />
                  <span className="text-sm font-semibold text-gray-900">
                    {report.category
                      .replace(/_/g, " ")
                      .replace(/\b\w/g, (c: string) => c.toUpperCase())}
                  </span>
                  {report.platform && (
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {report.platform}
                    </span>
                  )}
                  {report.resolved && (
                    <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                      Resolved
                    </span>
                  )}
                </div>
                {report.message && (
                  <p className="mt-1 text-sm text-gray-600">{report.message}</p>
                )}
                {report.parent_response && (
                  <div className="mt-2 flex items-start gap-1.5">
                    <MessageCircle className="mt-0.5 h-3.5 w-3.5 text-teal-500" />
                    <p className="text-xs text-teal-700">Parent: {report.parent_response}</p>
                  </div>
                )}
              </div>
              <span className="flex-shrink-0 text-xs text-gray-400">
                {formatRelativeTime(report.created_at)}
              </span>
            </div>

            {!report.resolved && (
              <div className="mt-3 flex flex-wrap gap-2">
                {quickResponses.map((response: string) => (
                  <Button
                    key={response}
                    variant="secondary"
                    size="sm"
                    isLoading={
                      respondMutation.isPending &&
                      respondMutation.variables?.reportId === report.id
                    }
                    onClick={() => handleRespond(report.id, response)}
                  >
                    {response}
                  </Button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
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
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
    return date.toLocaleDateString();
  } catch {
    return timestamp;
  }
}
