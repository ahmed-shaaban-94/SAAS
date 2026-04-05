"use client";

import { useOnboarding } from "@/hooks/use-onboarding";
import { OnboardingWizard } from "./onboarding-wizard";

export function OnboardingOverlay() {
  const { data, isLoading, completeStep, skip } = useOnboarding();

  // Don't render while loading, or if onboarding is complete/skipped
  if (isLoading || !data) return null;
  if (data.is_complete || data.skipped_at) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <OnboardingWizard
        stepsCompleted={data.steps_completed}
        onCompleteStep={completeStep}
        onSkip={skip}
      />
    </div>
  );
}
