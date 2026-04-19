"use client";

import { WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOfflineState } from "@/hooks/use-offline-state";

export function OfflineBadge() {
  const { isOnline, unresolved } = useOfflineState();

  if (!isOnline) {
    return (
      <div
        className={cn(
          "flex items-center gap-1.5 rounded-lg bg-destructive/20 px-3 py-1.5",
          "text-xs font-medium text-destructive animate-pulse",
        )}
        role="alert"
        aria-live="polite"
      >
        <WifiOff className="h-3.5 w-3.5" />
        {unresolved > 0 ? `OFFLINE · ${unresolved} pending` : "OFFLINE"}
      </div>
    );
  }

  if (unresolved > 0) {
    return (
      <div
        className="flex items-center gap-1.5 rounded-lg bg-amber-500/20 px-3 py-1.5 text-xs font-medium text-amber-600 dark:text-amber-400"
        role="status"
        aria-live="polite"
      >
        {unresolved} unsynced
      </div>
    );
  }

  return null;
}
