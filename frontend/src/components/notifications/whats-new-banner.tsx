"use client";

import { X, Sparkles } from "lucide-react";
import { useWhatsNew } from "@/hooks/use-whats-new";

export function WhatsNewBanner() {
  const { updates, dismiss } = useWhatsNew();

  if (updates.length === 0) return null;

  const latest = updates[0];

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 left-1/2 z-50 flex w-full max-w-md -translate-x-1/2 items-start gap-3 rounded-xl border border-accent/30 bg-card/95 px-4 py-3 shadow-lg backdrop-blur-sm"
    >
      <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-text-primary">{latest.title}</p>
        <p className="mt-0.5 line-clamp-2 text-xs text-text-secondary">{latest.message}</p>
        {updates.length > 1 && (
          <p className="mt-1 text-xs text-accent">+{updates.length - 1} more updates</p>
        )}
      </div>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Dismiss what's new"
        className="shrink-0 rounded-full p-1 text-text-secondary transition-colors hover:bg-surface-raised hover:text-text-primary"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
