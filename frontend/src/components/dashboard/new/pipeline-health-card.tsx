"use client";

import { CheckCircle2, AlertCircle, Loader2, MinusCircle } from "lucide-react";
import { usePipelineHealth } from "@/hooks/use-pipeline-health";
import type {
  PipelineHealth,
  PipelineHealthHistoryPoint,
  PipelineHealthNode,
} from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonEnhanced } from "@/components/ui/skeleton-enhanced";
import { cn } from "@/lib/utils";

export interface PipelineHealthCardProps {
  /** Override the hook — useful for Storybook / tests. */
  health?: PipelineHealth;
  className?: string;
}

const NODE_STATUS_TONE: Record<PipelineHealthNode["status"], string> = {
  ok: "text-cyan-300 bg-cyan-500/10 border-cyan-500/30",
  running: "text-amber-300 bg-amber-500/10 border-amber-500/30",
  pending: "text-text-secondary bg-white/5 border-white/10",
  failed: "text-red-300 bg-red-500/10 border-red-500/30",
};

const NODE_STATUS_ICON: Record<PipelineHealthNode["status"], typeof CheckCircle2> = {
  ok: CheckCircle2,
  running: Loader2,
  pending: MinusCircle,
  failed: AlertCircle,
};

const HISTORY_BAR_TONE: Record<PipelineHealthHistoryPoint["status"], string> = {
  ok: "bg-cyan-400",
  warning: "bg-amber-400",
  fail: "bg-red-400",
  none: "bg-white/10",
};

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return s === 0 ? `${m}m` : `${m}m ${s}s`;
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

/**
 * Composite Pipeline Health card (#509) — renders the 3-node medallion
 * strip, last/next run pointers, quality gates + tests counters, and a
 * 7-day per-day duration/status bar chart.
 *
 * Single payload from ``/pipeline/health`` — no orchestration needed.
 */
export function PipelineHealthCard({ health, className }: PipelineHealthCardProps) {
  const hookResult = usePipelineHealth();
  const data = health !== undefined ? health : hookResult.data;
  const isLoading = health === undefined && hookResult.isLoading;

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="pb-3">
        <CardTitle>Pipeline Health</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 p-4 pt-0">
        {isLoading && (
          <div role="status" aria-label="Loading pipeline health">
            <SkeletonEnhanced className="h-20" lines={3} />
          </div>
        )}
        {!isLoading && data && (
          <>
            {/* Medallion nodes */}
            <div className="grid grid-cols-3 gap-2">
              {data.nodes.map((node) => {
                const Icon = NODE_STATUS_ICON[node.status] ?? MinusCircle;
                return (
                  <div
                    key={node.label}
                    className={cn(
                      "flex flex-col items-start gap-1.5 rounded-xl border p-3",
                      NODE_STATUS_TONE[node.status] ?? NODE_STATUS_TONE.pending,
                    )}
                  >
                    <div className="flex items-center gap-1.5">
                      <Icon
                        aria-hidden="true"
                        className={cn(
                          "h-3.5 w-3.5",
                          node.status === "running" && "animate-spin",
                        )}
                      />
                      <span className="text-[10px] font-semibold uppercase tracking-wider">
                        {node.label}
                      </span>
                    </div>
                    <span className="text-xs font-medium text-text-primary">
                      {node.value}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Run summary + counters */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <p className="text-text-secondary">Last run</p>
                <p className="mt-0.5 font-medium text-text-primary">
                  {data.last_run ? formatDateTime(data.last_run.at) : "—"}
                </p>
                {data.last_run && (
                  <p className="text-[11px] text-text-secondary">
                    {formatDuration(Number(data.last_run.duration_seconds))}
                  </p>
                )}
              </div>
              <div>
                <p className="text-text-secondary">Next run</p>
                <p className="mt-0.5 font-medium text-text-primary">
                  {data.next_run_at ? formatDateTime(data.next_run_at) : "—"}
                </p>
              </div>
              <div>
                <p className="text-text-secondary">Gates</p>
                <p className="mt-0.5 font-medium text-text-primary">
                  {data.gates.passed} / {data.gates.total}
                </p>
              </div>
              <div>
                <p className="text-text-secondary">Tests</p>
                <p className="mt-0.5 font-medium text-text-primary">
                  {data.tests.passed} / {data.tests.total}
                </p>
              </div>
            </div>

            {/* 7-day history bar chart */}
            <div>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
                Last 7 days
              </p>
              <div
                className="flex items-end gap-1"
                role="img"
                aria-label="Pipeline run history for the last 7 days"
              >
                {data.history_7d.map((point) => {
                  const durationNum = Number(point.duration_seconds ?? 0);
                  // Scale bar height from 8px (empty) to 40px (longest run).
                  const maxDur = Math.max(
                    ...data.history_7d.map((p) => Number(p.duration_seconds ?? 0)),
                    1,
                  );
                  const height = Math.max(8, (durationNum / maxDur) * 40);
                  return (
                    <div
                      key={point.date}
                      className="flex flex-1 flex-col items-center gap-1"
                      title={`${point.date} — ${point.status} (${formatDuration(
                        Number(point.duration_seconds),
                      )})`}
                    >
                      <div
                        className={cn(
                          "w-full rounded-sm transition-all",
                          HISTORY_BAR_TONE[point.status] ?? HISTORY_BAR_TONE.none,
                        )}
                        style={{ height: `${height}px` }}
                      />
                      <span className="text-[9px] text-text-secondary">
                        {point.date.slice(-2)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
