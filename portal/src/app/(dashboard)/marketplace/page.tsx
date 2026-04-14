"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Puzzle, Star, Download, Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";
import { useTranslations } from "@/contexts/LocaleContext";

interface Module {
  id: string;
  name: string;
  slug: string;
  category: string;
  version: string;
  install_count: number;
  rating: number | null;
}

export default function MarketplacePage() {
  const t = useTranslations("marketplace");
  const [modules, setModules] = useState<Module[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<{ modules: Module[] }>("/api/v1/integrations/marketplace/modules")
      .then((d) => setModules(d.modules))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
        <p className="mt-1 text-sm text-gray-500">{t("subtitle")}</p>
      </div>

      {modules.length === 0 ? (
        <Card>
          <div className="py-16 text-center">
            <Puzzle className="mx-auto h-12 w-12 text-gray-300" />
            <h2 className="mt-4 text-lg font-semibold text-gray-900">{t("comingSoon")}</h2>
            <p className="mt-2 text-sm text-gray-500">{t("comingSoonDescription")}</p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {modules.map((mod) => (
            <Card key={mod.id}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100">
                    <Puzzle className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{mod.name}</p>
                    <p className="text-xs text-gray-500">{mod.category} &middot; v{mod.version}</p>
                  </div>
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span className="flex items-center gap-1"><Download className="h-3 w-3" />{mod.install_count}</span>
                  {mod.rating && <span className="flex items-center gap-1"><Star className="h-3 w-3 text-amber-400" />{mod.rating.toFixed(1)}</span>}
                </div>
                <Button size="sm">{t("install")}</Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
