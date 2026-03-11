"use client";

import { useState } from "react";
import {
  Shield,
  CheckCircle,
  XCircle,
  AlertTriangle,
  MinusCircle,
  Download,
  ClipboardCheck,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/use-auth";
import { useCOPPAChecklist, useCOPPAExport, useCOPPAReview } from "@/hooks/use-coppa";
import type { COPPAChecklistItem } from "@/types";

function ScoreGauge({ score, status }: { score: number; status: string }) {
  const color =
    status === "compliant"
      ? "text-green-600"
      : status === "partial"
        ? "text-amber-500"
        : "text-red-600";

  const bgColor =
    status === "compliant"
      ? "bg-green-50"
      : status === "partial"
        ? "bg-amber-50"
        : "bg-red-50";

  const badgeColor =
    status === "compliant"
      ? "bg-green-100 text-green-800"
      : status === "partial"
        ? "bg-amber-100 text-amber-800"
        : "bg-red-100 text-red-800";

  const statusLabel =
    status === "compliant"
      ? "Compliant"
      : status === "partial"
        ? "Partial"
        : "Non-Compliant";

  return (
    <div className="flex items-center gap-6">
      <div
        className={`flex h-24 w-24 items-center justify-center rounded-full ${bgColor}`}
      >
        <div className="text-center">
          <p className={`text-3xl font-bold ${color}`}>{Math.round(score)}%</p>
        </div>
      </div>
      <div>
        <span
          className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${badgeColor}`}
        >
          <Shield className="mr-1 h-4 w-4" />
          {statusLabel}
        </span>
        <p className="mt-2 text-sm text-gray-500">
          COPPA 2026 compliance score based on 12 automated checks.
        </p>
      </div>
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "complete":
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case "incomplete":
      return <XCircle className="h-5 w-5 text-red-500" />;
    case "warning":
      return <AlertTriangle className="h-5 w-5 text-amber-500" />;
    case "not_applicable":
      return <MinusCircle className="h-5 w-5 text-gray-400" />;
    default:
      return <MinusCircle className="h-5 w-5 text-gray-400" />;
  }
}

function ChecklistItemRow({ item }: { item: COPPAChecklistItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
      >
        <StatusIcon status={item.status} />
        <span className="flex-1 text-sm font-medium text-gray-900">
          {item.label}
        </span>
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400" />
        )}
      </button>
      {expanded && (
        <div className="px-4 pb-4 pl-12">
          <p className="text-sm text-gray-600">{item.description}</p>
          <p className="mt-2 text-xs text-gray-500">
            <strong>Evidence:</strong> {item.evidence}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            <strong>Regulation:</strong> {item.regulation_ref}
          </p>
          {item.status !== "complete" && item.status !== "not_applicable" && (
            <a
              href={item.action_url}
              className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary-700 hover:text-primary-800"
            >
              Take action
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      )}
    </div>
  );
}

export default function COPPADashboardPage() {
  const { user } = useAuth();
  const groupId = user?.group_id ?? undefined;

  const { data, isLoading, isError, error, refetch } = useCOPPAChecklist(groupId);
  const exportMutation = useCOPPAExport(groupId);
  const reviewMutation = useCOPPAReview(groupId);

  const handleExport = async () => {
    try {
      const blob = await exportMutation.mutateAsync();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "coppa_evidence.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Error handled by mutation state
    }
  };

  const handleReview = async () => {
    try {
      await reviewMutation.mutateAsync();
      refetch();
    } catch {
      // Error handled by mutation state
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">
          Assessing compliance...
        </span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load compliance data
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

  if (!data) return null;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          COPPA 2026 Compliance
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Automated compliance assessment for children&apos;s online privacy
        </p>
      </div>

      {/* Score and actions */}
      <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <ScoreGauge score={data.score} status={data.status} />
          <div className="flex flex-col gap-2 sm:items-end">
            <Button
              onClick={handleExport}
              isLoading={exportMutation.isPending}
              variant="secondary"
              size="sm"
            >
              <Download className="h-4 w-4" />
              Export Evidence
            </Button>
            <Button
              onClick={handleReview}
              isLoading={reviewMutation.isPending}
              size="sm"
            >
              <ClipboardCheck className="h-4 w-4" />
              Mark Review Complete
            </Button>
          </div>
        </div>
        {data.last_review && (
          <p className="mt-4 text-xs text-gray-400">
            Last annual review: {new Date(data.last_review).toLocaleDateString()}
          </p>
        )}
      </div>

      {/* Checklist */}
      <div className="mt-6">
        <Card title="Compliance Checklist" description="12 automated checks against COPPA 2026 requirements">
          <div className="divide-y divide-gray-100">
            {data.checklist.map((item) => (
              <ChecklistItemRow key={item.id} item={item} />
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
