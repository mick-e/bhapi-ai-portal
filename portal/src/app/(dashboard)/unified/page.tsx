"use client";

import { useState } from "react";
import {
  ChevronDown,
  Shield,
  Activity,
  Users,
  Clock,
  MapPin,
  Bell,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useMembers } from "@/hooks/use-members";
import {
  useUnifiedDashboard,
  type RiskScoreSummary,
  type AIActivitySummary,
  type SocialSummary,
  type ScreenTimeSummary,
  type LocationSummary,
  type ActionCenter,
} from "@/hooks/use-unified-dashboard";
import type { GroupMember } from "@/types";

// ─── Risk Score Card (web version) ───────────────────────────────────────────

function riskColor(score: number): string {
  if (score <= 30) return "text-green-600";
  if (score <= 60) return "text-amber-500";
  return "text-red-500";
}

function riskRingColor(score: number): string {
  if (score <= 30) return "border-green-500";
  if (score <= 60) return "border-amber-500";
  return "border-red-500";
}

function TrendIcon({ trend }: { trend: RiskScoreSummary["trend"] }) {
  if (trend === "up")
    return <TrendingUp className="h-4 w-4 text-red-500" aria-label="Rising" />;
  if (trend === "down")
    return (
      <TrendingDown className="h-4 w-4 text-green-500" aria-label="Falling" />
    );
  return <Minus className="h-4 w-4 text-gray-400" aria-label="Stable" />;
}

function confidenceBadgeClass(confidence: RiskScoreSummary["confidence"]): string {
  if (confidence === "high") return "bg-green-100 text-green-700";
  if (confidence === "medium") return "bg-amber-100 text-amber-700";
  return "bg-red-100 text-red-700";
}

