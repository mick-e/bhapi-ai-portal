"use client";

import { useState } from "react";
import {
  Shield,
  Eye,
  Bell,
  Database,
  Video,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ArrowLeft,
  RefreshCw,
  Lock,
  ShieldCheck,
  Clock,
} from "lucide-react";
import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/use-auth";
import { useMembers } from "@/hooks/use-members";
import { useToast } from "@/contexts/ToastContext";
import type { GroupMember } from "@/types";
import {
  useThirdPartyConsents,
  useUpdateThirdPartyConsent,
  useRefusePartialCollection,
  useRetentionPolicies,
  useUpdateRetentionPolicy,
  usePushNotificationConsents,
  useUpdatePushNotificationConsent,
  useVideoVerificationStatus,
  useVideoVerifications,
  useInitiateVideoVerification,
} from "@/hooks/use-coppa-privacy";
import type { ThirdPartyConsentItem, RetentionPolicy } from "@/hooks/use-coppa-privacy";

type PrivacySection =
  | "third-party"
  | "retention"
  | "push-notifications"
  | "verification";

const sections: { value: PrivacySection; label: string; icon: typeof Shield }[] = [
  { value: "third-party", label: "Third-Party Data", icon: Eye },
  { value: "retention", label: "Data Retention", icon: Database },
  { value: "push-notifications", label: "Push Notifications", icon: Bell },
  { value: "verification", label: "Identity Verification", icon: Video },
];

