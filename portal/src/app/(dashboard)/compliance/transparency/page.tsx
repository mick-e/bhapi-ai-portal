"use client";

import {
  Scale,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Brain,
  Database,
  Shield,
  Tag,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/use-auth";
import { useTransparencyReport } from "@/hooks/use-compliance";

export default function TransparencyPage() {
  const { user } = useAuth();
  const groupId = user?.group_id || null;

  const {
    data: report,
    isLoading,
    isError,
    error,
    refetch,
  } = useTransparencyReport(groupId);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">
          Loading transparency report...
        </span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load transparency report
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

  if (!report) {
    return (
      <div className="py-12 text-center">
        <Scale className="mx-auto h-12 w-12 text-gray-300" />
        <p className="mt-4 text-sm text-gray-500">
          No transparency report available
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Algorithmic Transparency
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          EU AI Act compliance report detailing how risk classification works
        </p>
      </div>

      <div className="space-y-6">
        {/* Classification Approach */}
        <Card
          title="Classification Approach"
          description="How the system classifies and assesses risk"
        >
          <div className="flex items-start gap-3">
            <Brain className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary-600" />
            <p className="text-sm text-gray-700 leading-relaxed">
              {report.classification_approach}
            </p>
          </div>
        </Card>

        {/* Categories */}
        <Card
          title="Risk Categories"
          description="Content categories monitored by the system"
        >
          <div className="flex items-start gap-3">
            <Tag className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary-600" />
            <div className="flex flex-wrap gap-2">
              {report.categories.map((category) => (
                <span
                  key={category}
                  className="rounded-full bg-primary-50 px-3 py-1 text-sm font-medium text-primary-700"
                >
                  {category.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </div>
        </Card>

        {/* Data Sources */}
        <Card
          title="Data Sources"
          description="Where the system collects data from"
        >
          <div className="flex items-start gap-3">
            <Database className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary-600" />
            <ul className="space-y-2">
              {report.data_sources.map((source) => (
                <li
                  key={source}
                  className="flex items-center gap-2 text-sm text-gray-700"
                >
                  <span className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary-400" />
                  {source}
                </li>
              ))}
            </ul>
          </div>
        </Card>

        {/* User Rights */}
        <Card
          title="Your Rights Under EU AI Act"
          description="Rights available to users of this system"
        >
          <div className="flex items-start gap-3">
            <Shield className="mt-0.5 h-5 w-5 flex-shrink-0 text-teal-600" />
            <ul className="space-y-3">
              {report.rights.map((right) => (
                <li
                  key={right}
                  className="flex items-start gap-2 text-sm text-gray-700"
                >
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-teal-500" />
                  {right}
                </li>
              ))}
            </ul>
          </div>
        </Card>
      </div>
    </div>
  );
}
