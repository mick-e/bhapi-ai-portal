"use client";

import React, { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Tabs } from "@/components/ui/Tabs";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import {
  Palette,
  ClipboardCheck,
  Check,
  X,
  Loader2,
} from "lucide-react";
import { useTranslations } from "@/contexts/LocaleContext";
import {
  useCreativeGallery,
  useCreativeReviewQueue,
  useApproveCreative,
  useRejectCreative,
} from "@/hooks/use-creative";

type TabKey = "gallery" | "review";

const typeIcons: Record<string, string> = {
  art: "🎨",
  story: "📖",
  sticker: "🏷️",
  drawing: "✏️",
};

export default function CreativePage() {
  const t = useTranslations("creative");
  const [activeTab, setActiveTab] = useState<TabKey>("gallery");

  // Queries
  const gallery = useCreativeGallery();
  const reviewQueue = useCreativeReviewQueue();

  // Mutations
  const approveItem = useApproveCreative();
  const rejectItem = useRejectCreative();

  const tabs = [
    { key: "gallery", label: t("tabGallery") },
    { key: "review", label: t("tabReview"), count: (reviewQueue.data ?? []).length || undefined },
  ];

  const statusBadge = (status: string) => {
    const map: Record<string, "success" | "warning" | "error"> = {
      approved: "success",
      pending: "warning",
      rejected: "error",
    };
    return map[status] ?? "neutral";
  };

  // ─── Tab: Gallery ──────────────────────────────────────────────────────────

  function renderGallery() {
    if (gallery.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = gallery.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabGallery")}
          message={t("emptyGallery")}
          icon={<Palette className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <Card key={item.id}>
            {item.thumbnail_url && (
              <img
                src={item.thumbnail_url}
                alt={item.title}
                className="mb-3 h-40 w-full rounded-lg object-cover"
              />
            )}
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium text-gray-900">
                  {typeIcons[item.content_type] ?? ""} {item.title}
                </p>
                <p className="text-xs text-gray-500">{item.member_name}</p>
                <p className="text-xs text-gray-400">
                  {new Date(item.created_at).toLocaleDateString()}
                </p>
              </div>
              <Badge variant={statusBadge(item.moderation_status)}>
                {item.moderation_status === "approved"
                  ? t("approved")
                  : item.moderation_status === "rejected"
                    ? t("rejected")
                    : t("pending")}
              </Badge>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  // ─── Tab: Review Queue ─────────────────────────────────────────────────────

  function renderReview() {
    if (reviewQueue.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = reviewQueue.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabReview")}
          message={t("emptyReview")}
          icon={<ClipboardCheck className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="space-y-3">
        {items.map((item) => (
          <Card key={item.id}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {item.thumbnail_url && (
                  <img
                    src={item.thumbnail_url}
                    alt={item.title}
                    className="h-16 w-16 rounded-lg object-cover"
                  />
                )}
                <div>
                  <p className="font-medium text-gray-900">
                    {typeIcons[item.content_type] ?? ""} {item.title}
                  </p>
                  <p className="text-sm text-gray-500">{item.member_name}</p>
                  {item.flagged_reason && (
                    <p className="text-xs text-amber-600">{item.flagged_reason}</p>
                  )}
                  <p className="text-xs text-gray-400">
                    {new Date(item.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  onClick={() => approveItem.mutate(item.id)}
                  disabled={approveItem.isPending}
                >
                  <Check className="mr-1 h-3 w-3" />
                  {t("approve")}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => rejectItem.mutate({ itemId: item.id })}
                  disabled={rejectItem.isPending}
                >
                  <X className="mr-1 h-3 w-3" />
                  {t("reject")}
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  const tabContent: Record<TabKey, () => React.ReactNode> = {
    gallery: renderGallery,
    review: renderReview,
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
        <p className="mt-1 text-sm text-gray-500">{t("subtitle")}</p>
      </div>

      <Tabs
        tabs={tabs}
        active={activeTab}
        onChange={(key) => setActiveTab(key as TabKey)}
        className="mb-6"
      />

      {tabContent[activeTab]()}
    </div>
  );
}
