import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { HealthStatus } from "@/types/api";

export function useHealth() {
  const { data, error } = useSWR(
    "/health",
    () => fetchAPI<HealthStatus>("/health"),
    { refreshInterval: 30000 },
  );
  return { data, error, isLoading: !data && !error };
}
