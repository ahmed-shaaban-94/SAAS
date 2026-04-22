"use client";

import useSWR from "swr";
import { fetchAPI, postAPI } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/constants";
import { getSession } from "@/lib/auth-bridge";

export interface ReportSchedule {
  id: number;
  name: string;
  report_type: string;
  cron_expression: string;
  recipients: string[];
  parameters: Record<string, unknown>;
  enabled: boolean;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export function useReportSchedules() {
  const { data, error, isLoading, mutate } = useSWR<ReportSchedule[]>(
    "/api/v1/report-schedules",
    () => fetchAPI<ReportSchedule[]>("/api/v1/report-schedules"),
  );

  const createSchedule = async (body: {
    name: string;
    report_type: string;
    cron_expression: string;
    recipients: string[];
    enabled?: boolean;
  }) => {
    await postAPI<ReportSchedule>("/api/v1/report-schedules", body);
    mutate();
  };

  const toggleSchedule = async (id: number, enabled: boolean) => {
    const session = await getSession();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (session?.accessToken)
      headers["Authorization"] = `Bearer ${session.accessToken}`;
    await fetch(`${API_BASE_URL}/api/v1/report-schedules/${id}`, {
      method: "PATCH",
      headers,
      body: JSON.stringify({ enabled }),
    });
    mutate();
  };

  const deleteSchedule = async (id: number) => {
    const session = await getSession();
    const headers: Record<string, string> = {};
    if (session?.accessToken)
      headers["Authorization"] = `Bearer ${session.accessToken}`;
    await fetch(`${API_BASE_URL}/api/v1/report-schedules/${id}`, {
      method: "DELETE",
      headers,
    });
    mutate();
  };

  return {
    schedules: data ?? [],
    error,
    isLoading,
    createSchedule,
    toggleSchedule,
    deleteSchedule,
  };
}
