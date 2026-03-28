import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { AnomalyReport } from "@/types/api";

export function useAIAnomalies() {
  const { data, error } = useSWR("/api/v1/ai-light/anomalies", () =>
    fetchAPI<AnomalyReport>("/api/v1/ai-light/anomalies"),
  );
  return { data, error, isLoading: !data && !error };
}
