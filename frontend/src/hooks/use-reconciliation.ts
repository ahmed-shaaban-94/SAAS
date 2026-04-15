"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ReconciliationData } from "@/types/dispensing";

export function useReconciliation() {
  const { data, error, isLoading } = useSWR<ReconciliationData>(
    "/api/v1/dispensing/reconciliation",
    () => fetchAPI<ReconciliationData>("/api/v1/dispensing/reconciliation"),
  );
  return { data, error, isLoading };
}
