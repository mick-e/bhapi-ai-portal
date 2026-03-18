"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Shield, Plus, AlertTriangle, Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";

interface Policy {
  id: string;
  name: string;
  policy_type: string;
  enforcement_level: string;
  active: boolean;
}

export default function GovernancePage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<{ policies: Policy[] }>("/api/v1/risk/policies")
      .then((d) => setPolicies(d.policies))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const typeLabels: Record<string, string> = {
    acceptable_use: "Acceptable Use",
    data_handling: "Data Handling",
    model_access: "Model Access",
    cost_control: "Cost Control",
  };

  const enforcementColors: Record<string, string> = {
    warn: "bg-amber-100 text-amber-700",
    block: "bg-red-100 text-red-700",
    audit: "bg-blue-100 text-blue-700",
  };

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
  }

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Governance</h1>
          <p className="mt-1 text-sm text-gray-500">Manage AI usage policies and compliance</p>
        </div>
        <Button><Plus className="mr-2 h-4 w-4" />Create Policy</Button>
      </div>

      {policies.length === 0 ? (
        <Card>
          <div className="py-12 text-center">
            <Shield className="mx-auto h-10 w-10 text-gray-300" />
            <p className="mt-3 text-sm text-gray-500">No policies created yet. Create your first AI usage policy.</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {policies.map((policy) => (
            <Card key={policy.id}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{policy.name}</p>
                  <p className="text-xs text-gray-500">{typeLabels[policy.policy_type] || policy.policy_type}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${enforcementColors[policy.enforcement_level] || "bg-gray-100 text-gray-700"}`}>
                    {policy.enforcement_level}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${policy.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-700"}`}>
                    {policy.active ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
