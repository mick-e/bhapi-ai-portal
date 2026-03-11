"use client";

import { useState } from "react";
import {
  Ban,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Plus,
  Trash2,
  Clock,
  CheckCircle,
  XCircle,
  BarChart3,
  Shield,
  Timer,
  Moon,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/use-auth";
import {
  useBlockRules,
  useCreateBlockRule,
  useRevokeBlockRule,
  usePendingApprovals,
  useBlockEffectiveness,
  useApproveUnblock,
  useDenyUnblock,
} from "@/hooks/use-blocking";
import { useToast } from "@/contexts/ToastContext";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

export default function BlockingPage() {
  const { user } = useAuth();
  const groupId = user?.group_id || null;
  const { addToast } = useToast();

  const {
    data: rules,
    isLoading,
    isError,
    error,
    refetch,
  } = useBlockRules(groupId);

  const { data: pendingApprovals } = usePendingApprovals(groupId);
  const { data: effectiveness } = useBlockEffectiveness(groupId);

  const createRule = useCreateBlockRule();
  const revokeRule = useRevokeBlockRule();
  const approveUnblock = useApproveUnblock();
  const denyUnblock = useDenyUnblock();

  const [activeTab, setActiveTab] = useState<"rules" | "screen-time" | "bedtime">("rules");
  const [showForm, setShowForm] = useState(false);
  const [memberId, setMemberId] = useState("");
  const [platforms, setPlatforms] = useState("");
  const [reason, setReason] = useState("");
  const [confirmRevoke, setConfirmRevoke] = useState<string | null>(null);

  function handleCreate() {
    if (!groupId || !memberId.trim()) return;
    const platformList = platforms.trim()
      ? platforms.split(",").map((p) => p.trim()).filter(Boolean)
      : undefined;
    createRule.mutate(
      {
        group_id: groupId,
        member_id: memberId.trim(),
        platforms: platformList,
        reason: reason.trim() || undefined,
      },
      {
        onSuccess: () => {
          addToast("Block rule created", "success");
          setShowForm(false);
          setMemberId("");
          setPlatforms("");
          setReason("");
        },
        onError: (err) =>
          addToast((err as Error).message || "Failed to create rule", "error"),
      }
    );
  }

  function handleRevoke(ruleId: string) {
    if (!groupId) return;
    revokeRule.mutate(
      { ruleId, groupId },
      {
        onSuccess: () => {
          addToast("Block rule revoked", "success");
          setConfirmRevoke(null);
        },
        onError: (err) =>
          addToast((err as Error).message || "Failed to revoke rule", "error"),
      }
    );
  }

  function handleApprove(approvalId: string) {
    if (!groupId) return;
    approveUnblock.mutate(
      { approvalId, groupId },
      {
        onSuccess: () => addToast("Unblock request approved", "success"),
        onError: (err) =>
          addToast((err as Error).message || "Failed to approve", "error"),
      }
    );
  }

  function handleDeny(approvalId: string) {
    if (!groupId) return;
    denyUnblock.mutate(
      { approvalId, groupId },
      {
        onSuccess: () => addToast("Unblock request denied", "success"),
        onError: (err) =>
          addToast((err as Error).message || "Failed to deny", "error"),
      }
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading block rules...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load block rules
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || "Something went wrong"}
        </p>
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={() => refetch()}
        >
          <RefreshCw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    );
  }

  const activeRules = (rules || []).filter((r) => r.active);
  const pending = pendingApprovals || [];

  return (
    <div>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Blocking & Screen Time</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage blocking rules, screen time budgets, and bedtime schedules
          </p>
        </div>
        {activeTab === "rules" && (
          <Button onClick={() => setShowForm(!showForm)}>
            <Plus className="h-4 w-4" />
            New Rule
          </Button>
        )}
      </div>

      {/* Tab bar */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1">
        {([
          { key: "rules" as const, label: "Block Rules", icon: Ban },
          { key: "screen-time" as const, label: "Screen Time", icon: Timer },
          { key: "bedtime" as const, label: "Bedtime", icon: Moon },
        ]).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-1.5 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {activeTab === "rules" && (
        <div>

      {/* Effectiveness Charts */}
      {effectiveness && (
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-4">
          <Card>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-orange-50 p-2">
                <Shield className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Active Rules</p>
                <p className="text-xl font-semibold text-gray-900">
                  {effectiveness.total_rules}
                </p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-red-50 p-2">
                <Ban className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Members Blocked</p>
                <p className="text-xl font-semibold text-gray-900">
                  {effectiveness.blocked_count}
                </p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-blue-50 p-2">
                <BarChart3 className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Events</p>
                <p className="text-xl font-semibold text-gray-900">
                  {effectiveness.total_events}
                </p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-teal-50 p-2">
                <Shield className="h-5 w-5 text-teal-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Block Rate</p>
                <p className="text-xl font-semibold text-gray-900">
                  {effectiveness.block_rate_pct}%
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Pending Approvals Queue */}
      {pending.length > 0 && (
        <Card title="Pending Unblock Requests" className="mb-6">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-4 py-3 text-left font-medium text-gray-500">
                    Member
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">
                    Reason
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">
                    Requested
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {pending.map((approval) => (
                  <tr
                    key={approval.id}
                    className="border-b border-gray-50 last:border-0"
                  >
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {approval.member_id}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {approval.reason}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(approval.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => handleApprove(approval.id)}
                          isLoading={approveUnblock.isPending}
                        >
                          <CheckCircle className="h-4 w-4" />
                          Approve
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => handleDeny(approval.id)}
                          isLoading={denyUnblock.isPending}
                        >
                          <XCircle className="h-4 w-4" />
                          Deny
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Create Form */}
      {showForm && (
        <Card title="Create Block Rule" className="mb-6">
          <div className="max-w-lg space-y-4">
            {createRule.isError && (
              <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {(createRule.error as Error)?.message || "Failed to create rule"}
              </div>
            )}
            <Input
              label="Member ID"
              value={memberId}
              onChange={(e) => setMemberId(e.target.value)}
              placeholder="Enter member ID to block"
            />
            <Input
              label="Platforms (optional)"
              value={platforms}
              onChange={(e) => setPlatforms(e.target.value)}
              placeholder="e.g. chatgpt, gemini, claude"
              helperText="Comma-separated list. Leave empty to block all platforms."
            />
            <Input
              label="Reason (optional)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why is this member being blocked?"
            />
            <div className="flex gap-2 pt-2">
              <Button
                onClick={handleCreate}
                isLoading={createRule.isPending}
                disabled={!memberId.trim()}
              >
                Create Rule
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setShowForm(false);
                  setMemberId("");
                  setPlatforms("");
                  setReason("");
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Rules Table */}
      <Card>
        {activeRules.length === 0 ? (
          <div className="py-12 text-center">
            <Ban className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-sm text-gray-500">No active block rules</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-4 py-3 text-left font-medium text-gray-500">
                    Member
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">
                    Platforms
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">
                    Reason
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">
                    Expires
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">
                    Created
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {activeRules.map((rule) => (
                  <tr
                    key={rule.id}
                    className="border-b border-gray-50 last:border-0"
                  >
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {rule.member_id}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {rule.platforms && rule.platforms.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {rule.platforms.map((p) => (
                            <span
                              key={p}
                              className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700"
                            >
                              {p}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-gray-400">All platforms</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {rule.reason || (
                        <span className="text-gray-400">No reason</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {rule.expires_at ? (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5 text-gray-400" />
                          {new Date(rule.expires_at).toLocaleDateString()}
                        </span>
                      ) : (
                        <span className="text-gray-400">Never</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(rule.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {confirmRevoke === rule.id ? (
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => handleRevoke(rule.id)}
                            isLoading={revokeRule.isPending}
                          >
                            Confirm
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setConfirmRevoke(null)}
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setConfirmRevoke(rule.id)}
                          aria-label={`Revoke block rule for member ${rule.member_id}`}
                        >
                          <Trash2 className="h-4 w-4" />
                          Revoke
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      </div>
      )}

      {/* Screen Time tab */}
      {activeTab === "screen-time" && (
        <ScreenTimeTab groupId={groupId} />
      )}

      {/* Bedtime tab */}
      {activeTab === "bedtime" && (
        <BedtimeTab groupId={groupId} />
      )}
    </div>
  );
}

// ─── Screen Time Tab ────────────────────────────────────────────────────────

function ScreenTimeTab({ groupId }: { groupId: string | null }) {
  const { data: members } = useQuery<{ items: Array<{ id: string; display_name: string }> }>({
    queryKey: ["members-list", groupId],
    queryFn: () => apiFetch(`/api/v1/groups/${groupId}/members?page_size=50`),
    enabled: !!groupId,
  });

  if (!members?.items?.length) {
    return (
      <Card>
        <div className="py-12 text-center">
          <Timer className="mx-auto h-12 w-12 text-gray-300" />
          <p className="mt-4 text-sm text-gray-500">No members to configure screen time for</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {members.items.map((member) => (
        <ScreenTimeMemberRow key={member.id} groupId={groupId!} member={member} />
      ))}
    </div>
  );
}

function ScreenTimeMemberRow({
  groupId,
  member,
}: {
  groupId: string;
  member: { id: string; display_name: string };
}) {
  const { data: budget } = useQuery({
    queryKey: ["time-budget", "budget", groupId, member.id],
    queryFn: () =>
      apiFetch<{
        enabled: boolean;
        weekday_minutes: number;
        weekend_minutes: number;
        minutes_used: number;
        budget_minutes: number;
        remaining: number;
        exceeded: boolean;
        warn: boolean;
      }>(`/api/v1/blocking/time-budget/${member.id}?group_id=${groupId}`),
    enabled: !!groupId,
  });

  const pct = budget?.budget_minutes
    ? Math.min(100, Math.round((budget.minutes_used / budget.budget_minutes) * 100))
    : 0;

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary">
            {member.display_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">{member.display_name}</p>
            {budget?.enabled ? (
              <p className="text-xs text-gray-500">
                {budget.minutes_used} / {budget.budget_minutes} min today
                {budget.exceeded && <span className="ml-1 font-medium text-red-600">Exceeded</span>}
                {budget.warn && !budget.exceeded && (
                  <span className="ml-1 font-medium text-amber-600">Warning</span>
                )}
              </p>
            ) : (
              <p className="text-xs text-gray-400">No budget set</p>
            )}
          </div>
        </div>
        {budget?.enabled && (
          <div className="flex items-center gap-3">
            <div className="h-2 w-24 rounded-full bg-gray-200">
              <div
                className={`h-2 rounded-full ${
                  pct >= 100 ? "bg-red-500" : pct >= 75 ? "bg-amber-500" : "bg-teal-500"
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs font-medium text-gray-600">{pct}%</span>
          </div>
        )}
      </div>
    </Card>
  );
}

// ─── Bedtime Tab ────────────────────────────────────────────────────────────

function BedtimeTab({ groupId }: { groupId: string | null }) {
  const { data: members } = useQuery<{ items: Array<{ id: string; display_name: string }> }>({
    queryKey: ["members-list", groupId],
    queryFn: () => apiFetch(`/api/v1/groups/${groupId}/members?page_size=50`),
    enabled: !!groupId,
  });

  if (!members?.items?.length) {
    return (
      <Card>
        <div className="py-12 text-center">
          <Moon className="mx-auto h-12 w-12 text-gray-300" />
          <p className="mt-4 text-sm text-gray-500">No members to configure bedtime for</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {members.items.map((member) => (
        <BedtimeMemberRow key={member.id} groupId={groupId!} member={member} />
      ))}
    </div>
  );
}

function BedtimeMemberRow({
  groupId,
  member,
}: {
  groupId: string;
  member: { id: string; display_name: string };
}) {
  const { data: bedtime } = useQuery({
    queryKey: ["time-budget", "bedtime", groupId, member.id],
    queryFn: () =>
      apiFetch<{
        enabled: boolean;
        start_hour: number | null;
        end_hour: number | null;
        timezone: string;
      }>(`/api/v1/blocking/bedtime/${member.id}?group_id=${groupId}`),
    enabled: !!groupId,
  });

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-600">
            {member.display_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">{member.display_name}</p>
            {bedtime?.enabled ? (
              <p className="text-xs text-gray-500">
                Bedtime: {bedtime.start_hour}:00 &ndash; {bedtime.end_hour}:00
              </p>
            ) : (
              <p className="text-xs text-gray-400">Bedtime not configured</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Moon className={`h-4 w-4 ${bedtime?.enabled ? "text-indigo-500" : "text-gray-300"}`} />
          <span className={`text-xs font-medium ${bedtime?.enabled ? "text-indigo-600" : "text-gray-400"}`}>
            {bedtime?.enabled ? "Active" : "Off"}
          </span>
        </div>
      </div>
    </Card>
  );
}
