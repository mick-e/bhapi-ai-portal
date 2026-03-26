"use client";

import { useState } from "react";
import { Users, AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useMembers } from "@/hooks/use-members";
import { useUnifiedDashboard } from "@/hooks/use-unified-dashboard";
import {
  RiskScoreSection,
  AIActivitySection,
  SocialActivitySection,
  ScreenTimeSection,
  LocationSection,
  ActionCenterSection,
  ChildSelector,
} from "./components";

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
          <div className="sm:col-span-1">
            <RiskScoreSection data={data.riskScore} />
          </div>
          <div className="sm:col-span-1">
            <AIActivitySection data={data.aiActivity} />
          </div>
          <div className="sm:col-span-1">
            <SocialActivitySection data={data.social} />
          </div>
          <div className="sm:col-span-1">
            <ScreenTimeSection data={data.screenTime} />
          </div>
          <div className="sm:col-span-1">
            <LocationSection data={data.location} />
          </div>
          <div className="sm:col-span-1">
            <ActionCenterSection data={data.actionCenter} />
          </div>
        </div>
      )}
    </div>
  );
}
