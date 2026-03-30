"use client";

import { usePipelineRuns } from "@/hooks/use-pipeline-runs";
import { RunStatusBadge } from "./run-status-badge";
import { formatDuration } from "@/lib/formatters";

function formatDatetime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatRows(rows: number | null): string {
  if (rows === null || rows === undefined) return "—";
  return rows.toLocaleString();
}

export function RunHistoryTable() {
  const { data, isLoading } = usePipelineRuns({ limit: 50 });

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-card">
        <div className="px-5 py-4">
          <div className="h-5 w-32 animate-pulse rounded bg-divider" />
        </div>
        <div className="divide-y divide-border">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-5 py-3">
              <div className="h-4 w-20 animate-pulse rounded bg-divider" />
              <div className="h-4 w-24 animate-pulse rounded bg-divider" />
              <div className="h-4 w-16 animate-pulse rounded bg-divider" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const items = data?.items ?? [];

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="border-b border-border px-5 py-4">
        <h2 className="text-sm font-semibold text-text-primary">Run History</h2>
        {data && (
          <p className="mt-0.5 text-xs text-text-secondary">
            Showing {items.length} of {data.total} runs
          </p>
        )}
      </div>

      {items.length === 0 ? (
        <div className="px-5 py-10 text-center text-sm text-text-secondary">
          No pipeline runs found.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm" aria-label="Pipeline run history">
            <thead>
              <tr className="border-b border-border">
                <th className="px-5 py-3 text-left text-xs font-semibold text-text-primary">
                  Status
                </th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-text-primary">
                  Run Type
                </th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-text-primary">
                  Trigger
                </th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-text-primary">
                  Started
                </th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-text-primary">
                  Duration
                </th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-text-primary">
                  Rows
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((run) => (
                <tr
                  key={run.id}
                  className="transition-colors hover:bg-divider/50"
                >
                  <td className="px-5 py-3">
                    <RunStatusBadge status={run.status} />
                  </td>
                  <td className="px-5 py-3 text-text-secondary">{run.run_type}</td>
                  <td className="px-5 py-3 text-text-secondary">
                    {run.trigger_source ?? "—"}
                  </td>
                  <td className="px-5 py-3 text-text-secondary">
                    {formatDatetime(run.started_at)}
                  </td>
                  <td className="px-5 py-3 text-text-secondary">
                    {formatDuration(run.duration_seconds)}
                  </td>
                  <td className="px-5 py-3 text-text-secondary">
                    {formatRows(run.rows_loaded)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
