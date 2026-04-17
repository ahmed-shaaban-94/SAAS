"use client";
import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { PurchaseOrder } from "@/types/purchase-orders";

export function usePurchaseOrders(status?: string) {
  const params = status ? { status } : undefined;
  const { data, error, isLoading } = useSWR<PurchaseOrder[]>(
    swrKey("/api/v1/purchase-orders", params),
    () => fetchAPI<PurchaseOrder[]>("/api/v1/purchase-orders", params),
  );
  return { data: data ?? [], error, isLoading };
}
