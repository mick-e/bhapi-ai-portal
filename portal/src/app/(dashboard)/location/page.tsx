"use client";

import React, { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Tabs } from "@/components/ui/Tabs";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { MapPin, School, Clock, Plus, Loader2, Trash2 } from "lucide-react";
import { useTranslations } from "@/contexts/LocaleContext";
import {
  useGeofences,
  useSchoolCheckIns,
  useLocationHistory,
  useCreateGeofence,
  useDeleteGeofence,
} from "@/hooks/use-location";

type TabKey = "geofences" | "checkin" | "history";

export default function LocationPage() {
  const t = useTranslations("location");
  const [activeTab, setActiveTab] = useState<TabKey>("geofences");
  const [createOpen, setCreateOpen] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [radius, setRadius] = useState("200");
  const [memberId, setMemberId] = useState("");

  // Queries
  const geofences = useGeofences();
  const checkIns = useSchoolCheckIns();
  const history = useLocationHistory();

  // Mutations
  const createGeofence = useCreateGeofence();
  const deleteGeofence = useDeleteGeofence();

  const tabs = [
    { key: "geofences", label: t("tabGeofences") },
    { key: "checkin", label: t("tabCheckIn") },
    { key: "history", label: t("tabHistory") },
  ];

  function handleCreate() {
    if (!name || !lat || !lng || !memberId) return;
    createGeofence.mutate(
      {
        name,
        latitude: parseFloat(lat),
        longitude: parseFloat(lng),
        radius_meters: parseInt(radius, 10),
        member_id: memberId,
      },
      {
        onSuccess: () => {
          setCreateOpen(false);
          setName("");
          setLat("");
          setLng("");
          setRadius("200");
          setMemberId("");
        },
      }
    );
  }

  // ─── Tab: Geofences ────────────────────────────────────────────────────────

  function renderGeofences() {
    if (geofences.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = geofences.data ?? [];

    return (
      <div className="space-y-4">
        <div className="flex justify-end">
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t("addGeofence")}
          </Button>
        </div>

        {items.length === 0 ? (
          <Card>
            <EmptyState
              title={t("tabGeofences")}
              message={t("emptyGeofences")}
              icon={<MapPin className="h-10 w-10" />}
              actionLabel={t("addGeofence")}
              onAction={() => setCreateOpen(true)}
            />
          </Card>
        ) : (
          <div className="space-y-3">
            {items.map((fence) => (
              <Card key={fence.id}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{fence.name}</p>
                    <p className="text-sm text-gray-500">
                      {fence.latitude.toFixed(4)}, {fence.longitude.toFixed(4)} &mdash; {fence.radius_meters}m
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={fence.active ? "success" : "neutral"}>
                      {fence.active ? t("active") : t("inactive")}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteGeofence.mutate(fence.id)}
                    >
                      <Trash2 className="h-4 w-4 text-gray-400" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ─── Tab: School Check-in ──────────────────────────────────────────────────

  function renderCheckIn() {
    if (checkIns.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = checkIns.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabCheckIn")}
          message={t("emptyCheckIn")}
          icon={<School className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="space-y-3">
        {items.map((ci) => (
          <Card key={ci.id}>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">{ci.member_name}</p>
                <p className="text-sm text-gray-500">{ci.school_name}</p>
              </div>
              <div className="text-right">
                <Badge variant={ci.status === "checked_in" ? "success" : "neutral"}>
                  {ci.status === "checked_in" ? t("checkedIn") : t("checkedOut")}
                </Badge>
                <p className="mt-1 text-xs text-gray-400">
                  {new Date(ci.checked_in_at).toLocaleString()}
                </p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  // ─── Tab: Location History ─────────────────────────────────────────────────

  function renderHistory() {
    if (history.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = history.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabHistory")}
          message={t("emptyHistory")}
          icon={<Clock className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="space-y-3">
        {items.map((entry) => (
          <Card key={entry.id}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {entry.latitude.toFixed(4)}, {entry.longitude.toFixed(4)}
                </p>
                <p className="text-xs text-gray-500">
                  {entry.event_type}
                  {entry.geofence_id && ` \u2014 ${t("insideGeofence")}`}
                </p>
              </div>
              <p className="text-xs text-gray-400">
                {new Date(entry.timestamp).toLocaleString()}
              </p>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  const tabContent: Record<TabKey, () => React.ReactNode> = {
    geofences: renderGeofences,
    checkin: renderCheckIn,
    history: renderHistory,
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

      {/* Create Geofence Modal */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title={t("addGeofence")}
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">{t("geofenceName")}</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("geofenceNamePlaceholder")} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">{t("latitude")}</label>
              <Input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="37.7749" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">{t("longitude")}</label>
              <Input value={lng} onChange={(e) => setLng(e.target.value)} placeholder="-122.4194" />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">{t("radius")}</label>
            <Input value={radius} onChange={(e) => setRadius(e.target.value)} placeholder="200" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">{t("memberId")}</label>
            <Input value={memberId} onChange={(e) => setMemberId(e.target.value)} placeholder={t("memberIdPlaceholder")} />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>
              {t("cancel")}
            </Button>
            <Button
              onClick={handleCreate}
              isLoading={createGeofence.isPending}
              disabled={!name || !lat || !lng || !memberId}
            >
              {t("create")}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
