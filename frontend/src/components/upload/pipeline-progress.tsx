"use client";

import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatNumber } from "@/lib/formatters";
import { getStageIndex, getStageLabel } from "@/hooks/use-pipeline-run";

interface RunProgress {
  run_id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  rows_loaded: number | null;
  error_message: string | null;
}

const PIPELINE_STAGES = [
  { key: "pending", label: "Queued" },
  { key: "running", label: "Bronze" },
  { key: "bronze_complete", label: "Silver" },
  { key: "silver_complete", label: "Gold" },
  { key: "success", label: "Done" },
] as const;

interface PipelineProgressProps {
  progress: RunProgress;
  isRunning: boolean;
  error: string | null;
}

export function PipelineProgress({ progress, isRunning, error }: PipelineProgressProps) {
  const currentIdx = getStageIndex(progress.status);
  const isFailed = progress.status === "failed";
  const isSuccess = progress.status === "success";

  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isRunning && <Loader2 className="h-4 w-4 animate-spin text-accent" />}
          {isSuccess && <CheckCircle2 className="h-4 w-4 text-green-500" />}
          {isFailed && <XCircle className="h-4 w-4 text-red-500" />}
          <h3 className="text-sm font-semibold text-text-primary">
            Pipeline {getStageLabel(progress.status)}
          </h3>
        </div>
        {progress.duration_seconds != null && (
          <span className="flex items-center gap-1 text-xs text-text-secondary">
            <Clock className="h-3 w-3" />
            {progress.duration_seconds.toFixed(1)}s
          </span>
        )}
      </div>

      {/* Stage progress bar */}
      <div className="flex items-center gap-1">
        {PIPELINE_STAGES.map((stage, i) => {
          const isPast = currentIdx > i;
          const isCurrent = currentIdx === i;
          return (
            <div key={stage.key} className="flex-1 space-y-1">
              <div
                className={cn(
                  "h-2 rounded-full transition-all duration-500",
                  isPast && "bg-green-500",
                  isCurrent && isRunning && "bg-accent animate-pulse",
                  isCurrent && isFailed && "bg-red-500",
                  isCurrent && isSuccess && "bg-green-500",
                  !isPast && !isCurrent && "bg-border",
                )}
              />
              <p
                className={cn(
                  "text-center text-[10px]",
                  (isPast || isCurrent) ? "text-text-primary font-medium" : "text-text-tertiary",
                )}
              >
                {stage.label}
              </p>
            </div>
          );
        })}
      </div>

      {/* Error message */}
      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-500">
          {error}
        </div>
      )}

      {/* Success details */}
      {isSuccess && progress.rows_loaded != null && (
        <p className="text-xs text-text-secondary">
          {formatNumber(progress.rows_loaded)} rows loaded
        </p>
      )}
    </div>
  );
}
