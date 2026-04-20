"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";
import type { TopInsight } from "@/types/api";

interface AlertBannerProps {
  data?: TopInsight | null;
  loading?: boolean;
}

export function AlertBanner({ data, loading }: AlertBannerProps) {
  if (loading) {
    return (
      <div
        className="flex items-start gap-3.5 p-4 rounded-xl border border-border/40 bg-card/40 animate-pulse"
        aria-busy="true"
        aria-live="polite"
      >
        <div className="w-8 h-8 rounded-lg bg-elevated/70 shrink-0" />
        <div className="flex-1 space-y-1.5">
          <div className="h-3 w-1/4 bg-elevated/70 rounded" />
          <div className="h-3 w-3/4 bg-elevated/70 rounded" />
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-start gap-3.5 p-4 rounded-xl border border-accent/25
                 bg-gradient-to-r from-accent/[0.08] via-accent/[0.03] to-transparent"
    >
      <div className="w-8 h-8 rounded-lg grid place-items-center bg-accent/15 text-accent shrink-0">
        <Sparkles className="w-4 h-4" aria-hidden />
      </div>
      <p className="text-sm leading-relaxed text-ink-secondary flex-1">
        <b className="text-ink-primary">{data.title}</b> · {data.body}
      </p>
      <Link
        href={data.action_target || "#"}
        className="text-sm font-semibold text-accent-strong whitespace-nowrap hover:underline
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded"
      >
        {data.action_label || "Investigate →"}
      </Link>
    </div>
  );
}
