"use client";
import React, { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

const STORAGE_KEY = "bhapi_onboarding_complete";

interface OnboardingWizardProps {
  hasGroup: boolean;
  memberCount: number;
  hasExtension: boolean;
  hasAlerts: boolean;
  onDismiss: () => void;
}

export default function OnboardingWizard({
  memberCount,
  hasExtension,
  onDismiss,
}: OnboardingWizardProps) {
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    try {
      if (localStorage.getItem(STORAGE_KEY) === "true") {
        setDismissed(true);
      }
    } catch {
      // ignore
    }
  }, []);

  if (dismissed || (memberCount > 0 && hasExtension)) return null;

  const steps = [
    {
      done: memberCount > 0,
      label: "Add your first child",
      action: "/members",
      cta: "Add child",
    },
    {
      done: hasExtension,
      label: "Install the browser extension",
      action: "https://chrome.google.com/webstore/detail/bhapi",
      cta: "Install extension",
    },
  ].filter((s) => !s.done);

  if (steps.length === 0) {
    try {
      localStorage.setItem(STORAGE_KEY, "true");
    } catch {
      // ignore
    }
    return null;
  }

  function handleDismiss() {
    try {
      localStorage.setItem(STORAGE_KEY, "true");
    } catch {
      // ignore
    }
    setDismissed(true);
    onDismiss();
  }

  return (
    <Card
      title="Get started"
      footer={
        <button
          onClick={handleDismiss}
          className="text-sm text-gray-400 hover:text-gray-600"
        >
          Dismiss
        </button>
      }
    >
      <div className="space-y-3">
        {steps.map((step, i) => (
          <div
            key={i}
            className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-3"
          >
            <span className="text-sm text-gray-700">{step.label}</span>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                window.location.href = step.action;
              }}
            >
              {step.cta}
            </Button>
          </div>
        ))}
      </div>
    </Card>
  );
}

export { OnboardingWizard };
