"use client";

import { useState, useEffect, Suspense } from "react";
import {
  Shield,
  Phone,
  Mail,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Trash2,
  UserPlus,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { OnboardingCard } from "@/components/ui/OnboardingCard";
import { ShieldCheck } from "lucide-react";
import { useGroupSettings, useUpdateGroupSettings } from "@/hooks/use-settings";
import {
  useEmergencyContacts,
  useAddEmergencyContact,
  useRemoveEmergencyContact,
} from "@/hooks/use-emergency-contacts";
import type { EmergencyContact } from "@/hooks/use-emergency-contacts";
import { useToast } from "@/contexts/ToastContext";
import { useTranslations } from "@/contexts/LocaleContext";
import type { SafetyLevel } from "@/types";

export default function SafetyPage() {
  return (
    <Suspense>
      <SafetyPageInner />
    </Suspense>
  );
}

function SafetyPageInner() {
  const t = useTranslations("safety");
  const {
    data: settings,
    isLoading,
    isError,
    error,
    refetch,
  } = useGroupSettings();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-sm text-gray-500">{t("loadingSettings")}</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">{t("failedToLoad")}</p>
        <p className="mt-1 text-sm text-gray-500">
          {(error as Error)?.message || t("somethingWentWrong")}
        </p>
        <Button variant="secondary" size="sm" className="mt-4" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
          {t("tryAgain")}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("title")}</h1>
        <p className="mt-1 text-sm text-gray-500">
          {t("description")}
        </p>
      </div>

      <OnboardingCard
        id="safety-intro"
        icon={ShieldCheck}
        title="Your Safety Rules"
        description="Set up blocking rules, bedtime schedules, and emergency contacts here. These apply across all your children's devices."
      />

      {settings && (
        <SafetyRulesSection
          safetyLevel={settings.safety_level}
          autoBlockCritical={settings.auto_block_critical}
          piiDetection={settings.pii_detection}
        />
      )}

      <EmergencyContactsSection />
    </div>
  );
}

// ─── Safety Rules ────────────────────────────────────────────────────────────

function SafetyRulesSection({
  safetyLevel: initialLevel,
  autoBlockCritical: initialAutoBlock,
  piiDetection: initialPiiDetect,
}: {
  safetyLevel: SafetyLevel;
  autoBlockCritical: boolean;
  piiDetection: boolean;
}) {
  const t = useTranslations("safety");
  const [safetyLevel, setSafetyLevel] = useState<SafetyLevel>(initialLevel);
  const [autoBlock, setAutoBlock] = useState(initialAutoBlock);
  const [piiDetect, setPiiDetect] = useState(initialPiiDetect);
  const updateSettings = useUpdateGroupSettings();
  const { addToast } = useToast();

  const SAFETY_LEVEL_OPTIONS = [
    { value: "strict", label: t("levelStrict") },
    { value: "moderate", label: t("levelModerate") },
    { value: "permissive", label: t("levelPermissive") },
  ];

  useEffect(() => {
    setSafetyLevel(initialLevel);
    setAutoBlock(initialAutoBlock);
    setPiiDetect(initialPiiDetect);
  }, [initialLevel, initialAutoBlock, initialPiiDetect]);

  function handleSave() {
    updateSettings.mutate(
      {
        safety_level: safetyLevel,
        auto_block_critical: autoBlock,
        pii_detection: piiDetect,
      },
      {
        onSuccess: () => addToast(t("rulesUpdated"), "success"),
        onError: (err) =>
          addToast((err as Error).message || t("failedUpdateRules"), "error"),
      }
    );
  }

  return (
    <Card
      title={t("safetyRules")}
      description={t("safetyRulesDesc")}
    >
      <div className="max-w-lg space-y-6">
        <Select
          label={t("defaultSafetyLevel")}
          options={SAFETY_LEVEL_OPTIONS}
          value={safetyLevel}
          onChange={(v) => setSafetyLevel(v as SafetyLevel)}
        />

        <SafetyToggle
          label={t("autoBlockCritical")}
          description={t("autoBlockDesc")}
          checked={autoBlock}
          disabled
          onToggle={() => {}}
          disabledLabel={t("alwaysEnabled")}
        />

        <SafetyToggle
          label={t("piiDetection")}
          description={t("piiDetectionDesc")}
          checked={piiDetect}
          onToggle={() => setPiiDetect(!piiDetect)}
        />

        <div className="pt-2">
          <Button onClick={handleSave} isLoading={updateSettings.isPending}>
            {t("saveRules")}
          </Button>
        </div>
      </div>
    </Card>
  );
}

// ─── Emergency Contacts ──────────────────────────────────────────────────────

