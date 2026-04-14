"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";

export interface HealthSummary {
  active_connections: number;
  last_sync_at: string | null;
  active_release_version: number | null;
  pending_drafts: number;
  failed_syncs_last_24h: number;
}

const KEY = "/api/v1/control-center/health-summary";

export function useHealthSummary() {
  const { data, error, isLoading, mutate } = useSWR<HealthSummary>(
    KEY,
    () => fetchAPI<HealthSummary>(KEY),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30_000,
    },
  );
  return { data, error, isLoading, mutate };
}
