"use client";

/**
 * /expiry — Near-expiry and write-off analytics on the v2 shell.
 *
 * Pharma Ops batch (Apr 2026): added a 4-tile `KpiCard` grid matching
 * the design-kit aesthetic. Totals roll up from
 * `useExpiryExposure` (tenant-wide 30/60/90d tiers) and
 * `useExpirySummary` (per-site bucket breakdown).
 */

import { useMemo } from "react";
import dynamic from "next/dynamic";
import { AlertOctagon, CalendarClock, Clock, FlaskConical } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { FilterBar } from "@/components/filters/filter-bar";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { LoadingCard } from "@/components/loading-card";
import { useExpiryExposure } from "@/hooks/use-expiry-exposure";
import { useExpirySummary } from "@/hooks/use-expiry-summary";
import { useFilters } from "@/contexts/filter-context";
import { formatCurrency, formatNumber } from "@/lib/formatters";

const ExpiryCalendar = dynamic(
  () =>
    import("@/components/expiry/expiry-calendar").then((m) => ({
      default: m.ExpiryCalendar,
    })),
  { loading: () => <LoadingCard lines={8} />, ssr: false },
);

const NearExpiryList = dynamic(
  () =>
    import("@/components/expiry/near-expiry-list").then((m) => ({
      default: m.NearExpiryList,
    })),
  { loading: () => <LoadingCard lines={6} />, ssr: false },
);

const ExpiredStockTable = dynamic(
  () =>
    import("@/components/expiry/expired-stock-table").then((m) => ({
      default: m.ExpiredStockTable,
    })),
  { loading: () => <LoadingCard lines={8} />, ssr: false },
);

const WriteOffSummaryChart = dynamic(
  () =>
    import("@/components/expiry/write-off-summary-chart").then((m) => ({
      default: m.WriteOffSummaryChart,
    })),
  { loading: () => <LoadingCard lines={4} />, ssr: false },
);

export default function ExpiryPage() {
  const { filters } = useFilters();
  const { data: exposure, isLoading: exposureLoading } = useExpiryExposure();
  const { data: summary, isLoading: summaryLoading } = useExpirySummary(filters);

  const kpiLoading = exposureLoading || summaryLoading;

  const kpis = useMemo(() => {
    const tiers = exposure ?? [];
    const tier30 = tiers.find((t) => t.tier === "30d");
    const tier60 = tiers.find((t) => t.tier === "60d");
    const tier90 = tiers.find((t) => t.tier === "90d");

    const totalExposure =
      (tier30?.total_egp ?? 0) + (tier60?.total_egp ?? 0) + (tier90?.total_egp ?? 0);
    const totalBatches =
      (tier30?.batch_count ?? 0) + (tier60?.batch_count ?? 0) + (tier90?.batch_count ?? 0);

    const sites = summary ?? [];
    const expiredBatches = sites.reduce((s, r) => s + r.expired_count, 0);
    const expiredValue = sites.reduce((s, r) => s + r.total_expired_value, 0);
    const criticalBatches = sites.reduce((s, r) => s + r.critical_count, 0);

    return [
      {
        id: "exposure",
        label: "Total Expiry Exposure",
        value: formatCurrency(totalExposure),
        delta: {
          dir: (totalExposure === 0 ? "up" : "down") as KpiDir,
          text: `${formatNumber(totalBatches)} batches`,
        },
        sub: "≤ 90 days to expiry, all tiers",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: AlertOctagon,
      },
      {
        id: "tier-30",
        label: "Critical (≤ 30d)",
        value: formatCurrency(tier30?.total_egp ?? 0),
        delta: {
          dir: ((tier30?.batch_count ?? 0) === 0 ? "up" : "down") as KpiDir,
          text: `${formatNumber(tier30?.batch_count ?? 0)} batches`,
        },
        sub: "write-off risk window",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: CalendarClock,
      },
      {
        id: "expired",
        label: "Already Expired",
        value: formatCurrency(expiredValue),
        delta: {
          dir: (expiredBatches === 0 ? "up" : "down") as KpiDir,
          text: `${formatNumber(expiredBatches)} batches`,
        },
        sub: "past expiry date, pending write-off",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: FlaskConical,
      },
      {
        id: "critical-sites",
        label: "Critical SKUs (site × batch)",
        value: formatNumber(criticalBatches),
        delta: {
          dir: (criticalBatches === 0 ? "up" : "down") as KpiDir,
          text: `${sites.length} sites`,
        },
        sub: "critical bucket across branches",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: Clock,
      },
    ];
  }, [exposure, summary]);

  return (
    <DashboardShell
      activeHref="/expiry"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Expiry" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Expiry.</h1>
          <p className="page-sub">
            Near-expiry inventory, expired batches, and write-off exposure
            across every branch.
          </p>
        </div>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Expiry KPIs"
        >
          {kpiLoading
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

        <FilterBar />

        <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
          <ExpiryCalendar />
          <WriteOffSummaryChart />
        </div>

        <div style={{ marginTop: 24 }}>
          <NearExpiryList />
        </div>

        <div style={{ marginTop: 24 }}>
          <ExpiredStockTable />
        </div>
      </div>
    </DashboardShell>
  );
}
