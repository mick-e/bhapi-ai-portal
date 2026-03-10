"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Users,
  AlertTriangle,
  Plus,
  Trash2,
  Loader2,
  RefreshCw,
  GraduationCap,
  Shield,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api-client";
import type { Group } from "@/types";

interface ClassGroup {
  id: string;
  group_id: string;
  name: string;
  grade_level: string | null;
  teacher_id: string | null;
  academic_year: string | null;
  member_count: number;
  created_at: string;
}

interface ClassMember {
  id: string;
  class_group_id: string;
  member_id: string;
  display_name: string;
  created_at: string;
}

interface RiskEvent {
  id: string;
  member_id: string;
  category: string;
  severity: string;
  confidence: number;
  created_at: string;
}

interface GroupMember {
  id: string;
  display_name: string;
  role: string;
}

export default function ClassDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-sm text-gray-500">Loading class...</span>
        </div>
      }
    >
      <ClassDetailContent />
    </Suspense>
  );
}

function ClassDetailContent() {
  const searchParams = useSearchParams();
  const classId = searchParams.get("id") || "";
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedMemberId, setSelectedMemberId] = useState("");

  // Fetch class list to get this class info
  const { data: classes } = useQuery<ClassGroup[]>({
    queryKey: ["school-classes"],
    queryFn: () => api.get("/api/v1/school/classes"),
  });
  const classInfo = (classes ?? []).find((c) => c.id === classId);

  // Fetch risks for this class
  const {
    data: risks,
    isLoading: risksLoading,
  } = useQuery<RiskEvent[]>({
    queryKey: ["class-risks", classId],
    queryFn: () => api.get(`/api/v1/school/classes/${classId}/risks`),
    enabled: !!classId,
  });

  // Fetch group members for the add modal
  const { data: groupMembers } = useQuery<GroupMember[]>({
    queryKey: ["group-members-for-class"],
    queryFn: async () => {
      // Use the groups API to get all members
      const groups = await api.get("/api/v1/groups") as Group[];
      if (groups && groups.length > 0) {
        return api.get(`/api/v1/groups/${groups[0].id}/members`);
      }
      return [];
    },
    enabled: showAddModal,
  });

  const addMemberMutation = useMutation({
    mutationFn: (memberId: string) =>
      api.post(`/api/v1/school/classes/${classId}/members`, {
        member_id: memberId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["school-classes"] });
      queryClient.invalidateQueries({ queryKey: ["class-risks", classId] });
      setShowAddModal(false);
      setSelectedMemberId("");
      addToast("Student added to class", "success");
    },
    onError: (err) => {
      addToast((err as Error).message || "Failed to add student", "error");
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: (memberId: string) =>
      api.delete(`/api/v1/school/classes/${classId}/members/${memberId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["school-classes"] });
      queryClient.invalidateQueries({ queryKey: ["class-risks", classId] });
      addToast("Student removed from class", "success");
    },
    onError: (err) => {
      addToast((err as Error).message || "Failed to remove student", "error");
    },
  });

  if (!classId) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">No class selected</p>
        <Link href="/school" className="mt-2 text-sm text-primary-700 hover:underline">
          Back to School Dashboard
        </Link>
      </div>
    );
  }

  if (!classInfo && !classes) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading class...</span>
      </div>
    );
  }

  if (!classInfo) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">Class not found</p>
        <Link href="/school" className="mt-2 text-sm text-primary-700 hover:underline">
          Back to School Dashboard
        </Link>
      </div>
    );
  }

  const severityColors: Record<string, string> = {
    low: "bg-green-100 text-green-700",
    medium: "bg-amber-100 text-amber-700",
    high: "bg-red-100 text-red-700",
    critical: "bg-red-200 text-red-800",
  };

  // Build per-member risk summary from risks data
  const memberRiskMap: Record<string, { count: number; maxSeverity: string }> = {};
  const severityOrder = ["low", "medium", "high", "critical"];
  for (const risk of risks ?? []) {
    if (!memberRiskMap[risk.member_id]) {
      memberRiskMap[risk.member_id] = { count: 0, maxSeverity: "low" };
    }
    memberRiskMap[risk.member_id].count += 1;
    if (
      severityOrder.indexOf(risk.severity) >
      severityOrder.indexOf(memberRiskMap[risk.member_id].maxSeverity)
    ) {
      memberRiskMap[risk.member_id].maxSeverity = risk.severity;
    }
  }

  return (
    <div>
      <Link
        href="/school"
        className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to School Dashboard
      </Link>

      {/* Class header */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-100">
            <GraduationCap className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{classInfo.name}</h1>
            <div className="mt-1 flex items-center gap-3 text-sm text-gray-500">
              {classInfo.grade_level && <span>{classInfo.grade_level}</span>}
              {classInfo.academic_year && <span>{classInfo.academic_year}</span>}
            </div>
          </div>
        </div>
        <Button onClick={() => setShowAddModal(true)}>
          <Plus className="h-4 w-4" />
          Add Student
        </Button>
      </div>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
              <Users className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{classInfo.member_count}</p>
              <p className="text-sm text-gray-500">Students</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{(risks ?? []).length}</p>
              <p className="text-sm text-gray-500">Risk events</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50">
              <Shield className="h-5 w-5 text-red-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {Object.values(memberRiskMap).filter((v) => v.maxSeverity === "high" || v.maxSeverity === "critical").length}
              </p>
              <p className="text-sm text-gray-500">High-risk students</p>
            </div>
          </div>
        </div>
      </div>

      {/* Student Safety Indicators - derived from risk data */}
      {Object.keys(memberRiskMap).length > 0 && (
        <div className="mb-6">
          <Card title="Student Safety Indicators">
            <div className="space-y-2">
              {Object.entries(memberRiskMap).map(([memberId, info]) => (
                <div
                  key={memberId}
                  className="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-gray-50"
                >
                  <span className="text-sm text-gray-700">
                    Student {memberId.slice(0, 8)}...
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      {info.count} risk{info.count !== 1 ? "s" : ""}
                    </span>
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${severityColors[info.maxSeverity]}`}
                    >
                      {info.maxSeverity}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Recent Risks */}
      <Card title="Recent Risks">
        {risksLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : (risks ?? []).length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500">
            No risk events for this class
          </p>
        ) : (
          <div className="-mx-6 -my-4 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Category
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Severity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Confidence
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Time
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {(risks ?? []).slice(0, 20).map((risk) => (
                  <tr key={risk.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-900">
                      {risk.category}
                    </td>
                    <td className="whitespace-nowrap px-6 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${severityColors[risk.severity]}`}
                      >
                        {risk.severity}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-600">
                      {Math.round(risk.confidence * 100)}%
                    </td>
                    <td className="whitespace-nowrap px-6 py-3 text-sm text-gray-500">
                      {formatRelativeTime(risk.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Add Student Modal */}
      {showAddModal && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setShowAddModal(false)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="add-student-title"
              className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
            >
              <h2 id="add-student-title" className="text-lg font-bold text-gray-900">
                Add Student to Class
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                Select a group member to add to this class
              </p>
              <div className="mt-4">
                <label htmlFor="member-select" className="mb-1.5 block text-sm font-medium text-gray-700">
                  Student
                </label>
                <select
                  id="member-select"
                  value={selectedMemberId}
                  onChange={(e) => setSelectedMemberId(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="">Select a student...</option>
                  {(groupMembers ?? [])
                    .filter((m) => m.role === "member")
                    .map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.display_name}
                      </option>
                    ))}
                </select>
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setShowAddModal(false);
                    setSelectedMemberId("");
                  }}
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => addMemberMutation.mutate(selectedMemberId)}
                  isLoading={addMemberMutation.isPending}
                  disabled={!selectedMemberId}
                >
                  Add Student
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
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