function RiskScoreSection({ data }: { data: RiskScoreSummary | null }) {
  if (!data) {
    return (
      <Card title="Risk Score" description="AI safety monitoring">
        <p className="text-sm text-gray-400">No risk data available yet.</p>
      </Card>
    );
  }

  const score = Math.max(0, Math.min(100, Math.round(data.score)));

  return (
    <Card title="Risk Score" description="AI safety monitoring">
      <div className="flex items-center gap-6">
        {/* Score circle */}
        <div
          className={`flex h-20 w-20 shrink-0 flex-col items-center justify-center rounded-full border-4 ${riskRingColor(score)}`}
          aria-label={`Risk score: ${score} out of 100`}
        >
          <span className={`text-2xl font-bold leading-tight ${riskColor(score)}`}>
            {score}
          </span>
          <span className="text-xs text-gray-400">/100</span>
        </div>

        {/* Trend + confidence */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-1.5 text-sm font-medium text-gray-700">
            <TrendIcon trend={data.trend} />
            <span className="capitalize">{data.trend}</span>
          </div>
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${confidenceBadgeClass(data.confidence)}`}
          >
            {data.confidence.charAt(0).toUpperCase() + data.confidence.slice(1)} confidence
          </span>
        </div>
      </div>

      {/* Contributing factors */}
      {data.factors.length > 0 && (
        <div className="mt-4 border-t border-gray-100 pt-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Top Factors
          </p>
          <ul className="space-y-1">
            {data.factors.slice(0, 3).map((factor, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <span className="mt-0.5 text-[#FF6B35]">•</span>
                {factor}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

// ─── AI Activity Card ─────────────────────────────────────────────────────────

function AIActivitySection({ data }: { data: AIActivitySummary | null }) {
  return (
    <Card title="AI Activity" description="Recent AI interactions today">
      {!data ? (
        <p className="text-sm text-gray-400">No activity data available.</p>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <Activity className="h-5 w-5 text-[#FF6B35]" aria-hidden />
            <div>
              <p className="text-2xl font-bold text-gray-900">{data.events_today}</p>
              <p className="text-xs text-gray-500">events today</p>
            </div>
          </div>
          {data.top_platforms.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                Top Platforms
              </p>
              <div className="flex flex-wrap gap-1.5">
                {data.top_platforms.map((p) => (
                  <span
                    key={p}
                    className="rounded-full bg-orange-50 px-2.5 py-0.5 text-xs font-medium text-[#FF6B35]"
                  >
                    {p}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// ─── Social Activity Card ─────────────────────────────────────────────────────

function SocialActivitySection({ data }: { data: SocialSummary | null }) {
  return (
    <Card title="Social Activity" description="Posts, comments & connections">
      {!data ? (
        <p className="text-sm text-gray-400">No social data available.</p>
      ) : (
        <div className="grid grid-cols-3 gap-3 text-center">
          <div>
            <p className="text-2xl font-bold text-gray-900">{data.posts_today}</p>
            <p className="text-xs text-gray-500">Posts</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{data.comments_today}</p>
            <p className="text-xs text-gray-500">Comments</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">
              {data.friend_requests_pending}
            </p>
            <p className="text-xs text-gray-500">Pending requests</p>
          </div>
        </div>
      )}
    </Card>
  );
}

// ─── Screen Time Card ─────────────────────────────────────────────────────────

function ScreenTimeSection({ data }: { data: ScreenTimeSummary | null }) {
  return (
    <Card title="Screen Time" description="Today's usage">
      {!data ? (
        <p className="text-sm text-gray-400">No screen time data available.</p>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <Clock className="h-5 w-5 text-[#0D9488]" aria-hidden />
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {Math.floor(data.total_minutes_today / 60)}h{" "}
                {data.total_minutes_today % 60}m
              </p>
              <p className="text-xs text-gray-500">total today</p>
            </div>
          </div>
          {data.top_categories.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                Top Categories
              </p>
              <ul className="space-y-1.5">
                {data.top_categories.slice(0, 3).map((c) => (
                  <li key={c.category} className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">{c.category}</span>
                    <span className="font-medium text-gray-900">{c.minutes}m</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// ─── Location Card ────────────────────────────────────────────────────────────

function geofenceStatusClass(status: LocationSummary["geofence_status"]): string {
  if (status === "inside") return "bg-green-100 text-green-700";
  if (status === "outside") return "bg-red-100 text-red-700";
  return "bg-gray-100 text-gray-500";
}

function LocationSection({ data }: { data: LocationSummary | null }) {
  return (
    <Card title="Location" description="Last known position">
      {!data ? (
        <p className="text-sm text-gray-400">No location data available.</p>
      ) : (
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-[#FF6B35]" aria-hidden />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-gray-900">
                {data.last_known_location ?? "Location unavailable"}
              </p>
              {data.last_updated && (
                <p className="mt-0.5 text-xs text-gray-400">
                  Updated {new Date(data.last_updated).toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${geofenceStatusClass(data.geofence_status)}`}
          >
            Geofence:{" "}
            {data.geofence_status === "inside"
              ? "Inside safe zone"
              : data.geofence_status === "outside"
              ? "Outside safe zone"
              : "Unknown"}
          </span>
        </div>
      )}
    </Card>
  );
}

// ─── Action Center Card ───────────────────────────────────────────────────────

function ActionCenterSection({ data }: { data: ActionCenter | null }) {
  return (
    <Card title="Action Center" description="Items requiring your attention">
      {!data ? (
        <p className="text-sm text-gray-400">Loading action items...</p>
      ) : (
        <div className="space-y-2">
          <ActionItem
            icon={<CheckCircle className="h-4 w-4 text-[#0D9488]" />}
            label="Pending approvals"
            count={data.pending_approvals}
            urgentThreshold={1}
          />
          <ActionItem
            icon={<Bell className="h-4 w-4 text-[#FF6B35]" />}
            label="Unread alerts"
            count={data.unread_alerts}
            urgentThreshold={3}
          />
          <ActionItem
            icon={<AlertTriangle className="h-4 w-4 text-amber-500" />}
            label="Extension requests"
            count={data.pending_extension_requests}
            urgentThreshold={1}
          />
        </div>
      )}
    </Card>
  );
}

