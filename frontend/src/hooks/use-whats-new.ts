"use client";

import { useCallback } from "react";
import useSWR from "swr";
import { fetchAPI, postAPI, swrKey } from "@/lib/api-client";
import type { Notification } from "@/hooks/use-notifications";

/** Returns unread product_update notifications from the last 14 days. */
export function useWhatsNew() {
  const { data, mutate } = useSWR<Notification[]>(
    swrKey("/api/v1/notifications", { limit: 50 }),
    () => fetchAPI<Notification[]>("/api/v1/notifications", { limit: 50 }),
    { refreshInterval: 0 },
  );

  const cutoff = Date.now() - 14 * 24 * 60 * 60 * 1000;
  const updates = (data ?? []).filter(
    (n) => n.type === "product_update" && !n.read && new Date(n.created_at).getTime() >= cutoff,
  );

  const dismiss = useCallback(async () => {
    await postAPI("/api/v1/notifications/read-all");
    mutate();
  }, [mutate]);

  return { updates, dismiss };
}
