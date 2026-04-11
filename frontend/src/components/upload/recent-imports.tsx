"use client";

import { usePipelineRuns, type PipelineRun } from "@/hooks/use-pipeline-runs";
import { LoadingCard } from "@/components/loading-card";
import { Clock, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "success":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-red-500" />;
    case "running":
    case "pending":
      return <Loader2 className="h-4 w-4 animate-spin text-accent" />;
    default:
      return <Clock className="h-4 w-4 text-text-tertiary" />;
  }
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    success: "bg-green-500/10 text-green-500",
    failed: "bg-red-500/10 text-red-500",
    running: "bg-blue-500/10 text-blue-500",
    pending: "bg-gray-500/10 text-gray-500",
  };
  return (
    <span className={cn("rounded px-1.5 py-0.5 text-xs font-medium", styles[status] ?? "bg-muted text-text-secondary")}>
      {status}
    </span>
  );
}

function RunRow({ run }: { run: PipelineRun }) {
  return (
    <div className="flex items-center gap-3 py-2.5">
      <StatusIcon status={run.status} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-text-primary capitalize">
          {run.run_type} run
        </p>
        <p className="text-xs text-text-secondary">
          {new Date(run.started_at).toLocaleString()}
          {run.duration_seconds != null && ` - ${run.duration_seconds.toFixed(1)}s`}
          {run.rows_loaded != null && ` - ${run.rows_loaded.toLocaleString()} rows`}
        </p>
      </div>
      <StatusBadge status={run.status} />
    </div>
  );
}

export function RecentImports() {
  const { runs, isLoading } = usePipelineRuns(5);

  if (isLoading) return <LoadingCard className="h-48" />;
  if (runs.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-3">
        Recent Pipeline Runs
      </h3>
      <div className="divide-y divide-border">
        {runs.map((run) => (
          <RunRow key={run.id} run={run} />
        ))}
      </div>
    </div>
  );
}
