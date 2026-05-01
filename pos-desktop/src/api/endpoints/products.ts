// Typed POS product/catalog endpoints (Sub-PR 5).

import type { ApiClient } from "@pos/api/client";
import type { paths } from "@pos/api/types";

type SearchResp =
  paths["/api/v1/pos/products/search"]["get"]["responses"]["200"]["content"]["application/json"];
type StockResp =
  paths["/api/v1/pos/products/{drug_code}/stock"]["get"]["responses"]["200"]["content"]["application/json"];
type CatalogResp =
  paths["/api/v1/pos/catalog/products"]["get"]["responses"]["200"]["content"]["application/json"];
type CatalogStockResp =
  paths["/api/v1/pos/catalog/stock"]["get"]["responses"]["200"]["content"]["application/json"];

export interface ProductEndpoints {
  search: (query: { q?: string; site_code: string; limit?: number }) => Promise<SearchResp>;
  stock: (drugCode: string, query: { site_code: string }) => Promise<StockResp>;
  catalog: (query?: { cursor?: string; limit?: number }) => Promise<CatalogResp>;
  catalogStock: (query: {
    site: string;
    cursor?: string;
    limit?: number;
  }) => Promise<CatalogStockResp>;
}

function qs(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

export function createProductEndpoints(client: ApiClient): ProductEndpoints {
  return {
    search: (query) => client.request("GET", `/api/v1/pos/products/search${qs(query)}`),
    stock: (drugCode, query) =>
      client.request("GET", `/api/v1/pos/products/${drugCode}/stock${qs(query)}`),
    catalog: (query = {}) => client.request("GET", `/api/v1/pos/catalog/products${qs(query)}`),
    catalogStock: (query) => client.request("GET", `/api/v1/pos/catalog/stock${qs(query)}`),
  };
}
