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
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/use-auth";
import {
  useBlockRules,
  useCreateBlockRule,
  useRevokeBlockRule,
} from "@/hooks/use-blocking";
import { useToast } from "@/contexts/ToastContext";

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

  const createRule = useCreateBlockRule();
  const revokeRule = useRevokeBlockRule();

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

  return (
    <div>
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Blocking Rules</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage content and platform blocking for group members
            {activeRules.length > 0 && (
              <span className="ml-1 text-gray-400">
                ({activeRules.length} active)
              </span>
            )}
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4" />
          New Rule
        </Button>
      </div>

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
  );
}
