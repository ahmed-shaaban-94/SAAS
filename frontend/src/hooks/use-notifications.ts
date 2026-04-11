"use client";

import useSWR from "swr";
import { fetchAPI, postAPI, swrKey } from "@/lib/api-client";

export interface Notification {
  id: number;
  type: "urgent" | "info" | "success";
  title: string;
  message: string;
  link: string | null;
  read: boolean;
  created_at: string;
}

export function useNotifications(limit = 20) {
  const { data, error, isLoading, mutate } = useSWR<Notification[]>(
    swrKey("/api/v1/notifications", { limit }),
    () => fetchAPI<Notification[]>("/api/v1/notifications", { limit }),
    { refreshInterval: 30000 },
  );

  const markRead = async (id: number) => {
    await postAPI(`/api/v1/notifications/${id}/read`);
    mutate();
  };

  const markAllRead = async () => {
    await postAPI("/api/v1/notifications/read-all");
    mutate();
  };

  return { notifications: data ?? [], error, isLoading, mutate, markRead, markAllRead };
}

export function useUnreadCount() {
  const { data, mutate } = useSWR<{ unread: number }>(
    swrKey("/api/v1/notifications/count"),
    () => fetchAPI<{ unread: number }>("/api/v1/notifications/count"),
    { refreshInterval: 15000 },
  );

  return { unreadCount: data?.unread ?? 0, mutate };
}
