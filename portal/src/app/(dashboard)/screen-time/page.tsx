"use client";

import React, { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Tabs } from "@/components/ui/Tabs";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import {
  Timer,
  Smartphone,
  CalendarClock,
  HandHelping,
  Plus,
  Loader2,
  Trash2,
  Check,
  X,
} from "lucide-react";
import { useTranslations } from "@/contexts/LocaleContext";
import {
  useScreenTimeUsage,
  useScreenTimeLimits,
  useScreenTimeSchedules,
  useExtensionRequests,
  useCreateLimit,
  useDeleteLimit,
  useDecideExtensionRequest,
} from "@/hooks/use-screen-time";

type TabKey = "usage" | "limits" | "schedules" | "requests";

export default function ScreenTimePage() {
  const t = useTranslations("screenTime");
  const [activeTab, setActiveTab] = useState<TabKey>("usage");
  const [createOpen, setCreateOpen] = useState(false);

  // Form state
  const [limitMemberId, setLimitMemberId] = useState("");
  const [limitApp, setLimitApp] = useState("");
  const [limitMinutes, setLimitMinutes] = useState("60");

  // Queries
  const usage = useScreenTimeUsage();
  const limits = useScreenTimeLimits();
  const schedules = useScreenTimeSchedules();
  const requests = useExtensionRequests();

  // Mutations
  const createLimit = useCreateLimit();
  const deleteLimit = useDeleteLimit();
  const decideRequest = useDecideExtensionRequest();

  const tabs = [
    { key: "usage", label: t("tabUsage") },
    { key: "limits", label: t("tabLimits") },
    { key: "schedules", label: t("tabSchedules") },
    { key: "requests", label: t("tabRequests"), count: (requests.data ?? []).filter((r) => r.status === "pending").length || undefined },
  ];

  function handleCreateLimit() {
    if (!limitMemberId || !limitMinutes) return;
    createLimit.mutate(
      {
        member_id: limitMemberId,
        app_name: limitApp || undefined,
        daily_minutes: parseInt(limitMinutes, 10),
      },
      {
        onSuccess: () => {
          setCreateOpen(false);
          setLimitMemberId("");
          setLimitApp("");
          setLimitMinutes("60");
        },
      }
    );
  }

  const dayNames = [t("daySun"), t("dayMon"), t("dayTue"), t("dayWed"), t("dayThu"), t("dayFri"), t("daySat")];

  // ─── Tab: Usage Overview ───────────────────────────────────────────────────

  function renderUsage() {
    if (usage.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = usage.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabUsage")}
          message={t("emptyUsage")}
          icon={<Smartphone className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="space-y-3">
        {items.map((app, idx) => {
          const pct = app.minutes_limit ? Math.min(100, (app.minutes_today / app.minutes_limit) * 100) : 0;
          const barColor = pct > 90 ? "bg-red-500" : pct > 70 ? "bg-amber-500" : "bg-teal-500";

          return (
            <Card key={`${app.member_id}-${app.app_name}-${idx}`}>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{app.app_name}</p>
                    <p className="text-xs text-gray-500">{app.member_name} &mdash; {app.category}</p>
                  </div>
                  <p className="text-sm font-semibold text-gray-700">
                    {app.minutes_today}m
                    {app.minutes_limit != null && <span className="font-normal text-gray-400"> / {app.minutes_limit}m</span>}
                  </p>
                </div>
                {app.minutes_limit != null && (
                  <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
                    <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    );
  }

  // ─── Tab: Limits ───────────────────────────────────────────────────────────

  function renderLimits() {
    if (limits.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = limits.data ?? [];

    return (
      <div className="space-y-4">
        <div className="flex justify-end">
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t("addLimit")}
          </Button>
        </div>

        {items.length === 0 ? (
          <Card>
            <EmptyState
              title={t("tabLimits")}
              message={t("emptyLimits")}
              icon={<Timer className="h-10 w-10" />}
              actionLabel={t("addLimit")}
              onAction={() => setCreateOpen(true)}
            />
          </Card>
        ) : (
          <div className="space-y-3">
            {items.map((limit) => (
              <Card key={limit.id}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">
                      {limit.app_name || limit.category || t("allApps")}
                    </p>
                    <p className="text-sm text-gray-500">{limit.daily_minutes} {t("minutesPerDay")}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={limit.active ? "success" : "neutral"}>
                      {limit.active ? t("active") : t("inactive")}
                    </Badge>
                    <Button variant="ghost" size="sm" onClick={() => deleteLimit.mutate(limit.id)}>
                      <Trash2 className="h-4 w-4 text-gray-400" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ─── Tab: Schedules ────────────────────────────────────────────────────────

  function renderSchedules() {
    if (schedules.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = schedules.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabSchedules")}
          message={t("emptySchedules")}
          icon={<CalendarClock className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="space-y-3">
        {items.map((sched) => (
          <Card key={sched.id}>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">{sched.label}</p>
                <p className="text-sm text-gray-500">
                  {sched.member_name} &mdash; {dayNames[sched.day_of_week]} {sched.start_time}&ndash;{sched.end_time}
                </p>
              </div>
              <Badge variant={sched.active ? "success" : "neutral"}>
                {sched.active ? t("active") : t("inactive")}
              </Badge>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  // ─── Tab: Extension Requests ───────────────────────────────────────────────

  function renderRequests() {
    if (requests.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = requests.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabRequests")}
          message={t("emptyRequests")}
          icon={<HandHelping className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="space-y-3">
        {items.map((req) => (
          <Card key={req.id}>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">{req.member_name}</p>
                <p className="text-sm text-gray-500">
                  +{req.requested_minutes} {t("minutes")} &mdash; {req.reason}
                </p>
                <p className="text-xs text-gray-400">
                  {new Date(req.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {req.status === "pending" ? (
                  <>
                    <Button
                      size="sm"
                      onClick={() => decideRequest.mutate({ requestId: req.id, decision: "approved" })}
                    >
                      <Check className="mr-1 h-3 w-3" />
                      {t("approve")}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => decideRequest.mutate({ requestId: req.id, decision: "denied" })}
                    >
                      <X className="mr-1 h-3 w-3" />
                      {t("deny")}
                    </Button>
                  </>
                ) : (
                  <Badge variant={req.status === "approved" ? "success" : "error"}>
                    {req.status === "approved" ? t("approved") : t("denied")}
                  </Badge>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  const tabContent: Record<TabKey, () => React.ReactNode> = {
    usage: renderUsage,
    limits: renderLimits,
    schedules: renderSchedules,
    requests: renderRequests,
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
        <p className="mt-1 text-sm text-gray-500">{t("subtitle")}</p>
      </div>

      <Tabs
        tabs={tabs}
        active={activeTab}
        onChange={(key) => setActiveTab(key as TabKey)}
        className="mb-6"
      />

      {tabContent[activeTab]()}

      {/* Create Limit Modal */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title={t("addLimit")}
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">{t("memberId")}</label>
            <Input value={limitMemberId} onChange={(e) => setLimitMemberId(e.target.value)} placeholder={t("memberIdPlaceholder")} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">{t("appName")}</label>
            <Input value={limitApp} onChange={(e) => setLimitApp(e.target.value)} placeholder={t("appNamePlaceholder")} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">{t("dailyMinutes")}</label>
            <Input value={limitMinutes} onChange={(e) => setLimitMinutes(e.target.value)} placeholder="60" />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>
              {t("cancel")}
            </Button>
            <Button
              onClick={handleCreateLimit}
              isLoading={createLimit.isPending}
              disabled={!limitMemberId || !limitMinutes}
            >
              {t("create")}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
