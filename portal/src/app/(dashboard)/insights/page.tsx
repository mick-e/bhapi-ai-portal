"use client";

import React, { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import {
  ShieldAlert,
  Activity,
  TrendingUp,
  Link2,
  Loader2,
  ArrowUp,
  ArrowDown,
  Minus,
} from "lucide-react";
import { useTranslations } from "@/contexts/LocaleContext";
import {
  useRiskScores,
  useAnomalyAlerts,
  useBehavioralBaselines,
  useCorrelations,
} from "@/hooks/use-insights";

type TabKey = "scores" | "anomalies" | "baselines" | "correlations";

export default function InsightsPage() {
  const t = useTranslations("insights");
  const [activeTab, setActiveTab] = useState<TabKey>("scores");

  // Queries
  const scores = useRiskScores();
  const anomalies = useAnomalyAlerts();
  const baselines = useBehavioralBaselines();
  const correlations = useCorrelations();

  const tabs = [
    { key: "scores", label: t("tabScores") },
    { key: "anomalies", label: t("tabAnomalies"), count: (anomalies.data ?? []).filter((a) => !a.resolved).length || undefined },
    { key: "baselines", label: t("tabBaselines") },
    { key: "correlations", label: t("tabCorrelations") },
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

  const trendIcon = (trend: string) => {
    if (trend === "improving") return <ArrowDown className="h-4 w-4 text-green-500" />;
    if (trend === "worsening") return <ArrowUp className="h-4 w-4 text-red-500" />;
    return <Minus className="h-4 w-4 text-gray-400" />;
  };

  // ─── Tab: Risk Scores ──────────────────────────────────────────────────────

  function renderScores() {
    if (scores.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = scores.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabScores")}
          message={t("emptyScores")}
          icon={<ShieldAlert className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((score) => {
          const color = score.overall_score <= 30
            ? "text-green-600"
            : score.overall_score <= 60
              ? "text-amber-600"
              : "text-red-600";
          return (
            <Card key={score.member_id}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-gray-900">{score.member_name}</p>
                  <p className="mt-1 text-xs text-gray-400">
                    {t("updated")} {new Date(score.updated_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  {trendIcon(score.trend)}
                  <span className={`text-2xl font-bold ${color}`}>
                    {score.overall_score}
                  </span>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-1">
                {Object.entries(score.category_scores).map(([cat, val]) => (
                  <Badge key={cat} variant={val > 60 ? "warning" : "neutral"}>
                    {cat}: {val}
                  </Badge>
                ))}
              </div>
            </Card>
          );
        })}
      </div>
    );
  }

  // ─── Tab: Anomaly Alerts ───────────────────────────────────────────────────

  function renderAnomalies() {
    if (anomalies.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = anomalies.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabAnomalies")}
          message={t("emptyAnomalies")}
          icon={<Activity className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="space-y-3">
        {items.map((alert) => (
          <Card key={alert.id}>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">{alert.anomaly_type}</p>
                <p className="text-sm text-gray-500">{alert.description}</p>
                <p className="text-xs text-gray-400">
                  {alert.member_name} &mdash; {new Date(alert.detected_at).toLocaleString()}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={severityBadge(alert.severity)}>
                  {alert.severity}
                </Badge>
                {alert.resolved && (
                  <Badge variant="success">{t("resolved")}</Badge>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  // ─── Tab: Behavioral Baselines ─────────────────────────────────────────────

  function renderBaselines() {
    if (baselines.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = baselines.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabBaselines")}
          message={t("emptyBaselines")}
          icon={<TrendingUp className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="space-y-3">
        {items.map((baseline, idx) => {
          const devColor = Math.abs(baseline.deviation_percent) > 50
            ? "text-red-600"
            : Math.abs(baseline.deviation_percent) > 25
              ? "text-amber-600"
              : "text-green-600";
          return (
            <Card key={`${baseline.member_id}-${baseline.metric}-${idx}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{baseline.metric}</p>
                  <p className="text-sm text-gray-500">{baseline.member_name}</p>
                  <p className="text-xs text-gray-400">{baseline.period}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-700">
                    {baseline.current_value}{" "}
                    <span className="text-gray-400">/ {baseline.baseline_value}</span>
                  </p>
                  <p className={`text-sm font-semibold ${devColor}`}>
                    {baseline.deviation_percent > 0 ? "+" : ""}{baseline.deviation_percent.toFixed(1)}%
                  </p>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    );
  }

  // ─── Tab: Correlations ─────────────────────────────────────────────────────

  function renderCorrelations() {
    if (correlations.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = correlations.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabCorrelations")}
          message={t("emptyCorrelations")}
          icon={<Link2 className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="space-y-3">
        {items.map((corr) => (
          <Card key={corr.id}>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">{corr.rule_name}</p>
                <p className="text-sm text-gray-500">
                  {corr.source_event} &rarr; {corr.correlated_event}
                </p>
                <p className="text-xs text-gray-400">
                  {corr.member_name} &mdash; {new Date(corr.detected_at).toLocaleString()}
                </p>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold text-gray-700">
                  {(corr.confidence * 100).toFixed(0)}%
                </p>
                <p className="text-xs text-gray-400">{t("confidence")}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  const tabContent: Record<TabKey, () => React.ReactNode> = {
    scores: renderScores,
    anomalies: renderAnomalies,
    baselines: renderBaselines,
    correlations: renderCorrelations,
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
