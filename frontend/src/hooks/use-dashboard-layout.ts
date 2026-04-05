"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/constants";
import { getSession } from "next-auth/react";

export interface LayoutItem {
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
}

interface LayoutResponse {
  layout: LayoutItem[];
}

export function useDashboardLayout() {
  const { data, error, isLoading, mutate } = useSWR<LayoutResponse>(
    swrKey("/dashboard/layout"),
    () => fetchAPI<LayoutResponse>("/dashboard/layout"),
  );

  const saveLayout = async (layout: LayoutItem[]) => {
    const session = await getSession();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (session?.accessToken) {
      headers["Authorization"] = `Bearer ${session.accessToken}`;
    }
    const res = await fetch(`${API_BASE_URL}/api/v1/dashboard/layout`, {
      method: "PUT",
      headers,
      body: JSON.stringify({ layout }),
    });
    const result = await res.json();
    mutate(result, false);
    return result;
  };

  return { layout: data?.layout ?? [], error, isLoading, saveLayout };
}
