"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Presentation, CheckCircle, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api-client";
import { useTranslations } from "@/contexts/LocaleContext";

interface DemoData {
  demo_token: string;
  expires_at: string;
  organisation: string;
}

export default function DemoPage() {
  const t = useTranslations("demo");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [organisation, setOrganisation] = useState("");
  const [accountType, setAccountType] = useState<"school" | "club" | "enterprise">("school");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DemoData | null>(null);

  async function handleCreate() {
    if (!name.trim() || !email.trim() || !organisation.trim()) {
      setError(t("fillAllFields"));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.post<DemoData>("/api/v1/portal/demo", {
        name,
        email,
        organisation,
        account_type: accountType,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("createFailed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
        <p className="mt-1 text-sm text-gray-500">
          {t("subtitle")}
        </p>
      </div>

      {result ? (
        <Card>
          <div className="text-center py-8">
            <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
            <h2 className="mt-4 text-xl font-bold text-gray-900">{t("demoCreated")}</h2>
            <p className="mt-2 text-sm text-gray-500">
              {t("demoReady").replace("{org}", result.organisation)}
            </p>
            <div className="mt-4 rounded-lg bg-gray-50 p-4 inline-block">
              <p className="text-xs text-gray-500">{t("demoToken")}</p>
              <code className="text-lg font-mono font-bold text-primary-700">{result.demo_token}</code>
            </div>
            <p className="mt-4 text-xs text-gray-400">
              {t("expires")}: {new Date(result.expires_at).toLocaleDateString()}
            </p>
            <Button className="mt-6" onClick={() => setResult(null)}>
              {t("createAnother")}
            </Button>
          </div>
        </Card>
      ) : (
        <div className="max-w-lg">
          <Card>
            <div className="space-y-4 p-2">
              <div className="flex items-center gap-3 mb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100">
                  <Presentation className="h-5 w-5 text-primary-600" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">{t("demoDetails")}</h2>
                  <p className="text-xs text-gray-500">{t("fillInHint")}</p>
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
                  <AlertTriangle className="h-4 w-4" />
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700">{t("yourName")}</label>
                <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("namePlaceholder")} className="mt-1" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">{t("email")}</label>
                <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("emailPlaceholder")} type="email" className="mt-1" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">{t("organisation")}</label>
                <Input value={organisation} onChange={(e) => setOrganisation(e.target.value)} placeholder={t("organisationPlaceholder")} className="mt-1" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">{t("accountType")}</label>
                <select
                  value={accountType}
                  onChange={(e) => setAccountType(e.target.value as "school" | "club" | "enterprise")}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="school">{t("school")}</option>
                  <option value="club">{t("club")}</option>
                  <option value="enterprise">{t("enterprise")}</option>
                </select>
              </div>

              <Button onClick={handleCreate} isLoading={loading} className="w-full mt-2">
                {t("generateDemo")}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
