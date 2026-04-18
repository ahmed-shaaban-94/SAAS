"use client";

import useSWR from "swr";
import { fetchAPI, postAPI, putAPI, swrKey } from "@/lib/api-client";

interface OnboardingStatus {
  steps_completed: string[];
  current_step: string;
  is_complete: boolean;
  skipped_at: string | null;
  completed_at: string | null;
  golden_path_progress: Record<string, string | null>;
  first_insight_dismissed_at: string | null;
}

export function useOnboarding() {
  const { data, error, isLoading, mutate } = useSWR<OnboardingStatus>(
    swrKey("/api/v1/onboarding/status"),
    () => fetchAPI<OnboardingStatus>("/api/v1/onboarding/status"),
  );

  const completeStep = async (step: string) => {
    const result = await postAPI<OnboardingStatus>("/api/v1/onboarding/complete-step", { step });
    mutate(result, false);
    return result;
  };

  const skip = async () => {
    const result = await postAPI<OnboardingStatus>("/api/v1/onboarding/skip");
    mutate(result, false);
    return result;
  };

  const updateGoldenPathProgress = async (
    progress: Record<string, string | null>,
  ) => {
    const result = await putAPI<OnboardingStatus>(
      "/api/v1/onboarding/golden-path-progress",
      { progress },
    );
    mutate(result, false);
    return result;
  };

  const dismissFirstInsight = async () => {
    const result = await postAPI<OnboardingStatus>(
      "/api/v1/onboarding/dismiss-first-insight",
    );
    mutate(result, false);
    return result;
  };

  return {
    data,
    error,
    isLoading,
    mutate,
    completeStep,
    skip,
    updateGoldenPathProgress,
    dismissFirstInsight,
  };
}
