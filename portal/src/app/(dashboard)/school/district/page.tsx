"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Building2, Users, Loader2, Plus, MapPin } from "lucide-react";
import { api } from "@/lib/api-client";

interface DistrictSchool {
  id: string;
  group_id: string;
  school_name: string;
  pilot_status: string;
  student_count: number;
}

interface DistrictSummary {
  district_id: string;
  total_schools: number;
  pilot_schools: number;
  active_schools: number;
  total_students: number;
  schools: DistrictSchool[];
}

export default function DistrictPage() {
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [code, setCode] = useState("");
  const [state, setState] = useState("");
  const [created, setCreated] = useState<{ id: string; name: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    if (!name.trim() || !adminEmail.trim()) {
      setError("Name and admin email are required.");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const result = await api.post<{ id: string; name: string; code: string }>("/api/v1/school/districts", {
        name, admin_email: adminEmail, code: code || undefined, state: state || undefined,
      });
      setCreated(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create district");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">District Management</h1>
        <p className="mt-1 text-sm text-gray-500">Manage school districts and pilot programs</p>
      </div>

      {created ? (
        <Card>
          <div className="text-center py-8">
            <Building2 className="mx-auto h-12 w-12 text-green-500" />
            <h2 className="mt-4 text-xl font-bold text-gray-900">District Created</h2>
            <p className="mt-2 text-sm text-gray-500">
              {created.name} is ready. You can now add schools to this district.
            </p>
            <Button className="mt-4" onClick={() => setCreated(null)}>Create Another</Button>
          </div>
        </Card>
      ) : (
        <div className="max-w-lg">
          <Card title="Create a District" description="Set up a school district for pilot management">
            <div className="space-y-4">
              {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
              <div>
                <label className="block text-sm font-medium text-gray-700">District name</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Springfield Unified" className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Admin email</label>
                <input type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} placeholder="admin@district.edu" className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">District code</label>
                  <input type="text" value={code} onChange={(e) => setCode(e.target.value)} placeholder="SPFLD-01" className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">State</label>
                  <input type="text" value={state} onChange={(e) => setState(e.target.value)} placeholder="Illinois" className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
              </div>
              <Button onClick={handleCreate} isLoading={creating} className="w-full">Create District</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
