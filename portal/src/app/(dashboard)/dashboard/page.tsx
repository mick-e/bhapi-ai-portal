"use client";

import {
  Users,
  Activity,
  AlertTriangle,
  CreditCard,
  TrendingUp,
  TrendingDown,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";

export default function DashboardPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Overview of your group&apos;s AI activity and safety
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          title="Active Members"
          value="12"
          subtitle="of 15 total"
          icon={<Users className="h-5 w-5 text-primary" />}
          trend={{ direction: "up", label: "+2 this week" }}
        />
        <SummaryCard
          title="AI Interactions"
          value="342"
          subtitle="today"
          icon={<Activity className="h-5 w-5 text-green-600" />}
          trend={{ direction: "up", label: "+18% vs yesterday" }}
        />
        <SummaryCard
          title="Active Alerts"
          value="3"
          subtitle="1 critical"
          icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
          trend={{ direction: "down", label: "-5 since yesterday" }}
        />
        <SummaryCard
          title="Spend Today"
          value="$4.82"
          subtitle="$150 budget"
          icon={<CreditCard className="h-5 w-5 text-accent" />}
          trend={{ direction: "up", label: "3.2% of budget" }}
        />
      </div>

      {/* Recent Activity and Alerts */}
      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Activity */}
        <Card
          title="Recent Activity"
          description="Latest AI interactions across your group"
          footer={
            <Link
              href="/activity"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-primary-700"
            >
              View all activity
              <ArrowRight className="h-4 w-4" />
            </Link>
          }
        >
          <div className="space-y-4">
            <ActivityItem
              name="Sarah"
              action="ChatGPT conversation"
              time="2 min ago"
              risk="low"
            />
            <ActivityItem
              name="Tom"
              action="Claude code generation"
              time="15 min ago"
              risk="low"
            />
            <ActivityItem
              name="Emma"
              action="Gemini image analysis"
              time="32 min ago"
              risk="medium"
            />
            <ActivityItem
              name="James"
              action="ChatGPT conversation"
              time="1 hour ago"
              risk="high"
            />
            <ActivityItem
              name="Lucy"
              action="Claude writing assistance"
              time="2 hours ago"
              risk="low"
            />
          </div>
        </Card>

        {/* Alert Summary */}
        <Card
          title="Alert Summary"
          description="Safety alerts requiring attention"
          footer={
            <Link
              href="/alerts"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-primary-700"
            >
              View all alerts
              <ArrowRight className="h-4 w-4" />
            </Link>
          }
        >
          <div className="space-y-4">
            <AlertItem
              severity="critical"
              title="Unsafe content detected"
              description="James attempted to generate restricted content via ChatGPT"
              time="1 hour ago"
            />
            <AlertItem
              severity="warning"
              title="Spend threshold reached"
              description="Tom has used 80% of daily API budget"
              time="3 hours ago"
            />
            <AlertItem
              severity="info"
              title="New member joined"
              description="Alex accepted the group invitation"
              time="5 hours ago"
            />
          </div>
        </Card>
      </div>

      {/* Spend Summary */}
      <div className="mt-6">
        <Card
          title="Spend Summary"
          description="API costs for the current billing period"
          footer={
            <Link
              href="/spend"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:text-primary-700"
            >
              View spend details
              <ArrowRight className="h-4 w-4" />
            </Link>
          }
        >
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            <div>
              <p className="text-sm text-gray-500">This month</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">$42.18</p>
              <p className="mt-1 text-xs text-gray-400">
                of $150.00 budget
              </p>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-100">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: "28%" }}
                />
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-500">Top provider</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">OpenAI</p>
              <p className="mt-1 text-xs text-gray-400">$28.45 (67%)</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Top user</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">Tom</p>
              <p className="mt-1 text-xs text-gray-400">$15.20 (36%)</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

function SummaryCard({
  title,
  value,
  subtitle,
  icon,
  trend,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
  trend: { direction: "up" | "down"; label: string };
}) {
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-500">{title}</span>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-50">
          {icon}
        </div>
      </div>
      <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
      <div className="mt-1 flex items-center gap-2">
        <span className="text-sm text-gray-400">{subtitle}</span>
      </div>
      <div className="mt-2 flex items-center gap-1">
        {trend.direction === "up" ? (
          <TrendingUp className="h-3.5 w-3.5 text-green-500" />
        ) : (
          <TrendingDown className="h-3.5 w-3.5 text-green-500" />
        )}
        <span className="text-xs text-gray-500">{trend.label}</span>
      </div>
    </div>
  );
}

function ActivityItem({
  name,
  action,
  time,
  risk,
}: {
  name: string;
  action: string;
  time: string;
  risk: "low" | "medium" | "high";
}) {
  const riskColors = {
    low: "bg-green-100 text-green-700",
    medium: "bg-amber-100 text-amber-700",
    high: "bg-red-100 text-red-700",
  };

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary">
          {name.charAt(0)}
        </div>
        <div>
          <p className="text-sm font-medium text-gray-900">{name}</p>
          <p className="text-xs text-gray-500">{action}</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColors[risk]}`}
        >
          {risk}
        </span>
        <span className="text-xs text-gray-400">{time}</span>
      </div>
    </div>
  );
}

function AlertItem({
  severity,
  title,
  description,
  time,
}: {
  severity: "critical" | "warning" | "info";
  title: string;
  description: string;
  time: string;
}) {
  const severityStyles = {
    critical: "border-l-red-500 bg-red-50",
    warning: "border-l-amber-500 bg-amber-50",
    info: "border-l-blue-500 bg-blue-50",
  };

  return (
    <div
      className={`rounded-r-lg border-l-4 p-3 ${severityStyles[severity]}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold text-gray-900">{title}</p>
          <p className="mt-0.5 text-xs text-gray-600">{description}</p>
        </div>
        <span className="flex-shrink-0 text-xs text-gray-400">{time}</span>
      </div>
    </div>
  );
}