function ActionItem({
  icon,
  label,
  count,
  urgentThreshold,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  urgentThreshold: number;
}) {
  const isUrgent = count >= urgentThreshold;
  return (
    <div className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2">
      <div className="flex items-center gap-2 text-sm text-gray-700">
        {icon}
        {label}
      </div>
      <span
        className={`rounded-full px-2 py-0.5 text-xs font-bold ${
          count === 0
            ? "bg-gray-200 text-gray-500"
            : isUrgent
            ? "bg-red-100 text-red-700"
            : "bg-amber-100 text-amber-700"
        }`}
      >
        {count}
      </span>
    </div>
  );
}

// ─── Child Selector ───────────────────────────────────────────────────────────

function ChildSelector({
  members,
  selectedId,
  onSelect,
}: {
  members: GroupMember[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const children = members.filter((m) => m.role === "member");
  if (children.length === 0) return null;

  return (
    <div className="relative inline-block">
      <label htmlFor="child-selector" className="sr-only">
        Select child
      </label>
      <div className="relative">
        <select
          id="child-selector"
          value={selectedId}
          onChange={(e) => onSelect(e.target.value)}
          className="h-9 appearance-none rounded-lg border border-gray-300 bg-white pl-3 pr-8 text-sm font-medium text-gray-700 shadow-sm focus:border-[#FF6B35] focus:outline-none focus:ring-2 focus:ring-[#FF6B35]/20"
        >
          {children.map((m) => (
            <option key={m.id} value={m.id}>
              {m.display_name}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2 top-2.5 h-4 w-4 text-gray-400" />
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function UnifiedDashboardPage() {
  const { data: membersData, isLoading: membersLoading } = useMembers({ page_size: 20 });
  const members = membersData?.items ?? [];
  const children = members.filter((m) => m.role === "member");

  const [selectedChildId, setSelectedChildId] = useState<string>("");

  // Pick first child if no selection yet
  const effectiveChildId =
    selectedChildId || (children.length > 0 ? children[0].id : "");

  const { data, isLoading, isError, refetchAll } = useUnifiedDashboard(effectiveChildId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Unified Dashboard</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Complete view of your child&apos;s digital wellbeing
          </p>
        </div>
        <div className="flex items-center gap-3">
          {!membersLoading && (
            <ChildSelector
              members={members}
              selectedId={effectiveChildId}
              onSelect={setSelectedChildId}
            />
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={refetchAll}
            disabled={isLoading}
            aria-label="Refresh dashboard"
          >
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* No children state */}
      {!membersLoading && children.length === 0 && (
        <Card>
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <Users className="h-10 w-10 text-gray-300" aria-hidden />
            <p className="font-medium text-gray-700">No children added yet</p>
            <p className="text-sm text-gray-500">
              Add a child to your group to see their unified dashboard.
            </p>
          </div>
        </Card>
      )}

      {/* Loading state */}
      {membersLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-[#FF6B35]" aria-label="Loading" />
        </div>
      )}

      {/* Error banner */}
      {isError && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />
          Some sections failed to load. Other sections may still show data.
        </div>
      )}

      {/* Dashboard grid */}
      {effectiveChildId && !membersLoading && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {/* Risk Score — full width on mobile, spans 1 col */}
          <div className="sm:col-span-1">
            <RiskScoreSection data={data.riskScore} />
          </div>

          {/* AI Activity */}
          <div className="sm:col-span-1">
            <AIActivitySection data={data.aiActivity} />
          </div>

          {/* Social Activity */}
          <div className="sm:col-span-1">
            <SocialActivitySection data={data.social} />
          </div>

          {/* Screen Time */}
          <div className="sm:col-span-1">
            <ScreenTimeSection data={data.screenTime} />
          </div>

          {/* Location */}
          <div className="sm:col-span-1">
            <LocationSection data={data.location} />
          </div>

          {/* Action Center */}
          <div className="sm:col-span-1">
            <ActionCenterSection data={data.actionCenter} />
          </div>
        </div>
      )}
    </div>
  );
}

// Exports for testing
export {
  RiskScoreSection,
  AIActivitySection,
  SocialActivitySection,
  ScreenTimeSection,
  LocationSection,
  ActionCenterSection,
  ChildSelector,
};
