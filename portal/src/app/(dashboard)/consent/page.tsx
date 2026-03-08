"use client";

import { useState } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  Loader2,
  RefreshCw,
  CheckCircle2,
  Clock,
  X,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useMembers, useRecordConsent } from "@/hooks/use-members";
import { useToast } from "@/contexts/ToastContext";
import type { GroupMember, ConsentType } from "@/types";

const CONSENT_TYPES: { value: ConsentType; label: string; description: string }[] = [
  { value: "monitoring", label: "AI Monitoring", description: "Consent to monitor AI interactions for safety" },
  { value: "ai_interaction", label: "AI Interaction", description: "Consent to use AI tools through monitored platforms" },
  { value: "data_collection", label: "Data Collection", description: "Consent to collect and process usage data" },
  { value: "coppa", label: "COPPA (US)", description: "Children's Online Privacy Protection Act — required for users under 13 in the US" },
  { value: "gdpr", label: "GDPR (EU)", description: "General Data Protection Regulation — required for users under 16 in the EU" },
  { value: "lgpd", label: "LGPD (Brazil)", description: "Lei Geral de Protecao de Dados — required for users under 18 in Brazil" },
  { value: "au_privacy", label: "AU Privacy (Australia)", description: "Australian Privacy Act — required for users under 16" },
];

export default function ConsentPage() {
  const [showRecordModal, setShowRecordModal] = useState(false);
  const [selectedMember, setSelectedMember] = useState<GroupMember | null>(null);

  const {
    data: membersData,
    isLoading,
    isError,
    error,
    refetch,
  } = useMembers({ page: 1, page_size: 100 });

  const members = membersData?.items ?? [];

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading consent data...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">Failed to load consent data</p>
        <p className="mt-1 text-sm text-gray-500">{(error as Error)?.message || "Something went wrong"}</p>
        <Button variant="secondary" size="sm" className="mt-4" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    );
  }

  // Separate members by consent status based on role heuristic:
  // "member" role members likely need consent (children/students)
  const membersNeedingConsent = members.filter(
    (m) => m.role === "member" || m.role === "viewer"
  );

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Consent Management</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage guardian consent for monitored members (COPPA/GDPR/LGPD compliance)
        </p>
      </div>

      {/* Overview Stats */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {membersNeedingConsent.filter((m) => m.status === "active").length}
              </p>
              <p className="text-sm text-gray-500">Consent recorded</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50">
              <Clock className="h-5 w-5 text-amber-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {membersNeedingConsent.filter((m) => m.status === "invited").length}
              </p>
              <p className="text-sm text-gray-500">Pending consent</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
              <ShieldCheck className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {membersNeedingConsent.length}
              </p>
              <p className="text-sm text-gray-500">Members requiring consent</p>
            </div>
          </div>
        </div>
      </div>

      {/* Consent Types Reference */}
      <Card title="Required Consent Types" description="Based on member age and jurisdiction">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {CONSENT_TYPES.map((ct) => (
            <div
              key={ct.value}
              className="rounded-lg border border-gray-100 p-3"
            >
              <p className="text-sm font-medium text-gray-900">{ct.label}</p>
              <p className="mt-0.5 text-xs text-gray-500">{ct.description}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Members Consent Table */}
      <div className="mt-6">
        <Card title="Member Consent Status">
          <div className="-mx-6 -my-4 overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Member
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Status
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {membersNeedingConsent.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center">
                      <ShieldCheck className="mx-auto h-10 w-10 text-gray-300" />
                      <p className="mt-3 text-sm text-gray-500">
                        No members currently require consent
                      </p>
                    </td>
                  </tr>
                ) : (
                  membersNeedingConsent.map((member) => (
                    <tr key={member.id} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary">
                            {member.display_name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">
                              {member.display_name}
                            </p>
                            <p className="text-xs text-gray-500">{member.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-sm capitalize text-gray-600">
                        {member.role}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4">
                        {member.status === "active" ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                            <CheckCircle2 className="h-3 w-3" />
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                            <Clock className="h-3 w-3" />
                            Pending
                          </span>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-6 py-4 text-right">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            setSelectedMember(member);
                            setShowRecordModal(true);
                          }}
                        >
                          Record Consent
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {showRecordModal && selectedMember && (
        <RecordConsentModal
          member={selectedMember}
          onClose={() => {
            setShowRecordModal(false);
            setSelectedMember(null);
          }}
        />
      )}
    </div>
  );
}

function RecordConsentModal({
  member,
  onClose,
}: {
  member: GroupMember;
  onClose: () => void;
}) {
  const { addToast } = useToast();
  const recordConsent = useRecordConsent();
  const [consentType, setConsentType] = useState<ConsentType>("monitoring");
  const [evidence, setEvidence] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    recordConsent.mutate(
      {
        memberId: member.id,
        data: {
          consent_type: consentType,
          evidence: evidence || undefined,
        },
      },
      {
        onSuccess: () => {
          addToast(`Consent recorded for ${member.display_name}`, "success");
          onClose();
        },
        onError: (err) =>
          addToast((err as Error).message || "Failed to record consent", "error"),
      }
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Record Consent</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <p className="mt-1 text-sm text-gray-500">
          Recording consent for <strong>{member.display_name}</strong>
        </p>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label htmlFor="consent-type" className="block text-sm font-medium text-gray-700">
              Consent Type
            </label>
            <select
              id="consent-type"
              value={consentType}
              onChange={(e) => setConsentType(e.target.value as ConsentType)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              {CONSENT_TYPES.map((ct) => (
                <option key={ct.value} value={ct.value}>
                  {ct.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="consent-evidence" className="block text-sm font-medium text-gray-700">
              Evidence (optional)
            </label>
            <textarea
              id="consent-evidence"
              value={evidence}
              onChange={(e) => setEvidence(e.target.value)}
              placeholder="Reference to signed consent form, verbal consent date, etc."
              rows={3}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button variant="secondary" size="sm" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button size="sm" type="submit" isLoading={recordConsent.isPending}>
              Record Consent
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
