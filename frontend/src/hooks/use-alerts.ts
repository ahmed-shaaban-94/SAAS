"use client";
import useSWR from "swr";
import { fetchAPI, postAPI } from "@/lib/api-client";
import type { AlertLogItem } from "@/types/api";

export function useAlertLog(unacknowledgedOnly: boolean = false, limit: number = 50) {
  const params: Record<string, string | boolean | number> = { limit };
  if (unacknowledgedOnly) params.unacknowledged_only = true;
  const { data, error, isLoading, mutate } = useSWR<AlertLogItem[]>(
    ["/api/v1/targets/alerts/log", unacknowledgedOnly, limit],
    () => fetchAPI<AlertLogItem[]>("/api/v1/targets/alerts/log", params),
  );

  const acknowledgeAlert = async (alertId: number) => {
    await postAPI(`/api/v1/targets/alerts/log/${alertId}/acknowledge`);
    mutate();
  };

  return { data, error, isLoading, mutate, acknowledgeAlert };
}

export function useUnacknowledgedCount() {
  const { data } = useAlertLog(true);
  return data?.length ?? 0;
}
