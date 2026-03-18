"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { GraduationCap, Users, AlertTriangle, Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";

interface ClassData {
  id: string;
  name: string;
  grade_level: string | null;
  member_count: number;
}

interface TeacherDashboard {
  teacher_id: string;
  group_id: string;
  classes: ClassData[];
  total_classes: number;
  unread_alerts: number;
}

export default function TeacherDashboardPage() {
  const [data, setData] = useState<TeacherDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<TeacherDashboard>("/api/v1/school/teacher-dashboard")
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
  }

  if (error) {
    return <div className="text-center py-16"><AlertTriangle className="mx-auto h-10 w-10 text-amber-500" /><p className="mt-3 text-sm text-gray-600">{error}</p></div>;
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Teacher Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Manage your classes and monitor student AI usage</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 mb-8">
        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
          <GraduationCap className="h-5 w-5 text-primary" />
          <p className="mt-2 text-3xl font-bold text-gray-900">{data?.total_classes ?? 0}</p>
          <p className="text-sm text-gray-500">Classes</p>
        </div>
        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
          <Users className="h-5 w-5 text-green-600" />
          <p className="mt-2 text-3xl font-bold text-gray-900">{data?.classes.reduce((s, c) => s + c.member_count, 0) ?? 0}</p>
          <p className="text-sm text-gray-500">Total students</p>
        </div>
        <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <p className="mt-2 text-3xl font-bold text-gray-900">{data?.unread_alerts ?? 0}</p>
          <p className="text-sm text-gray-500">Unread alerts</p>
        </div>
      </div>

      <Card title="Your Classes">
        {data?.classes.length === 0 ? (
          <p className="py-6 text-center text-sm text-gray-500">No classes assigned yet</p>
        ) : (
          <div className="space-y-3">
            {data?.classes.map((cls) => (
              <div key={cls.id} className="flex items-center justify-between rounded-lg border border-gray-200 p-4">
                <div>
                  <p className="font-medium text-gray-900">{cls.name}</p>
                  {cls.grade_level && <p className="text-xs text-gray-500">{cls.grade_level}</p>}
                </div>
                <span className="text-sm text-gray-500">{cls.member_count} students</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
