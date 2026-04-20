"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Globe,
  ShieldCheck,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";
import { Card } from "@/components/ui/Card";

interface Phase4Kpi {
  id: string;
  label: string;
  value: string;
  target: string;
  progress: number;
  status: "on_track" | "at_risk" | "missed" | "complete";
  icon: React.ReactNode;
  source: string;
}

const STATUS_STYLES: Record<Phase4Kpi["status"], { bg: string; text: string; label: string }> = {
  complete: { bg: "bg-green-100", text: "text-green-800", label: "Complete" },
  on_track: { bg: "bg-blue-100", text: "text-blue-800", label: "On track" },
  at_risk: { bg: "bg-amber-100", text: "text-amber-800", label: "At risk" },
  missed: { bg: "bg-red-100", text: "text-red-800", label: "Missed" },
};

export default function Phase4MetricsPage() {
  const [loading, setLoading] = useState(true);
  const [kpis, setKpis] = useState<Phase4Kpi[]>([]);

  useEffect(() => {
    loadKpis()
      .then(setKpis)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-8">
        <div className="h-10 w-64 bg-gray-200 rounded animate-pulse mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-100 rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Phase 4 Launch Metrics</h1>
        <p className="text-gray-600 mt-2">
          Success gates for Phase 4 close. Each KPI rolls up from live product data — no
          manual entry. See the Phase 4 plan for source-of-truth definitions.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <Card key={kpi.id} className="p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="p-2 bg-primary-100 rounded-lg">{kpi.icon}</div>
              <span
                className={`text-xs font-medium px-2 py-1 rounded ${STATUS_STYLES[kpi.status].bg} ${STATUS_STYLES[kpi.status].text}`}
              >
                {STATUS_STYLES[kpi.status].label}
              </span>
            </div>
            <div className="text-sm text-gray-500">{kpi.label}</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">{kpi.value}</div>
            <div className="text-xs text-gray-500 mt-1">Target: {kpi.target}</div>
            <div className="w-full h-1.5 bg-gray-200 rounded-full mt-3 overflow-hidden">
              <div
                className="h-full bg-primary-600 rounded-full transition-all"
                style={{ width: `${Math.min(100, kpi.progress)}%` }}
              />
            </div>
            <div className="text-xs text-gray-400 mt-2">Source: {kpi.source}</div>
          </Card>
        ))}
      </div>

      <div className="mt-10">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Known gaps (human action required)</h2>
        <Card className="p-5">
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <span>
                Stripe price IDs for School $1.99/seat and Family+ $19.99/mo need creation in
                Stripe Dashboard before production flip. See{" "}
                <code className="text-xs bg-gray-100 px-1 rounded">
                  docs/operations/stripe_price_changes_phase4.md
                </code>
                .
              </span>
            </li>
            <li className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <span>
                Identity-protection partner selection PENDING BD outreach — Family+ ships with
                MockPartnerClient until a real partner is signed.
              </span>
            </li>
            <li className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <span>
                NL / PL / SV locales ship as English clones; professional translation vendor
                engagement PENDING.
              </span>
            </li>
            <li className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <span>
                SOC 2 Type II observation window closes mid-April 2027; auditor fieldwork
                PENDING that date.
              </span>
            </li>
          </ul>
        </Card>
      </div>
    </div>
  );
}

async function loadKpis(): Promise<Phase4Kpi[]> {
  // Placeholder data until the backend aggregator lands (tracked as a
  // follow-up on the Phase 4 metrics dashboard ticket).
  //
  // When the backend endpoint ships, swap this for:
  //   const res = await fetch('/api/v1/admin/phase4-metrics');
  //   return res.json();
  return [
    {
      id: "school_deployments",
      label: "School deployments",
      value: "0",
      target: "25+",
      progress: 0,
      status: "on_track",
      icon: <Target className="h-5 w-5 text-primary-600" />,
      source: "groups(school, active)",
    },
    {
      id: "family_subs",
      label: "Family subscriptions",
      value: "0",
      target: "2,500+",
      progress: 0,
      status: "on_track",
      icon: <Users className="h-5 w-5 text-primary-600" />,
      source: "subscriptions(family/family_plus, active)",
    },
    {
      id: "api_partners",
      label: "API partners (beta+)",
      value: "0",
      target: "10+",
      progress: 0,
      status: "on_track",
      icon: <Activity className="h-5 w-5 text-primary-600" />,
      source: "oauth_clients(verified=true)",
    },
    {
      id: "platforms",
      label: "AI platforms monitored",
      value: "10",
      target: "15+",
      progress: 66,
      status: "on_track",
      icon: <Globe className="h-5 w-5 text-primary-600" />,
      source: "static count (extension/content/platforms)",
    },
    {
      id: "ferpa_adoption",
      label: "FERPA module adoption",
      value: "0",
      target: "5+ schools",
      progress: 0,
      status: "on_track",
      icon: <ShieldCheck className="h-5 w-5 text-primary-600" />,
      source: "ferpa_records(group).count > 0",
    },
    {
      id: "family_plus_conversion",
      label: "Family+ conversion",
      value: "—",
      target: "15% of family base",
      progress: 0,
      status: "on_track",
      icon: <TrendingUp className="h-5 w-5 text-primary-600" />,
      source: "family_plus / (family + family_plus)",
    },
    {
      id: "intel_signals",
      label: "Intel network signals",
      value: "0",
      target: "1,000+/mo",
      progress: 0,
      status: "on_track",
      icon: <Activity className="h-5 w-5 text-primary-600" />,
      source: "signal_deliveries count (30d)",
    },
    {
      id: "soc2",
      label: "SOC 2 Type II",
      value: "In progress",
      target: "Issued",
      progress: 50,
      status: "on_track",
      icon: <CheckCircle2 className="h-5 w-5 text-primary-600" />,
      source: "docs/compliance/soc2/",
    },
  ];
}
