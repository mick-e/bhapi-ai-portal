"use client";

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface OnboardingCardProps {
  id: string;
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  actionHref?: string;
}

function getStorageKey(id: string) {
  return `bhapi_onboarding_dismissed_${id}`;
}

export function OnboardingCard({
  id,
  icon: Icon,
  title,
  description,
  actionLabel,
  actionHref,
}: OnboardingCardProps) {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(getStorageKey(id));
    setDismissed(stored === "true");
  }, [id]);

  function handleDismiss() {
    localStorage.setItem(getStorageKey(id), "true");
    setDismissed(true);
  }

  if (dismissed) return null;

  return (
    <div className="mb-6 rounded-xl border border-teal-200 border-l-4 border-l-teal-500 bg-teal-50 p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-teal-100">
          <Icon className="h-5 w-5 text-teal-600" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-sm font-semibold text-teal-900">{title}</h3>
            <button
              onClick={handleDismiss}
              className="flex-shrink-0 rounded-md p-1 text-teal-400 hover:bg-teal-100 hover:text-teal-600 transition-colors"
              aria-label="Dismiss tip"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-0.5 text-sm text-teal-700">{description}</p>
          {actionLabel && actionHref && (
            <a
              href={actionHref}
              className="mt-2 inline-flex items-center rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-700 transition-colors"
            >
              {actionLabel}
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
