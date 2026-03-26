"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Key,
  Copy,
  CheckCircle,
  TrendingUp,
  BookOpen,
  Webhook,
  LifeBuoy,
  Loader2,
  AlertCircle,
  ArrowUpRight,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  useApiClients,
  useApiUsage,
} from "@/hooks/use-developer-portal";

function maskClientId(id: string): string {
  if (id.length <= 8) return "••••••••";
  return id.slice(0, 8) + "••••••••••••••••";
}

function UsageBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const color =
    pct >= 90
      ? "bg-red-500"
      : pct >= 70
      ? "bg-amber-500"
      : "bg-teal-500";
  return (
    <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-gray-100">
      <div
        className={`h-full rounded-full transition-all ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function MiniBarChart({ days }: { days: { date: string; calls: number }[] }) {
  const max = Math.max(...days.map((d) => d.calls), 1);
  return (
    <div className="flex h-20 items-end gap-1" aria-label="Daily API calls chart">
      {days.map((day) => {
        const heightPct = (day.calls / max) * 100;
        return (
          <div
            key={day.date}
            title={`${day.date}: ${day.calls.toLocaleString()} calls`}
            className="flex-1 rounded-sm bg-primary-200 hover:bg-primary-400 transition-colors"
            style={{ height: `${Math.max(4, heightPct)}%` }}
          />
        );
      })}
    </div>
  );
}

const QUICK_LINKS = [
  {
    icon: BookOpen,
    label: "API Docs",
    href: "/developers/docs",
    desc: "Endpoints, auth, examples",
  },
  {
    icon: Webhook,
    label: "Webhooks",
    href: "/developers/webhooks",
    desc: "Manage event subscriptions",
  },
  {
    icon: LifeBuoy,
    label: "Support",
    href: "mailto:developers@bhapi.ai",
    desc: "Email our developer team",
  },
];

export default function ApiDashboardPage() {
  const { data: clientsData, isLoading: clientsLoading, isError: clientsError } = useApiClients();
  const { data: usage, isLoading: usageLoading } = useApiUsage(30);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const primaryClient = clientsData?.items?.[0] ?? null;

  function handleCopy(text: string, id: string) {
    navigator.clipboard.writeText(text).catch(() => {});
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">API Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Monitor usage, manage credentials, and configure your integration.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column — credentials + usage */}
        <div className="space-y-6 lg:col-span-2">
          {/* API Key card */}
          <Card>
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Key className="h-5 w-5 text-primary-600" />
                <h2 className="font-semibold text-gray-900">API Credentials</h2>
              </div>
              {primaryClient && !primaryClient.is_approved && (
                <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">
                  Pending Approval
                </span>
              )}
              {primaryClient?.is_approved && (
                <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
                  Active
                </span>
              )}
            </div>

            {clientsLoading && (
              <div className="flex h-16 items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
              </div>
            )}

            {clientsError && (
              <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                Failed to load credentials. Please try refreshing.
              </div>
            )}

            {!clientsLoading && !clientsError && !primaryClient && (
              <div className="rounded-lg bg-gray-50 py-8 text-center">
                <Key className="mx-auto mb-3 h-8 w-8 text-gray-300" />
                <p className="mb-4 text-sm text-gray-500">
                  You haven&apos;t registered an API client yet.
                </p>
                <Link href="/developer">
                  <Button size="sm">Register App</Button>
                </Link>
              </div>
            )}

            {primaryClient && (
              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-500">
                    App Name
                  </label>
                  <p className="text-sm font-medium text-gray-900">
                    {primaryClient.name}
                  </p>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-500">
                    Client ID
                  </label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 rounded-lg bg-gray-50 px-3 py-2 font-mono text-sm text-gray-800 ring-1 ring-gray-200">
                      {maskClientId(primaryClient.client_id)}
                    </code>
                    <button
                      onClick={() =>
                        handleCopy(primaryClient.client_id, "client_id")
                      }
                      className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
                      title="Copy client ID"
                    >
                      {copiedId === "client_id" ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>
                <p className="text-xs text-gray-400">
                  Your client secret was shown once at creation and cannot be
                  retrieved. Regenerate it in the{" "}
                  <Link href="/developer" className="text-primary-700 hover:underline">
                    integrations page
                  </Link>
                  .
                </p>
              </div>
            )}
          </Card>

          {/* Usage card */}
          <Card>
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-teal-600" />
                <h2 className="font-semibold text-gray-900">API Usage</h2>
              </div>
              <span className="text-xs text-gray-400">Last 30 days</span>
            </div>

            {usageLoading && (
              <div className="flex h-24 items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
              </div>
            )}

            {!usageLoading && usage && (
              <>
                <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
                  <div>
                    <p className="text-xs font-medium text-gray-500">Total Calls</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {usage.total_calls.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500">Current Plan</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {usage.tier_name}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500">Daily Limit</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {usage.tier_limit.toLocaleString()}
                    </p>
                  </div>
                </div>

                {/* Usage bar */}
                <div className="mb-6">
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Today&apos;s usage</span>
                    <span>
                      {(
                        (usage.days[usage.days.length - 1]?.calls ?? 0) /
                        usage.tier_limit *
                        100
                      ).toFixed(1)}
                      % of limit
                    </span>
                  </div>
                  <UsageBar
                    value={usage.days[usage.days.length - 1]?.calls ?? 0}
                    max={usage.tier_limit}
                  />
                </div>

                {/* Mini bar chart */}
                {usage.days.length > 0 && (
                  <div>
                    <p className="mb-2 text-xs font-medium text-gray-500">
                      Calls per day (last {usage.days.length} days)
                    </p>
                    <MiniBarChart days={usage.days} />
                  </div>
                )}

                <div className="mt-4 flex justify-end">
                  <Button variant="secondary" size="sm">
                    <ArrowUpRight className="mr-1.5 h-3.5 w-3.5" />
                    Upgrade Plan
                  </Button>
                </div>
              </>
            )}

            {!usageLoading && !usage && (
              <div className="py-8 text-center text-sm text-gray-500">
                No usage data available yet. Make your first API call to see
                metrics here.
              </div>
            )}
          </Card>
        </div>

        {/* Right column — quick links */}
        <div className="space-y-4">
          <h2 className="font-semibold text-gray-900">Quick Links</h2>
          {QUICK_LINKS.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.label}
                href={item.href}
                className="block rounded-xl border border-gray-200 bg-white p-4 hover:border-primary-200 hover:bg-primary-50 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-primary-100">
                    <Icon className="h-4 w-4 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{item.label}</p>
                    <p className="text-xs text-gray-500">{item.desc}</p>
                  </div>
                </div>
              </Link>
            );
          })}

          {/* Tier info */}
          <div className="rounded-xl border border-teal-200 bg-teal-50 p-4">
            <p className="mb-1 text-sm font-semibold text-teal-800">
              Current Tier
            </p>
            <p className="mb-3 text-2xl font-bold text-teal-900">
              {usage?.tier_name ?? "—"}
            </p>
            <p className="mb-4 text-xs text-teal-700">
              {usage
                ? `${usage.tier_limit.toLocaleString()} calls / day`
                : "Register an API client to see your tier."}
            </p>
            <Button size="sm" variant="secondary" className="w-full border-teal-300 text-teal-700 hover:bg-teal-100">
              View All Plans
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
