"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Activity,
  CreditCard,
  Clock,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Ban,
  ShieldCheck,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useMember } from "@/hooks/use-members";
import { useActivity } from "@/hooks/use-activity";
import { useRiskEvents } from "@/hooks/use-alerts";
import { useSpendRecords } from "@/hooks/use-spend";
import { useBlockCheck, useCreateBlockRule, useRevokeBlockRule } from "@/hooks/use-blocking";
import { useAuth } from "@/hooks/use-auth";
import { integrationsApi } from "@/lib/api-client";
import { useToast } from "@/contexts/ToastContext";

export default function MemberDetailPage() {
  return (
    <Suspense fallback={<div className="flex h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /><span className="ml-3 text-sm text-gray-500">Loading member...</span></div>}>
      <MemberDetailContent />
    </Suspense>
  );
}

function MemberDetailContent() {
  const searchParams = useSearchParams();
  const memberId = searchParams.get("id") || "";
  const { user } = useAuth();
  const { addToast } = useToast();
  const groupId = user?.group_id || "";

  const {
    data: member,
    isLoading,
    isError,
    error,
    refetch,
  } = useMember(memberId);

  const { data: activityData } = useActivity({
    member_id: memberId,
    page_size: 5,
  });

  const { data: riskData } = useRiskEvents({
    member_id: memberId,
    page_size: 5,
  });

  const { data: spendData } = useSpendRecords({
    member_id: memberId,
    page_size: 5,
  });

  const { data: blockStatus } = useBlockCheck(groupId || null, memberId);
  const createBlock = useCreateBlockRule();
  const revokeBlock = useRevokeBlockRule();
  const [ageVerifying, setAgeVerifying] = useState(false);

  if (!memberId) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">No member selected</p>
        <Link href="/members" className="mt-2 text-sm text-primary-700 hover:underline">
          Back to Members
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading member...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">Failed to load member</p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || "Something went wrong"}
        </p>
        <Button variant="secondary" size="sm" className="mt-4" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    );
  }

  if (!member) return null;

  const recentActivity = activityData?.items ?? [];
  const recentRisks = riskData?.items ?? [];
  const recentSpend = spendData?.items ?? [];
  const totalSpend = recentSpend.reduce((sum, r) => sum + r.cost_usd, 0);

  const riskColors: Record<string, string> = {
    low: "bg-green-100 text-green-700",
    medium: "bg-amber-100 text-amber-700",
    high: "bg-red-100 text-red-700",
    critical: "bg-red-200 text-red-800",
  };

  const statusColors: Record<string, string> = {
    active: "bg-green-100 text-green-700",
    invited: "bg-amber-100 text-amber-700",
    suspended: "bg-red-100 text-red-700",
  };

  return (
    <div>
      <Link
        href="/members"
        className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Members
      </Link>

      {/* Member header */}
      <div className="mb-8 flex items-center gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-100 text-lg font-bold text-primary">
          {member.display_name.charAt(0).toUpperCase()}
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{member.display_name}</h1>
          <div className="mt-1 flex items-center gap-3">
            <span className="text-sm text-gray-500">{member.email}</span>
            <span className="text-sm capitalize text-gray-500">{member.role}</span>
            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[member.status]}`}>
              {member.status}
            </span>
            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${riskColors[member.risk_level || "low"]}`}>
              {member.risk_level || "low"} risk
            </span>
          </div>
        </div>
      </div>

      {/* Stats cards */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-4">
        <StatCard icon={<Activity className="h-5 w-5 text-primary" />} label="Total Activity" value={String(activityData?.total ?? 0)} />
        <StatCard icon={<AlertTriangle className="h-5 w-5 text-amber-500" />} label="Risk Events" value={String(riskData?.total ?? 0)} />
        <StatCard icon={<CreditCard className="h-5 w-5 text-accent" />} label="Total Spend" value={`$${totalSpend.toFixed(2)}`} />
        <StatCard icon={<Clock className="h-5 w-5 text-gray-500" />} label="Last Active" value={member.last_active ? formatRelativeTime(member.last_active) : "Never"} />
      </div>

      {/* Age Verification & Blocking Controls */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card title="Age Verification">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">
                {member.date_of_birth ? `DOB: ${member.date_of_birth}` : "Date of birth not verified"}
              </p>
              {member.age_verified && (
                <p className="mt-1 flex items-center gap-1 text-xs text-green-600">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Verified
                </p>
              )}
            </div>
            {!member.age_verified && (
              <Button
                size="sm"
                variant="secondary"
                isLoading={ageVerifying}
                onClick={async () => {
                  setAgeVerifying(true);
                  try {
                    await integrationsApi.startAgeVerification(groupId, memberId);
                    addToast("Age verification started", "success");
                  } catch {
                    addToast("Failed to start verification", "error");
                  } finally {
                    setAgeVerifying(false);
                  }
                }}
              >
                <ShieldCheck className="h-4 w-4" />
                Verify Age
              </Button>
            )}
          </div>
        </Card>

        <Card title="Blocking Controls">
          <div className="flex items-center justify-between">
            <div>
              {blockStatus?.blocked ? (
                <p className="flex items-center gap-1.5 text-sm font-medium text-red-600">
                  <Ban className="h-4 w-4" />
                  AI access blocked ({blockStatus.rules?.length || 0} active rule{(blockStatus.rules?.length || 0) !== 1 ? "s" : ""})
                </p>
              ) : (
                <p className="text-sm text-gray-600">AI access allowed</p>
              )}
            </div>
            {blockStatus?.blocked ? (
              <Button
                size="sm"
                variant="secondary"
                isLoading={revokeBlock.isPending}
                onClick={() => {
                  const rule = blockStatus.rules?.[0];
                  if (rule) {
                    revokeBlock.mutate(
                      { ruleId: rule.id, groupId },
                      {
                        onSuccess: () => addToast("Block rule revoked", "success"),
                        onError: () => addToast("Failed to revoke block", "error"),
                      }
                    );
                  }
                }}
              >
                Unblock
              </Button>
            ) : (
              <Button
                size="sm"
                variant="secondary"
                isLoading={createBlock.isPending}
                onClick={() => {
                  createBlock.mutate(
                    { group_id: groupId, member_id: memberId, reason: "Manual block from member page" },
                    {
                      onSuccess: () => addToast("Member blocked", "success"),
                      onError: () => addToast("Failed to block member", "error"),
                    }
                  );
                }}
              >
                <Ban className="h-4 w-4" />
                Block Access
              </Button>
            )}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Recent Activity">
          {recentActivity.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-500">No activity yet</p>
          ) : (
            <div className="space-y-3">
              {recentActivity.map((event) => (
                <div key={event.id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-900">{event.provider} / {event.model}</p>
                    <p className="text-xs text-gray-500 truncate max-w-[250px]">{event.prompt_preview}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColors[event.risk_level]}`}>{event.risk_level}</span>
                    <span className="text-xs text-gray-400">{formatRelativeTime(event.timestamp)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Risk Events">
          {recentRisks.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-500">No risk events</p>
          ) : (
            <div className="space-y-3">
              {recentRisks.map((risk) => (
                <div key={risk.id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{risk.category}</p>
                    <p className="text-xs text-gray-500 truncate max-w-[250px]">{risk.description}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskColors[risk.severity]}`}>{risk.severity}</span>
                    {risk.acknowledged && <span className="text-xs text-green-600">Ack</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div className="mt-6">
        <Card title="Recent Spend">
          {recentSpend.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-500">No spend records</p>
          ) : (
            <div className="-mx-6 -my-4 overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Provider</th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Model</th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Tokens</th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Cost</th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {recentSpend.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-600">{record.provider}</td>
                      <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-600">{record.model}</td>
                      <td className="whitespace-nowrap px-6 py-3 text-right text-sm text-gray-600">{record.token_count.toLocaleString()}</td>
                      <td className="whitespace-nowrap px-6 py-3 text-right text-sm font-medium text-gray-900">${record.cost_usd.toFixed(3)}</td>
                      <td className="whitespace-nowrap px-6 py-3 text-right text-xs text-gray-400">{formatRelativeTime(record.timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-50">{icon}</div>
        <div>
          <p className="text-xs text-gray-500">{label}</p>
          <p className="text-lg font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}

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
