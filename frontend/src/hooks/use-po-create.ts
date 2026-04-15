"use client";
import useSWRMutation from "swr/mutation";
import { postAPI } from "@/lib/api-client";
import type { POCreateRequest, PurchaseOrder } from "@/types/purchase-orders";

export function usePOCreate() {
  const { trigger, isMutating, error } = useSWRMutation(
    "/api/v1/purchase-orders",
    (_url: string, { arg }: { arg: POCreateRequest }) =>
      postAPI<PurchaseOrder>("/api/v1/purchase-orders", arg),
  );
  return { createPO: trigger, isCreating: isMutating, error };
}
