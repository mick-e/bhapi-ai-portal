"use client";
import React from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useAlerts } from "@/hooks/use-alerts";
import type { BadgeVariant } from "@/components/ui/Badge";
import type { AlertSeverity } from "@/types";

function severityToBadgeVariant(severity: AlertSeverity): BadgeVariant {
  switch (severity) {
    case "critical":
      return "error";
    case "error":
      return "error";
    case "warning":
      return "warning";
    case "info":
    default:
      return "info";
  }
}

/**
 * Shows up to 5 unread alerts. Returns null when there are no pending alerts
 * (progressive disclosure — only visible when action is required).
 */
export function ActionsNeeded() {
  const router = useRouter();
  const { data, isLoading } = useAlerts({ read: false, page_size: 5 });

  if (isLoading) return null;

  const alerts = data?.items ?? [];
  if (alerts.length === 0) return null;

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
      <h2 className="mb-3 text-sm font-semibold text-amber-900">
        Actions Needed
      </h2>
      <ul className="space-y-2">
        {alerts.map((alert) => (
          <li
            key={alert.id}
            className="flex items-start justify-between gap-3 rounded-lg bg-white px-3 py-2 shadow-sm ring-1 ring-gray-100"
          >
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <div className="flex items-center gap-2">
                <Badge variant={severityToBadgeVariant(alert.severity)}>
                  {alert.severity}
                </Badge>
                {alert.member_name && (
                  <span className="text-xs text-gray-500">
                    {alert.member_name}
                  </span>
                )}
              </div>
              <p className="truncate text-sm font-medium text-gray-900">
                {alert.title}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push(`/alerts?id=${alert.id}`)}
            >
              View
            </Button>
          </li>
        ))}
      </ul>
      {(data?.total ?? 0) > 5 && (
        <button
          className="mt-3 w-full text-center text-xs font-medium text-amber-700 hover:text-amber-900"
          onClick={() => router.push("/alerts")}
        >
          View all {data?.total} alerts
        </button>
      )}
    </div>
  );
}
