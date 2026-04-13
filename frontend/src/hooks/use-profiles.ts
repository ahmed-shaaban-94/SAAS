"use client";
import useSWR, { mutate as globalMutate } from "swr";
import { fetchAPI, postAPI, patchAPI } from "@/lib/api-client";

export interface PipelineProfile {
  id: number;
  tenant_id: number;
  profile_key: string;
  display_name: string;
  target_domain: string;
  is_default: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PipelineProfileList {
  items: PipelineProfile[];
  total: number;
}

export interface CreateProfilePayload {
  profile_key: string;
  display_name: string;
  target_domain: string;
  is_default?: boolean;
  config?: Record<string, unknown>;
}

export interface UpdateProfilePayload {
  display_name?: string;
  is_default?: boolean;
  config?: Record<string, unknown>;
}

const BASE = "/api/v1/control-center";

export function useProfiles(params?: { target_domain?: string; page?: number; page_size?: number }) {
  const query = new URLSearchParams();
  if (params?.target_domain) query.set("target_domain", params.target_domain);
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));
  const key = `${BASE}/profiles?${query}`;

  const { data, error, isLoading } = useSWR<PipelineProfileList>(
    key,
    () => fetchAPI<PipelineProfileList>(`${BASE}/profiles?${query}`),
    { revalidateOnFocus: false, dedupingInterval: 30_000 },
  );
  return {
    data: data ?? { items: [], total: 0 },
    error,
    isLoading,
    mutate: () => globalMutate(key),
  };
}

export async function createProfile(payload: CreateProfilePayload): Promise<PipelineProfile> {
  return postAPI<PipelineProfile>(`${BASE}/profiles`, payload);
}

export async function updateProfile(id: number, payload: UpdateProfilePayload): Promise<PipelineProfile> {
  return patchAPI<PipelineProfile>(`${BASE}/profiles/${id}`, payload);
}
