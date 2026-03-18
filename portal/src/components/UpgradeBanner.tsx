"use client";

import { ArrowRight, Zap } from "lucide-react";
import Link from "next/link";

interface UpgradeBannerProps {
  feature: string;
  plan?: string;
}

export default function UpgradeBanner({ feature, plan = "Family" }: UpgradeBannerProps) {
  return (
    <div className="rounded-lg bg-gradient-to-r from-primary-50 to-accent-50 p-4 ring-1 ring-primary-200">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100">
            <Zap className="h-4 w-4 text-primary-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-900">Upgrade to unlock {feature}</p>
            <p className="text-xs text-gray-500">This feature is available on the {plan} plan and above.</p>
          </div>
        </div>
        <Link
          href="/settings?tab=billing"
          className="inline-flex items-center gap-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          Upgrade <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
