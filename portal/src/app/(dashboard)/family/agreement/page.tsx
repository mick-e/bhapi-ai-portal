"use client";

import { useState, useEffect } from "react";
import {
  FileText,
  Check,
  Edit3,
  Plus,
  Trash2,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Calendar,
  Users,
  Shield,
  Clock,
  CheckCircle2,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  useAgreementTemplates,
  useActiveAgreement,
  useCreateAgreement,
  useUpdateAgreement,
  useSignAgreement,
  useReviewAgreement,
} from "@/hooks/use-agreement";
import { useToast } from "@/contexts/ToastContext";

interface AgreementRule {
  category: string;
  rule_text: string;
  enabled: boolean;
}

interface AgreementTemplate {
  title: string;
  rules: { category: string; text: string }[];
}

interface SignatureEntry {
  member_id: string;
  name: string;
  signed_at: string;
}

interface Agreement {
  id: string;
  group_id: string;
  title: string;
  template_id: string;
  rules: AgreementRule[];
  signed_by_parent: string | null;
  signed_by_parent_at: string | null;
  signed_by_members: SignatureEntry[];
  active: boolean;
  review_due: string | null;
  last_reviewed: string | null;
  created_at: string | null;
}

const ageBandDescriptions: Record<string, string> = {
  ages_7_10: "Simple, clear rules for young children using AI with close supervision.",
  ages_11_13: "Age-appropriate guidelines for pre-teens learning to use AI responsibly.",
  ages_14_16: "Collaborative agreement for teens balancing independence with safety.",
  ages_17_plus: "Mature guidelines for young adults preparing for independent AI use.",
};

const ageBandLabels: Record<string, string> = {
  ages_7_10: "Ages 7-10",
  ages_11_13: "Ages 11-13",
  ages_14_16: "Ages 14-16",
  ages_17_plus: "Ages 17+",
};

