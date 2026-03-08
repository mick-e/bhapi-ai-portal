"use client";

import { useEffect } from "react";
import {
  X,
  MessageSquare,
  Code,
  Image,
  FileText,
  Clock,
  User,
  Monitor,
  AlertTriangle,
  Shield,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useActivityEvent } from "@/hooks/use-activity";
import type { EventType } from "@/types";

const typeIcons: Record<EventType, typeof MessageSquare> = {
  chat: MessageSquare,
  code: Code,
  image: Image,
  document: FileText,
};

const typeLabels: Record<EventType, string> = {
  chat: "Chat",
  code: "Code generation",
  image: "Image analysis",
  document: "Document",
};

const riskStyles = {
  low: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-red-100 text-red-700",
  critical: "bg-red-200 text-red-800",
};

export function ActivityDetailModal({
  eventId,
  onClose,
}: {
  eventId: string;
  onClose: () => void;
}) {
  const { data: event, isLoading, isError } = useActivityEvent(eventId);

  // Close on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  // Prevent body scroll
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  const TypeIcon = event
    ? typeIcons[(event.event_type as EventType) || "chat"] ?? MessageSquare
    : MessageSquare;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={onClose}
      />

      {/* Slide-over panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="activity-detail-title"
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col bg-white shadow-xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 id="activity-detail-title" className="text-lg font-bold text-gray-900">
            Activity Detail
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close detail panel"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {isLoading && (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          )}

          {isError && (
            <div className="flex flex-col items-center py-8 text-center">
              <AlertTriangle className="h-8 w-8 text-amber-500" />
              <p className="mt-2 text-sm text-gray-500">Failed to load event details</p>
              <Button variant="secondary" size="sm" className="mt-3" onClick={onClose}>
                Close
              </Button>
            </div>
          )}

          {event && (
            <div className="space-y-6">
              {/* Type + Risk */}
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100">
                  <TypeIcon className="h-5 w-5 text-gray-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">
                    {typeLabels[(event.event_type as EventType) || "chat"] || event.event_type}
                  </p>
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${riskStyles[event.risk_level]}`}
                  >
                    {event.risk_level} risk
                  </span>
                </div>
              </div>

              {/* Metadata grid */}
              <div className="grid grid-cols-2 gap-4">
                <DetailItem icon={User} label="Member" value={event.member_name} />
                <DetailItem icon={Monitor} label="Provider" value={`${event.provider} / ${event.model}`} />
                <DetailItem
                  icon={Clock}
                  label="Timestamp"
                  value={new Date(event.timestamp).toLocaleString()}
                />
                <DetailItem icon={Shield} label="Flagged" value={event.flagged ? "Yes" : "No"} />
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-4 rounded-lg bg-gray-50 p-4">
                <div>
                  <p className="text-xs text-gray-500">Tokens</p>
                  <p className="text-sm font-semibold text-gray-900">
                    {event.token_count.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Cost</p>
                  <p className="text-sm font-semibold text-gray-900">
                    ${event.cost_usd.toFixed(4)}
                  </p>
                </div>
              </div>

              {/* Prompt preview */}
              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-700">Prompt</h3>
                <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-700 whitespace-pre-wrap break-words">
                  {event.prompt_preview || "No prompt data available"}
                </div>
              </div>

              {/* Response preview */}
              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-700">Response</h3>
                <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-700 whitespace-pre-wrap break-words">
                  {event.response_preview || "No response data available"}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function DetailItem({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof User;
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-xs text-gray-500">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className="mt-0.5 text-sm font-medium text-gray-900">{value}</p>
    </div>
  );
}
