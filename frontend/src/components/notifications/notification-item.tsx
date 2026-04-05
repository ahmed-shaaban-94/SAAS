"use client";

import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import type { Notification } from "@/hooks/use-notifications";

const TYPE_CONFIG = {
  urgent: { icon: AlertCircle, color: "text-growth-red", bg: "bg-growth-red/10" },
  success: { icon: CheckCircle2, color: "text-growth-green", bg: "bg-growth-green/10" },
  info: { icon: Info, color: "text-chart-blue", bg: "bg-chart-blue/10" },
} as const;

interface NotificationItemProps {
  notification: Notification;
  onMarkRead: (id: number) => void;
  onNavigate?: (link: string) => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function NotificationItem({ notification, onMarkRead, onNavigate }: NotificationItemProps) {
  const config = TYPE_CONFIG[notification.type];
  const Icon = config.icon;

  const handleClick = () => {
    if (!notification.read) onMarkRead(notification.id);
    if (notification.link && onNavigate) onNavigate(notification.link);
  };

  return (
    <button
      onClick={handleClick}
      className={cn(
        "flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-divider",
        !notification.read && "bg-accent/5",
      )}
    >
      <div className={cn("mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full", config.bg)}>
        <Icon className={cn("h-3.5 w-3.5", config.color)} />
      </div>
      <div className="min-w-0 flex-1">
        <p className={cn("text-sm", notification.read ? "text-text-secondary" : "font-medium text-text-primary")}>
          {notification.title}
        </p>
        <p className="mt-0.5 text-xs text-text-secondary line-clamp-2">{notification.message}</p>
        <p className="mt-1 text-[10px] text-text-secondary">{timeAgo(notification.created_at)}</p>
      </div>
      {!notification.read && (
        <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-accent" />
      )}
    </button>
  );
}
