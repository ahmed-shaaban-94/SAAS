"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { SupplierPerformance } from "@/types/suppliers";

export function useSupplierPerformance(supplierCode?: string | null) {
  const path = supplierCode
    ? `/api/v1/suppliers/${supplierCode}/performance`
    : "/api/v1/suppliers/performance";
  const { data, error, isLoading } = useSWR<SupplierPerformance[]>(
    supplierCode !== null ? path : null,
    () => fetchAPI<SupplierPerformance[]>(path),
  );
  return { data: data ?? [], error, isLoading };
}
