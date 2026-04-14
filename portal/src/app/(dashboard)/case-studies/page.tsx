"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { BookOpen, Quote, ArrowRight, Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";
import { useTranslations } from "@/contexts/LocaleContext";

interface CaseStudyResult {
  metric: string;
  before: string;
  after: string;
}

interface CaseStudy {
  id: string;
  title: string;
  subtitle: string;
  industry: string;
  size: string;
  challenge: string;
  solution: string;
  results: CaseStudyResult[];
  quote: string;
  quote_author: string;
}

export default function CaseStudiesPage() {
  const t = useTranslations("caseStudies");
  const [studies, setStudies] = useState<CaseStudy[]>([]);
  const [selected, setSelected] = useState<CaseStudy | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<{ case_studies: CaseStudy[] }>("/api/v1/portal/case-studies")
      .then((data) => {
        setStudies(data.case_studies);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (selected) {
    return (
      <div>
        <button onClick={() => setSelected(null)} className="mb-4 text-sm text-primary-700 hover:text-primary-800">
          &larr; {t("backToCaseStudies")}
        </button>
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">{selected.title}</h1>
          <p className="mt-1 text-sm text-gray-500">{selected.subtitle}</p>
          <div className="mt-2 flex gap-2">
            <span className="rounded-full bg-primary-100 px-3 py-1 text-xs font-medium text-primary-700">{selected.industry}</span>
            <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">{selected.size}</span>
          </div>
        </div>

        <div className="space-y-6">
          <Card title={t("challenge")}>
            <p className="text-sm text-gray-600">{selected.challenge}</p>
          </Card>

          <Card title={t("solution")}>
            <p className="text-sm text-gray-600">{selected.solution}</p>
          </Card>

          <Card title={t("results")}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="py-2 text-left font-medium text-gray-700">{t("metric")}</th>
                    <th className="py-2 text-left font-medium text-red-600">{t("before")}</th>
                    <th className="py-2 text-left font-medium text-green-600">{t("after")}</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.results.map((r, i) => (
                    <tr key={i} className="border-b border-gray-100">
                      <td className="py-2 font-medium text-gray-900">{r.metric}</td>
                      <td className="py-2 text-red-600">{r.before}</td>
                      <td className="py-2 text-green-600">{r.after}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <div className="rounded-xl bg-primary-50 p-6">
            <Quote className="h-6 w-6 text-primary-400" />
            <p className="mt-3 text-lg italic text-gray-800">&ldquo;{selected.quote}&rdquo;</p>
            <p className="mt-2 text-sm font-medium text-primary-700">&mdash; {selected.quote_author}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
        <p className="mt-1 text-sm text-gray-500">
          {t("subtitle")}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {studies.map((study) => (
          <button
            key={study.id}
            onClick={() => setSelected(study)}
            className="rounded-xl bg-white p-6 text-left shadow-sm ring-1 ring-gray-200 transition hover:ring-primary-300 hover:shadow-md"
          >
            <div className="flex items-center gap-2 mb-3">
              <BookOpen className="h-5 w-5 text-primary-600" />
              <span className="text-xs font-medium text-primary-600">{study.industry}</span>
            </div>
            <h3 className="text-lg font-bold text-gray-900">{study.title}</h3>
            <p className="mt-1 text-sm text-gray-500">{study.subtitle}</p>
            <div className="mt-4 flex items-center gap-1 text-sm font-medium text-primary-700">
              {t("readMore")} <ArrowRight className="h-4 w-4" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
