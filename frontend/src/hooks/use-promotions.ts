import useSWR from "swr";
import { fetchAPI, patchAPI, postAPI, swrKey } from "@/lib/api-client";
import type {
  Promotion,
  PromotionCreateInput,
  PromotionStatus,
  PromotionUpdateInput,
} from "@/types/promotions";

export interface UsePromotionsFilters {
  status?: PromotionStatus;
}

/**
 * List promotions for the current tenant, optionally filtered by status.
 * Mirrors `GET /api/v1/pos/promotions`.
 */
export function usePromotions(filters?: UsePromotionsFilters) {
  const params = filters?.status ? { status: filters.status } : undefined;
  const key = swrKey("/api/v1/pos/promotions", params);

  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<Promotion[]>("/api/v1/pos/promotions", params),
  );
  return {
    data: data ?? [],
    error,
    isLoading,
    mutate,
  };
}

/**
 * Fetch a single promotion by id. Returns undefined while loading.
 */
export function usePromotion(id: number | null) {
  const key = id ? `/api/v1/pos/promotions/${id}` : null;
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<Promotion>(`/api/v1/pos/promotions/${id}`),
  );
  return { data, error, isLoading, mutate };
}

export async function createPromotion(input: PromotionCreateInput): Promise<Promotion> {
  return postAPI<Promotion>("/api/v1/pos/promotions", input);
}

export async function updatePromotion(
  id: number,
  input: PromotionUpdateInput,
): Promise<Promotion> {
  return patchAPI<Promotion>(`/api/v1/pos/promotions/${id}`, input);
}

export async function setPromotionStatus(
  id: number,
  status: "active" | "paused",
): Promise<Promotion> {
  return patchAPI<Promotion>(`/api/v1/pos/promotions/${id}/status`, { status });
}
