"use client";

/**
 * /control-center — pipeline health overview on the v2 shell.
 *
 * Task-surfaces batch (Apr 2026): migrated from `(app)/control-center/page.tsx`.
 * Legacy StatCard grid swapped for a 4-tile `KpiCard` row. The failed-sync
 * count surfaces via a red-tinted tile rather than a highlighted StatCard.
 */

import { useMemo } from "react";
import { Activity, Clock, CheckCircle2, AlertTriangle } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { useHealthSummary } from "@/hooks/use-health-summary";

function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function ControlCenterPage() {
  const { data, error, isLoading, mutate } = useHealthSummary();

  const kpis = useMemo(() => {
    if (!data) return null;
    const hasFailed = data.failed_syncs_last_24h > 0;

    return [
      {
        id: "active",
        label: "Active Connections",
        value: String(data.active_connections),
        delta: { dir: "up" as KpiDir, text: "source integrations" },
        sub: "currently configured",
        color: "accent" as KpiColor,
        sparkline: [] as number[],
        icon: Activity,
      },
      {
        id: "last-sync",
        label: "Last Sync",
        value: formatDate(data.last_sync_at),
        delta: { dir: "up" as KpiDir, text: data.last_sync_at ? "recent" : "no runs" },
        sub: "most recent pipeline run",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: Clock,
      },
      {
        id: "release",
        label: "Active Release",
        value:
          data.active_release_version != null
            ? `v${data.active_release_version}`
            : "None",
        delta: { dir: "up" as KpiDir, text: `${data.pending_drafts} drafts pending` },
        sub: "published configuration in effect",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: CheckCircle2,
      },
      {
        id: "failed",
        label: "Failed Syncs (24h)",
        value: String(data.failed_syncs_last_24h),
        delta: {
          dir: (hasFailed ? "down" : "up") as KpiDir,
          text: hasFailed ? "investigate now" : "all green",
        },
        sub: "within the last 24 hours",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: AlertTriangle,
      },
    ];
  }, [data]);

  return (
    <DashboardShell
      activeHref="/control-center"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Control Center" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Control center.</h1>
          <p className="page-sub">
            Overview of your data pipeline health across sources, profiles, and releases.
          </p>
        </div>

        {isLoading ? (
          <LoadingCard />
        ) : error ? (
          <ErrorRetry onRetry={() => mutate()} />
        ) : !kpis ? null : (
          <section
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
            aria-label="Control center KPIs"
          >
            {kpis.map((k) => (
              <KpiCard
                key={k.id}
                label={k.label}
                value={k.value}
                delta={k.delta}
                sub={k.sub}
                color={k.color}
                sparkline={k.sparkline}
                icon={k.icon}
              />
            ))}
          </section>
        )}
      </div>
    </DashboardShell>
  );
}
