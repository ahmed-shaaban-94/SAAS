"use client";

import { cn } from "@/lib/utils";

interface DataFreshnessProps {
  /** Last updated timestamp (ISO string or Date) */
  updatedAt: string | Date | null;
  className?: string;
}

function getMinutesAgo(date: Date): number {
  return Math.max(Math.floor((Date.now() - date.getTime()) / 60000), 0);
}

function getFreshnessLevel(minutesAgo: number): "fresh" | "stale" | "old" {
  if (minutesAgo < 5) return "fresh";
  if (minutesAgo < 30) return "stale";
  return "old";
}

function formatRelative(minutesAgo: number): string {
  if (minutesAgo < 1) return "Just now";
  if (minutesAgo < 60) return `${minutesAgo}m ago`;
  const hours = Math.floor(minutesAgo / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const dotColors = {
  fresh: "bg-growth-green",
  stale: "bg-chart-amber",
  old: "bg-growth-red",
} as const;

const dotPulse = {
  fresh: "animate-pulse",
  stale: "",
  old: "",
} as const;

export function DataFreshness({ updatedAt, className }: DataFreshnessProps) {
  if (!updatedAt) return null;

  const date = typeof updatedAt === "string" ? new Date(updatedAt) : updatedAt;
  const minutesAgo = getMinutesAgo(date);
  const level = getFreshnessLevel(minutesAgo);

  return (
    <div
      className={cn("flex items-center gap-1.5 text-xs text-text-secondary", className)}
      title={`Last updated: ${date.toLocaleString()}`}
    >
      <span
        className={cn(
          "inline-block h-2 w-2 rounded-full",
          dotColors[level],
          dotPulse[level],
        )}
      />
      <span>Updated {formatRelative(minutesAgo)}</span>
    </div>
  );
}
