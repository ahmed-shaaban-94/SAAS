"use client";

import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUnreadCount } from "@/hooks/use-notifications";

interface NotificationBellProps {
  onClick: () => void;
  className?: string;
}

export function NotificationBell({ onClick, className }: NotificationBellProps) {
  const { unreadCount } = useUnreadCount();

  return (
    <button
      onClick={onClick}
      className={cn(
        "relative rounded-lg p-2 text-text-secondary transition-colors hover:bg-divider hover:text-text-primary",
        className,
      )}
      aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
    >
      <Bell className="h-5 w-5" />
      {unreadCount > 0 && (
        <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white animate-pulse">
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      )}
    </button>
  );
}
