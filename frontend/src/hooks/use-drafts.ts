"use client";
import useSWR, { mutate as globalMutate } from "swr";
import { fetchAPI } from "@/lib/api-client";

export interface PipelineDraft {
  id: number;
  tenant_id: number;
  entity_type: string;
  entity_id: number | null;
  draft: Record<string, unknown>;
  status: string;
  validation_report: Record<string, unknown> | null;
  preview_result: Record<string, unknown> | null;
  version: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface PipelineDraftList {
  items: PipelineDraft[];
  total: number;
}

export interface CreateDraftPayload {
  entity_type: string;
  entity_id?: number | null;
  draft?: Record<string, unknown>;
}

const BASE = "/api/v1/control-center";

export function useDrafts(params?: { page?: number; page_size?: number }) {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  const key = `${BASE}/drafts?${query}`;

  const { data, error, isLoading } = useSWR<PipelineDraftList>(
    key,
    () => fetchAPI<PipelineDraftList>(`${BASE}/drafts?${query}`),
    { revalidateOnFocus: false, dedupingInterval: 15_000 },
  );
  return {
    data: data ?? { items: [], total: 0 },
    error,
    isLoading,
    mutate: () => globalMutate(key),
  };
}

export function useDraft(id: number | null) {
  const { data, error, isLoading, mutate } = useSWR<PipelineDraft>(
    id ? `${BASE}/drafts/${id}` : null,
    () => fetchAPI<PipelineDraft>(`${BASE}/drafts/${id}`),
    { revalidateOnFocus: false },
  );
  return { data, error, isLoading, mutate };
}

export async function createDraft(payload: CreateDraftPayload): Promise<PipelineDraft> {
  return fetchAPI<PipelineDraft>(`${BASE}/drafts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function validateDraft(id: number): Promise<PipelineDraft> {
  return fetchAPI<PipelineDraft>(`${BASE}/drafts/${id}/validate`, { method: "POST" });
}

export async function previewDraft(
  id: number,
  params?: { max_rows?: number; sample_rows?: number },
): Promise<PipelineDraft> {
  const q = new URLSearchParams();
  if (params?.max_rows) q.set("max_rows", String(params.max_rows));
  if (params?.sample_rows) q.set("sample_rows", String(params.sample_rows));
  return fetchAPI<PipelineDraft>(`${BASE}/drafts/${id}/preview?${q}`, { method: "POST" });
}

export async function publishDraft(id: number, releaseNotes = ""): Promise<unknown> {
  return fetchAPI(`${BASE}/drafts/${id}/publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ release_notes: releaseNotes }),
  });
}
