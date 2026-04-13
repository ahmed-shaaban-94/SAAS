"use client";
import useSWR, { mutate as globalMutate } from "swr";
import { fetchAPI } from "@/lib/api-client";

export interface MappingColumn {
  source: string;
  canonical: string;
  cast?: string;
}

export interface MappingTemplate {
  id: number;
  tenant_id: number;
  source_type: string;
  template_name: string;
  source_schema_hash: string | null;
  mapping: { columns?: MappingColumn[] };
  version: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface MappingTemplateList {
  items: MappingTemplate[];
  total: number;
}

export interface ValidationIssue {
  code: string;
  message: string;
  field: string | null;
}

export interface ValidationReport {
  ok: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export interface CreateMappingPayload {
  source_type: string;
  template_name: string;
  columns: MappingColumn[];
  source_schema_hash?: string;
}

export interface UpdateMappingPayload {
  template_name?: string;
  columns?: MappingColumn[];
}

export interface ValidateMappingPayload {
  source_type: string;
  columns: MappingColumn[];
  target_domain: string;
  profile_config?: Record<string, unknown>;
  source_preview?: Record<string, unknown> | null;
}

const BASE = "/api/v1/control-center";

export function useMappings(params?: { source_type?: string; template_name?: string; page?: number; page_size?: number }) {
  const query = new URLSearchParams();
  if (params?.source_type) query.set("source_type", params.source_type);
  if (params?.template_name) query.set("template_name", params.template_name);
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  const key = `${BASE}/mappings?${query}`;

  const { data, error, isLoading } = useSWR<MappingTemplateList>(
    key,
    () => fetchAPI<MappingTemplateList>(`${BASE}/mappings?${query}`),
    { revalidateOnFocus: false, dedupingInterval: 30_000 },
  );
  return {
    data: data ?? { items: [], total: 0 },
    error,
    isLoading,
    mutate: () => globalMutate(key),
  };
}

export async function createMapping(payload: CreateMappingPayload): Promise<MappingTemplate> {
  return fetchAPI<MappingTemplate>(`${BASE}/mappings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateMapping(id: number, payload: UpdateMappingPayload): Promise<MappingTemplate> {
  return fetchAPI<MappingTemplate>(`${BASE}/mappings/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function validateMapping(payload: ValidateMappingPayload): Promise<ValidationReport> {
  return fetchAPI<ValidationReport>(`${BASE}/mappings/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
