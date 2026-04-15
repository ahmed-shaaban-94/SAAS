"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { SupplierInfo } from "@/types/suppliers";

export function useSuppliers() {
  const { data, error, isLoading } = useSWR<SupplierInfo[]>(
    "/api/v1/suppliers",
    () => fetchAPI<SupplierInfo[]>("/api/v1/suppliers"),
  );
  return { data: data ?? [], error, isLoading };
}
