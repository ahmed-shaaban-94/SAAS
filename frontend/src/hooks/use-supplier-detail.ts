"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { SupplierInfo } from "@/types/suppliers";

export function useSupplierDetail(supplierCode: string | null) {
  const { data, error, isLoading } = useSWR<SupplierInfo>(
    supplierCode ? `/api/v1/suppliers/${supplierCode}` : null,
    () => fetchAPI<SupplierInfo>(`/api/v1/suppliers/${supplierCode}`),
  );
  return { data, error, isLoading };
}
