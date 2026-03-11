"use client";

import { useState } from "react";
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Filter,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Loader2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  usePlatformSafetyRatings,
  usePlatformSafetyRecommendations,
} from "@/hooks/use-platform-safety";
import type { PlatformSafetyRating, PlatformSafetyRecommendation } from "@/types";

const gradeColors: Record<string, string> = {
  A: "bg-green-100 text-green-800 ring-green-200",
  B: "bg-blue-100 text-blue-800 ring-blue-200",
  C: "bg-amber-100 text-amber-800 ring-amber-200",
  D: "bg-orange-100 text-orange-800 ring-orange-200",
  F: "bg-red-100 text-red-800 ring-red-200",
};

function GradeBadge({ grade }: { grade: string }) {
  const color = gradeColors[grade] || gradeColors.F;
  return (
    <span
      className={`inline-flex h-10 w-10 items-center justify-center rounded-full text-lg font-bold ring-1 ${color}`}
    >
      {grade}
    </span>
  );
}

function RecommendationLabel({
  recommendation,
}: {
  recommendation?: string;
}) {
  if (!recommendation) return null;

  switch (recommendation) {
    case "recommended":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
          <ShieldCheck className="h-3 w-3" />
          Recommended
        </span>
      );
    case "use_with_caution":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
          <ShieldAlert className="h-3 w-3" />
          Use with caution
        </span>
      );
    case "not_recommended":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
          <ShieldX className="h-3 w-3" />
          Not Recommended
        </span>
      );
    default:
      return null;
  }
}

function PlatformCard({
  platform,
}: {
  platform: PlatformSafetyRating & { recommendation?: string };
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200 transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <GradeBadge grade={platform.overall_grade} />
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {platform.name}
            </h3>
            <p className="text-xs text-gray-500">
              Ages {platform.min_age_recommended}+
            </p>
          </div>
        </div>
        <RecommendationLabel
          recommendation={(platform as PlatformSafetyRecommendation).recommendation}
        />
      </div>

      {/* Quick info */}
      <div className="mt-4 flex flex-wrap gap-3">
        <div className="flex items-center gap-1 text-xs">
          {platform.has_content_filters ? (
            <CheckCircle className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <XCircle className="h-3.5 w-3.5 text-red-400" />
          )}
          <span className="text-gray-600">Content filters</span>
        </div>
        <div className="flex items-center gap-1 text-xs">
          {platform.has_parental_controls ? (
            <CheckCircle className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <XCircle className="h-3.5 w-3.5 text-red-400" />
          )}
          <span className="text-gray-600">Parental controls</span>
        </div>
        <div className="flex items-center gap-1 text-xs">
          {platform.coppa_compliant ? (
            <CheckCircle className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <XCircle className="h-3.5 w-3.5 text-red-400" />
          )}
          <span className="text-gray-600">COPPA</span>
        </div>
      </div>

      {/* Expand/collapse */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-3 flex items-center gap-1 text-xs font-medium text-primary-700 hover:text-primary-800"
      >
        {expanded ? "Show less" : "Show details"}
        {expanded ? (
          <ChevronUp className="h-3 w-3" />
        ) : (
          <ChevronDown className="h-3 w-3" />
        )}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-gray-100 pt-3">
          <div>
            <p className="text-xs font-medium text-gray-700">Strengths</p>
            <ul className="mt-1 space-y-1">
              {platform.strengths.map((s, i) => (
                <li key={i} className="flex items-start gap-1.5 text-xs text-gray-600">
                  <CheckCircle className="mt-0.5 h-3 w-3 flex-shrink-0 text-green-500" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-700">Concerns</p>
            <ul className="mt-1 space-y-1">
              {platform.concerns.map((c, i) => (
                <li key={i} className="flex items-start gap-1.5 text-xs text-gray-600">
                  <AlertTriangle className="mt-0.5 h-3 w-3 flex-shrink-0 text-amber-500" />
                  {c}
                </li>
              ))}
            </ul>
          </div>
          <div className="flex gap-4 text-xs text-gray-500">
            <span>Data retention: {platform.data_retention_days} days</span>
            <span>Known incidents: {platform.known_incidents}</span>
          </div>
          <p className="text-xs text-gray-400">
            Last updated: {platform.last_updated}
          </p>
        </div>
      )}
    </div>
  );
}

export default function SafetyRatingsPage() {
  const [ageFilter, setAgeFilter] = useState<number | null>(null);
  const [ageInput, setAgeInput] = useState("");

  const allRatingsQuery = usePlatformSafetyRatings(ageFilter === null);

  const filteredQuery = usePlatformSafetyRecommendations(ageFilter);

  const isLoading =
    ageFilter === null ? allRatingsQuery.isLoading : filteredQuery.isLoading;
  const isError =
    ageFilter === null ? allRatingsQuery.isError : filteredQuery.isError;
  const errorObj =
    ageFilter === null ? allRatingsQuery.error : filteredQuery.error;
  const refetch =
    ageFilter === null ? allRatingsQuery.refetch : filteredQuery.refetch;

  const platforms: (PlatformSafetyRating & { recommendation?: string })[] =
    ageFilter === null
      ? allRatingsQuery.data?.platforms ?? []
      : filteredQuery.data?.platforms ?? [];

  const handleAgeFilter = () => {
    const age = parseInt(ageInput, 10);
    if (age > 0 && age <= 100) {
      setAgeFilter(age);
    }
  };

  const clearFilter = () => {
    setAgeFilter(null);
    setAgeInput("");
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">
          Loading safety ratings...
        </span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load ratings
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(errorObj as Error)?.message || "Something went wrong"}
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

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          AI Platform Safety Ratings
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Independent safety assessments of popular AI platforms for children
        </p>
      </div>

      {/* Age filter */}
      <div className="mb-6 rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-500" />
            <label
              htmlFor="age-filter"
              className="text-sm font-medium text-gray-700"
            >
              Filter by age:
            </label>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="age-filter"
              type="number"
              min={1}
              max={100}
              value={ageInput}
              onChange={(e) => setAgeInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAgeFilter()}
              placeholder="Enter age"
              className="w-24 rounded-lg border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
            <Button size="sm" onClick={handleAgeFilter} disabled={!ageInput}>
              <Shield className="h-4 w-4" />
              Filter
            </Button>
            {ageFilter !== null && (
              <Button size="sm" variant="secondary" onClick={clearFilter}>
                Clear
              </Button>
            )}
          </div>
          {ageFilter !== null && (
            <p className="text-sm text-gray-500">
              Showing recommendations for age {ageFilter}
            </p>
          )}
        </div>
      </div>

      {/* Platform grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {platforms.map((platform) => (
          <PlatformCard key={platform.key} platform={platform} />
        ))}
      </div>

      {platforms.length === 0 && (
        <div className="flex h-32 items-center justify-center">
          <p className="text-sm text-gray-500">No platforms found.</p>
        </div>
      )}
    </div>
  );
}
