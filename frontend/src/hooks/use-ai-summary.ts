import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { AISummary } from "@/types/api";

export function useAISummary() {
  const { data, error } = useSWR("/api/v1/ai-light/summary", () =>
    fetchAPI<AISummary>("/api/v1/ai-light/summary"),
  );
  return { data, error, isLoading: !data && !error };
}
