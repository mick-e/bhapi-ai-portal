"use client";

import { useState } from "react";
import {
  Bell,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  Filter,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface AlertItem {
  id: string;
  type: "risk" | "spend" | "member" | "system";
  severity: "info" | "warning" | "error" | "critical";
  title: string;
  message: string;
  memberName?: string;
  read: boolean;
  actioned: boolean;
  createdAt: string;
}

const placeholderAlerts: AlertItem[] = [
  {
    id: "1",
    type: "risk",
    severity: "critical",
    title: "Unsafe content detected",
    message:
      "James attempted to generate content that violates safety policies via ChatGPT. The request was automatically blocked.",
    memberName: "James",
    read: false,
    actioned: false,
    createdAt: "1 hour ago",
  },
  {
    id: "2",
    type: "spend",
    severity: "warning",
    title: "Budget threshold reached",
    message:
      "Tom has used 80% of their daily API budget ($4.00 of $5.00). Consider adjusting limits.",
    memberName: "Tom",
    read: false,
    actioned: false,
    createdAt: "3 hours ago",
  },
  {
    id: "3",
    type: "member",
    severity: "info",
    title: "New member joined",
    message:
      "Alex Chen accepted the group invitation and has been added as a Member.",
    memberName: "Alex",
    read: true,
    actioned: true,
    createdAt: "5 hours ago",
  },
  {
    id: "4",
    type: "risk",
    severity: "warning",
    title: "Elevated risk pattern",
    message:
      "Emma has had 3 medium-risk interactions in the past hour. Consider reviewing activity.",
    memberName: "Emma",
    read: true,
    actioned: false,
    createdAt: "6 hours ago",
  },
  {
    id: "5",
    type: "system",
    severity: "info",
    title: "Weekly safety report ready",
    message:
      "Your weekly AI safety report has been generated. View it in the Reports section.",
    read: true,
    actioned: true,
    createdAt: "1 day ago",
  },
  {
    id: "6",
    type: "spend",
    severity: "error",
    title: "Budget exceeded",
    message:
      "Monthly group budget of $150 has been exceeded. Current spend: $152.40.",
    read: true,
    actioned: false,
    createdAt: "2 days ago",
  },
];

const severityIcons = {
  info: Info,
  warning: AlertTriangle,
  error: AlertCircle,
  critical: AlertTriangle,
};

const severityStyles = {
  info: {
    border: "border-l-blue-500",
    bg: "bg-blue-50",
    iconColor: "text-blue-500",
  },
  warning: {
    border: "border-l-amber-500",
    bg: "bg-amber-50",
    iconColor: "text-amber-500",
  },
  error: {
    border: "border-l-red-500",
    bg: "bg-red-50",
    iconColor: "text-red-500",
  },
  critical: {
    border: "border-l-red-700",
    bg: "bg-red-100",
    iconColor: "text-red-700",
  },
};

export default function AlertsPage() {
  const [filterSeverity, setFilterSeverity] = useState<string>("all");
  const [filterType, setFilterType] = useState<string>("all");
  const [alerts, setAlerts] = useState(placeholderAlerts);

  const unreadCount = alerts.filter((a) => !a.read).length;

  const filtered = alerts.filter((alert) => {
    const matchesSeverity =
      filterSeverity === "all" || alert.severity === filterSeverity;
    const matchesType = filterType === "all" || alert.type === filterType;
    return matchesSeverity && matchesType;
  });

  function markAllRead() {
    setAlerts((prev) => prev.map((a) => ({ ...a, read: true })));
  }

  function markAsActioned(id: string) {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === id ? { ...a, actioned: true, read: true } : a
      )
    );
  }

  return (
    <div>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
          <p className="mt-1 text-sm text-gray-500">
            {unreadCount > 0
              ? `${unreadCount} unread alert${unreadCount > 1 ? "s" : ""}`
              : "All caught up"}
          </p>
        </div>
        {unreadCount > 0 && (
          <Button variant="secondary" size="sm" onClick={markAllRead}>
            <CheckCircle2 className="h-4 w-4" />
            Mark all read
          </Button>
        )}
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Filter className="h-4 w-4 text-gray-400" />
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="all">All severities</option>
          <option value="critical">Critical</option>
          <option value="error">Error</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="all">All types</option>
          <option value="risk">Risk</option>
          <option value="spend">Spend</option>
          <option value="member">Member</option>
          <option value="system">System</option>
        </select>
      </div>

      {/* Alert List */}
      <div className="space-y-3">
        {filtered.map((alert) => {
          const style = severityStyles[alert.severity];
          const SeverityIcon = severityIcons[alert.severity];

          return (
            <div
              key={alert.id}
              className={`rounded-r-xl border-l-4 ${style.border} ${
                alert.read ? "bg-white" : style.bg
              } p-4 shadow-sm ring-1 ring-gray-200`}
            >
              <div className="flex items-start gap-3">
                <SeverityIcon
                  className={`mt-0.5 h-5 w-5 flex-shrink-0 ${style.iconColor}`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3
                        className={`text-sm font-semibold ${
                          alert.read ? "text-gray-700" : "text-gray-900"
                        }`}
                      >
                        {alert.title}
                        {!alert.read && (
                          <span className="ml-2 inline-block h-2 w-2 rounded-full bg-primary" />
                        )}
                      </h3>
                      {alert.memberName && (
                        <span className="text-xs text-gray-400">
                          Member: {alert.memberName}
                        </span>
                      )}
                    </div>
                    <span className="flex-shrink-0 text-xs text-gray-400">
                      {alert.createdAt}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-gray-600">{alert.message}</p>
                  {!alert.actioned && (
                    <div className="mt-3">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => markAsActioned(alert.id)}
                      >
                        Acknowledge
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="py-12 text-center">
            <Bell className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-sm text-gray-500">
              No alerts match your filters
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
