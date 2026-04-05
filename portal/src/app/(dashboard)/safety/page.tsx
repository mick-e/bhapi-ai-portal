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
import { useGroupSettings, useUpdateGroupSettings } from "@/hooks/use-settings";
import {
  useEmergencyContacts,
  useAddEmergencyContact,
  useRemoveEmergencyContact,
} from "@/hooks/use-emergency-contacts";
import type { EmergencyContact } from "@/hooks/use-emergency-contacts";
import { useToast } from "@/contexts/ToastContext";
import type { SafetyLevel } from "@/types";

export default function SafetyPage() {
  return (
    <Suspense>
      <SafetyPageInner />
    </Suspense>
  );
}

function SafetyPageInner() {
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
        <span className="ml-3 text-sm text-gray-500">Loading safety settings...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <AlertTriangle className="h-10 w-10 text-amber-500" />
        <p className="mt-3 text-sm font-medium text-gray-900">Failed to load safety settings</p>
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

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Safety</h1>
        <p className="mt-1 text-sm text-gray-500">
          Configure content filtering rules and emergency contacts
        </p>
      </div>

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

const SAFETY_LEVEL_OPTIONS = [
  { value: "strict", label: "Strict (recommended for children)" },
  { value: "moderate", label: "Moderate" },
  { value: "permissive", label: "Permissive" },
];

function SafetyRulesSection({
  safetyLevel: initialLevel,
  autoBlockCritical: initialAutoBlock,
  piiDetection: initialPiiDetect,
}: {
  safetyLevel: SafetyLevel;
  autoBlockCritical: boolean;
  piiDetection: boolean;
}) {
  const [safetyLevel, setSafetyLevel] = useState<SafetyLevel>(initialLevel);
  const [autoBlock, setAutoBlock] = useState(initialAutoBlock);
  const [piiDetect, setPiiDetect] = useState(initialPiiDetect);
  const updateSettings = useUpdateGroupSettings();
  const { addToast } = useToast();

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
        onSuccess: () => addToast("Safety rules updated", "success"),
        onError: (err) =>
          addToast((err as Error).message || "Failed to update safety rules", "error"),
      }
    );
  }

  return (
    <Card
      title="Safety Rules"
      description="Configure content filtering and safety policies"
    >
      <div className="max-w-lg space-y-6">
        <Select
          label="Default safety level"
          options={SAFETY_LEVEL_OPTIONS}
          value={safetyLevel}
          onChange={(v) => setSafetyLevel(v as SafetyLevel)}
        />

        <SafetyToggle
          label="Auto-block critical content"
          description="Automatically block interactions flagged as critical risk"
          checked={autoBlock}
          disabled
          onToggle={() => {}}
        />

        <SafetyToggle
          label="PII detection"
          description="Flag interactions containing personal information"
          checked={piiDetect}
          onToggle={() => setPiiDetect(!piiDetect)}
        />

        <div className="pt-2">
          <Button onClick={handleSave} isLoading={updateSettings.isPending}>
            Save Rules
          </Button>
        </div>
      </div>
    </Card>
  );
}

// ─── Emergency Contacts ──────────────────────────────────────────────────────

const RELATIONSHIP_LABELS: Record<string, string> = {
  grandparent: "Grandparent",
  school_counselor: "School Counselor",
  trusted_adult: "Trusted Adult",
  aunt_uncle: "Aunt / Uncle",
  family_friend: "Family Friend",
  therapist: "Therapist",
  other: "Other",
};

const RELATIONSHIP_OPTIONS = Object.entries(RELATIONSHIP_LABELS).map(([value, label]) => ({
  value,
  label,
}));

function EmergencyContactsSection() {
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
          addToast("Emergency contact added", "success");
        },
        onError: (err) =>
          addToast((err as Error).message || "Failed to add contact", "error"),
      }
    );
  }

  function handleRemove(id: string) {
    removeContact.mutate(id, {
      onSuccess: () => {
        setConfirmDelete(null);
        addToast("Emergency contact removed", "success");
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
      title="Emergency Contacts"
      description="People who should be notified during critical safety events"
    >
      <div className="max-w-lg space-y-4">
        {addContact.isError && (
          <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {(addContact.error as Error)?.message || "Failed to add contact"}
          </div>
        )}

        {isLoading && (
          <div className="flex items-center gap-2 py-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm text-gray-500">Loading contacts...</span>
          </div>
        )}

        {isError && (
          <p className="text-sm text-red-600">Failed to load emergency contacts.</p>
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
                    <p className="mt-1 text-xs text-amber-600">Consent not yet given</p>
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
                      Confirm
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setConfirmDelete(null)}
                    >
                      Cancel
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
            No emergency contacts yet. Add someone who should be notified during
            critical safety events.
          </p>
        )}

        {showForm ? (
          <div className="space-y-3 rounded-lg border border-gray-200 p-4">
            <h4 className="text-sm font-semibold text-gray-900">Add Emergency Contact</h4>
            <Input
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Full name"
            />
            <Select
              label="Relationship"
              options={RELATIONSHIP_OPTIONS}
              value={relationship}
              onChange={setRelationship}
            />
            <Input
              label="Phone (optional)"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 (555) 123-4567"
            />
            <Input
              label="Email (optional)"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="contact@example.com"
            />
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Notify on
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
              label="Contact has given consent"
              description="This person has agreed to be contacted during emergencies"
              checked={consentGiven}
              onToggle={() => setConsentGiven(!consentGiven)}
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={resetForm}>
                Cancel
              </Button>
              <Button
                onClick={handleAdd}
                isLoading={addContact.isPending}
                disabled={!name || (!phone && !email)}
              >
                Add Contact
              </Button>
            </div>
          </div>
        ) : (
          <Button variant="secondary" onClick={() => setShowForm(true)}>
            <UserPlus className="h-4 w-4" />
            Add Emergency Contact
          </Button>
        )}

        <p className="text-xs text-gray-400">
          Emergency contacts will be notified via SMS and/or email when critical
          safety events are detected. Ensure you have their consent before adding them.
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
}: {
  label: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-gray-900">{label}</p>
        <p className="mt-0.5 text-xs text-gray-500">{description}</p>
        {disabled && (
          <p className="mt-0.5 text-xs text-amber-600">Always enabled for safety</p>
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
