"use client";

import {
  CreditCard,
  TrendingUp,
  DollarSign,
  Users,
  AlertTriangle,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export default function SpendPage() {
  return (
    <div>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Spend Management</h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor and control AI API costs across your group
          </p>
        </div>
        <Button variant="secondary">
          <CreditCard className="h-4 w-4" />
          Edit Budget
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="This Month"
          value="$42.18"
          subtitle="of $150.00 budget"
          icon={<DollarSign className="h-5 w-5 text-primary" />}
        />
        <StatCard
          label="Today"
          value="$4.82"
          subtitle="avg $5.20/day"
          icon={<TrendingUp className="h-5 w-5 text-green-600" />}
        />
        <StatCard
          label="Active Spenders"
          value="8"
          subtitle="of 15 members"
          icon={<Users className="h-5 w-5 text-accent" />}
        />
        <StatCard
          label="Over Budget"
          value="1"
          subtitle="member exceeded limit"
          icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
        />
      </div>

      {/* Budget Progress */}
      <Card
        title="Monthly Budget"
        description="Current period: 1 Feb - 28 Feb 2026"
      >
        <div className="space-y-6">
          <div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Group Total</span>
              <span className="font-medium text-gray-900">
                $42.18 / $150.00
              </span>
            </div>
            <div className="mt-2 h-3 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: "28%" }}
              />
            </div>
            <p className="mt-1 text-xs text-gray-400">
              28% used, $107.82 remaining
            </p>
          </div>
        </div>
      </Card>

      {/* Provider Breakdown */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="By Provider">
          <div className="space-y-4">
            <ProviderRow
              name="OpenAI"
              amount={28.45}
              percentage={67}
              requests={245}
            />
            <ProviderRow
              name="Anthropic"
              amount={9.12}
              percentage={22}
              requests={87}
            />
            <ProviderRow
              name="Google"
              amount={4.61}
              percentage={11}
              requests={42}
            />
          </div>
        </Card>

        <Card title="By Member">
          <div className="space-y-4">
            <MemberSpendRow name="Tom" amount={15.2} limit={20} />
            <MemberSpendRow name="Sarah" amount={8.45} limit={15} />
            <MemberSpendRow name="Emma" amount={7.3} limit={15} />
            <MemberSpendRow name="James" amount={6.12} limit={10} />
            <MemberSpendRow name="Lucy" amount={5.11} limit={15} />
          </div>
        </Card>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  subtitle,
  icon,
}: {
  label: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-500">{label}</span>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-50">
          {icon}
        </div>
      </div>
      <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
      <p className="mt-1 text-xs text-gray-400">{subtitle}</p>
    </div>
  );
}

function ProviderRow({
  name,
  amount,
  percentage,
  requests,
}: {
  name: string;
  amount: number;
  percentage: number;
  requests: number;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-gray-900">{name}</span>
        <span className="text-gray-600">
          ${amount.toFixed(2)} ({percentage}%)
        </span>
      </div>
      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-primary"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="mt-1 text-xs text-gray-400">
        {requests} requests
      </p>
    </div>
  );
}

function MemberSpendRow({
  name,
  amount,
  limit,
}: {
  name: string;
  amount: number;
  limit: number;
}) {
  const percentage = Math.round((amount / limit) * 100);
  const isOverBudget = percentage >= 100;

  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary">
            {name.charAt(0)}
          </div>
          <span className="font-medium text-gray-900">{name}</span>
        </div>
        <span
          className={`text-sm ${
            isOverBudget ? "font-semibold text-red-600" : "text-gray-600"
          }`}
        >
          ${amount.toFixed(2)} / ${limit.toFixed(2)}
        </span>
      </div>
      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full transition-all ${
            isOverBudget ? "bg-red-500" : percentage >= 80 ? "bg-amber-500" : "bg-primary"
          }`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  );
}
