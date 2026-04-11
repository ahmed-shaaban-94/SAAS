"use client";

import useSWR from "swr";
import { fetchAPI, postAPI, deleteAPI, swrKey } from "@/lib/api-client";

export interface SavedView {
  id: number;
  name: string;
  page_path: string;
  filters: Record<string, string | number>;
  is_default: boolean;
  created_at: string;
}

export function useSavedViews() {
  const { data, error, isLoading, mutate } = useSWR<SavedView[]>(
    swrKey("/api/v1/views"),
    () => fetchAPI<SavedView[]>("/api/v1/views"),
  );

  const createView = async (
    name: string,
    pagePath: string,
    filters: Record<string, string | number>,
  ) => {
    const result = await postAPI<SavedView>("/api/v1/views", {
      name,
      page_path: pagePath,
      filters,
    });
    mutate();
    return result;
  };

  const deleteView = async (id: number) => {
    await deleteAPI(`/api/v1/views/${id}`);
    mutate();
  };

  return {
    views: data ?? [],
    error,
    isLoading,
    mutate,
    createView,
    deleteView,
  };
}
