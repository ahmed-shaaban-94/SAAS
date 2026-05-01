import useSWR from "swr";
import { fetchAPI } from "@shared/lib/api-client";
import type { PosProductResult, PosStockInfo } from "@pos/types/pos";

interface ProductSearchParams {
  query: string;
  siteCode: string;
}

/** Debounced product search — skips fetch when query < 2 chars */
export function usePosProducts({ query, siteCode }: ProductSearchParams) {
  const shouldFetch = query.trim().length >= 2;
  const key = shouldFetch
    ? `/api/v1/pos/products/search?q=${encodeURIComponent(query)}&site_code=${siteCode}`
    : null;

  const { data, error, isLoading } = useSWR<PosProductResult[]>(
    key,
    () =>
      fetchAPI<PosProductResult[]>("/api/v1/pos/products/search", {
        q: query,
        site_code: siteCode,
      }),
    {
      // Debounce: don't revalidate on focus/reconnect for search results
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      dedupingInterval: 300,
    },
  );

  return {
    products: data ?? [],
    isLoading: shouldFetch && isLoading,
    isError: !!error,
  };
}

export function usePosStockInfo(drugCode: string | null, siteCode: string) {
  const { data, error, isLoading } = useSWR<PosStockInfo>(
    drugCode ? `/api/v1/pos/products/${drugCode}/stock?site_code=${siteCode}` : null,
    () =>
      fetchAPI<PosStockInfo>(`/api/v1/pos/products/${drugCode}/stock`, {
        site_code: siteCode,
      }),
  );

  return {
    stock: data ?? null,
    isLoading,
    isError: !!error,
  };
}
