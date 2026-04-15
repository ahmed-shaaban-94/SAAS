"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { PODetailResponse } from "@/types/purchase-orders";

export function usePODetail(poNumber: string | null) {
  const { data, error, isLoading } = useSWR<PODetailResponse>(
    poNumber ? `/api/v1/purchase-orders/${poNumber}` : null,
    () => fetchAPI<PODetailResponse>(`/api/v1/purchase-orders/${poNumber}`),
  );
  return { data, error, isLoading };
}
