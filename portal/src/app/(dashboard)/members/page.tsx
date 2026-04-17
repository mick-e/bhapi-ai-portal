"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Users,
  UserPlus,
  Search,
  MoreVertical,
  Shield,
  Mail,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Trash2,
  UserCog,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { OnboardingCard } from "@/components/ui/OnboardingCard";
import {
  useMembers,
  useInviteMember,
  useUpdateMember,
  useRemoveMember,
  useBulkUpdateMembers,
  useBulkRemoveMembers,
} from "@/hooks/use-members";
import { useToast } from "@/contexts/ToastContext";
import { useTranslations } from "@/contexts/LocaleContext";

export default function MembersPage() {
  const t = useTranslations("members");
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Invite form state
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"admin" | "member" | "viewer">(
    "member"
  );

  const pageSize = 20;
  const {
    data: membersData,
    isLoading,
    isError,
    error,
    refetch,
  } = useMembers({ page, page_size: pageSize, search: searchQuery || undefined });

  const { addToast } = useToast();
  const inviteMutation = useInviteMember();
  const updateMutation = useUpdateMember();
  const removeMutation = useRemoveMember();
  const bulkUpdateMutation = useBulkUpdateMembers();
  const bulkRemoveMutation = useBulkRemoveMembers();

  const members = membersData?.items ?? [];
  const totalPages = membersData?.total_pages ?? 1;
  const totalMembers = membersData?.total ?? 0;

  const activeCount = members.filter((m) => m.status === "active").length;
  const invitedCount = members.filter((m) => m.status === "invited").length;

  function handleInvite() {
    if (!inviteEmail) return;
    inviteMutation.mutate(
      { email: inviteEmail, role: inviteRole },
      {
        onSuccess: () => {
          setShowInviteModal(false);
          setInviteEmail("");
          setInviteRole("member");
          addToast("Invitation sent successfully", "success");
        },
        onError: (err) => {
          addToast((err as Error).message || "Failed to send invite", "error");
        },
      }
    );
  }

  function handleSuspend(memberId: string) {
    updateMutation.mutate(
      { memberId, data: { status: "suspended" } },
      {
        onSuccess: () => addToast("Member suspended", "success"),
        onError: (err) => addToast((err as Error).message || "Failed to suspend member", "error"),
      }
    );
    setMenuOpenId(null);
  }

  function handleActivate(memberId: string) {
    updateMutation.mutate(
      { memberId, data: { status: "active" } },
      {
        onSuccess: () => addToast("Member reactivated", "success"),
        onError: (err) => addToast((err as Error).message || "Failed to reactivate member", "error"),
      }
    );
    setMenuOpenId(null);
  }

  function handleRemove(memberId: string) {
    if (window.confirm("Are you sure you want to remove this member?")) {
      removeMutation.mutate(memberId, {
        onSuccess: () => addToast("Member removed", "success"),
        onError: (err) => addToast((err as Error).message || "Failed to remove member", "error"),
      });
    }
    setMenuOpenId(null);
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selectedIds.size === members.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(members.map((m) => m.id)));
    }
  }

  function handleBulkSuspend() {
    const ids = Array.from(selectedIds);
    bulkUpdateMutation.mutate(
      { memberIds: ids, data: { status: "suspended" } },
      {
        onSuccess: () => {
          addToast(`${ids.length} member(s) suspended`, "success");
          setSelectedIds(new Set());
        },
        onError: (err) => addToast((err as Error).message || "Bulk suspend failed", "error"),
      }
    );
  }

  function handleBulkActivate() {
    const ids = Array.from(selectedIds);
    bulkUpdateMutation.mutate(
      { memberIds: ids, data: { status: "active" } },
      {
        onSuccess: () => {
          addToast(`${ids.length} member(s) reactivated`, "success");
          setSelectedIds(new Set());
        },
        onError: (err) => addToast((err as Error).message || "Bulk activate failed", "error"),
      }
    );
  }

  function handleBulkRemove() {
    const ids = Array.from(selectedIds);
    if (!window.confirm(`Remove ${ids.length} member(s)? This cannot be undone.`)) return;
    bulkRemoveMutation.mutate(ids, {
      onSuccess: () => {
        addToast(`${ids.length} member(s) removed`, "success");
        setSelectedIds(new Set());
      },
      onError: (err) => addToast((err as Error).message || "Bulk remove failed", "error"),
    });
  }

  const isBulkLoading = bulkUpdateMutation.isPending || bulkRemoveMutation.isPending;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">{t("loading")}</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          {t("failedToLoad")}
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || t("somethingWentWrong")}
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

  return (
    <div>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {t("description")}
          </p>
        </div>
        <Button onClick={() => setShowInviteModal(true)}>
          <UserPlus className="h-4 w-4" />
          {t("inviteMember")}
        </Button>
      </div>

      <OnboardingCard
        id="members-intro"
        icon={Users}
        title="Add Your Family"
        description="Add each child you want to monitor. You can add up to 5 family members. Each child gets age-appropriate settings automatically."
        actionLabel="Add a Child"
        actionHref="/members?action=add"
      />

      {/* Stats */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
              <Users className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{activeCount}</p>
              <p className="text-sm text-gray-500">{t("activeMembers")}</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50">
              <Mail className="h-5 w-5 text-amber-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{invitedCount}</p>
              <p className="text-sm text-gray-500">{t("pendingInvites")}</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50">
              <Shield className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalMembers}</p>
              <p className="text-sm text-gray-500">{t("totalMembers")}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder={t("searchMembers")}
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            aria-label={t("searchAriaLabel")}
            className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      {/* Bulk Action Bar */}
      {selectedIds.size > 0 && (
        <div className="mb-4 flex items-center gap-3 rounded-lg bg-primary-50 px-4 py-3 ring-1 ring-primary-200">
          <span className="text-sm font-medium text-primary-700">
            {selectedIds.size} selected
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleBulkSuspend}
            isLoading={isBulkLoading}
          >
            Suspend
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleBulkActivate}
            isLoading={isBulkLoading}
          >
            Reactivate
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleBulkRemove}
            isLoading={isBulkLoading}
            className="text-red-600 hover:bg-red-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Remove
          </Button>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="ml-auto text-xs text-gray-500 hover:text-gray-700"
          >
            Clear selection
          </button>
        </div>
      )}

      {/* Members Table */}
      <Card>
        <div className="-mx-6 -my-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="w-10 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={members.length > 0 && selectedIds.size === members.length}
                    onChange={toggleSelectAll}
                    className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    aria-label="Select all members"
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Member
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Risk
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Last Active
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {members.map((member) => (
                <tr
                  key={member.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => router.push(`/members/detail?id=${member.id}`)}
                >
                  <td className="whitespace-nowrap px-4 py-4" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(member.id)}
                      onChange={() => toggleSelect(member.id)}
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      aria-label={`Select ${member.display_name}`}
                    />
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary">
                        {member.display_name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {member.display_name}
                        </p>
                        <p className="text-xs text-gray-500">{member.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600 capitalize">
                    {member.role}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <StatusBadge status={member.status} />
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <RiskBadge level={member.risk_level || "low"} />
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {member.last_active
                      ? formatRelativeTime(member.last_active)
                      : "Never"}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="relative inline-block">
                      <button
                        onClick={() =>
                          setMenuOpenId(
                            menuOpenId === member.id ? null : member.id
                          )
                        }
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                        aria-label={`Actions for ${member.display_name}`}
                        aria-expanded={menuOpenId === member.id}
                        aria-haspopup="true"
                      >
                        <MoreVertical className="h-4 w-4" aria-hidden="true" />
                      </button>
                      {menuOpenId === member.id && (
                        <>
                          <div
                            className="fixed inset-0 z-10"
                            onClick={() => setMenuOpenId(null)}
                          />
                          <div className="absolute right-0 z-20 mt-1 w-44 rounded-lg bg-white py-1 shadow-lg ring-1 ring-gray-200">
                            {member.status === "active" && (
                              <button
                                onClick={() => handleSuspend(member.id)}
                                className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                              >
                                <UserCog className="h-4 w-4" />
                                Suspend
                              </button>
                            )}
                            {member.status === "suspended" && (
                              <button
                                onClick={() => handleActivate(member.id)}
                                className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                              >
                                <UserCog className="h-4 w-4" />
                                Reactivate
                              </button>
                            )}
                            <button
                              onClick={() => handleRemove(member.id)}
                              className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                            >
                              <Trash2 className="h-4 w-4" />
                              Remove
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {members.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center">
                    <Users className="mx-auto h-10 w-10 text-gray-300" />
                    <p className="mt-3 text-sm text-gray-500">
                      {searchQuery
                        ? "No members match your search"
                        : "No members yet. Invite someone to get started."}
                    </p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Showing {members.length} of {totalMembers} members
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <span className="text-sm text-gray-600">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Invite Modal */}
      {showInviteModal && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setShowInviteModal(false)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="invite-modal-title"
              className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
            >
              <h2 id="invite-modal-title" className="text-lg font-bold text-gray-900">
                Invite a Member
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                Send an invitation to join your group
              </p>
              {inviteMutation.isError && (
                <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                  {(inviteMutation.error as Error)?.message ||
                    "Failed to send invite"}
                </div>
              )}
              <div className="mt-4 space-y-4">
                <Input
                  label="Email address"
                  type="email"
                  placeholder="member@example.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
                <div>
                  <label htmlFor="invite-role" className="mb-1.5 block text-sm font-medium text-gray-700">
                    Role
                  </label>
                  <select
                    id="invite-role"
                    value={inviteRole}
                    onChange={(e) =>
                      setInviteRole(
                        e.target.value as "admin" | "member" | "viewer"
                      )
                    }
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setShowInviteModal(false);
                    setInviteEmail("");
                    inviteMutation.reset();
                  }}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleInvite}
                  isLoading={inviteMutation.isPending}
                  disabled={!inviteEmail}
                >
                  Send Invite
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function StatusBadge({
  status,
}: {
  status: "active" | "invited" | "suspended";
}) {
  const styles = {
    active: "bg-green-100 text-green-700",
    invited: "bg-amber-100 text-amber-700",
    suspended: "bg-red-100 text-red-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {status}
    </span>
  );
}

function RiskBadge({ level }: { level: "low" | "medium" | "high" }) {
  const styles = {
    low: "bg-green-100 text-green-700",
    medium: "bg-amber-100 text-amber-700",
    high: "bg-red-100 text-red-700",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${styles[level]}`}
    >
      {level}
    </span>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────────────

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
    if (diffHours < 24)
      return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    if (diffDays < 7)
      return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
    return date.toLocaleDateString();
  } catch {
    return timestamp;
  }
}
