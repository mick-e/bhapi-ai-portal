"use client";

import React, { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Tabs } from "@/components/ui/Tabs";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import {
  FileText,
  ClipboardList,
  Bell,
  Handshake,
  Plus,
  Loader2,
  Search,
} from "lucide-react";
import { useTranslations } from "@/contexts/LocaleContext";
import {
  useFerpaRecords,
  useFerpaAccessLog,
  useFerpaSharingAgreements,
  useDesignateRecord,
  useSendAnnualNotification,
} from "@/hooks/use-ferpa";

type TabKey = "records" | "access" | "notifications" | "agreements";

export default function FerpaPage() {
  const t = useTranslations("ferpa");
  const [activeTab, setActiveTab] = useState<TabKey>("records");
  const [designateOpen, setDesignateOpen] = useState(false);
  const [memberFilter, setMemberFilter] = useState("");

  // ─── Form state ─────────────────────────────────────────────────────────
  const [newRecordType, setNewRecordType] = useState("");
  const [newRecordDesc, setNewRecordDesc] = useState("");
  const [notifYear, setNotifYear] = useState(
    new Date().getFullYear().toString()
  );

  // ─── Queries ────────────────────────────────────────────────────────────
  const records = useFerpaRecords();
  const accessLog = useFerpaAccessLog(memberFilter || undefined);
  const agreements = useFerpaSharingAgreements();

  // ─── Mutations ──────────────────────────────────────────────────────────
  const designate = useDesignateRecord();
  const sendNotification = useSendAnnualNotification();

  const tabs = [
    { key: "records", label: t("tabRecords") },
    { key: "access", label: t("tabAccess") },
    { key: "notifications", label: t("tabNotifications") },
    { key: "agreements", label: t("tabAgreements") },
  ];

  function handleDesignate() {
    if (!newRecordType || !newRecordDesc) return;
    designate.mutate(
      { record_type: newRecordType, description: newRecordDesc },
      {
        onSuccess: () => {
          setDesignateOpen(false);
          setNewRecordType("");
          setNewRecordDesc("");
        },
      }
    );
  }

  function handleSendNotification() {
    sendNotification.mutate({ academic_year: notifYear });
  }

  // ─── Tab Content ────────────────────────────────────────────────────────

  function renderRecords() {
    if (records.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = records.data ?? [];

    return (
      <div className="space-y-4">
        <div className="flex justify-end">
          <Button onClick={() => setDesignateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t("designate")}
          </Button>
        </div>

        {items.length === 0 ? (
          <Card>
            <EmptyState
              title={t("tabRecords")}
              message={t("empty")}
              icon={<FileText className="h-10 w-10" />}
              actionLabel={t("designate")}
              onAction={() => setDesignateOpen(true)}
            />
          </Card>
        ) : (
          <div className="space-y-3">
            {items.map((rec) => (
              <Card key={rec.id}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">
                      {rec.record_type}
                    </p>
                    <p className="text-sm text-gray-500">{rec.description}</p>
                  </div>
                  <p className="text-xs text-gray-400">
                    {new Date(rec.created_at).toLocaleDateString()}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  function renderAccessLog() {
    if (accessLog.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = accessLog.data ?? [];

    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="Filter by member ID..."
              value={memberFilter}
              onChange={(e) => setMemberFilter(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {items.length === 0 ? (
          <Card>
            <EmptyState
              title={t("tabAccess")}
              message={t("emptyAccess")}
              icon={<ClipboardList className="h-10 w-10" />}
            />
          </Card>
        ) : (
          <div className="space-y-3">
            {items.map((entry) => (
              <Card key={entry.id}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">
                      {entry.record_type}
                    </p>
                    <p className="text-sm text-gray-500">
                      Accessed by {entry.accessed_by} &mdash; {entry.purpose}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-400">
                      {new Date(entry.timestamp).toLocaleString()}
                    </p>
                    <Badge variant="neutral">{entry.member_id}</Badge>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  function renderNotifications() {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <select
            value={notifYear}
            onChange={(e) => setNotifYear(e.target.value)}
            className="block rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          >
            {[0, 1, 2].map((offset) => {
              const year = new Date().getFullYear() - offset;
              return (
                <option key={year} value={year.toString()}>
                  {year}-{year + 1}
                </option>
              );
            })}
          </select>
          <Button
            onClick={handleSendNotification}
            isLoading={sendNotification.isPending}
          >
            <Bell className="mr-2 h-4 w-4" />
            {t("sendNotification")}
          </Button>
        </div>

        {sendNotification.isSuccess && sendNotification.data ? (
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">
                  Annual Notification Sent
                </p>
                <p className="text-sm text-gray-500">
                  Academic year {sendNotification.data.academic_year} &mdash;{" "}
                  {sendNotification.data.recipients_count} recipients
                </p>
              </div>
              <Badge variant="success">{sendNotification.data.status}</Badge>
            </div>
          </Card>
        ) : (
          <Card>
            <EmptyState
              title={t("tabNotifications")}
              message={t("emptyNotifications")}
              icon={<Bell className="h-10 w-10" />}
            />
          </Card>
        )}
      </div>
    );
  }

  function renderAgreements() {
    if (agreements.isLoading) {
      return (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      );
    }

    const items = agreements.data ?? [];

    return items.length === 0 ? (
      <Card>
        <EmptyState
          title={t("tabAgreements")}
          message={t("emptyAgreements")}
          icon={<Handshake className="h-10 w-10" />}
        />
      </Card>
    ) : (
      <div className="space-y-3">
        {items.map((agreement) => (
          <Card key={agreement.id}>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">
                  {agreement.partner_name}
                </p>
                <p className="text-sm text-gray-500">{agreement.purpose}</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {agreement.record_types.map((rt) => (
                    <Badge key={rt} variant="neutral">
                      {rt}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="text-right">
                <Badge
                  variant={
                    agreement.status === "active" ? "success" : "neutral"
                  }
                >
                  {agreement.status}
                </Badge>
                {agreement.expires_at && (
                  <p className="mt-1 text-xs text-gray-400">
                    Expires{" "}
                    {new Date(agreement.expires_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  const tabContent: Record<TabKey, () => React.ReactNode> = {
    records: renderRecords,
    access: renderAccessLog,
    notifications: renderNotifications,
    agreements: renderAgreements,
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

      {/* Designate Record Modal */}
      <Modal
        open={designateOpen}
        onClose={() => setDesignateOpen(false)}
        title={t("designate")}
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Record Type
            </label>
            <select
              value={newRecordType}
              onChange={(e) => setNewRecordType(e.target.value)}
              className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            >
              <option value="">Select a type...</option>
              <option value="grades">Grades</option>
              <option value="attendance">Attendance</option>
              <option value="disciplinary">Disciplinary Records</option>
              <option value="health">Health Records</option>
              <option value="special_education">Special Education</option>
              <option value="transcripts">Transcripts</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Description
            </label>
            <Input
              placeholder="Describe the record designation..."
              value={newRecordDesc}
              onChange={(e) => setNewRecordDesc(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={() => setDesignateOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleDesignate}
              isLoading={designate.isPending}
              disabled={!newRecordType || !newRecordDesc}
            >
              {t("designate")}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
