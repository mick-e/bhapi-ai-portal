"use client";

import { useState } from "react";
import { Calendar } from "lucide-react";

export type DatePreset = "today" | "7d" | "30d" | "90d" | "custom";

const presetLabels: Record<DatePreset, string> = {
  today: "Today",
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  "90d": "Last 90 days",
  custom: "Custom",
};

function getPresetDates(preset: DatePreset): { start: string; end: string } | null {
  if (preset === "custom") return null;
  const end = new Date();
  const start = new Date();
  switch (preset) {
    case "today":
      start.setHours(0, 0, 0, 0);
      break;
    case "7d":
      start.setDate(start.getDate() - 7);
      break;
    case "30d":
      start.setDate(start.getDate() - 30);
      break;
    case "90d":
      start.setDate(start.getDate() - 90);
      break;
  }
  return {
    start: start.toISOString().split("T")[0],
    end: end.toISOString().split("T")[0],
  };
}

export function DateRangeFilter({
  onChange,
}: {
  onChange: (range: { start?: string; end?: string } | null) => void;
}) {
  const [preset, setPreset] = useState<DatePreset | "all">("all");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");

  function handlePresetChange(value: string) {
    if (value === "all") {
      setPreset("all");
      onChange(null);
      return;
    }
    const p = value as DatePreset;
    setPreset(p);
    if (p !== "custom") {
      const dates = getPresetDates(p);
      onChange(dates);
    }
  }

  function handleCustomApply() {
    if (customStart || customEnd) {
      onChange({
        start: customStart || undefined,
        end: customEnd || undefined,
      });
    }
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <Calendar className="h-4 w-4 text-gray-400" />
      <select
        value={preset}
        onChange={(e) => handlePresetChange(e.target.value)}
        aria-label="Date range"
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
      >
        <option value="all">All time</option>
        {(Object.keys(presetLabels) as DatePreset[]).map((key) => (
          <option key={key} value={key}>
            {presetLabels[key]}
          </option>
        ))}
      </select>

      {preset === "custom" && (
        <>
          <input
            type="date"
            value={customStart}
            onChange={(e) => setCustomStart(e.target.value)}
            aria-label="Start date"
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <span className="text-sm text-gray-400">to</span>
          <input
            type="date"
            value={customEnd}
            onChange={(e) => setCustomEnd(e.target.value)}
            aria-label="End date"
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <button
            onClick={handleCustomApply}
            className="rounded-lg bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
          >
            Apply
          </button>
        </>
      )}
    </div>
  );
}
