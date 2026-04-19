"use client";

import { useEffect } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface ScanToastProps {
  /** Non-null message = visible; null = hidden. */
  message: string | null;
  onDismiss: () => void;
  durationMs?: number;
}

/**
 * Bottom-left confirmation pill that appears after every successful
 * scan-to-cart. Auto-dismisses after 1.6s.
 */
export function ScanToast({ message, onDismiss, durationMs = 1600 }: ScanToastProps) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onDismiss, durationMs);
    return () => clearTimeout(t);
  }, [message, onDismiss, durationMs]);

  if (!message) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="scan-toast"
      style={{ animation: "dpSlideUp 220ms cubic-bezier(0.2, 0.9, 0.3, 1.1)" }}
      className={cn(
        "pointer-events-none fixed bottom-6 left-6 z-[300] flex max-w-[360px] items-center gap-2.5",
        "rounded-full border border-cyan-400/50 bg-cyan-400/15 px-4 py-2.5",
        "font-semibold text-cyan-300 shadow-[0_10px_30px_rgba(0,199,242,0.2)]",
      )}
    >
      <Check className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span className="truncate text-[12.5px]">{message}</span>
    </div>
  );
}
