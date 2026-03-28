import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { AIStatus } from "@/types/api";

export function useAIStatus() {
  const { data, error } = useSWR("/api/v1/ai-light/status", () =>
    fetchAPI<AIStatus>("/api/v1/ai-light/status"),
  );
  return { data, error, isLoading: !data && !error };
}
