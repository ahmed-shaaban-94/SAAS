"use client";

import { useState } from "react";
import { useQualityScorecard } from "@/hooks/use-quality-scorecard";
import { RunDetailPanel } from "./run-detail-panel";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
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

  const totalFailed = data.runs.reduce((s, r) => s + r.failed, 0);
  const totalWarned = data.runs.reduce((s, r) => s + r.warned, 0);

  return (
    <div className="space-y-6 mt-6">
      {/* Summary cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-4 flex flex-col items-center">
          <PassRateRing rate={data.overall_pass_rate} />
          <p className="text-xs text-text-secondary mt-2">Overall Pass Rate</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <ShieldCheck className="h-4 w-4 text-green-500 mb-2" />
          <p className="text-xs text-text-secondary">Total Runs</p>
          <p className="text-2xl font-bold text-text-primary">{data.total_runs}</p>
        </div>
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
          <ShieldX className="h-4 w-4 text-red-500 mb-2" />
          <p className="text-xs text-text-secondary">Failed Checks</p>
          <p className="text-2xl font-bold text-red-500">{totalFailed}</p>
        </div>
        <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-4">
          <AlertTriangle className="h-4 w-4 text-yellow-500 mb-2" />
          <p className="text-xs text-text-secondary">Warnings</p>
          <p className="text-2xl font-bold text-yellow-500">{totalWarned}</p>
        </div>
      </div>

      {/* Run history table */}
      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-secondary">
              <th className="px-4 py-3 font-medium">Run</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Checks</th>
              <th className="px-4 py-3 font-medium">Pass Rate</th>
              <th className="px-4 py-3 font-medium">Failed</th>
              <th className="px-4 py-3 font-medium">Warned</th>
              <th className="px-4 py-3 font-medium w-8"></th>
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
                    ? "bg-accent/5"
                    : "hover:bg-muted/50",
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

      {/* Run detail panel — expands below table */}
      {selectedRunId && (
        <RunDetailPanel
          runId={selectedRunId}
          onClose={() => setSelectedRunId(null)}
        />
      )}
    </div>
  );
}
