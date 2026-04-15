import useSWR from "swr";
import { ApiError, fetchAPI, putAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";
import type { ReorderConfig } from "@/types/inventory";

type ReorderConfigFilters = FilterParams & {
  drug_code?: string;
  site_code?: string;
};

const PATH = "/api/v1/inventory/reorder-config";

async function fetchReorderConfig(filters?: ReorderConfigFilters): Promise<ReorderConfig | null> {
  if (!filters?.drug_code || !filters?.site_code) return null;

  try {
    return await fetchAPI<ReorderConfig>(PATH, filters);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export function useReorderConfig(filters?: ReorderConfigFilters) {
  const enabled = Boolean(filters?.drug_code && filters?.site_code);
  const key = enabled ? swrKey(PATH, filters) : null;
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchReorderConfig(filters),
  );

  async function saveConfig(payload: ReorderConfig) {
    const saved = await putAPI<ReorderConfig>(PATH, payload);
    await mutate(saved, { revalidate: false });
    return saved;
  }

  return {
    data,
    error,
    isLoading: enabled ? isLoading : false,
    mutate,
    saveConfig,
  };
}
