import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { PosProductResult } from "@/types/pos";

interface CatalogPage {
  items: Array<{
    drug_code: string;
    drug_name: string;
    drug_brand: string | null;
    drug_cluster?: string | null;
    drug_category?: string | null;
    is_controlled: boolean;
    requires_pharmacist?: boolean;
    unit_price: number;
    updated_at?: string;
  }>;
  next_cursor: string | null;
}

/**
 * Drug-search hook powering the Drugs tab.
 *
 * Empty query -> paginated catalog (/pos/catalog/products) so the tab
 * can show inventory on first render. A typed query (>= 2 chars) falls
 * through to the search endpoint which ranks by name/brand/SKU.
 *
 * Both endpoints return unit_price + controlled flag. Stock count is
 * left at 0 until the catalog-stock join lands — the UI shows an
 * "unknown" pill rather than "out" so rows stay addable.
 */
export function useDrugSearch(query: string, siteCode: string) {
  const trimmed = query.trim();
  const shouldSearch = trimmed.length >= 2;

  const searchKey = shouldSearch
    ? `/api/v1/pos/products/search?q=${encodeURIComponent(trimmed)}&site_code=${siteCode}`
    : null;
  const catalogKey = !shouldSearch ? `/api/v1/pos/catalog/products?limit=200` : null;

  const searchResult = useSWR<PosProductResult[]>(
    searchKey,
    () =>
      fetchAPI<PosProductResult[]>("/api/v1/pos/products/search", {
        q: trimmed,
        site_code: siteCode,
        limit: 100,
      }),
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      dedupingInterval: 300,
    },
  );

  const catalogResult = useSWR<CatalogPage>(
    catalogKey,
    () =>
      fetchAPI<CatalogPage>("/api/v1/pos/catalog/products", {
        limit: 200,
      }),
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    },
  );

  const products: PosProductResult[] = shouldSearch
    ? (searchResult.data ?? [])
    : (catalogResult.data?.items ?? []).map((row) => ({
        drug_code: row.drug_code,
        drug_name: row.drug_name,
        drug_brand: row.drug_brand,
        is_controlled: row.is_controlled,
        unit_price: row.unit_price,
        stock_available: 0,
      }));

  const error = shouldSearch ? searchResult.error : catalogResult.error;
  const isLoading = shouldSearch ? searchResult.isLoading : catalogResult.isLoading;

  return {
    products,
    isLoading,
    isError: !!error,
  };
}
