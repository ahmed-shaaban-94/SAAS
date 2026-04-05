"use client";

import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { DashboardData } from "@/hooks/use-dashboard";

interface ComparisonPeriod {
  start_date: string;
  end_date: string;
  label: string;
}

interface ComparisonResult {
  current: DashboardData | undefined;
  previous: DashboardData | undefined;
  isLoading: boolean;
  error: unknown;
}

export type { ComparisonPeriod };

export function useComparison(
  currentPeriod: ComparisonPeriod | null,
  previousPeriod: ComparisonPeriod | null,
): ComparisonResult {
  const currentKey = currentPeriod
    ? `/api/v1/analytics/dashboard?start_date=${currentPeriod.start_date}&end_date=${currentPeriod.end_date}`
    : null;
  const previousKey = previousPeriod
    ? `/api/v1/analytics/dashboard?start_date=${previousPeriod.start_date}&end_date=${previousPeriod.end_date}`
    : null;

  const { data: current, isLoading: l1, error: e1 } = useSWR(
    currentKey ? `comparison:current:${currentKey}` : null,
    () => fetchAPI<DashboardData>(currentKey!),
  );
  const { data: previous, isLoading: l2, error: e2 } = useSWR(
    previousKey ? `comparison:previous:${previousKey}` : null,
    () => fetchAPI<DashboardData>(previousKey!),
  );

  return { current, previous, isLoading: l1 || l2, error: e1 || e2 };
}
