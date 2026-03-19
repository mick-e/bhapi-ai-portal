"use client";

import { Shield, Eye, Trash2, HelpCircle } from "lucide-react";
import { useTranslations } from "@/contexts/LocaleContext";

const sections = [
  {
    key: "what_we_watch",
    icon: Eye,
    color: "text-teal-600",
    bgColor: "bg-teal-50",
    borderColor: "border-teal-200",
  },
  {
    key: "who_can_see",
    icon: Shield,
    color: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
  },
  {
    key: "your_rights",
    icon: Trash2,
    color: "text-orange-600",
    bgColor: "bg-orange-50",
    borderColor: "border-orange-200",
  },
  {
    key: "need_help",
    icon: HelpCircle,
    color: "text-purple-600",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200",
  },
] as const;

export default function PrivacyForChildrenPage() {
  const t = useTranslations("privacy_children");

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="text-center mb-10">
        <Shield className="w-12 h-12 text-primary-600 mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-gray-900">
          {t("title")}
        </h1>
      </div>

      <div className="space-y-6">
        {sections.map(({ key, icon: Icon, color, bgColor, borderColor }) => (
          <div
            key={key}
            className={`rounded-xl border-2 ${borderColor} ${bgColor} p-6`}
          >
            <div className="flex items-center gap-3 mb-3">
              <Icon className={`w-7 h-7 ${color}`} />
              <h2 className="text-xl font-semibold text-gray-900">
                {t(`${key}_title`)}
              </h2>
            </div>
            <p className="text-lg text-gray-700 leading-relaxed">
              {t(`${key}_text`)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
