import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { AnomalyReport } from "@/types/api";

/**
 * Fetch AI anomalies only when the AI-Light service is available.
 * First checks /status, then fetches /anomalies only if configured.
 * Prevents unnecessary API calls when OpenRouter key is not set.
 */
export function useAIAnomalies() {
  const { data: status } = useSWR("/api/v1/ai-light/status", () =>
    fetchAPI<{ available: boolean }>("/api/v1/ai-light/status"),
  );

  const shouldFetch = status?.available === true;

  const { data, error, isLoading } = useSWR(
    shouldFetch ? "/api/v1/ai-light/anomalies" : null,
    () => fetchAPI<AnomalyReport>("/api/v1/ai-light/anomalies"),
  );
  return { data, error, isLoading };
}
