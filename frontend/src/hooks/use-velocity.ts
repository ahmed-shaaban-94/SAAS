"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { VelocityClassification } from "@/types/dispensing";

export function useVelocity() {
  const { data, error, isLoading } = useSWR<VelocityClassification[]>(
    "/api/v1/dispensing/velocity",
    () => fetchAPI<VelocityClassification[]>("/api/v1/dispensing/velocity"),
  );
  return { data: data ?? [], error, isLoading };
}
