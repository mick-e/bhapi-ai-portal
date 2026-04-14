"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Code, Key, Loader2, Plus, Copy, CheckCircle } from "lucide-react";
import { api } from "@/lib/api-client";
import { useTranslations } from "@/contexts/LocaleContext";

interface DevApp {
  id: string;
  name: string;
  client_id: string;
  active: boolean;
  approved: boolean;
}

export default function DeveloperPage() {
  const t = useTranslations("developer");
  const [apps, setApps] = useState<DevApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [newSecret, setNewSecret] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.get<{ apps: DevApp[] }>("/api/v1/integrations/developer/apps")
      .then((d) => setApps(d.apps))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate() {
    setCreating(true);
    try {
      const result = await api.post<{ id: string; name: string; client_id: string; client_secret: string }>("/api/v1/integrations/developer/apps", { name });
      setNewSecret(result.client_secret);
      setApps([...apps, { id: result.id, name: result.name, client_id: result.client_id, active: true, approved: false }]);
      setShowCreate(false);
      setName("");
    } catch {
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
          <p className="mt-1 text-sm text-gray-500">{t("subtitle")}</p>
        </div>
        <Button onClick={() => setShowCreate(true)}><Plus className="mr-2 h-4 w-4" />{t("createApp")}</Button>
      </div>

      {newSecret && (
        <div className="mb-6 rounded-lg bg-green-50 p-4 ring-1 ring-green-200">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span className="font-medium text-green-800">{t("appCreatedMessage")}</span>
          </div>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded bg-white px-3 py-2 text-sm font-mono">{newSecret}</code>
            <Button variant="secondary" size="sm" onClick={() => { navigator.clipboard.writeText(newSecret); setCopied(true); }}>
              {copied ? <CheckCircle className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            </Button>
          </div>
          <p className="mt-2 text-xs text-green-700">{t("secretNotShownAgain")}</p>
        </div>
      )}

      {showCreate && (
        <Card className="mb-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">{t("appNameLabel")}</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder={t("appNamePlaceholder")} className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div className="flex gap-2">
              <Button onClick={handleCreate} isLoading={creating}>{t("create")}</Button>
              <Button variant="secondary" onClick={() => setShowCreate(false)}>{t("cancel")}</Button>
            </div>
          </div>
        </Card>
      )}

      {loading ? (
        <div className="flex h-32 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
      ) : apps.length === 0 ? (
        <Card>
          <div className="py-12 text-center">
            <Code className="mx-auto h-10 w-10 text-gray-300" />
            <p className="mt-3 text-sm text-gray-500">{t("emptyMessage")}</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {apps.map((app) => (
            <Card key={app.id}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100">
                    <Key className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{app.name}</p>
                    <p className="text-xs text-gray-500 font-mono">{app.client_id}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${app.approved ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
                    {app.approved ? t("approved") : t("pendingReview")}
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
