import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import OnboardingWizard from "../OnboardingWizard";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

describe("OnboardingWizard", () => {
  const defaultProps = {
    hasGroup: false,
    memberCount: 0,
    hasExtension: false,
    hasAlerts: false,
    onDismiss: vi.fn(),
  };

  it("renders all steps", () => {
    render(<OnboardingWizard {...defaultProps} />);
    expect(screen.getByText("Create Your Group")).toBeInTheDocument();
    expect(screen.getByText("Add Members")).toBeInTheDocument();
    expect(screen.getByText("Install Browser Extension")).toBeInTheDocument();
    expect(screen.getByText("Set Up Alerts")).toBeInTheDocument();
  });

  it("shows progress", () => {
    render(<OnboardingWizard {...defaultProps} />);
    expect(screen.getByText("0 of 4 complete")).toBeInTheDocument();
  });

  it("marks completed steps", () => {
    render(
      <OnboardingWizard {...defaultProps} hasGroup={true} memberCount={3} />
    );
    expect(screen.getByText("2 of 4 complete")).toBeInTheDocument();
  });

  it("hides when all complete", () => {
    const { container } = render(
      <OnboardingWizard
        hasGroup={true}
        memberCount={2}
        hasExtension={true}
        hasAlerts={true}
        onDismiss={vi.fn()}
      />
    );
    expect(container.innerHTML).toBe("");
  });

  it("calls onDismiss when dismissed", () => {
    const onDismiss = vi.fn();
    render(<OnboardingWizard {...defaultProps} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByLabelText("Dismiss onboarding"));
    expect(onDismiss).toHaveBeenCalled();
  });
});
