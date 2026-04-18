import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { WizardProgress } from "@/components/upload/wizard-progress";

describe("WizardProgress", () => {
  it("renders all three step labels", () => {
    render(<WizardProgress currentStep={1} />);
    expect(screen.getByText(/choose source/i)).toBeInTheDocument();
    expect(screen.getByText(/map columns/i)).toBeInTheDocument();
    expect(screen.getByText(/validate & run/i)).toBeInTheDocument();
  });

  it("marks steps before currentStep as complete", () => {
    const { container } = render(<WizardProgress currentStep={3} />);
    const completed = container.querySelectorAll('[data-step-state="complete"]');
    // Two steps before step 3 should be complete.
    expect(completed.length).toBe(2);
  });

  it("marks current step as active", () => {
    const { container } = render(<WizardProgress currentStep={2} />);
    const active = container.querySelectorAll('[data-step-state="active"]');
    expect(active.length).toBe(1);
  });

  it("marks steps after currentStep as upcoming", () => {
    const { container } = render(<WizardProgress currentStep={1} />);
    const upcoming = container.querySelectorAll('[data-step-state="upcoming"]');
    expect(upcoming.length).toBe(2);
  });

  it("clamps currentStep to valid range (floor 1)", () => {
    const { container } = render(<WizardProgress currentStep={0} />);
    const active = container.querySelectorAll('[data-step-state="active"]');
    expect(active.length).toBe(1);
  });

  it("clamps currentStep to valid range (ceiling 3)", () => {
    const { container } = render(<WizardProgress currentStep={99} />);
    const completed = container.querySelectorAll('[data-step-state="complete"]');
    // All steps complete when we go past the last.
    expect(completed.length).toBeGreaterThanOrEqual(2);
  });
});
