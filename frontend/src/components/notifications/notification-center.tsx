"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { X, CheckCheck } from "lucide-react";
import { useNotifications } from "@/hooks/use-notifications";
import { NotificationItem } from "./notification-item";

interface NotificationCenterProps {
  open: boolean;
  onClose: () => void;
}

export function NotificationCenter({ open, onClose }: NotificationCenterProps) {
  const { notifications, markRead, markAllRead } = useNotifications();
  const router = useRouter();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleEsc);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleEsc);
    };
  }, [open, onClose]);

  if (!open) return null;

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div ref={ref} className="absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-border bg-card shadow-2xl sm:w-96">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold text-text-primary">Notifications</h3>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button onClick={markAllRead} className="flex items-center gap-1 text-xs text-accent hover:underline" title="Mark all read">
              <CheckCheck className="h-3.5 w-3.5" />
              <span>Read all</span>
            </button>
          )}
          <button onClick={onClose} className="rounded-md p-1 text-text-secondary hover:text-text-primary">
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* List */}
      <div className="max-h-96 overflow-y-auto">
        {notifications.length === 0 ? (
          <p className="py-8 text-center text-sm text-text-secondary">No notifications yet</p>
        ) : (
          notifications.map((n) => (
            <NotificationItem
              key={n.id}
              notification={n}
              onMarkRead={markRead}
              onNavigate={(link) => { router.push(link); onClose(); }}
            />
          ))
        )}
      </div>
    </div>
  );
}
