import useSWR from "swr";
import { fetchAPI } from "@shared/lib/api-client";
import type { TransactionResponse } from "@pos/types/pos";

interface HistoryParams {
  page?: number;
  limit?: number;
  status?: string;
}

export function usePosHistory(params: HistoryParams = {}) {
  const { page = 1, limit = 20, status } = params;
  // Backend uses offset-based pagination, not page-based
  const offset = (page - 1) * limit;

  const key = `/api/v1/pos/transactions?limit=${limit}&offset=${offset}${status ? `&status=${status}` : ""}`;

  const { data, error, isLoading, mutate } = useSWR<TransactionResponse[]>(
    key,
    () =>
      fetchAPI<TransactionResponse[]>("/api/v1/pos/transactions", {
        limit,
        offset,
        ...(status ? { status } : {}),
      }),
  );

  return {
    transactions: data ?? [],
    total: data?.length ?? 0,
    page,
    limit,
    isLoading,
    isError: !!error,
    mutate,
  };
}
