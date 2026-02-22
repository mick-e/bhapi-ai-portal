"use client";

import { useState } from "react";
import {
  Activity,
  Search,
  Filter,
  MessageSquare,
  Code,
  Image,
  FileText,
} from "lucide-react";
import { Card } from "@/components/ui/Card";

interface ActivityEvent {
  id: string;
  memberName: string;
  provider: string;
  model: string;
  type: "chat" | "code" | "image" | "document";
  preview: string;
  riskLevel: "low" | "medium" | "high" | "critical";
  tokenCount: number;
  cost: number;
  timestamp: string;
}

const placeholderEvents: ActivityEvent[] = [
  {
    id: "1",
    memberName: "Sarah",
    provider: "OpenAI",
    model: "GPT-4o",
    type: "chat",
    preview: "Help me with my history homework about World War II...",
    riskLevel: "low",
    tokenCount: 1245,
    cost: 0.03,
    timestamp: "2 min ago",
  },
  {
    id: "2",
    memberName: "Tom",
    provider: "Anthropic",
    model: "Claude 3.5",
    type: "code",
    preview: "Write a Python function that sorts a list using...",
    riskLevel: "low",
    tokenCount: 2100,
    cost: 0.05,
    timestamp: "15 min ago",
  },
  {
    id: "3",
    memberName: "Emma",
    provider: "Google",
    model: "Gemini Pro",
    type: "image",
    preview: "Analyse this diagram from my science textbook...",
    riskLevel: "medium",
    tokenCount: 890,
    cost: 0.02,
    timestamp: "32 min ago",
  },
  {
    id: "4",
    memberName: "James",
    provider: "OpenAI",
    model: "GPT-4o",
    type: "chat",
    preview: "Tell me about how to bypass content filters...",
    riskLevel: "high",
    tokenCount: 450,
    cost: 0.01,
    timestamp: "1 hour ago",
  },
  {
    id: "5",
    memberName: "Lucy",
    provider: "Anthropic",
    model: "Claude 3.5",
    type: "document",
    preview: "Summarise this article about climate change for my essay...",
    riskLevel: "low",
    tokenCount: 3200,
    cost: 0.08,
    timestamp: "2 hours ago",
  },
  {
    id: "6",
    memberName: "Sarah",
    provider: "OpenAI",
    model: "GPT-4o",
    type: "chat",
    preview: "Can you explain photosynthesis in simple terms...",
    riskLevel: "low",
    tokenCount: 980,
    cost: 0.02,
    timestamp: "3 hours ago",
  },
];

const typeIcons = {
  chat: MessageSquare,
  code: Code,
  image: Image,
  document: FileText,
};

export default function ActivityPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterRisk, setFilterRisk] = useState<string>("all");

  const filtered = placeholderEvents.filter((event) => {
    const matchesSearch =
      event.memberName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      event.preview.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRisk =
      filterRisk === "all" || event.riskLevel === filterRisk;
    return matchesSearch && matchesRisk;
  });

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Activity</h1>
        <p className="mt-1 text-sm text-gray-500">
          Timeline of all AI interactions across your group
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search activity..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-400" />
          <select
            value={filterRisk}
            onChange={(e) => setFilterRisk(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">All risk levels</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
      </div>

      {/* Activity Timeline */}
      <div className="space-y-4">
        {filtered.map((event) => {
          const TypeIcon = typeIcons[event.type];
          return (
            <Card key={event.id}>
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100">
                  <TypeIcon className="h-5 w-5 text-gray-600" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900">
                        {event.memberName}
                      </span>
                      <span className="text-xs text-gray-400">
                        {event.provider} / {event.model}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <RiskBadge level={event.riskLevel} />
                      <span className="text-xs text-gray-400">
                        {event.timestamp}
                      </span>
                    </div>
                  </div>
                  <p className="mt-1 truncate text-sm text-gray-600">
                    {event.preview}
                  </p>
                  <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
                    <span>{event.tokenCount.toLocaleString()} tokens</span>
                    <span>${event.cost.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}

        {filtered.length === 0 && (
          <div className="py-12 text-center">
            <Activity className="mx-auto h-12 w-12 text-gray-300" />
            <p className="mt-4 text-sm text-gray-500">
              No activity matches your search
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function RiskBadge({
  level,
}: {
  level: "low" | "medium" | "high" | "critical";
}) {
  const styles = {
    low: "bg-green-100 text-green-700",
    medium: "bg-amber-100 text-amber-700",
    high: "bg-red-100 text-red-700",
    critical: "bg-red-200 text-red-800",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${styles[level]}`}
    >
      {level}
    </span>
  );
}
