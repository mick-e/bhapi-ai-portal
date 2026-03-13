"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Plus,
  Users,
  Download,
  Bell,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  X,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useTranslations } from "@/contexts/LocaleContext";
import { groupsApi, settingsApi } from "@/lib/api-client";

const STORAGE_KEY = "bhapi_onboarding_complete";

type GroupType = "family" | "school" | "club";
type EmailFrequency = "immediate" | "daily" | "weekly";
type SeverityThreshold = "critical" | "high" | "medium" | "low";

interface MemberEntry {
  name: string;
}

interface OnboardingWizardProps {
  hasGroup: boolean;
  memberCount: number;
  hasExtension: boolean;
  hasAlerts: boolean;
  onDismiss: () => void;
}

export default function OnboardingWizard({
  hasGroup,
  memberCount,
  hasExtension,
  hasAlerts,
  onDismiss,
}: OnboardingWizardProps) {
  const t = useTranslations("onboarding");
  const [step, setStep] = useState(1);
  const [completed, setCompleted] = useState(false);

  // Step 1 state
  const [groupName, setGroupName] = useState("");
  const [groupType, setGroupType] = useState<GroupType>("family");
  const [creatingGroup, setCreatingGroup] = useState(false);
  const [groupError, setGroupError] = useState<string | null>(null);

  // Step 2 state
  const [members, setMembers] = useState<MemberEntry[]>([{ name: "" }]);

  // Step 4 state
  const [emailFrequency, setEmailFrequency] = useState<EmailFrequency>("daily");
  const [severityThreshold, setSeverityThreshold] = useState<SeverityThreshold>("high");
  const [savingAlerts, setSavingAlerts] = useState(false);

  const totalSteps = 4;

  // Check localStorage on mount
  useEffect(() => {
    try {
      const done = localStorage.getItem(STORAGE_KEY);
      if (done === "true") {
        setCompleted(true);
      }
    } catch {
      // ignore
    }
  }, []);

  const markComplete = useCallback(() => {
    setCompleted(true);
    try {
      localStorage.setItem(STORAGE_KEY, "true");
      localStorage.setItem("bhapi_onboarding_dismissed", "true");
    } catch {
      // ignore
    }
    onDismiss();
  }, [onDismiss]);

  const handleDismiss = useCallback(() => {
    try {
      localStorage.setItem("bhapi_onboarding_dismissed", "true");
    } catch {
      // ignore
    }
    onDismiss();
  }, [onDismiss]);

  // Step 1: Create group
  async function handleCreateGroup() {
    if (!groupName.trim()) {
      setGroupError(t("wizardGroupNameRequired"));
      return;
    }
    setCreatingGroup(true);
    setGroupError(null);
    try {
      await groupsApi.create({ name: groupName.trim(), type: groupType });
      setStep(2);
    } catch (err) {
      setGroupError(
        err instanceof Error ? err.message : t("wizardGroupCreateFailed")
      );
    } finally {
      setCreatingGroup(false);
    }
  }

  // Step 2: Member helpers
  function addMember() {
    setMembers([...members, { name: "" }]);
  }

  function updateMember(index: number, name: string) {
    const updated = [...members];
    updated[index] = { name };
    setMembers(updated);
  }

  function removeMember(index: number) {
    if (members.length > 1) {
      setMembers(members.filter((_, i) => i !== index));
    }
  }

  // Step 4: Save alert preferences
  async function handleSaveAlerts() {
    setSavingAlerts(true);
    try {
      await settingsApi.updateGroupSettings({
        digest_mode: emailFrequency,
        notifications: {
          critical_safety: true,
          risk_warnings: severityThreshold !== "critical",
          spend_alerts: true,
          member_updates: true,
          weekly_digest: emailFrequency === "weekly",
          report_notifications: true,
        },
      });
    } catch {
      // Silently continue -- alert prefs can be set later in settings
    } finally {
      setSavingAlerts(false);
      markComplete();
    }
  }

  if (completed) return null;

  const stepIcons = [Plus, Users, Download, Bell];
  const stepLabels = [
    t("wizardStep1Title"),
    t("wizardStep2Title"),
    t("wizardStep3Title"),
    t("wizardStep4Title"),
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative mx-auto w-full max-w-lg rounded-xl bg-white shadow-xl">
        {/* Close button */}
        <button
          onClick={handleDismiss}
          className="absolute right-4 top-4 text-gray-400 hover:text-gray-600"
          aria-label={t("wizardDismiss")}
        >
          <X className="h-5 w-5" />
        </button>

        <div className="p-6 sm:p-8">
          {/* Step indicator */}
          {step <= totalSteps && (
            <div className="mb-6">
              <div className="flex items-center justify-center gap-3">
                {[1, 2, 3, 4].map((s) => {
                  const Icon = stepIcons[s - 1];
                  const isActive = s === step;
                  const isDone = s < step;
                  return (
                    <div key={s} className="flex items-center gap-3">
                      <div
                        className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold transition-colors ${
                          isDone
                            ? "bg-green-500 text-white"
                            : isActive
                              ? "bg-primary-600 text-white"
                              : "bg-gray-100 text-gray-400"
                        }`}
                      >
                        {isDone ? (
                          <CheckCircle className="h-5 w-5" />
                        ) : (
                          <Icon className="h-4 w-4" />
                        )}
                      </div>
                      {s < 4 && (
                        <div
                          className={`hidden h-0.5 w-6 sm:block ${
                            s < step ? "bg-green-500" : "bg-gray-200"
                          }`}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
              <p className="mt-3 text-center text-xs text-gray-400">
                {t("wizardStepOf")
                  .replace("{step}", String(step))
                  .replace("{total}", String(totalSteps))}
              </p>
            </div>
          )}

          {/* Step 1: Create Your Group */}
          {step === 1 && (
            <div>
              <div className="text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary-100">
                  <Plus className="h-7 w-7 text-primary-600" />
                </div>
                <h2 className="mt-4 text-xl font-bold text-gray-900">
                  {t("wizardStep1Title")}
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  {t("wizardStep1Desc")}
                </p>
              </div>

              <div className="mt-6 space-y-4">
                {groupError && (
                  <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">
                    {groupError}
                  </div>
                )}

                <div>
                  <label
                    htmlFor="wizard-group-name"
                    className="block text-sm font-medium text-gray-700"
                  >
                    {t("wizardGroupName")}
                  </label>
                  <input
                    id="wizard-group-name"
                    type="text"
                    value={groupName}
                    onChange={(e) => setGroupName(e.target.value)}
                    placeholder={
                      groupType === "family"
                        ? t("wizardPlaceholderFamily")
                        : groupType === "school"
                          ? t("wizardPlaceholderSchool")
                          : t("wizardPlaceholderClub")
                    }
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    onKeyDown={(e) => e.key === "Enter" && handleCreateGroup()}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    {t("wizardGroupType")}
                  </label>
                  <div className="mt-2 grid grid-cols-3 gap-2">
                    {(["family", "school", "club"] as GroupType[]).map(
                      (type) => (
                        <button
                          key={type}
                          onClick={() => setGroupType(type)}
                          className={`rounded-lg border p-3 text-sm font-medium transition-colors ${
                            groupType === type
                              ? "border-primary-500 bg-primary-50 text-primary-700"
                              : "border-gray-200 text-gray-700 hover:border-gray-300"
                          }`}
                        >
                          {t(`wizardType_${type}`)}
                        </button>
                      )
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-6 flex items-center justify-between">
                <button
                  onClick={handleDismiss}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  {t("wizardSkip")}
                </button>
                <Button
                  onClick={handleCreateGroup}
                  isLoading={creatingGroup}
                  disabled={!groupName.trim()}
                >
                  {t("wizardNext")}
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Step 2: Add Members */}
          {step === 2 && (
            <div>
              <div className="text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-teal-100">
                  <Users className="h-7 w-7 text-teal-600" />
                </div>
                <h2 className="mt-4 text-xl font-bold text-gray-900">
                  {t("wizardStep2Title")}
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  {t("wizardStep2Desc")}
                </p>
              </div>

              <div className="mt-6 space-y-3">
                {members.map((member, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={member.name}
                      onChange={(e) => updateMember(i, e.target.value)}
                      placeholder={t("wizardMemberPlaceholder")}
                      className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    />
                    {members.length > 1 && (
                      <button
                        onClick={() => removeMember(i)}
                        className="flex-shrink-0 text-sm text-red-500 hover:text-red-700"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ))}

                <button
                  onClick={addMember}
                  className="flex w-full items-center justify-center gap-1 rounded-lg border-2 border-dashed border-gray-300 py-2 text-sm text-gray-500 hover:border-primary-400 hover:text-primary-600"
                >
                  <Plus className="h-4 w-4" />
                  {t("wizardAddAnother")}
                </button>
              </div>

              <div className="mt-6 flex items-center justify-between">
                <Button variant="secondary" onClick={() => setStep(1)}>
                  <ArrowLeft className="h-4 w-4" />
                  {t("wizardBack")}
                </Button>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setStep(3)}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    {t("wizardSkip")}
                  </button>
                  <Button onClick={() => setStep(3)}>
                    {t("wizardNext")}
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Install Extension */}
          {step === 3 && (
            <div>
              <div className="text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary-100">
                  <Download className="h-7 w-7 text-primary-600" />
                </div>
                <h2 className="mt-4 text-xl font-bold text-gray-900">
                  {t("wizardStep3Title")}
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  {t("wizardStep3Desc")}
                </p>
              </div>

              <div className="mt-6 space-y-4">
                <a
                  href="https://chrome.google.com/webstore"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 rounded-lg border border-gray-200 p-4 transition-colors hover:border-primary-300 hover:bg-primary-50"
                >
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100">
                    <Download className="h-5 w-5 text-gray-600" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-900">
                      {t("wizardChromeStore")}
                    </p>
                    <p className="text-xs text-gray-500">
                      {t("wizardChromeStoreDesc")}
                    </p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-gray-400" />
                </a>

                <div className="rounded-lg bg-gray-50 p-4">
                  <h3 className="text-sm font-semibold text-gray-900">
                    {t("wizardInstallSteps")}
                  </h3>
                  <ol className="mt-2 space-y-1.5 text-xs text-gray-600">
                    <li className="flex items-start gap-2">
                      <span className="mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-[10px] font-bold text-primary-700">
                        1
                      </span>
                      {t("wizardInstallStep1")}
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-[10px] font-bold text-primary-700">
                        2
                      </span>
                      {t("wizardInstallStep2")}
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 text-[10px] font-bold text-primary-700">
                        3
                      </span>
                      {t("wizardInstallStep3")}
                    </li>
                  </ol>
                </div>
              </div>

              <div className="mt-6 flex items-center justify-between">
                <Button variant="secondary" onClick={() => setStep(2)}>
                  <ArrowLeft className="h-4 w-4" />
                  {t("wizardBack")}
                </Button>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setStep(4)}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    {t("wizardSkip")}
                  </button>
                  <Button onClick={() => setStep(4)}>
                    {t("wizardNext")}
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Configure Alerts */}
          {step === 4 && (
            <div>
              <div className="text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-teal-100">
                  <Bell className="h-7 w-7 text-teal-600" />
                </div>
                <h2 className="mt-4 text-xl font-bold text-gray-900">
                  {t("wizardStep4Title")}
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  {t("wizardStep4Desc")}
                </p>
              </div>

              <div className="mt-6 space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    {t("wizardEmailFrequency")}
                  </label>
                  <div className="mt-2 space-y-2">
                    {(
                      [
                        { value: "immediate", label: t("wizardFreqImmediate") },
                        { value: "daily", label: t("wizardFreqDaily") },
                        { value: "weekly", label: t("wizardFreqWeekly") },
                      ] as { value: EmailFrequency; label: string }[]
                    ).map((option) => (
                      <button
                        key={option.value}
                        onClick={() => setEmailFrequency(option.value)}
                        className={`flex w-full items-center gap-3 rounded-lg border p-3 text-left text-sm transition-colors ${
                          emailFrequency === option.value
                            ? "border-primary-500 bg-primary-50 font-medium text-primary-700"
                            : "border-gray-200 text-gray-700 hover:border-gray-300"
                        }`}
                      >
                        <div
                          className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border-2 ${
                            emailFrequency === option.value
                              ? "border-primary-500"
                              : "border-gray-300"
                          }`}
                        >
                          {emailFrequency === option.value && (
                            <div className="h-2.5 w-2.5 rounded-full bg-primary-500" />
                          )}
                        </div>
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    {t("wizardSeverityThreshold")}
                  </label>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    {(
                      [
                        { value: "low", label: t("wizardSevLow"), color: "text-green-600" },
                        { value: "medium", label: t("wizardSevMedium"), color: "text-amber-500" },
                        { value: "high", label: t("wizardSevHigh"), color: "text-orange-600" },
                        { value: "critical", label: t("wizardSevCritical"), color: "text-red-600" },
                      ] as { value: SeverityThreshold; label: string; color: string }[]
                    ).map((option) => (
                      <button
                        key={option.value}
                        onClick={() => setSeverityThreshold(option.value)}
                        className={`rounded-lg border p-3 text-sm transition-colors ${
                          severityThreshold === option.value
                            ? "border-primary-500 bg-primary-50 font-medium text-primary-700"
                            : "border-gray-200 text-gray-700 hover:border-gray-300"
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-6 flex items-center justify-between">
                <Button variant="secondary" onClick={() => setStep(3)}>
                  <ArrowLeft className="h-4 w-4" />
                  {t("wizardBack")}
                </Button>
                <div className="flex items-center gap-3">
                  <button
                    onClick={markComplete}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    {t("wizardSkip")}
                  </button>
                  <Button onClick={handleSaveAlerts} isLoading={savingAlerts}>
                    {t("wizardFinish")}
                    <CheckCircle className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Completion screen */}
          {step > totalSteps && (
            <div className="text-center py-4">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
              <h2 className="mt-4 text-xl font-bold text-gray-900">
                {t("wizardAllSet")}
              </h2>
              <p className="mt-2 text-sm text-gray-500">
                {t("wizardAllSetDesc")}
              </p>
              <Button onClick={markComplete} className="mt-6 w-full">
                {t("wizardGoToDashboard")}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export { OnboardingWizard };