export default function AgreementPage() {
  const { data: templates, isLoading: loadingTemplates } = useAgreementTemplates();
  const { data: agreement, isLoading: loadingAgreement, isError, error, refetch } = useActiveAgreement();
  const createAgreement = useCreateAgreement();
  const updateAgreement = useUpdateAgreement();
  const signAgreement = useSignAgreement();
  const reviewAgreement = useReviewAgreement();
  const { addToast } = useToast();

  const [editMode, setEditMode] = useState(false);
  const [editedRules, setEditedRules] = useState<AgreementRule[]>([]);
  const [customRule, setCustomRule] = useState("");
  const [customCategory, setCustomCategory] = useState("custom");
  const [signerName, setSignerName] = useState("");
  const [signerId, setSignerId] = useState("");

  useEffect(() => {
    if (agreement?.rules) {
      setEditedRules(agreement.rules);
    }
  }, [agreement]);

  const isReviewDue =
    agreement?.review_due &&
    new Date(agreement.review_due) <= new Date();

  if (loadingTemplates || loadingAgreement) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">Loading agreement...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">
          Failed to load agreement
        </p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || "Something went wrong"}
        </p>
        <Button variant="secondary" size="sm" className="mt-4" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    );
  }

  function handleCreate(templateId: string) {
    createAgreement.mutate(
      { template_id: templateId },
      {
        onSuccess: () => addToast("Agreement created successfully", "success"),
        onError: (err) => addToast((err as Error).message || "Failed to create agreement", "error"),
      }
    );
  }

  function handleSaveRules() {
    updateAgreement.mutate(
      { rules: editedRules },
      {
        onSuccess: () => {
          setEditMode(false);
          addToast("Rules updated successfully", "success");
        },
        onError: (err) => addToast((err as Error).message || "Failed to update rules", "error"),
      }
    );
  }

  function handleAddCustomRule() {
    if (!customRule.trim()) return;
    setEditedRules([
      ...editedRules,
      { category: customCategory, rule_text: customRule.trim(), enabled: true },
    ]);
    setCustomRule("");
  }

  function handleToggleRule(index: number) {
    const updated = [...editedRules];
    updated[index] = { ...updated[index], enabled: !updated[index].enabled };
    setEditedRules(updated);
  }

  function handleRemoveRule(index: number) {
    setEditedRules(editedRules.filter((_, i) => i !== index));
  }

  function handleSign() {
    if (!signerId || !signerName) return;
    signAgreement.mutate(
      { member_id: signerId, name: signerName },
      {
        onSuccess: () => {
          setSignerName("");
          setSignerId("");
          addToast("Agreement signed successfully", "success");
        },
        onError: (err) => addToast((err as Error).message || "Failed to sign", "error"),
      }
    );
  }

  function handleReview() {
    reviewAgreement.mutate(undefined, {
      onSuccess: () => addToast("Agreement marked as reviewed", "success"),
      onError: (err) => addToast((err as Error).message || "Failed to mark reviewed", "error"),
    });
  }

  // No active agreement: show template selector
  if (!agreement) {
    return (
      <div>
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Family AI Agreement</h1>
          <p className="mt-1 text-sm text-gray-500">
            Create a shared agreement about AI usage with your family
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {templates &&
            Object.entries(templates as Record<string, AgreementTemplate>).map(([id, tpl]) => (
              <Card key={id}>
                <div className="flex flex-col gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-50">
                      <Shield className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900">{tpl.title}</h3>
                      <p className="text-xs text-gray-500">{ageBandLabels[id] || id}</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    {ageBandDescriptions[id] || ""}
                  </p>
                  <ul className="space-y-1.5">
                    {tpl.rules.slice(0, 3).map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                        <Check className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-teal-500" />
                        {r.text}
                      </li>
                    ))}
                    {tpl.rules.length > 3 && (
                      <li className="text-xs text-gray-400">
                        +{tpl.rules.length - 3} more rules
                      </li>
                    )}
                  </ul>
                  <Button
                    onClick={() => handleCreate(id)}
                    isLoading={createAgreement.isPending}
                    size="sm"
                  >
                    <FileText className="h-4 w-4" />
                    Use This Template
                  </Button>
                </div>
              </Card>
            ))}
        </div>
      </div>
    );
  }

  // Active agreement display
  return (
    <div>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Family AI Agreement</h1>
          <p className="mt-1 text-sm text-gray-500">{agreement.title}</p>
        </div>
        <div className="flex gap-2">
          {!editMode && (
            <Button variant="secondary" size="sm" onClick={() => setEditMode(true)}>
              <Edit3 className="h-4 w-4" />
              Edit Rules
            </Button>
          )}
        </div>
      </div>

      {/* Review reminder banner */}
      {isReviewDue && (
        <div className="mb-6 flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <Clock className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-amber-900">
              Agreement review is due
            </h4>
            <p className="mt-1 text-sm text-amber-700">
              It has been 90 days since this agreement was last reviewed. Review the rules
              with your family to make sure they are still appropriate.
            </p>
            <Button
              size="sm"
              className="mt-2"
              onClick={handleReview}
              isLoading={reviewAgreement.isPending}
            >
              Mark as Reviewed
            </Button>
          </div>
        </div>
      )}

      {/* Rules section */}
      <Card
        title="Agreement Rules"
        description={editMode ? "Toggle, add, or remove rules" : "Your family has agreed to these rules"}
      >
        <div className="space-y-3">
          {(editMode ? editedRules : agreement.rules).map((rule, index) => (
            <div
              key={index}
              className="flex items-start justify-between gap-3 rounded-lg border border-gray-100 p-3"
            >
              <div className="flex items-start gap-3">
                {editMode ? (
                  <button
                    type="button"
                    onClick={() => handleToggleRule(index)}
                    className={`mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded border transition-colors ${
                      rule.enabled
                        ? "border-teal-500 bg-teal-500 text-white"
                        : "border-gray-300 bg-white"
                    }`}
                  >
                    {rule.enabled && <Check className="h-3 w-3" />}
                  </button>
                ) : (
                  <CheckCircle2
                    className={`mt-0.5 h-5 w-5 flex-shrink-0 ${
                      rule.enabled ? "text-teal-500" : "text-gray-300"
                    }`}
                  />
                )}
                <div>
                  <p className={`text-sm ${rule.enabled ? "text-gray-900" : "text-gray-400 line-through"}`}>
                    {rule.rule_text}
                  </p>
                  <span className="mt-0.5 inline-block rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500 capitalize">
                    {rule.category}
                  </span>
                </div>
              </div>
              {editMode && (
                <button
                  onClick={() => handleRemoveRule(index)}
                  className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}

          {editMode && (
            <>
              <div className="flex gap-2 pt-2">
                <select
                  value={customCategory}
                  onChange={(e) => setCustomCategory(e.target.value)}
                  className="rounded-lg border border-gray-300 px-2 py-2 text-sm focus:border-primary focus:outline-none"
                >
                  <option value="custom">Custom</option>
                  <option value="platforms">Platforms</option>
                  <option value="time">Time</option>
                  <option value="content">Content</option>
                  <option value="safety">Safety</option>
                  <option value="honesty">Honesty</option>
                  <option value="privacy">Privacy</option>
                </select>
                <div className="flex-1">
                  <Input
                    value={customRule}
                    onChange={(e) => setCustomRule(e.target.value)}
                    placeholder="Add a custom rule..."
                    onKeyDown={(e) => e.key === "Enter" && handleAddCustomRule()}
                  />
                </div>
                <Button variant="secondary" size="sm" onClick={handleAddCustomRule}>
                  <Plus className="h-4 w-4" />
                  Add
                </Button>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setEditMode(false);
                    setEditedRules(agreement.rules);
                  }}
                >
                  Cancel
                </Button>
                <Button onClick={handleSaveRules} isLoading={updateAgreement.isPending}>
                  Save Rules
                </Button>
              </div>
            </>
          )}
        </div>
      </Card>

      {/* Signatures section */}
      <div className="mt-6">
        <Card title="Signatures" description="Family members who have agreed to these rules">
          <div className="space-y-3">
            {/* Parent signature */}
            {agreement.signed_by_parent && (
              <div className="flex items-center gap-3 rounded-lg bg-green-50 p-3">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                <div>
                  <p className="text-sm font-medium text-green-900">Parent (creator)</p>
                  <p className="text-xs text-green-700">
                    Signed {agreement.signed_by_parent_at
                      ? new Date(agreement.signed_by_parent_at).toLocaleDateString()
                      : ""}
                  </p>
                </div>
              </div>
            )}

            {/* Member signatures */}
            {agreement.signed_by_members.map((sig, i) => (
              <div key={i} className="flex items-center gap-3 rounded-lg bg-green-50 p-3">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                <div>
                  <p className="text-sm font-medium text-green-900">{sig.name}</p>
                  <p className="text-xs text-green-700">
                    Signed {new Date(sig.signed_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}

            {/* Sign form */}
            <div className="border-t border-gray-200 pt-4">
              <h4 className="mb-3 text-sm font-semibold text-gray-900">
                Add a Signature
              </h4>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  value={signerId}
                  onChange={(e) => setSignerId(e.target.value)}
                  placeholder="Member ID"
                />
                <Input
                  value={signerName}
                  onChange={(e) => setSignerName(e.target.value)}
                  placeholder="Name"
                />
                <Button
                  onClick={handleSign}
                  isLoading={signAgreement.isPending}
                  disabled={!signerId || !signerName}
                  size="sm"
                >
                  <FileText className="h-4 w-4" />
                  Sign
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Agreement info */}
      <div className="mt-6">
        <Card>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4" />
                Created: {agreement.created_at ? new Date(agreement.created_at).toLocaleDateString() : "—"}
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="h-4 w-4" />
                Review due: {agreement.review_due ? new Date(agreement.review_due).toLocaleDateString() : "—"}
              </span>
              <span className="flex items-center gap-1.5">
                <Users className="h-4 w-4" />
                {agreement.signed_by_members.length + (agreement.signed_by_parent ? 1 : 0)} signatures
              </span>
            </div>
            {!isReviewDue && (
              <Button variant="ghost" size="sm" onClick={handleReview} isLoading={reviewAgreement.isPending}>
                Mark Reviewed
              </Button>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