export default function PrivacySettingsPage() {
  const { user } = useAuth();
  const { data: membersData, isLoading: membersLoading } = useMembers({ page_size: 10 });
  const [activeSection, setActiveSection] = useState<PrivacySection>("third-party");
  const [selectedMemberId, setSelectedMemberId] = useState<string>("");

  const members = membersData?.items ?? [];
  const childMembers = members.filter(
    (m: GroupMember) => m.role === "member" || m.role === "viewer"
  );

  // Auto-select first child member
  const activeMemberId = selectedMemberId || childMembers[0]?.id || "";
  const groupId = user?.group_id || "";

  if (membersLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading privacy settings...</span>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <Link
          href="/settings?tab=privacy"
          className="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Settings
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">COPPA Privacy Controls</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage third-party data sharing, retention policies, notification consent, and
          parental identity verification as required by COPPA 2026.
        </p>
      </div>

      {/* Member selector */}
      {childMembers.length > 0 && (
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select child member
          </label>
          <select
            value={activeMemberId}
            onChange={(e) => setSelectedMemberId(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {childMembers.map((m: GroupMember) => (
              <option key={m.id} value={m.id}>
                {m.display_name}
              </option>
            ))}
          </select>
        </div>
      )}

      {childMembers.length === 0 ? (
        <Card title="No Members" description="">
          <p className="text-sm text-gray-500">
            Add a child member to your group to configure COPPA privacy controls.
          </p>
        </Card>
      ) : (
        <div className="flex flex-col gap-6 lg:flex-row">
          {/* Section nav */}
          <nav className="w-full lg:w-52 flex-shrink-0">
            <ul className="flex gap-1 overflow-x-auto lg:flex-col">
              {sections.map((s) => {
                const Icon = s.icon;
                return (
                  <li key={s.value}>
                    <button
                      onClick={() => setActiveSection(s.value)}
                      className={`flex w-full items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                        activeSection === s.value
                          ? "bg-primary-50 text-primary"
                          : "text-gray-600 hover:bg-gray-50"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {s.label}
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {activeSection === "third-party" && (
              <ThirdPartySection groupId={groupId} memberId={activeMemberId} />
            )}
            {activeSection === "retention" && (
              <RetentionSection groupId={groupId} />
            )}
            {activeSection === "push-notifications" && (
              <PushNotificationSection groupId={groupId} memberId={activeMemberId} />
            )}
            {activeSection === "verification" && (
              <VerificationSection groupId={groupId} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Third-Party Data Consent Section ────────────────────────────────────────

function ThirdPartySection({ groupId, memberId }: { groupId: string; memberId: string }) {
  const { data: consents, isLoading } = useThirdPartyConsents(groupId, memberId);
  const updateConsent = useUpdateThirdPartyConsent(groupId, memberId);
  const refuseAll = useRefusePartialCollection(groupId);
  const { addToast } = useToast();

  if (isLoading) {
    return <LoadingCard title="Third-Party Data Sharing" />;
  }

  const items = consents || [];

  return (
    <Card
      title="Third-Party Data Sharing"
      description="Control which third-party services can process your child's data. You can consent to monitoring while refusing third-party sharing."
    >
      <div className="space-y-4">
        {/* Refuse all toggle */}
        <div className="rounded-lg border-2 border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-amber-900">
                Refuse all third-party data sharing
              </p>
              <p className="mt-1 text-xs text-amber-700">
                Allow Bhapi to collect data for safety monitoring, but prevent sharing with
                third-party analytics, AI, and communication providers.
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() =>
                refuseAll.mutate(
                  { member_id: memberId, refuse_third_party_sharing: true },
                  {
                    onSuccess: () => addToast("Third-party sharing refused", "success"),
                    onError: (e) => addToast((e as Error).message, "error"),
                  }
                )
              }
              isLoading={refuseAll.isPending}
            >
              <Lock className="h-3 w-3" />
              Refuse All
            </Button>
          </div>
        </div>

        {/* Per-provider toggles */}
        <div className="divide-y divide-gray-100">
          {items.map((item: ThirdPartyConsentItem) => (
            <div key={item.id} className="flex items-start justify-between gap-4 py-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">{item.provider_name}</p>
                <p className="mt-0.5 text-xs text-gray-500">{item.data_purpose}</p>
                {item.consented_at && (
                  <p className="mt-1 text-xs text-green-600">
                    Consented: {new Date(item.consented_at).toLocaleDateString()}
                  </p>
                )}
                {item.withdrawn_at && (
                  <p className="mt-1 text-xs text-red-600">
                    Withdrawn: {new Date(item.withdrawn_at).toLocaleDateString()}
                  </p>
                )}
              </div>
              <label className="relative inline-flex cursor-pointer items-center">
                <input
                  type="checkbox"
                  checked={item.consented}
                  onChange={() =>
                    updateConsent.mutate(
                      { provider_key: item.provider_key, consented: !item.consented },
                      {
                        onSuccess: () =>
                          addToast(
                            item.consented ? "Consent withdrawn" : "Consent granted",
                            "success"
                          ),
                        onError: (e) => addToast((e as Error).message, "error"),
                      }
                    )
                  }
                  className="peer sr-only"
                />
                <div className="h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all peer-checked:bg-primary-600 peer-checked:after:translate-x-full peer-checked:after:border-white" />
              </label>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ─── Data Retention Section ──────────────────────────────────────────────────

function RetentionSection({ groupId }: { groupId: string }) {
  const { data: policies, isLoading } = useRetentionPolicies(groupId);
  const updatePolicy = useUpdateRetentionPolicy(groupId);
  const { addToast } = useToast();

  if (isLoading) {
    return <LoadingCard title="Data Retention Policies" />;
  }

  const items = policies || [];

  return (
    <Card
      title="Data Retention Policies"
      description="Configure how long each type of your child's data is kept. Data is automatically and permanently deleted after the retention period."
    >
      <div className="space-y-4">
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-xs text-blue-700">
            <ShieldCheck className="mr-1 inline h-3 w-3" />
            Some data types have regulatory minimum retention periods that cannot be reduced.
            Audit logs must be kept for at least 3 years.
          </p>
        </div>

        <div className="divide-y divide-gray-100">
          {items.map((policy: RetentionPolicy) => (
            <RetentionPolicyRow
              key={policy.id}
              policy={policy}
              onUpdate={(days, autoDelete) =>
                updatePolicy.mutate(
                  { data_type: policy.data_type, retention_days: days, auto_delete: autoDelete },
                  {
                    onSuccess: () => addToast("Retention policy updated", "success"),
                    onError: (e) => addToast((e as Error).message, "error"),
                  }
                )
              }
            />
          ))}
        </div>
      </div>
    </Card>
  );
}

function RetentionPolicyRow({
  policy,
  onUpdate,
}: {
  policy: RetentionPolicy;
  onUpdate: (days: number, autoDelete: boolean) => void;
}) {
  const [days, setDays] = useState(policy.retention_days);

  return (
    <div className="py-4 space-y-2">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-gray-900 capitalize">
            {policy.data_type.replace(/_/g, " ")}
          </p>
          <p className="text-xs text-gray-500">{policy.description}</p>
          {policy.records_deleted > 0 && (
            <p className="mt-1 text-xs text-gray-400">
              <Clock className="mr-1 inline h-3 w-3" />
              {policy.records_deleted.toLocaleString()} records deleted to date
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={30}
            max={3650}
            value={days}
            onChange={(e) => setDays(parseInt(e.target.value, 10) || 30)}
            className="w-20 rounded border border-gray-300 px-2 py-1 text-sm text-right"
          />
          <span className="text-xs text-gray-500">days</span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onUpdate(days, policy.auto_delete)}
            disabled={days === policy.retention_days}
          >
            Save
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Push Notification Consent Section ───────────────────────────────────────

function PushNotificationSection({ groupId, memberId }: { groupId: string; memberId: string }) {
  const { data: consents, isLoading } = usePushNotificationConsents(groupId, memberId);
  const updateConsent = useUpdatePushNotificationConsent(groupId);
  const { addToast } = useToast();

  if (isLoading) {
    return <LoadingCard title="Push Notification Consent" />;
  }

  const notificationTypes = [
    {
      type: "risk_alerts",
      label: "Safety Risk Alerts",
      description: "Critical and high-severity safety alerts about your child's AI interactions",
    },
    {
      type: "activity_summaries",
      label: "Activity Summaries",
      description: "Daily summaries of your child's AI usage and conversation topics",
    },
    {
      type: "weekly_reports",
      label: "Weekly Reports",
      description: "Weekly safety and usage reports with trends and insights",
    },
  ];

  const consentMap = new Map(
    (consents || []).map((c) => [c.notification_type, c])
  );

  return (
    <Card
      title="Push Notification Consent"
      description="COPPA 2026 requires separate consent before sending push notifications containing information about your child. Toggle each notification type below."
    >
      <div className="divide-y divide-gray-100">
        {notificationTypes.map(({ type, label, description }) => {
          const consent = consentMap.get(type);
          const isConsented = consent?.consented ?? false;

          return (
            <div key={type} className="flex items-start justify-between gap-4 py-4">
              <div>
                <p className="text-sm font-medium text-gray-900">{label}</p>
                <p className="mt-0.5 text-xs text-gray-500">{description}</p>
              </div>
              <label className="relative inline-flex cursor-pointer items-center">
                <input
                  type="checkbox"
                  checked={isConsented}
                  onChange={() =>
                    updateConsent.mutate(
                      { member_id: memberId, notification_type: type, consented: !isConsented },
                      {
                        onSuccess: () =>
                          addToast(isConsented ? "Consent withdrawn" : "Consent granted", "success"),
                        onError: (e) => addToast((e as Error).message, "error"),
                      }
                    )
                  }
                  className="peer sr-only"
                />
                <div className="h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all peer-checked:bg-primary-600 peer-checked:after:translate-x-full peer-checked:after:border-white" />
              </label>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// ─── Identity Verification Section ───────────────────────────────────────────

function VerificationSection({ groupId }: { groupId: string }) {
  const { data: statusData, isLoading: statusLoading } = useVideoVerificationStatus(groupId);
  const { data: verifications, isLoading: verifLoading } = useVideoVerifications(groupId);
  const initiate = useInitiateVideoVerification(groupId);
  const { addToast } = useToast();

  if (statusLoading || verifLoading) {
    return <LoadingCard title="Identity Verification" />;
  }

  const hasValid = statusData?.has_valid_verification ?? false;
  const items = verifications || [];

  return (
    <Card
      title="Parental Identity Verification"
      description="COPPA 2026 requires video-based identity verification for parental consent. Knowledge-based verification alone is no longer sufficient."
    >
      <div className="space-y-4">
        {/* Current status */}
        <div
          className={`rounded-lg p-4 ${
            hasValid ? "bg-green-50 border border-green-200" : "bg-amber-50 border border-amber-200"
          }`}
        >
          <div className="flex items-center gap-2">
            {hasValid ? (
              <>
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                <div>
                  <p className="text-sm font-medium text-green-900">Identity Verified</p>
                  <p className="text-xs text-green-700">
                    Your identity has been verified. Parental consent is valid.
                  </p>
                </div>
              </>
            ) : (
              <>
                <AlertTriangle className="h-5 w-5 text-amber-600" />
                <div>
                  <p className="text-sm font-medium text-amber-900">Verification Required</p>
                  <p className="text-xs text-amber-700">
                    Please verify your identity to maintain COPPA-compliant parental consent.
                  </p>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Verification methods */}
        <div className="space-y-3">
          <p className="text-sm font-medium text-gray-700">Start verification</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              {
                method: "yoti_id_check",
                label: "ID Document Check",
                desc: "Upload a government ID for automated verification",
              },
              {
                method: "video_selfie",
                label: "Video Selfie",
                desc: "Record a short video selfie for identity matching",
              },
            ].map(({ method, label, desc }) => (
              <button
                key={method}
                onClick={() =>
                  initiate.mutate(
                    { verification_method: method },
                    {
                      onSuccess: () => addToast("Verification initiated", "success"),
                      onError: (e) => addToast((e as Error).message, "error"),
                    }
                  )
                }
                disabled={initiate.isPending}
                className="rounded-lg border border-gray-200 p-4 text-left transition-colors hover:border-primary-300 hover:bg-primary-50"
              >
                <Video className="mb-2 h-5 w-5 text-primary" />
                <p className="text-sm font-medium text-gray-900">{label}</p>
                <p className="mt-0.5 text-xs text-gray-500">{desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Verification history */}
        {items.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700">Verification history</p>
            <div className="divide-y divide-gray-100 rounded-lg border border-gray-200">
              {items.map((v) => (
                <div key={v.id} className="flex items-center justify-between px-4 py-3">
                  <div>
                    <p className="text-sm text-gray-900 capitalize">
                      {v.verification_method.replace(/_/g, " ")}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(v.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <StatusBadge status={v.status} />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

// ─── Shared components ───────────────────────────────────────────────────────

function LoadingCard({ title }: { title: string }) {
  return (
    <Card title={title} description="">
      <div className="flex items-center gap-2 py-8">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm text-gray-500">Loading...</span>
      </div>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    verified: "bg-green-100 text-green-700",
    pending: "bg-yellow-100 text-yellow-700",
    in_progress: "bg-blue-100 text-blue-700",
    failed: "bg-red-100 text-red-700",
    expired: "bg-gray-100 text-gray-500",
  };

  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
        colors[status] || "bg-gray-100 text-gray-500"
      }`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
