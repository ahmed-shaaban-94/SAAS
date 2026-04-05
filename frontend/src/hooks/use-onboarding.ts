"use client";

import useSWR from "swr";
import { fetchAPI, postAPI, swrKey } from "@/lib/api-client";

interface OnboardingStatus {
  steps_completed: string[];
  current_step: string;
  is_complete: boolean;
  skipped_at: string | null;
  completed_at: string | null;
}

export function useOnboarding() {
  const { data, error, isLoading, mutate } = useSWR<OnboardingStatus>(
    swrKey("/onboarding/status"),
    () => fetchAPI<OnboardingStatus>("/onboarding/status"),
  );

  const completeStep = async (step: string) => {
    const result = await postAPI<OnboardingStatus>("/onboarding/complete-step", { step });
    mutate(result, false);
    return result;
  };

  const skip = async () => {
    const result = await postAPI<OnboardingStatus>("/onboarding/skip");
    mutate(result, false);
    return result;
  };

  return { data, error, isLoading, mutate, completeStep, skip };
}
