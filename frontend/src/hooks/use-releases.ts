"use client";
import useSWR, { mutate as globalMutate } from "swr";
import { fetchAPI } from "@/lib/api-client";

export interface PipelineRelease {
  id: number;
  tenant_id: number;
  release_version: number;
  draft_id: number | null;
  source_release_id: number | null;
  snapshot: Record<string, unknown>;
  release_notes: string;
  is_rollback: boolean;
  published_by: string | null;
  published_at: string;
}

export interface PipelineReleaseList {
  items: PipelineRelease[];
  total: number;
}

const BASE = "/api/v1/control-center";

export function useReleases(params?: { page?: number; page_size?: number }) {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  const key = `${BASE}/releases?${query}`;

  const { data, error, isLoading } = useSWR<PipelineReleaseList>(
    key,
    () => fetchAPI<PipelineReleaseList>(`${BASE}/releases?${query}`),
    { revalidateOnFocus: false, dedupingInterval: 30_000 },
  );
  return {
    data: data ?? { items: [], total: 0 },
    error,
    isLoading,
    mutate: () => globalMutate(key),
  };
}

export async function rollbackRelease(id: number): Promise<PipelineRelease> {
  return fetchAPI<PipelineRelease>(`${BASE}/releases/${id}/rollback`, { method: "POST" });
}
