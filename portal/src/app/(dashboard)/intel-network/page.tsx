"use client";

import React, { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  Shield,
  Radio,
  Loader2,
  ThumbsUp,
  ThumbsDown,
} from "lucide-react";
import { useTranslations } from "@/contexts/LocaleContext";
import {
  useIntelFeed,
  useIntelSubscription,
  useSubscribeToNetwork,
  useUnsubscribeFromNetwork,
  useSubmitSignalFeedback,
} from "@/hooks/use-intel-network";
import type { ThreatSignal } from "@/hooks/use-intel-network";

type TabKey = "feed" | "subscription";

export default function IntelNetworkPage() {
  const t = useTranslations("intelNetwork");
  const [activeTab, setActiveTab] = useState<TabKey>("feed");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("medium");

  // Queries
  const feed = useIntelFeed();
  const subscription = useIntelSubscription();

  // Mutations
  const subscribeMut = useSubscribeToNetwork();
  const unsubscribeMut = useUnsubscribeFromNetwork();
  const feedbackMut = useSubmitSignalFeedback();

  const tabs = [
    { key: "feed", label: t("tabFeed") },
    { key: "subscription", label: t("tabSubscription") },
  ];

  const severityBadge = (severity: string) => {
    const map: Record<string, "error" | "warning" | "info" | "neutral"> = {
      critical: "error",
      high: "error",
      medium: "warning",
      low: "info",
    };
    return map[severity] ?? "neutral";
  };

  // ─── Tab: Signal Feed ───────────────────────────────────────────────────────

  function renderFeed() {
    if (feed.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = feed.data ?? [];

    if (feed.isError || items.length === 0) {
      return (
        <Card>
          <EmptyState
            title={t("tabFeed")}
            message={feed.isError ? t("emptySubscription") : t("emptyFeed")}
            icon={<Radio className="h-10 w-10" />}
          />
        </Card>
      );
    }

    return (
      <div className="space-y-3">
        {items.map((signal: ThreatSignal) => (
          <Card key={signal.id}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900">
                    {signal.signal_type}
                  </p>
                  <Badge variant={severityBadge(signal.severity)}>
                    {signal.severity}
                  </Badge>
                </div>
                {signal.description && (
                  <p className="mt-1 text-sm text-gray-500">
                    {signal.description}
                  </p>
                )}
                <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-400">
                  <span>
                    {t("confidence")}: {(signal.confidence * 100).toFixed(0)}%
                  </span>
                  <span>
                    {t("sampleSize")}: {signal.sample_size}
                  </span>
                  {signal.contributor_region && (
                    <span>
                      {t("region")}: {signal.contributor_region}
                    </span>
                  )}
                  <span>
                    {new Date(signal.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
              <div className="ml-4 flex gap-1">
                <button
                  onClick={() =>
                    feedbackMut.mutate({
                      signal_id: signal.id,
                      is_helpful: true,
                    })
                  }
                  className="rounded p-1.5 text-gray-400 hover:bg-green-50 hover:text-green-600"
                  title={t("helpful")}
                >
                  <ThumbsUp className="h-4 w-4" />
                  {signal.feedback_helpful > 0 && (
                    <span className="ml-0.5 text-xs">
                      {signal.feedback_helpful}
                    </span>
                  )}
                </button>
                <button
                  onClick={() =>
                    feedbackMut.mutate({
                      signal_id: signal.id,
                      is_helpful: false,
                    })
                  }
                  className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                  title={t("falsePositive")}
                >
                  <ThumbsDown className="h-4 w-4" />
                  {signal.feedback_false_positive > 0 && (
                    <span className="ml-0.5 text-xs">
                      {signal.feedback_false_positive}
                    </span>
                  )}
                </button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  // ─── Tab: Subscription ──────────────────────────────────────────────────────

  function renderSubscription() {
    if (subscription.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const sub = subscription.data;
    const isSubscribed = sub?.is_active === true;

    return (
      <Card>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900">
                {isSubscribed ? t("subscribed") : t("notSubscribed")}
              </p>
              <p className="text-sm text-gray-500">
                {t("subscribeDescription")}
              </p>
            </div>
            <Badge variant={isSubscribed ? "success" : "neutral"}>
              {isSubscribed ? t("subscribed") : t("notSubscribed")}
            </Badge>
          </div>

          {!isSubscribed && (
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {t("minimumSeverity")}
                </label>
                <select
                  value={selectedSeverity}
                  onChange={(e) => setSelectedSeverity(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <Button
                onClick={() =>
                  subscribeMut.mutate({
                    minimum_severity: selectedSeverity,
                  })
                }
                isLoading={subscribeMut.isPending}
              >
                {t("subscribe")}
              </Button>
            </div>
          )}

          {isSubscribed && (
            <div className="space-y-3">
              <div className="rounded-md bg-gray-50 p-3 text-sm">
                <p>
                  <span className="font-medium">{t("minimumSeverity")}:</span>{" "}
                  {sub.minimum_severity}
                </p>
                {sub.signal_types.length > 0 && (
                  <p className="mt-1">
                    <span className="font-medium">{t("signalTypes")}:</span>{" "}
                    {sub.signal_types.join(", ")}
                  </p>
                )}
              </div>
              <Button
                variant="secondary"
                onClick={() => unsubscribeMut.mutate()}
                isLoading={unsubscribeMut.isPending}
              >
                {t("unsubscribe")}
              </Button>
            </div>
          )}
        </div>
      </Card>
    );
  }

  const tabContent: Record<TabKey, () => React.ReactNode> = {
    feed: renderFeed,
    subscription: renderSubscription,
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
    </div>
  );
}
