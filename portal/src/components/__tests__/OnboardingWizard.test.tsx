import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import OnboardingWizard from "../OnboardingWizard";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock LocaleContext
vi.mock("@/contexts/LocaleContext", () => ({
  useTranslations: () => (key: string) => {
    const strings: Record<string, string> = {
      wizardStep1Title: "Create Your Group",
      wizardStep1Desc: "Name your group and select the type to get started.",
      wizardStep2Title: "Add Members",
      wizardStep2Desc: "Add child or student names you want to monitor.",
      wizardStep3Title: "Install Extension",
      wizardStep3Desc: "Install the Bhapi browser extension on your devices.",
      wizardStep4Title: "Configure Alerts",
      wizardStep4Desc: "Set your alert preferences to stay informed.",
      wizardStepOf: "Step {step} of {total}",
      wizardGroupName: "Group name",
      wizardGroupType: "Group type",
      wizardType_family: "Family",
      wizardType_school: "School",
      wizardType_club: "Club",
      wizardPlaceholderFamily: "The Smith Family",
      wizardPlaceholderSchool: "Oakwood Academy",
      wizardPlaceholderClub: "My Club",
      wizardGroupNameRequired: "Please enter a group name.",
      wizardMemberPlaceholder: "Child or student name",
      wizardAddAnother: "Add another member",
      wizardChromeStore: "Chrome Web Store",
      wizardInstallSteps: "How to install",
      wizardEmailFrequency: "Email notification frequency",
      wizardSeverityThreshold: "Minimum severity to alert on",
      wizardBack: "Back",
      wizardNext: "Next",
      wizardSkip: "Skip for now",
      wizardFinish: "Finish Setup",
      wizardAllSet: "You're all set!",
      wizardGoToDashboard: "Go to Dashboard",
      wizardDismiss: "Dismiss",
    };
    return strings[key] ?? key;
  },
}));

// Mock api-client
vi.mock("@/lib/api-client", () => ({
  groupsApi: {
    create: vi.fn().mockResolvedValue({ id: "g1", name: "Test" }),
  },
  settingsApi: {
    updateGroupSettings: vi.fn().mockResolvedValue({}),
  },
}));

describe("OnboardingWizard", () => {
  const defaultProps = {
    hasGroup: false,
    memberCount: 0,
    hasExtension: false,
    hasAlerts: false,
    onDismiss: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("renders step 1 with group creation form", () => {
    render(<OnboardingWizard {...defaultProps} />);
    expect(screen.getByText("Create Your Group")).toBeInTheDocument();
    expect(screen.getByText("Group name")).toBeInTheDocument();
    expect(screen.getByText("Group type")).toBeInTheDocument();
  });

  it("shows step indicator", () => {
    render(<OnboardingWizard {...defaultProps} />);
    expect(screen.getByText(/Step 1 of 4/)).toBeInTheDocument();
  });

  it("shows skip option", () => {
    render(<OnboardingWizard {...defaultProps} />);
    expect(screen.getByText("Skip for now")).toBeInTheDocument();
  });

  it("shows group type selector with family, school, club", () => {
    render(<OnboardingWizard {...defaultProps} />);
    expect(screen.getByText("Family")).toBeInTheDocument();
    expect(screen.getByText("School")).toBeInTheDocument();
    expect(screen.getByText("Club")).toBeInTheDocument();
  });

  it("calls onDismiss when dismiss button is clicked", () => {
    const onDismiss = vi.fn();
    render(<OnboardingWizard {...defaultProps} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByLabelText("Dismiss"));
    expect(onDismiss).toHaveBeenCalled();
  });

  it("does not render when completed in localStorage", () => {
    localStorage.setItem("bhapi_onboarding_complete", "true");
    const { container } = render(<OnboardingWizard {...defaultProps} />);
    // The modal overlay should not be present
    expect(container.querySelector(".fixed")).toBeNull();
  });

  it("renders as a modal overlay", () => {
    const { container } = render(<OnboardingWizard {...defaultProps} />);
    expect(container.querySelector(".fixed.inset-0")).toBeInTheDocument();
  });
});
