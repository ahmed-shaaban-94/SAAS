"use client";

import useSWR from "swr";
import { fetchAPI, postAPI, swrKey } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/constants";
import { getSession } from "@/lib/auth-bridge";

export interface Annotation {
  id: number;
  chart_id: string;
  data_point: string;
  note: string;
  color: string;
  user_id: string;
  created_at: string;
}

export function useAnnotations(chartId: string) {
  const { data, error, isLoading, mutate } = useSWR<Annotation[]>(
    chartId ? swrKey("/annotations", { chart_id: chartId }) : null,
    () => fetchAPI<Annotation[]>("/annotations", { chart_id: chartId }),
  );

  const addAnnotation = async (
    dataPoint: string,
    note: string,
    color = "#D97706",
  ) => {
    const result = await postAPI<Annotation>("/annotations", {
      chart_id: chartId,
      data_point: dataPoint,
      note,
      color,
    });
    mutate();
    return result;
  };

  const deleteAnnotation = async (id: number) => {
    const session = await getSession();
    const headers: Record<string, string> = {};
    if (session?.accessToken)
      headers["Authorization"] = `Bearer ${session.accessToken}`;
    await fetch(`${API_BASE_URL}/api/v1/annotations/${id}`, {
      method: "DELETE",
      headers,
    });
    mutate();
  };

  return {
    annotations: data ?? [],
    error,
    isLoading,
    addAnnotation,
    deleteAnnotation,
  };
}
