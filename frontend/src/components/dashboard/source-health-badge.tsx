"use client";

import { CheckCircle2, XCircle, Clock, AlertCircle } from "lucide-react";
import { usePipelineRuns } from "@/hooks/use-pipeline-runs";
import { cn } from "@/lib/utils";

function relativeTime(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function SourceHealthBadge() {
  const { runs, isLoading } = usePipelineRuns(1);

  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5">
        <div className="h-3 w-3 animate-pulse rounded-full bg-divider" />
        <span className="inline-block h-3 w-20 animate-pulse rounded bg-divider" />
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-text-secondary">
        <AlertCircle className="h-3.5 w-3.5" />
        <span>No data yet</span>
      </div>
    );
  }

  const last = runs[0];
  const isSuccess = last.status === "success";
  const finishedAt = last.finished_at ?? last.started_at;

  return (
    <div
      title={isSuccess ? "Data is current" : "Last run failed"}
      className={cn(
        "flex items-center gap-1.5 text-xs font-medium",
        isSuccess ? "text-growth-green" : "text-growth-red",
      )}
    >
      {isSuccess ? (
        <CheckCircle2 className="h-3.5 w-3.5" />
      ) : (
        <XCircle className="h-3.5 w-3.5" />
      )}
      <span>{isSuccess ? "Current" : "Failed"}</span>
      {finishedAt && (
        <span className="text-text-secondary font-normal">
          <Clock className="mr-0.5 inline h-3 w-3" />
          {relativeTime(finishedAt)}
        </span>
      )}
    </div>
  );
}
