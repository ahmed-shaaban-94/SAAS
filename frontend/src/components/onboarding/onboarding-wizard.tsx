"use client";

import { ConnectDataStep } from "./steps/connect-data-step";
import { FirstReportStep } from "./steps/first-report-step";
import { FirstGoalStep } from "./steps/first-goal-step";

const STEPS = [
  { key: "connect_data", label: "Connect Data" },
  { key: "first_report", label: "First Report" },
  { key: "first_goal", label: "Set a Goal" },
] as const;

interface OnboardingWizardProps {
  stepsCompleted: string[];
  onCompleteStep: (step: string) => Promise<unknown>;
  onSkip: () => void;
}

export function OnboardingWizard({
  stepsCompleted,
  onCompleteStep,
  onSkip,
}: OnboardingWizardProps) {
  // Determine the current step index based on completed steps
  const currentIndex = STEPS.findIndex(
    (step) => !stepsCompleted.includes(step.key),
  );
  const activeIndex = currentIndex === -1 ? STEPS.length - 1 : currentIndex;

  const handleCompleteStep = async (stepKey: string) => {
    await onCompleteStep(stepKey);
  };

  return (
    <div className="relative mx-4 w-full max-w-xl rounded-2xl border border-border bg-card shadow-2xl">
      {/* Skip button */}
      <button
        onClick={onSkip}
        className="absolute right-4 top-4 text-xs text-text-secondary transition-colors hover:text-text-primary"
      >
        Skip
      </button>

      {/* Step indicator */}
      <div className="px-8 pt-8">
        <div className="flex items-center justify-center gap-0">
          {STEPS.map((step, index) => {
            const isCompleted = stepsCompleted.includes(step.key);
            const isActive = index === activeIndex;
            return (
              <div key={step.key} className="flex items-center">
                {/* Circle */}
                <div className="flex flex-col items-center">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold transition-colors ${
                      isCompleted
                        ? "border-accent bg-accent text-white"
                        : isActive
                          ? "border-accent bg-transparent text-accent"
                          : "border-border bg-transparent text-text-secondary"
                    }`}
                  >
                    {isCompleted ? (
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={3}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    ) : (
                      index + 1
                    )}
                  </div>
                  <span
                    className={`mt-1.5 text-[10px] font-medium ${
                      isCompleted || isActive
                        ? "text-accent"
                        : "text-text-secondary"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
                {/* Connector line */}
                {index < STEPS.length - 1 && (
                  <div
                    className={`mx-2 mb-5 h-0.5 w-16 transition-colors ${
                      stepsCompleted.includes(STEPS[index].key)
                        ? "bg-accent"
                        : "bg-border"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Progress text */}
        <p className="mt-4 text-center text-xs text-text-secondary">
          Step {activeIndex + 1} of {STEPS.length}
        </p>
      </div>

      {/* Divider */}
      <div className="mx-8 my-4 h-px bg-divider" />

      {/* Step content */}
      <div className="px-8 pb-8">
        {activeIndex === 0 && (
          <ConnectDataStep
            onComplete={() => handleCompleteStep("connect_data")}
          />
        )}
        {activeIndex === 1 && (
          <FirstReportStep
            onComplete={() => handleCompleteStep("first_report")}
          />
        )}
        {activeIndex === 2 && (
          <FirstGoalStep
            onComplete={() => handleCompleteStep("first_goal")}
          />
        )}
      </div>
    </div>
  );
}
