"use client";

import {
  FileBarChart,
  Download,
  Calendar,
  Shield,
  TrendingUp,
  Users,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface ReportItem {
  id: string;
  title: string;
  description: string;
  type: "safety" | "spend" | "activity" | "compliance";
  period: string;
  generatedAt: string;
  status: "ready" | "generating";
}

const placeholderReports: ReportItem[] = [
  {
    id: "1",
    title: "Weekly Safety Summary",
    description:
      "Overview of risk events, blocked content, and safety trends across all members.",
    type: "safety",
    period: "10 Feb - 16 Feb 2026",
    generatedAt: "17 Feb 2026",
    status: "ready",
  },
  {
    id: "2",
    title: "Monthly Spend Report",
    description:
      "Detailed breakdown of AI API costs by member, provider, and model.",
    type: "spend",
    period: "January 2026",
    generatedAt: "1 Feb 2026",
    status: "ready",
  },
  {
    id: "3",
    title: "Member Activity Report",
    description:
      "Usage patterns, session durations, and interaction types per member.",
    type: "activity",
    period: "10 Feb - 16 Feb 2026",
    generatedAt: "17 Feb 2026",
    status: "ready",
  },
  {
    id: "4",
    title: "Compliance Report",
    description:
      "Regulatory compliance status, policy adherence, and audit trail for your organisation.",
    type: "compliance",
    period: "Q1 2026",
    generatedAt: "Generating...",
    status: "generating",
  },
];

const typeIcons = {
  safety: Shield,
  spend: TrendingUp,
  activity: Users,
  compliance: FileBarChart,
};

const typeColors = {
  safety: "bg-red-50 text-red-600",
  spend: "bg-green-50 text-green-600",
  activity: "bg-blue-50 text-blue-600",
  compliance: "bg-purple-50 text-purple-600",
};

export default function ReportsPage() {
  return (
    <div>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
          <p className="mt-1 text-sm text-gray-500">
            Generated reports on AI usage, safety, and compliance
          </p>
        </div>
        <Button>
          <FileBarChart className="h-4 w-4" />
          Generate Report
        </Button>
      </div>

      {/* Quick Stats */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
              <FileBarChart className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">12</p>
              <p className="text-sm text-gray-500">Reports generated</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50">
              <Calendar className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">Weekly</p>
              <p className="text-sm text-gray-500">Auto-generate schedule</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50">
              <Download className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">PDF / CSV</p>
              <p className="text-sm text-gray-500">Export formats</p>
            </div>
          </div>
        </div>
      </div>

      {/* Reports List */}
      <div className="space-y-4">
        {placeholderReports.map((report) => {
          const TypeIcon = typeIcons[report.type];
          const colorClass = typeColors[report.type];

          return (
            <Card key={report.id}>
              <div className="flex items-start gap-4">
                <div
                  className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${colorClass}`}
                >
                  <TypeIcon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900">
                        {report.title}
                      </h3>
                      <p className="mt-0.5 text-xs text-gray-400">
                        Period: {report.period}
                      </p>
                    </div>
                    {report.status === "ready" ? (
                      <Button variant="secondary" size="sm">
                        <Download className="h-3.5 w-3.5" />
                        Download
                      </Button>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
                        Generating
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-gray-600">
                    {report.description}
                  </p>
                  <p className="mt-2 text-xs text-gray-400">
                    Generated: {report.generatedAt}
                  </p>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
