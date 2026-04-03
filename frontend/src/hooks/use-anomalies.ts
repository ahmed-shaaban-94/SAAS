import useSWR from "swr";
import { fetchAPI, postAPI } from "@/lib/api-client";
import type { AnomalyAlertItem } from "@/types/api";

export function useActiveAnomalies(limit = 20) {
  const key = `/api/v1/anomalies/active?limit=${limit}`;
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<AnomalyAlertItem[]>(key),
  );
  return { data, error, isLoading, mutate };
}

export function useAnomalyHistory(startDate?: string, endDate?: string, limit = 50) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  const key = `/api/v1/anomalies/history?${qs}`;
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<AnomalyAlertItem[]>(key),
  );
  return { data, error, isLoading };
}

export async function acknowledgeAnomaly(alertId: number) {
  return postAPI(`/api/v1/anomalies/${alertId}/acknowledge`, {});
}
