"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  completed: boolean;
}

const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    id: "create_group",
    title: "Create Your Group",
    description: "Set up a family, school, or club group to get started.",
    completed: false,
  },
  {
    id: "add_members",
    title: "Add Members",
    description: "Invite family members, students, or participants.",
    completed: false,
  },
  {
    id: "install_extension",
    title: "Install Browser Extension",
    description: "Install the bhapi extension to start monitoring AI usage.",
    completed: false,
  },
  {
    id: "configure_alerts",
    title: "Set Up Alerts",
    description: "Choose how you want to be notified about AI activity.",
    completed: false,
  },
];

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
  const router = useRouter();
  const [dismissed, setDismissed] = useState(false);

  const steps = ONBOARDING_STEPS.map((step) => ({
    ...step,
    completed:
      (step.id === "create_group" && hasGroup) ||
      (step.id === "add_members" && memberCount > 0) ||
      (step.id === "install_extension" && hasExtension) ||
      (step.id === "configure_alerts" && hasAlerts),
  }));

  const completedCount = steps.filter((s) => s.completed).length;
  const progress = Math.round((completedCount / steps.length) * 100);
  const allComplete = completedCount === steps.length;

  const handleStepClick = useCallback(
    (stepId: string) => {
      switch (stepId) {
        case "create_group":
          router.push("/groups");
          break;
        case "add_members":
          router.push("/members");
          break;
        case "install_extension":
          router.push("/extension");
          break;
        case "configure_alerts":
          router.push("/alerts");
          break;
      }
    },
    [router]
  );

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss();
    try {
      localStorage.setItem("bhapi_onboarding_dismissed", "true");
    } catch {
      // ignore
    }
  };

  if (dismissed || allComplete) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Welcome to bhapi!
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Complete these steps to start monitoring AI usage.
          </p>
        </div>
        <button
          onClick={handleDismiss}
          className="text-gray-400 hover:text-gray-600 text-sm"
          aria-label="Dismiss onboarding"
        >
          <span aria-hidden="true">&times;</span>
        </button>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-100 rounded-full h-2 mb-6">
        <div
          className="bg-primary-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="text-xs text-gray-400 mb-4">
        {completedCount} of {steps.length} complete
      </p>

      {/* Steps */}
      <div className="space-y-3">
        {steps.map((step, index) => (
          <button
            key={step.id}
            onClick={() => !step.completed && handleStepClick(step.id)}
            disabled={step.completed}
            className={`w-full flex items-center gap-4 p-4 rounded-lg border text-left transition-colors ${
              step.completed
                ? "bg-green-50 border-green-200 cursor-default"
                : "bg-gray-50 border-gray-200 hover:bg-primary-50 hover:border-primary-300 cursor-pointer"
            }`}
          >
            <div
              className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step.completed
                  ? "bg-green-500 text-white"
                  : "bg-gray-200 text-gray-600"
              }`}
            >
              {step.completed ? "\u2713" : index + 1}
            </div>
            <div>
              <p
                className={`font-medium ${
                  step.completed ? "text-green-700" : "text-gray-900"
                }`}
              >
                {step.title}
              </p>
              <p className="text-sm text-gray-500">{step.description}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
