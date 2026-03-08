"use client";

import { useState } from "react";
import {
  Gavel,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Plus,
  CheckCircle2,
  Clock,
  XCircle,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/use-auth";
import { useAppeals, useSubmitAppeal } from "@/hooks/use-compliance";
import { useToast } from "@/contexts/ToastContext";

const statusStyles: Record<string, { bg: string; text: string; icon: typeof Clock }> = {
  pending: { bg: "bg-amber-100", text: "text-amber-700", icon: Clock },
  approved: { bg: "bg-green-100", text: "text-green-700", icon: CheckCircle2 },
  rejected: { bg: "bg-red-100", text: "text-red-700", icon: XCircle },
  reviewing: { bg: "bg-blue-100", text: "text-blue-700", icon: Clock },
};

export default function AppealsPage() {
  const { user } = useAuth();
  const groupId = user?.group_id || null;
  const { addToast } = useToast();

  const {
    data: appealsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useAppeals(groupId);

  const submitAppeal = useSubmitAppeal();

  const [showForm, setShowForm] = useState(false);
  const [riskEventId, setRiskEventId] = useState("");
  const [reason, setReason] = useState("");

  function handleSubmit() {
    if (!groupId || !riskEventId.trim() || !reason.trim()) return;
    submitAppeal.mutate(
      {
        riskEventId: riskEventId.trim(),
        group_id: groupId,
        reason: reason.trim(),
      },
      {
        onSuccess: () => {
          addToast("Appeal submitted successfully", "success");
          setShowForm(false);
          setRiskEventId("");
          setReason("");
        },
        onError: (err) =>
          addToast((err as Error).message || "Failed to submit appeal", "error"),
      }
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading appeals...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load appeals
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

  const appeals = appealsData?.items ?? [];
  const total = appealsData?.total ?? 0;

  return (
    <div>
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Appeals</h1>
          <p className="mt-1 text-sm text-gray-500">
            Contest risk classifications under your right to human review
            {total > 0 && (
              <span className="ml-1 text-gray-400">({total} total)</span>
            )}
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4" />
          New Appeal
        </Button>
      </div>

      {/* Submit Form */}
      {showForm && (
        <Card title="Submit Appeal" className="mb-6">
          <div className="max-w-lg space-y-4">
            {submitAppeal.isError && (
              <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {(submitAppeal.error as Error)?.message || "Failed to submit"}
              </div>
            )}
            <Input
              label="Risk Event ID"
              value={riskEventId}
              onChange={(e) => setRiskEventId(e.target.value)}
              placeholder="Enter the risk event ID to appeal"
              helperText="You can find this on the Risks page for each event."
            />
            <div>
              <label
                htmlFor="appeal-reason"
                className="mb-1.5 block text-sm font-medium text-gray-700"
              >
                Reason for Appeal
              </label>
              <textarea
                id="appeal-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Explain why you believe this classification is incorrect..."
                rows={4}
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <Button
                onClick={handleSubmit}
                isLoading={submitAppeal.isPending}
                disabled={!riskEventId.trim() || !reason.trim()}
              >
                Submit Appeal
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setShowForm(false);
                  setRiskEventId("");
                  setReason("");
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Appeals List */}
      {appeals.length === 0 ? (
        <Card>
          <div className="py-12 text-center">
            <Gavel className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-sm text-gray-500">No appeals submitted</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {appeals.map((appeal) => {
            const style = statusStyles[appeal.status] || statusStyles.pending;
            const StatusIcon = style.icon;
            return (
              <Card key={appeal.id}>
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-gray-900">
                        Event: {appeal.risk_event_id}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${style.bg} ${style.text}`}
                      >
                        <StatusIcon className="h-3 w-3" />
                        {appeal.status}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-600">{appeal.reason}</p>
                    {appeal.resolution && (
                      <div className="mt-3 rounded-lg bg-gray-50 p-3">
                        <p className="text-xs font-medium text-gray-500 uppercase">
                          Resolution
                        </p>
                        <p className="mt-1 text-sm text-gray-700">
                          {appeal.resolution}
                        </p>
                        {appeal.resolution_notes && (
                          <p className="mt-1 text-xs text-gray-500">
                            {appeal.resolution_notes}
                          </p>
                        )}
                      </div>
                    )}
                    <p className="mt-2 text-xs text-gray-400">
                      Submitted {new Date(appeal.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
