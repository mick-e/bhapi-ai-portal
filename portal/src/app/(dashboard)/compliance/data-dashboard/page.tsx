"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  Database,
  Eye,
  Loader2,
  RefreshCw,
  Shield,
  ShieldAlert,
  Activity,
  Bell,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/use-auth";
import { useDataDashboard } from "@/hooks/use-data-dashboard";
import { useTranslations } from "@/contexts/LocaleContext";

function StatCard({
  label,
  value,
  icon: Icon,
  color = "text-gray-900",
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color?: string;
}) {
  return (
    <div className="rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100">
          <Icon className={`h-5 w-5 ${color}`} />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

function DataDashboardContent() {
  const t = useTranslations("complianceDataDashboard");
  const searchParams = useSearchParams();
  const memberId = searchParams.get("member_id") ?? "";
  const { user } = useAuth();
  const groupId = user?.group_id ?? "";

  const { data, isLoading, isError, error, refetch } = useDataDashboard(
    groupId,
    memberId
  );

  if (!memberId) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <Eye className="h-10 w-10 text-gray-400" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          {t("noMemberSelected")}
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {t("noMemberSelectedHint")}
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">
          {t("loading")}
        </span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          {t("failedLoad")}
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || t("somethingWrong")}
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

  if (!data) return null;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          {t("title")}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {t("subtitleBefore")}{" "}
          <span className="font-medium text-gray-700">{data.member_name}</span>{" "}
          {t("subtitleAfter")}
        </p>
      </div>

      {/* Degraded providers warning */}
      {data.degraded_providers.length > 0 && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 text-amber-600" />
            <div>
              <p className="text-sm font-medium text-amber-800">
                {t("featuresLimited")}
              </p>
              <p className="mt-1 text-sm text-amber-700">
                {t("consentNotGranted")}{" "}
                {data.degraded_providers.join(", ")}. {t("safetyFeaturesNote")}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Data summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          label={t("captureEvents")}
          value={data.data_summary.capture_events_count}
          icon={Database}
          color="text-blue-600"
        />
        <StatCard
          label={t("platformsMonitored")}
          value={data.data_summary.platforms_monitored.length}
          icon={Eye}
          color="text-teal-600"
        />
        <StatCard
          label={t("riskEvents")}
          value={data.data_summary.risk_events_count}
          icon={Activity}
          color={
            data.data_summary.high_severity_count > 0
              ? "text-red-600"
              : "text-gray-600"
          }
        />
        <StatCard
          label={t("alertsSent")}
          value={data.data_summary.alerts_sent_count}
          icon={Bell}
          color="text-primary-600"
        />
      </div>

      {/* Platforms list */}
      {data.data_summary.platforms_monitored.length > 0 && (
        <div className="mt-4">
          <Card title={t("monitoredPlatformsTitle")}>
            <div className="flex flex-wrap gap-2">
              {data.data_summary.platforms_monitored.map((platform) => (
                <span
                  key={platform}
                  className="inline-flex items-center rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700"
                >
                  {platform}
                </span>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* High severity note */}
      {data.data_summary.high_severity_count > 0 && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3">
          <p className="text-sm text-red-700">
            <span className="font-medium">
              {data.data_summary.high_severity_count}
            </span>{" "}
            {t("highSeverityMessage")}
          </p>
        </div>
      )}

      {/* Third-party sharing */}
      <div className="mt-6">
        <Card
          title={t("thirdPartyTitle")}
          description={t("thirdPartyDescription")}
        >
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="pb-2 pr-4 font-medium text-gray-700">
                    {t("provider")}
                  </th>
                  <th className="pb-2 pr-4 font-medium text-gray-700">
                    {t("consentStatus")}
                  </th>
                  <th className="pb-2 font-medium text-gray-700">
                    {t("lastUpdated")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.third_party_sharing.map((item) => (
                  <tr key={item.provider}>
                    <td className="py-2.5 pr-4 text-gray-900">
                      {item.provider}
                    </td>
                    <td className="py-2.5 pr-4">
                      {item.consented ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                          <Shield className="h-3 w-3" />
                          {t("consented")}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                          {t("notConsented")}
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 text-gray-500">
                      {item.last_updated
                        ? new Date(item.last_updated).toLocaleDateString()
                        : t("never")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Retention policies */}
      {data.retention_policies.length > 0 && (
        <div className="mt-6">
          <Card
            title={t("retentionTitle")}
            description={t("retentionDescription")}
          >
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left">
                    <th className="pb-2 pr-4 font-medium text-gray-700">
                      {t("dataType")}
                    </th>
                    <th className="pb-2 pr-4 font-medium text-gray-700">
                      {t("retention")}
                    </th>
                    <th className="pb-2 pr-4 font-medium text-gray-700">
                      {t("autoDelete")}
                    </th>
                    <th className="pb-2 font-medium text-gray-700">
                      {t("estimatedDeletion")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.retention_policies.map((policy) => (
                    <tr key={policy.data_type}>
                      <td className="py-2.5 pr-4 text-gray-900">
                        {policy.data_type.replace(/_/g, " ")}
                      </td>
                      <td className="py-2.5 pr-4 text-gray-600">
                        {policy.retention_days} {t("days")}
                      </td>
                      <td className="py-2.5 pr-4">
                        {policy.auto_delete ? (
                          <span className="text-green-600">{t("yes")}</span>
                        ) : (
                          <span className="text-gray-400">{t("no")}</span>
                        )}
                      </td>
                      <td className="py-2.5 text-gray-500">
                        {policy.estimated_deletion
                          ? new Date(
                              policy.estimated_deletion
                            ).toLocaleDateString()
                          : t("manual")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

export default function DataDashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-sm text-gray-500">Loading...</span>
        </div>
      }
    >
      <DataDashboardContent />
    </Suspense>
  );
}
