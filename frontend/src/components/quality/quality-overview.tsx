"use client";

import { useState } from "react";
import { useQualityScorecard } from "@/hooks/use-quality-scorecard";
import { RunDetailPanel } from "./run-detail-panel";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { EmptyState } from "@/components/empty-state";
import {
  LoadSampleAction,
  UploadDataAction,
} from "@/components/shared/empty-state-actions";
import { ShieldCheck, ShieldX, AlertTriangle, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

function PassRateRing({ rate }: { rate: number }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - rate / 100);
  const color = rate >= 90 ? "text-green-500" : rate >= 70 ? "text-yellow-500" : "text-red-500";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="100" height="100" className="-rotate-90">
        <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="8"
          className="stroke-border" />
        <circle cx="50" cy="50" r={radius} fill="none" strokeWidth="8"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round" className={`${color} stroke-current`} />
      </svg>
      <span className={`absolute text-lg font-bold ${color}`}>
        {rate.toFixed(0)}%
      </span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    success: "bg-green-500/10 text-green-500",
    failed: "bg-red-500/10 text-red-500",
    running: "bg-blue-500/10 text-blue-500",
    pending: "bg-gray-500/10 text-gray-500",
  };
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${map[status] ?? "bg-muted text-text-secondary"}`}>
      {status}
    </span>
  );
}

export function QualityOverview() {
  const { data, isLoading, error } = useQualityScorecard();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  if (isLoading && data.runs.length === 0) return <LoadingCard className="h-96" />;
  if (error) return <ErrorRetry title="Failed to load quality scorecard" />;

  if (!isLoading && data.total_runs === 0) {
    return (
      <div className="mt-6">
        <EmptyState
          icon={<ShieldCheck className="h-10 w-10 text-accent" aria-hidden="true" />}
          title="No pipeline runs yet"
          description="Pipeline Health populates after your first import. Load a curated sample dataset to see how a healthy run looks, or bring your own file."
          action={
            <div className="flex flex-wrap items-center justify-center gap-3">
              <LoadSampleAction />
              <UploadDataAction />
            </div>
          }
        />
      </div>
    );
  }

  const totalFailed = data.runs.reduce((s, r) => s + r.failed, 0);
  const totalWarned = data.runs.reduce((s, r) => s + r.warned, 0);

  return (
    <div className="mt-6 space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <div className="viz-panel viz-card-hover flex flex-col items-center rounded-[1.5rem] p-5">
          <PassRateRing rate={data.overall_pass_rate} />
          <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">Overall Pass Rate</p>
        </div>
        <div className="viz-panel viz-card-hover rounded-[1.5rem] p-5">
          <ShieldCheck className="mb-3 h-4 w-4 text-green-500" />
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">Total Runs</p>
          <p className="text-2xl font-bold text-text-primary">{data.total_runs}</p>
        </div>
        <div className="viz-panel rounded-[1.5rem] border-red-500/20 bg-red-500/8 p-5">
          <ShieldX className="mb-3 h-4 w-4 text-red-500" />
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">Failed Checks</p>
          <p className="text-2xl font-bold text-red-500">{totalFailed}</p>
        </div>
        <div className="viz-panel rounded-[1.5rem] border-yellow-500/20 bg-yellow-500/8 p-5">
          <AlertTriangle className="mb-3 h-4 w-4 text-yellow-500" />
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">Warnings</p>
          <p className="text-2xl font-bold text-yellow-500">{totalWarned}</p>
        </div>
      </div>

      <div className="viz-panel overflow-x-auto rounded-[1.75rem] border border-border/80">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-text-secondary">
              <th className="px-4 py-3">Run</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Checks</th>
              <th className="px-4 py-3">Pass Rate</th>
              <th className="px-4 py-3">Failed</th>
              <th className="px-4 py-3">Warned</th>
              <th className="px-4 py-3 w-8"></th>
            </tr>
          </thead>
          <tbody>
            {data.runs.map((run) => (
              <tr
                key={run.run_id}
                onClick={() => setSelectedRunId(selectedRunId === run.run_id ? null : run.run_id)}
                className={cn(
                  "border-b border-border/50 cursor-pointer transition-colors",
                  selectedRunId === run.run_id
                    ? "bg-accent/8"
                    : "hover:bg-background/50",
                )}
              >
                <td className="px-4 py-2 text-xs text-text-secondary whitespace-nowrap">
                  {new Date(run.started_at).toLocaleString()}
                </td>
                <td className="px-4 py-2 text-xs font-medium text-text-primary">{run.run_type}</td>
                <td className="px-4 py-2"><StatusBadge status={run.status} /></td>
                <td className="px-4 py-2 text-xs text-text-primary">{run.total_checks}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs font-bold ${run.pass_rate >= 90 ? "text-green-500" : run.pass_rate >= 70 ? "text-yellow-500" : "text-red-500"}`}>
                    {run.pass_rate.toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-2 text-xs text-red-500 font-medium">
                  {run.failed > 0 ? run.failed : "-"}
                </td>
                <td className="px-4 py-2 text-xs text-yellow-500 font-medium">
                  {run.warned > 0 ? run.warned : "-"}
                </td>
                <td className="px-4 py-2">
                  <ChevronRight
                    className={cn(
                      "h-4 w-4 text-text-tertiary transition-transform",
                      selectedRunId === run.run_id && "rotate-90 text-accent",
                    )}
                  />
                </td>
              </tr>
            ))}
            {data.runs.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-text-tertiary">
                  No quality check data available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedRunId && (
        <RunDetailPanel
          runId={selectedRunId}
          onClose={() => setSelectedRunId(null)}
        />
      )}
    </div>
  );
}
