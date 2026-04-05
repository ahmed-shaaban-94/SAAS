"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";

export interface SearchResult {
  key?: number;
  name: string;
  subtitle?: string;
  path?: string;
  type: "product" | "customer" | "staff" | "page";
}

interface SearchResponse {
  products: SearchResult[];
  customers: SearchResult[];
  staff: SearchResult[];
  pages: SearchResult[];
}

export function useSearch(query: string) {
  const trimmed = query.trim();
  const { data, error, isLoading } = useSWR<SearchResponse>(
    trimmed.length >= 2 ? swrKey("/search", { q: trimmed, limit: 10 }) : null,
    () => fetchAPI<SearchResponse>("/search", { q: trimmed, limit: "10" }),
    { dedupingInterval: 300, keepPreviousData: true },
  );

  return { data, error, isLoading };
}
