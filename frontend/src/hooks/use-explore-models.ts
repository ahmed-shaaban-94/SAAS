import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ExploreCatalog, ExploreModel } from "@/types/api";

export function useExploreModels() {
  const { data, error, isLoading, mutate } = useSWR(
    "/api/v1/explore/models",
    () => fetchAPI<ExploreCatalog>("/api/v1/explore/models"),
  );
  return { data, error, isLoading, mutate };
}

export function useExploreModel(modelName: string | null) {
  const key = modelName ? `/api/v1/explore/models/${modelName}` : null;
  const { data, error, isLoading } = useSWR(key, () =>
    modelName
      ? fetchAPI<ExploreModel>(`/api/v1/explore/models/${modelName}`)
      : null,
  );
  return { data, error, isLoading };
}
