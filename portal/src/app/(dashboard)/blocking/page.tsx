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
  Shield,
  Timer,
  Moon,
  ShieldCheck,
  ShieldAlert,
  Users,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
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

const AI_PLATFORMS = [
  "ChatGPT",
  "Gemini",
  "Copilot",
  "Claude",
  "Grok",
  "Character.AI",
  "Replika",
  "Pi",
  "Perplexity",
  "Poe",
];

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

  // Members list for the child picker
  const { data: membersData } = useQuery<{ items: Array<{ id: string; display_name: string }> }>({
    queryKey: ["members-list", groupId],
    queryFn: () => apiFetch(`/api/v1/groups/${groupId}/members?page_size=50`),
    enabled: !!groupId,
  });
  const membersList = membersData?.items ?? [];
  const membersMap = new Map(membersList.map((m) => [m.id, m.display_name]));

  const createRule = useCreateBlockRule();
  const revokeRule = useRevokeBlockRule();
  const approveUnblock = useApproveUnblock();
  const denyUnblock = useDenyUnblock();

  const [activeTab, setActiveTab] = useState<"rules" | "screen-time" | "bedtime">("rules");
  const [showForm, setShowForm] = useState(false);
  const [selectedMemberId, setSelectedMemberId] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(new Set());
  const [blockAllPlatforms, setBlockAllPlatforms] = useState(true);
  const [reason, setReason] = useState("");
  const [confirmRevoke, setConfirmRevoke] = useState<string | null>(null);

  function getMemberName(memberId: string) {
    return membersMap.get(memberId) || memberId;
  }

  function togglePlatform(platform: string) {
    setSelectedPlatforms((prev) => {
      const next = new Set(prev);
      if (next.has(platform)) next.delete(platform);
      else next.add(platform);
      return next;
    });
  }

  function handleCreate() {
    if (!groupId || !selectedMemberId) return;
    const platformList = blockAllPlatforms
      ? undefined
      : Array.from(selectedPlatforms);
    createRule.mutate(
      {
        group_id: groupId,
        member_id: selectedMemberId,
        platforms: platformList,
        reason: reason.trim() || undefined,
      },
      {
        onSuccess: () => {
          addToast("Block rule created", "success");
          setShowForm(false);
          setSelectedMemberId("");
          setSelectedPlatforms(new Set());
          setBlockAllPlatforms(true);
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
          addToast("Block rule removed", "success");
          setConfirmRevoke(null);
        },
        onError: (err) =>
          addToast((err as Error).message || "Failed to remove rule", "error"),
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
        <span className="ml-3 text-sm text-gray-500">Loading...</span>
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
          <h1 className="text-2xl font-bold text-gray-900">AI Controls</h1>
          <p className="mt-1 text-sm text-gray-500">
            Control which AI tools your children can use and when
          </p>
        </div>
        {activeTab === "rules" && (
          <Button onClick={() => setShowForm(!showForm)}>
            <Plus className="h-4 w-4" />
            Block an AI Platform
          </Button>
        )}
      </div>

      {/* Tab bar */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1">
        {([
          { key: "rules" as const, label: "Blocked Platforms", icon: Ban },
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
          {/* Summary stats */}
          {effectiveness && (
            <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Card>
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-teal-50 p-2">
                    <ShieldCheck className="h-5 w-5 text-teal-600" />
                  </div>
                  <div>
                    <p className="text-xl font-semibold text-gray-900">
                      {effectiveness.total_rules}
                    </p>
                    <p className="text-sm text-gray-500">Active block rules</p>
                  </div>
                </div>
              </Card>
              <Card>
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-orange-50 p-2">
                    <Users className="h-5 w-5 text-orange-600" />
                  </div>
                  <div>
                    <p className="text-xl font-semibold text-gray-900">
                      {effectiveness.blocked_count}
                    </p>
                    <p className="text-sm text-gray-500">Children protected</p>
                  </div>
                </div>
              </Card>
              <Card>
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-blue-50 p-2">
                    <ShieldAlert className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-xl font-semibold text-gray-900">
                      {effectiveness.total_events}
                    </p>
                    <p className="text-sm text-gray-500">Blocked attempts</p>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {/* Pending Unblock Requests */}
          {pending.length > 0 && (
            <Card className="mb-6">
              <div className="mb-4">
                <h2 className="text-base font-semibold text-gray-900">Unblock Requests</h2>
                <p className="mt-0.5 text-xs text-gray-500">Your children are asking to access blocked platforms</p>
              </div>
              <div className="space-y-3">
                {pending.map((approval) => (
                  <div
                    key={approval.id}
                    className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {getMemberName(approval.member_id)}
                      </p>
                      <p className="text-xs text-gray-600">
                        &ldquo;{approval.reason}&rdquo; &middot; {new Date(approval.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleApprove(approval.id)}
                        isLoading={approveUnblock.isPending}
                      >
                        <CheckCircle className="h-4 w-4" />
                        Allow
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleDeny(approval.id)}
                        isLoading={denyUnblock.isPending}
                      >
                        <XCircle className="h-4 w-4" />
                        Keep Blocked
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Create Block Rule Form */}
          {showForm && (
            <Card className="mb-6">
              <h2 className="text-base font-semibold text-gray-900">Block an AI Platform</h2>
              <p className="mt-0.5 mb-4 text-xs text-gray-500">
                Choose a child and the AI platforms you want to block
              </p>
              <div className="max-w-lg space-y-5">
                {createRule.isError && (
                  <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                    {(createRule.error as Error)?.message || "Failed to create rule"}
                  </div>
                )}

                {/* Child picker */}
                <div>
                  <label htmlFor="block-member" className="mb-1.5 block text-sm font-medium text-gray-700">
                    Which child?
                  </label>
                  {membersList.length === 0 ? (
                    <p className="text-sm text-gray-500">
                      No members in your group yet. <a href="/members" className="font-medium text-primary-700 underline">Invite a member</a> first.
                    </p>
                  ) : (
                    <select
                      id="block-member"
                      value={selectedMemberId}
                      onChange={(e) => setSelectedMemberId(e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                    >
                      <option value="">Select a child...</option>
                      {membersList.map((m) => (
                        <option key={m.id} value={m.id}>{m.display_name}</option>
                      ))}
                    </select>
                  )}
                </div>

                {/* Platform picker */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700">
                    Which AI platforms?
                  </label>
                  <label className="mb-3 flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={blockAllPlatforms}
                      onChange={(e) => setBlockAllPlatforms(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm font-medium text-gray-700">Block all AI platforms</span>
                  </label>
                  {!blockAllPlatforms && (
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                      {AI_PLATFORMS.map((platform) => (
                        <label
                          key={platform}
                          className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
                            selectedPlatforms.has(platform.toLowerCase())
                              ? "border-primary bg-primary-50 text-primary-700"
                              : "border-gray-200 bg-white text-gray-700 hover:border-gray-300"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedPlatforms.has(platform.toLowerCase())}
                            onChange={() => togglePlatform(platform.toLowerCase())}
                            className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          {platform}
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                {/* Reason */}
                <div>
                  <label htmlFor="block-reason" className="mb-1.5 block text-sm font-medium text-gray-700">
                    Reason <span className="font-normal text-gray-400">(optional)</span>
                  </label>
                  <input
                    id="block-reason"
                    type="text"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="e.g. Too much time on ChatGPT this week"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>

                <div className="flex gap-2 pt-1">
                  <Button
                    onClick={handleCreate}
                    isLoading={createRule.isPending}
                    disabled={!selectedMemberId || (!blockAllPlatforms && selectedPlatforms.size === 0)}
                  >
                    Create Block Rule
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setShowForm(false);
                      setSelectedMemberId("");
                      setSelectedPlatforms(new Set());
                      setBlockAllPlatforms(true);
                      setReason("");
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            </Card>
          )}

          {/* Active Rules */}
          <Card>
            {activeRules.length === 0 ? (
              <div className="py-12 text-center">
                <Shield className="mx-auto h-12 w-12 text-gray-300" />
                <p className="mt-4 text-sm font-medium text-gray-700">No active block rules</p>
                <p className="mt-1 max-w-sm mx-auto text-xs text-gray-500">
                  Block rules prevent your children from accessing specific AI platforms.
                  Click &ldquo;Block an AI Platform&rdquo; above to create your first rule.
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-4"
                  onClick={() => setShowForm(true)}
                >
                  <Plus className="h-4 w-4" />
                  Block an AI Platform
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="px-4 py-3 text-left font-medium text-gray-500">Child</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-500">Blocked Platforms</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-500">Reason</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-500">Expires</th>
                      <th className="px-4 py-3 text-left font-medium text-gray-500">Created</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-500">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeRules.map((rule) => (
                      <tr key={rule.id} className="border-b border-gray-50 last:border-0">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary">
                              {getMemberName(rule.member_id).charAt(0).toUpperCase()}
                            </div>
                            <span className="font-medium text-gray-900">
                              {getMemberName(rule.member_id)}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {rule.platforms && rule.platforms.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {rule.platforms.map((p) => (
                                <span
                                  key={p}
                                  className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700"
                                >
                                  {p}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                              All platforms
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {rule.reason || <span className="text-gray-400">&mdash;</span>}
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {rule.expires_at ? (
                            <span className="flex items-center gap-1">
                              <Clock className="h-3.5 w-3.5 text-gray-400" />
                              {new Date(rule.expires_at).toLocaleDateString()}
                            </span>
                          ) : (
                            <span className="text-gray-400">Until removed</span>
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
                                Yes, Remove
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
                              aria-label={`Remove block rule for ${getMemberName(rule.member_id)}`}
                            >
                              <Trash2 className="h-4 w-4" />
                              Remove
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
          <p className="mt-4 text-sm font-medium text-gray-700">No members yet</p>
          <p className="mt-1 text-xs text-gray-500">
            <a href="/members" className="font-medium text-primary-700 underline">Add a family member</a> to start managing screen time.
          </p>
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
                {budget.exceeded && <span className="ml-1 font-medium text-red-600">Limit reached</span>}
                {budget.warn && !budget.exceeded && (
                  <span className="ml-1 font-medium text-amber-600">Almost at limit</span>
                )}
              </p>
            ) : (
              <p className="text-xs text-gray-400">No daily limit set</p>
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

function formatHour(hour: number): string {
  const period = hour >= 12 ? "PM" : "AM";
  const h = hour % 12 || 12;
  return `${h}:00 ${period}`;
}

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
          <p className="mt-4 text-sm font-medium text-gray-700">No members yet</p>
          <p className="mt-1 text-xs text-gray-500">
            <a href="/members" className="font-medium text-primary-700 underline">Add a family member</a> to start managing bedtime schedules.
          </p>
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
            {bedtime?.enabled && bedtime.start_hour != null && bedtime.end_hour != null ? (
              <p className="text-xs text-gray-500">
                AI blocked {formatHour(bedtime.start_hour)} &ndash; {formatHour(bedtime.end_hour)}
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
