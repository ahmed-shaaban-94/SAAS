"use client";

import { useState } from "react";
import { PageTransition } from "@/components/layout/page-transition";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { useConnections } from "@/hooks/use-connections";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { SyncJob, SyncJobList } from "@/hooks/use-connections";
import { Activity, ChevronDown, ChevronUp } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  pending:   "bg-yellow-500/10 text-yellow-500",
  running:   "bg-blue-500/10 text-blue-500",
  success:   "bg-green-500/10 text-green-500",
  failed:    "bg-red-500/10 text-red-500",
};

function SyncHistory({ connectionId }: { connectionId: number }) {
  const { data, isLoading } = useSWR<SyncJobList>(
    `/api/v1/control-center/connections/${connectionId}/sync-history`,
    () => fetchAPI<SyncJobList>(`/api/v1/control-center/connections/${connectionId}/sync-history`),
    { refreshInterval: 15_000 },
  );

  if (isLoading) return <p className="px-4 py-3 text-xs text-text-secondary">Loading…</p>;
  if (!data?.items.length) return <p className="px-4 py-3 text-xs text-text-secondary italic">No sync runs yet.</p>;

  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="border-b border-border/50 text-left text-text-tertiary">
          <th className="px-4 py-2 font-medium">Run ID</th>
          <th className="px-4 py-2 font-medium">Mode</th>
          <th className="px-4 py-2 font-medium">Status</th>
          <th className="px-4 py-2 font-medium">Rows</th>
          <th className="px-4 py-2 font-medium">Duration</th>
          <th className="px-4 py-2 font-medium">Started</th>
        </tr>
      </thead>
      <tbody>
        {data.items.map((job: SyncJob) => (
          <tr key={job.id} className="border-b border-border/20">
            <td className="px-4 py-2 font-mono text-text-secondary">{job.pipeline_run_id?.slice(0, 8) ?? "—"}</td>
            <td className="px-4 py-2 text-text-secondary">{job.run_mode}</td>
            <td className="px-4 py-2">
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[job.status ?? ""] ?? "text-text-secondary"}`}>
                {job.status ?? "pending"}
              </span>
            </td>
            <td className="px-4 py-2 text-text-secondary">{job.rows_loaded?.toLocaleString() ?? "—"}</td>
            <td className="px-4 py-2 text-text-secondary">{job.duration_seconds != null ? `${job.duration_seconds.toFixed(1)}s` : "—"}</td>
            <td className="px-4 py-2 text-text-secondary">{job.started_at ? new Date(job.started_at).toLocaleString() : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function SyncRunsPage() {
  const [expanded, setExpanded] = useState<number | null>(null);
  const { data, isLoading, error } = useConnections({ status: "active", page_size: 100 });

  if (isLoading) return <LoadingCard className="h-64" />;
  if (error) return <ErrorRetry title="Failed to load connections" />;

  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Sync Runs"
        description="Per-connection pipeline execution history"
      />

      <div className="mt-6 space-y-3">
        {data.items.map((conn) => (
          <div key={conn.id} className="rounded-2xl border border-border/50 bg-card overflow-hidden">
            <button
              onClick={() => setExpanded(expanded === conn.id ? null : conn.id)}
              className="flex w-full items-center justify-between px-5 py-4 text-left hover:bg-accent/10"
            >
              <div className="flex items-center gap-3">
                <Activity className="h-4 w-4 text-primary" />
                <span className="font-medium text-text-primary">{conn.name}</span>
                <span className="text-xs font-mono text-text-secondary">{conn.source_type}</span>
              </div>
              {expanded === conn.id ? (
                <ChevronUp className="h-4 w-4 text-text-secondary" />
              ) : (
                <ChevronDown className="h-4 w-4 text-text-secondary" />
              )}
            </button>
            {expanded === conn.id && (
              <div className="border-t border-border/50 overflow-x-auto">
                <SyncHistory connectionId={conn.id} />
              </div>
            )}
          </div>
        ))}
        {data.items.length === 0 && (
          <p className="py-12 text-center text-text-secondary">No active connections. Add sources first.</p>
        )}
      </div>
    </PageTransition>
  );
}
