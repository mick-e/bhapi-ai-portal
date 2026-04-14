"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  GraduationCap,
  Users,
  AlertTriangle,
  Plus,
  Loader2,
  RefreshCw,
  Shield,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/contexts/ToastContext";
import { useTranslations } from "@/contexts/LocaleContext";
import { api } from "@/lib/api-client";

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

interface SafeguardingReport {
  period_start: string;
  period_end: string;
  total_risks: number;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
  flagged_students: Array<{
    member_id: string;
    display_name: string;
    risk_count: number;
  }>;
}

export default function SchoolPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const t = useTranslations("school");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [className, setClassName] = useState("");
  const [gradeLevel, setGradeLevel] = useState("");
  const [academicYear, setAcademicYear] = useState("");

  const {
    data: classes,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<ClassGroup[]>({
    queryKey: ["school-classes"],
    queryFn: () => api.get("/api/v1/school/classes"),
  });

  const { data: report } = useQuery<SafeguardingReport>({
    queryKey: ["safeguarding-report"],
    queryFn: () => api.get("/api/v1/school/safeguarding-report"),
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; grade_level?: string; academic_year?: string }) =>
      api.post("/api/v1/school/classes", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["school-classes"] });
      setShowCreateModal(false);
      setClassName("");
      setGradeLevel("");
      setAcademicYear("");
      addToast(t("toastClassCreated"), "success");
    },
    onError: (err) => {
      addToast((err as Error).message || t("toastCreateFailed"), "error");
    },
  });

  const totalStudents = (classes ?? []).reduce((sum, c) => sum + c.member_count, 0);

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
        <p className="mt-3 text-sm font-medium text-gray-900">{t("loadError")}</p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || t("somethingWentWrong")}
        </p>
        <Button variant="secondary" size="sm" className="mt-4" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
          {t("tryAgain")}
        </Button>
      </div>
    );
  }

  const severityColors: Record<string, string> = {
    low: "bg-green-100 text-green-700",
    medium: "bg-amber-100 text-amber-700",
    high: "bg-red-100 text-red-700",
    critical: "bg-red-200 text-red-800",
  };

  return (
    <div>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {t("subtitle")}
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4" />
          {t("createClass")}
        </Button>
      </div>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
              <GraduationCap className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{(classes ?? []).length}</p>
              <p className="text-sm text-gray-500">{t("classes")}</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
              <Users className="h-5 w-5 text-accent" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalStudents}</p>
              <p className="text-sm text-gray-500">{t("totalStudents")}</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50">
              <AlertTriangle className="h-5 w-5 text-red-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{report?.total_risks ?? 0}</p>
              <p className="text-sm text-gray-500">{t("risks30Days")}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Heat Map */}
      {report && report.total_risks > 0 && (
        <Card title={t("riskHeatMap")}>
          <div className="mb-4">
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
              {t("bySeverity")}
            </h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(report.by_severity).map(([severity, count]) => (
                <span
                  key={severity}
                  className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium ${severityColors[severity] || "bg-gray-100 text-gray-700"}`}
                >
                  {severity}: {count}
                </span>
              ))}
            </div>
          </div>
          <div className="mb-4">
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
              {t("byCategory")}
            </h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(report.by_category).map(([category, count]) => (
                <span
                  key={category}
                  className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700"
                >
                  {category}: {count}
                </span>
              ))}
            </div>
          </div>
          {report.flagged_students.length > 0 && (
            <div>
              <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                {t("flaggedStudents")}
              </h4>
              <div className="space-y-2">
                {report.flagged_students.map((student) => (
                  <div
                    key={student.member_id}
                    className="flex items-center justify-between rounded-lg bg-red-50 px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-red-500" />
                      <span className="text-sm font-medium text-gray-900">
                        {student.display_name}
                      </span>
                    </div>
                    <span className="text-xs font-medium text-red-600">
                      {student.risk_count} {student.risk_count !== 1 ? t("risksLabel") : t("riskLabel")}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Class List */}
      <div className="mt-6">
        <Card title={t("classes")}>
          {(classes ?? []).length === 0 ? (
            <div className="py-8 text-center">
              <GraduationCap className="mx-auto h-10 w-10 text-gray-300" />
              <p className="mt-3 text-sm text-gray-500">
                {t("noClassesYet")}
              </p>
            </div>
          ) : (
            <div className="-mx-6 -my-4 overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      {t("colClass")}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      {t("colGrade")}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      {t("colYear")}
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                      {t("colStudents")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {(classes ?? []).map((cls) => (
                    <tr
                      key={cls.id}
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() => router.push(`/school/class?id=${cls.id}`)}
                    >
                      <td className="whitespace-nowrap px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-50">
                            <GraduationCap className="h-4 w-4 text-primary" />
                          </div>
                          <span className="text-sm font-medium text-gray-900">{cls.name}</span>
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                        {cls.grade_level || "-"}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                        {cls.academic_year || "-"}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium text-gray-900">
                        {cls.member_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      {/* Create Class Modal */}
      {showCreateModal && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/30"
            onClick={() => setShowCreateModal(false)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="create-class-title"
              className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
            >
              <h2 id="create-class-title" className="text-lg font-bold text-gray-900">
                {t("createClass")}
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                {t("modalSubtitle")}
              </p>
              <div className="mt-4 space-y-4">
                <Input
                  label={t("classNameLabel")}
                  placeholder={t("classNamePlaceholder")}
                  value={className}
                  onChange={(e) => setClassName(e.target.value)}
                />
                <Input
                  label={t("gradeLevelLabel")}
                  placeholder={t("gradeLevelPlaceholder")}
                  value={gradeLevel}
                  onChange={(e) => setGradeLevel(e.target.value)}
                />
                <Input
                  label={t("academicYearLabel")}
                  placeholder={t("academicYearPlaceholder")}
                  value={academicYear}
                  onChange={(e) => setAcademicYear(e.target.value)}
                />
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setShowCreateModal(false);
                    setClassName("");
                    setGradeLevel("");
                    setAcademicYear("");
                  }}
                >
                  {t("cancel")}
                </Button>
                <Button
                  onClick={() =>
                    createMutation.mutate({
                      name: className,
                      grade_level: gradeLevel || undefined,
                      academic_year: academicYear || undefined,
                    })
                  }
                  isLoading={createMutation.isPending}
                  disabled={!className}
                >
                  {t("createClass")}
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
