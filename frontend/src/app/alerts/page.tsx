"use client";

/**
 * /alerts — Alerts & Notifications on the v2 shell.
 *
 * Ops Surfaces batch (Apr 2026): migrated from `(app)/alerts/page.tsx`,
 * added a 4-tile KpiCard row (total, unack, acknowledged, critical).
 * `AlertsOverview` renders with `hideStats` so its legacy 3-tile block
 * doesn't duplicate.
 */

import { useMemo } from "react";
import { Bell, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { AlertsOverview } from "@/components/alerts/alerts-overview";
import { LoadingCard } from "@/components/loading-card";
import { useAlertLog } from "@/hooks/use-alerts";
import { formatNumber } from "@/lib/formatters";

export default function AlertsPage() {
  const { data: allAlerts, isLoading } = useAlertLog(false);

  const kpis = useMemo(() => {
    const all = allAlerts ?? [];
    const unack = all.filter((a) => !a.acknowledged).length;
    const ack = all.length - unack;
    const critical = all.filter((a) =>
      (a.message ?? "").toLowerCase().includes("critical"),
    ).length;

    return [
      {
        id: "total",
        label: "Total Alerts",
        value: formatNumber(all.length),
        delta: { dir: "up" as KpiDir, text: "recent history" },
        sub: "across all severities",
        color: "accent" as KpiColor,
        sparkline: [] as number[],
        icon: Bell,
      },
      {
        id: "unacknowledged",
        label: "Unacknowledged",
        value: formatNumber(unack),
        delta: {
          dir: (unack === 0 ? "up" : "down") as KpiDir,
          text: unack === 0 ? "inbox clear" : "awaiting review",
        },
        sub: "require operator acknowledgement",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: AlertTriangle,
      },
      {
        id: "acknowledged",
        label: "Acknowledged",
        value: formatNumber(ack),
        delta: { dir: "up" as KpiDir, text: "handled" },
        sub: "cleared by the team",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: CheckCircle2,
      },
      {
        id: "critical",
        label: "Critical",
        value: formatNumber(critical),
        delta: {
          dir: (critical === 0 ? "up" : "down") as KpiDir,
          text: critical === 0 ? "none" : "investigate now",
        },
        sub: "tagged critical in message",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: XCircle,
      },
    ];
  }, [allAlerts]);

  return (
    <DashboardShell
      activeHref="/alerts"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Monitoring" },
        { label: "Alerts" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Alerts & notifications.</h1>
          <p className="page-sub">
            Configure metric alerts and view notification history across the team.
          </p>
        </div>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Alerts KPIs"
        >
          {isLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <LoadingCard key={i} lines={3} className="h-[168px]" />
              ))
            : kpis.map((k) => (
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

        <AlertsOverview hideStats />
      </div>
    </DashboardShell>
  );
}
