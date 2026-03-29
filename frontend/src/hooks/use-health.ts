import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { HealthStatus } from "@/types/api";

export function useHealth() {
  const { data, error, isLoading } = useSWR(
    "/health",
    () => fetchAPI<HealthStatus>("/health"),
    { refreshInterval: 30000, refreshWhenHidden: false },
  );
  return { data, error, isLoading };
}
