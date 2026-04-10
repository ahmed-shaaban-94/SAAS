"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import { getSession } from "next-auth/react";
import { API_BASE_URL } from "@/lib/constants";

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

const LAYOUT_PATH = "/api/v1/dashboard/layout";

export function useDashboardLayout() {
  const { data, error, isLoading, mutate } = useSWR<LayoutResponse>(
    swrKey(LAYOUT_PATH),
    () => fetchAPI<LayoutResponse>(LAYOUT_PATH),
  );

  const saveLayout = async (layout: LayoutItem[]): Promise<LayoutItem[]> => {
    // Optimistic update — show the new layout immediately
    await mutate({ layout }, false);

    const session = await getSession();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (session?.accessToken) {
      headers["Authorization"] = `Bearer ${session.accessToken}`;
    }

    const res = await fetch(`${API_BASE_URL}${LAYOUT_PATH}`, {
      method: "PUT",
      headers,
      body: JSON.stringify({ layout }),
    });

    if (!res.ok) {
      // Roll back optimistic update on failure
      await mutate();
      throw new Error(`Failed to save layout: ${res.status}`);
    }

    const result: LayoutResponse = await res.json();
    await mutate(result, false);
    return result.layout;
  };

  return { layout: data?.layout ?? [], error, isLoading, saveLayout };
}
