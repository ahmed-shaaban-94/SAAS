"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";

export interface AuditLogEntry {
  id: number;
  action: string;
  endpoint: string;
  method: string;
  ip_address: string | null;
  user_id: string | null;
  response_status: number | null;
  duration_ms: number | null;
  created_at: string;
}

export interface AuditLogPage {
  items: AuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogFilters {
  action?: string;
  endpoint?: string;
  method?: string;
  user_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

export function useAuditLog(filters: AuditLogFilters = {}) {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== undefined && v !== ""),
  );

  const { data, error, isLoading, mutate } = useSWR<AuditLogPage>(
    swrKey("/api/v1/audit-log", params),
    () => fetchAPI<AuditLogPage>("/api/v1/audit-log", params),
  );

  return {
    data: data ?? { items: [], total: 0, page: 1, page_size: 50 },
    error,
    isLoading,
    mutate,
  };
}
