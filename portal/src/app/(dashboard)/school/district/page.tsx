"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Building2, Users, Loader2, Plus, MapPin } from "lucide-react";
import { useTranslations } from "@/contexts/LocaleContext";
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
  const t = useTranslations("schoolDistrict");
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
      setError(t("errorRequired"));
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
      setError(err instanceof Error ? err.message : t("errorCreateFailed"));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
        <p className="mt-1 text-sm text-gray-500">{t("subtitle")}</p>
      </div>

      {created ? (
        <Card>
          <div className="text-center py-8">
            <Building2 className="mx-auto h-12 w-12 text-green-500" />
            <h2 className="mt-4 text-xl font-bold text-gray-900">{t("districtCreated")}</h2>
            <p className="mt-2 text-sm text-gray-500">
              {created.name} {t("districtReady")}
            </p>
            <Button className="mt-4" onClick={() => setCreated(null)}>{t("createAnother")}</Button>
          </div>
        </Card>
      ) : (
        <div className="max-w-lg">
          <Card title={t("createDistrictCardTitle")} description={t("createDistrictCardDesc")}>
            <div className="space-y-4">
              {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
              <div>
                <label className="block text-sm font-medium text-gray-700">{t("districtName")}</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder={t("districtNamePlaceholder")} className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">{t("adminEmail")}</label>
                <input type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} placeholder={t("adminEmailPlaceholder")} className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">{t("districtCode")}</label>
                  <input type="text" value={code} onChange={(e) => setCode(e.target.value)} placeholder={t("districtCodePlaceholder")} className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">{t("stateLabel")}</label>
                  <input type="text" value={state} onChange={(e) => setState(e.target.value)} placeholder={t("statePlaceholder")} className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
              </div>
              <Button onClick={handleCreate} isLoading={creating} className="w-full">{t("createDistrict")}</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
