import useSWR from "swr";
import { fetchAPI, postAPI } from "@/lib/api-client";
import type { BillingStatus, CheckoutResponse, PortalResponse } from "@/types/billing";

export function useBilling() {
  const { data, error, isLoading, mutate } = useSWR<BillingStatus>(
    "/api/v1/billing/status",
    fetchAPI<BillingStatus>,
  );

  return {
    billing: data,
    isLoading,
    isError: !!error,
    error,
    mutate,
  };
}

export async function createCheckout(priceId: string): Promise<string> {
  const res = await postAPI<CheckoutResponse>("/api/v1/billing/checkout", {
    price_id: priceId,
  });
  return res.checkout_url;
}

export async function createPortalSession(): Promise<string> {
  const res = await postAPI<PortalResponse>("/api/v1/billing/portal", {});
  return res.portal_url;
}
