"use client";

import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ProvisionalBannerProps {
  pending: number;
}

/**
 * Amber warning banner shown when the terminal is operating offline.
 * Sits directly below the header; sale can continue but all new lines
 * will be queued and synced later.
 */
export function ProvisionalBanner({ pending }: ProvisionalBannerProps) {
  return (
    <div
      role="status"
      data-testid="provisional-banner"
      className={cn(
        "flex items-center gap-2.5 border-b border-amber-400/30 bg-amber-400/10 px-4 py-2",
        "text-[12.5px] font-medium text-amber-200",
      )}
    >
      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" aria-hidden="true" />
      <span>
        Provisional mode — <span className="font-mono tabular-nums">{pending}</span> queued
      </span>
    </div>
  );
}
