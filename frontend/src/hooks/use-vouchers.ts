import useSWR from "swr";
import { fetchAPI, postAPI, swrKey } from "@/lib/api-client";
import type { Voucher, VoucherCreateInput, VoucherStatus } from "@/types/vouchers";

export interface UseVouchersFilters {
  status?: VoucherStatus;
}

/**
 * List vouchers for the current tenant, optionally filtered by status.
 * Mirrors `GET /api/v1/pos/vouchers`.
 */
export function useVouchers(filters?: UseVouchersFilters) {
  const params = filters?.status ? { status: filters.status } : undefined;
  const key = swrKey("/api/v1/pos/vouchers", params);

  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<Voucher[]>("/api/v1/pos/vouchers", params),
  );
  return {
    data: data ?? [],
    error,
    isLoading,
    mutate,
  };
}

/**
 * Create a new voucher. Returns the persisted row from the server.
 * Callers should revalidate `useVouchers` after a successful call.
 */
export async function createVoucher(input: VoucherCreateInput): Promise<Voucher> {
  return postAPI<Voucher>("/api/v1/pos/vouchers", input);
}
