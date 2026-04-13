"use client";
import useSWR, { mutate as globalMutate } from "swr";
import { fetchAPI, postAPI, patchAPI, deleteAPI } from "@/lib/api-client";

export interface SourceConnection {
  id: number;
  tenant_id: number;
  name: string;
  source_type: string;
  status: "draft" | "active" | "error" | "archived";
  config: Record<string, unknown>;
  credentials_ref: string | null;
  last_sync_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceConnectionList {
  items: SourceConnection[];
  total: number;
}

export interface CreateConnectionPayload {
  name: string;
  source_type: string;
  config?: Record<string, unknown>;
}

export interface UpdateConnectionPayload {
  name?: string;
  status?: string;
  config?: Record<string, unknown>;
}

export interface ConnectionTestResult {
  ok: boolean;
  latency_ms: number | null;
  error: string | null;
  warnings: string[];
}

export interface ConnectionPreviewResult {
  columns: { source_name: string; detected_type: string; null_count: number; unique_count: number; sample_values: string[] }[];
  sample_rows: Record<string, unknown>[];
  row_count_estimate: number;
  null_ratios: Record<string, number>;
  warnings: string[];
}

export interface SyncJob {
  id: number;
  tenant_id: number;
  connection_id: number;
  pipeline_run_id: string | null;
  release_id: number | null;
  profile_id: number | null;
  run_mode: string;
  status: string | null;
  rows_loaded: number | null;
  duration_seconds: number | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

export interface SyncJobList {
  items: SyncJob[];
  total: number;
}

const BASE = "/api/v1/control-center";

export function useConnections(params?: { source_type?: string; status?: string; page?: number; page_size?: number }) {
  const query = new URLSearchParams();
  if (params?.source_type) query.set("source_type", params.source_type);
  if (params?.status) query.set("status", params.status);
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  const key = `${BASE}/connections?${query}`;

  const { data, error, isLoading } = useSWR<SourceConnectionList>(
    key,
    () => fetchAPI<SourceConnectionList>(`${BASE}/connections?${query}`),
    { revalidateOnFocus: false, dedupingInterval: 30_000 },
  );
  return {
    data: data ?? { items: [], total: 0 },
    error,
    isLoading,
    mutate: () => globalMutate(key),
  };
}

export function useConnection(id: number | null) {
  const { data, error, isLoading, mutate } = useSWR<SourceConnection>(
    id ? `${BASE}/connections/${id}` : null,
    () => fetchAPI<SourceConnection>(`${BASE}/connections/${id}`),
    { revalidateOnFocus: false },
  );
  return { data, error, isLoading, mutate };
}

export async function createConnection(payload: CreateConnectionPayload): Promise<SourceConnection> {
  return postAPI<SourceConnection>(`${BASE}/connections`, payload);
}

export async function updateConnection(id: number, payload: UpdateConnectionPayload): Promise<SourceConnection> {
  return patchAPI<SourceConnection>(`${BASE}/connections/${id}`, payload);
}

export async function archiveConnection(id: number): Promise<void> {
  await deleteAPI(`${BASE}/connections/${id}`);
}

export async function testConnection(id: number): Promise<ConnectionTestResult> {
  return postAPI<ConnectionTestResult>(`${BASE}/connections/${id}/test`);
}

export async function previewConnection(
  id: number,
  params?: { max_rows?: number; sample_rows?: number },
): Promise<ConnectionPreviewResult> {
  const q = new URLSearchParams();
  if (params?.max_rows) q.set("max_rows", String(params.max_rows));
  if (params?.sample_rows) q.set("sample_rows", String(params.sample_rows));
  return postAPI<ConnectionPreviewResult>(`${BASE}/connections/${id}/preview?${q}`);
}

export async function triggerSync(
  id: number,
  payload?: { run_mode?: string; release_id?: number | null; profile_id?: number | null },
) {
  return postAPI(`${BASE}/connections/${id}/sync`, payload ?? { run_mode: "manual" });
}