function EmergencyContactsSection() {
  const t = useTranslations("safety");
  const RELATIONSHIP_LABELS: Record<string, string> = {
    grandparent: t("relGrandparent"),
    school_counselor: t("relSchoolCounselor"),
    trusted_adult: t("relTrustedAdult"),
    aunt_uncle: t("relAuntUncle"),
    family_friend: t("relFamilyFriend"),
    therapist: t("relTherapist"),
    other: t("relOther"),
  };

  const RELATIONSHIP_OPTIONS = Object.entries(RELATIONSHIP_LABELS).map(([value, label]) => ({
    value,
    label,
  }));
  const { data: contacts, isLoading, isError } = useEmergencyContacts();
  const addContact = useAddEmergencyContact();
  const removeContact = useRemoveEmergencyContact();
  const { addToast } = useToast();

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [relationship, setRelationship] = useState("trusted_adult");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [notifyOn, setNotifyOn] = useState<string[]>(["critical"]);
  const [consentGiven, setConsentGiven] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  function handleAdd() {
    if (!name || (!phone && !email)) return;
    addContact.mutate(
      {
        name,
        relationship,
        phone: phone || undefined,
        email: email || undefined,
        notify_on: notifyOn,
        consent_given: consentGiven,
      },
      {
        onSuccess: () => {
          setShowForm(false);
          setName("");
          setPhone("");
          setEmail("");
          setNotifyOn(["critical"]);
          setConsentGiven(false);
          addToast(t("contactAdded"), "success");
        },
        onError: (err) =>
          addToast((err as Error).message || t("failedAddContact"), "error"),
      }
    );
  }

  function handleRemove(id: string) {
    removeContact.mutate(id, {
      onSuccess: () => {
        setConfirmDelete(null);
        addToast(t("contactRemoved"), "success");
      },
    });
  }

  function toggleNotifyType(type: string) {
    setNotifyOn((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  }

  function resetForm() {
    setShowForm(false);
    setName("");
    setPhone("");
    setEmail("");
    setNotifyOn(["critical"]);
    setConsentGiven(false);
  }

  return (
    <Card
      title={t("emergencyContacts")}
      description={t("emergencyContactsDesc")}
    >
      <div className="max-w-lg space-y-4">
        {addContact.isError && (
          <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {(addContact.error as Error)?.message || t("failedAddContact")}
          </div>
        )}

        {isLoading && (
          <div className="flex items-center gap-2 py-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm text-gray-500">{t("loadingContacts")}</span>
          </div>
        )}

        {isError && (
          <p className="text-sm text-red-600">{t("failedLoadContacts")}</p>
        )}

        {contacts && contacts.length > 0 && (
          <div className="space-y-3">
            {contacts.map((c: EmergencyContact) => (
              <div
                key={c.id}
                className="flex items-start justify-between rounded-lg border border-gray-200 p-4"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{c.name}</p>
                  <p className="mt-0.5 text-xs text-gray-500 capitalize">
                    {RELATIONSHIP_LABELS[c.relationship] || c.relationship}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-400">
                    {c.phone && (
                      <span className="flex items-center gap-1">
                        <Phone className="h-3 w-3" /> {c.phone}
                      </span>
                    )}
                    {c.email && (
                      <span className="flex items-center gap-1">
                        <Mail className="h-3 w-3" /> {c.email}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex gap-1">
                    {c.notify_on.map((type) => (
                      <span
                        key={type}
                        className="rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-600"
                      >
                        {type}
                      </span>
                    ))}
                  </div>
                  {!c.consent_given && (
                    <p className="mt-1 text-xs text-amber-600">{t("consentNotYet")}</p>
                  )}
                </div>
                {confirmDelete === c.id ? (
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemove(c.id)}
                      isLoading={removeContact.isPending}
                    >
                      {t("confirm")}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setConfirmDelete(null)}
                    >
                      {t("cancel")}
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setConfirmDelete(c.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}

        {contacts && contacts.length === 0 && !showForm && (
          <p className="text-sm text-gray-500">
            {t("noContactsYet")}
          </p>
        )}

        {showForm ? (
          <div className="space-y-3 rounded-lg border border-gray-200 p-4">
            <h4 className="text-sm font-semibold text-gray-900">{t("addEmergencyContact")}</h4>
            <Input
              label={t("nameLabel")}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("fullNamePlaceholder")}
            />
            <Select
              label={t("relationship")}
              options={RELATIONSHIP_OPTIONS}
              value={relationship}
              onChange={setRelationship}
            />
            <Input
              label={t("phoneOptional")}
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 (555) 123-4567"
            />
            <Input
              label={t("emailOptional")}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="contact@example.com"
            />
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                {t("notifyOn")}
              </label>
              <div className="flex flex-wrap gap-2">
                {["critical", "self_harm", "csam_adjacent"].map((type) => (
                  <button
                    key={type}
                    onClick={() => toggleNotifyType(type)}
                    className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                      notifyOn.includes(type)
                        ? "border-red-200 bg-red-50 text-red-700"
                        : "border-gray-200 text-gray-500 hover:bg-gray-50"
                    }`}
                  >
                    {type.replace("_", " ")}
                  </button>
                ))}
              </div>
            </div>
            <SafetyToggle
              label={t("contactConsentLabel")}
              description={t("contactConsentDesc")}
              checked={consentGiven}
              onToggle={() => setConsentGiven(!consentGiven)}
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={resetForm}>
                {t("cancel")}
              </Button>
              <Button
                onClick={handleAdd}
                isLoading={addContact.isPending}
                disabled={!name || (!phone && !email)}
              >
                {t("addContact")}
              </Button>
            </div>
          </div>
        ) : (
          <Button variant="secondary" onClick={() => setShowForm(true)}>
            <UserPlus className="h-4 w-4" />
            {t("addEmergencyContact")}
          </Button>
        )}

        <p className="text-xs text-gray-400">
          {t("contactsFooterNote")}
        </p>
      </div>
    </Card>
  );
}

// ─── Toggle helper ───────────────────────────────────────────────────────────

function SafetyToggle({
  label,
  description,
  checked,
  disabled,
  onToggle,
  disabledLabel,
}: {
  label: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onToggle: () => void;
  disabledLabel?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-gray-900">{label}</p>
        <p className="mt-0.5 text-xs text-gray-500">{description}</p>
        {disabled && (
          <p className="mt-0.5 text-xs text-amber-600">{disabledLabel ?? "Always enabled for safety"}</p>
        )}
      </div>
      <button
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={onToggle}
        className={`relative mt-0.5 inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
          checked ? "bg-primary" : "bg-gray-200"
        } ${disabled ? "cursor-not-allowed opacity-50" : ""}`}
      >
        <span
          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition-transform ${
            checked ? "translate-x-4" : "translate-x-0"
          }`}
        />
      </button>
    </div>
  );
}
