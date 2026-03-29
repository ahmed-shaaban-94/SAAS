"use client";

import { usePipelineRuns } from "@/hooks/use-pipeline-runs";
import { formatDuration } from "@/lib/formatters";

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export function PipelineOverview() {
  const { data, isLoading } = usePipelineRuns({ limit: 100 });

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="animate-pulse rounded-xl border border-border bg-card p-5"
          >
            <div className="mb-3 h-3 w-1/2 rounded bg-divider" />
            <div className="h-7 w-2/3 rounded bg-divider" />
          </div>
        ))}
      </div>
    );
  }

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const successCount = items.filter((r) => r.status === "success").length;
  const successRate = items.length > 0 ? (successCount / items.length) * 100 : 0;

  const completedWithDuration = items.filter(
    (r) => r.duration_seconds !== null && r.duration_seconds !== undefined,
  );
  const avgDuration =
    completedWithDuration.length > 0
      ? completedWithDuration.reduce((sum, r) => sum + (r.duration_seconds ?? 0), 0) /
        completedWithDuration.length
      : null;

  const mostRecent = items.length > 0 ? items[0] : null;

  const kpis = [
    {
      label: "Total Runs",
      value: total.toLocaleString(),
    },
    {
      label: total > items.length ? "Success Rate (recent)" : "Success Rate",
      value: items.length > 0 ? `${successRate.toFixed(1)}%` : "—",
    },
    {
      label: "Avg Duration",
      value: avgDuration !== null ? formatDuration(avgDuration) : "—",
    },
    {
      label: "Last Run",
      value: mostRecent ? formatRelativeTime(mostRecent.started_at) : "—",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {kpis.map((kpi) => (
        <div
          key={kpi.label}
          className="rounded-xl border border-border bg-card p-5 transition-colors hover:border-accent/30"
        >
          <p className="text-sm font-medium text-text-secondary">{kpi.label}</p>
          <p className="mt-2 text-2xl font-bold text-text-primary">{kpi.value}</p>
        </div>
      ))}
    </div>
  );
}
