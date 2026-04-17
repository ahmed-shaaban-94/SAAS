"use client";

import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";

export function OfflineBadge() {
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    setIsOnline(navigator.onLine);
    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  if (isOnline) return null;

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
      OFFLINE
    </div>
  );
}
