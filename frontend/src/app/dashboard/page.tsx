"use client";

/**
 * /dashboard — new Daily Operations Overview (epic #501, task #502).
 *
 * Replaces the v2 editorial layout with the high-fidelity design
 * handoff. All 10 widgets bind to live SWR hooks — no mock data.
 *
 * Golden-Path (Phase 2 #399) telemetry still fires on mount so upload
 * → first-insight latency continues to be measured after the cutover.
 */

import { useEffect, useState } from "react";
import { Download, Plus } from "lucide-react";
import { useSession } from "next-auth/react";

import {
  DashboardSidebar,
  AlertBanner,
  KpiCard,
  DEFAULT_KPI_ICONS,
  RevenueChart,
  ChannelDonut,
  InventoryTable,
  ExpiryHeatmap,
  BranchList,
  AnomalyFeed,
  PipelineHealthCard,
} from "@/components/dashboard/new";
import { OnboardingStrip } from "@/components/dashboard/onboarding-strip";
import { FirstInsightCard } from "@/components/dashboard/first-insight-card";
import { useDashboard } from "@/hooks/use-dashboard";
import { useRevenueForecast, type RevenueForecastPeriod } from "@/hooks/use-revenue-forecast";
import { useChannels } from "@/hooks/use-channels";
import { useReorderAlerts } from "@/hooks/use-reorder-alerts";
import { useExpiryCalendar } from "@/hooks/use-expiry-calendar";
import { useExpiryExposure } from "@/hooks/use-expiry-exposure";
import { useAnomalyCards } from "@/hooks/use-anomaly-cards";
import { usePipelineHealth } from "@/hooks/use-pipeline-health";
import { useTopInsight } from "@/hooks/use-top-insight";
import { useSites } from "@/hooks/use-sites";
import { trackFirstDashboardView } from "@/lib/analytics-events";
import type { KpiColor, KpiDir } from "@/components/dashboard/new";
import type { KPISparkline, KPISummary, TimeSeriesPoint } from "@/types/api";

type Period = "Day" | "Week" | "Month" | "Quarter" | "YTD";
const PERIODS: Period[] = ["Day", "Week", "Month", "Quarter", "YTD"];

const periodToApi: Record<Period, RevenueForecastPeriod> = {
  Day: "day",
  Week: "week",
  Month: "month",
  Quarter: "quarter",
  YTD: "ytd",
};

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `EGP ${(value / 1_000).toFixed(0)}K`;
  return `EGP ${value.toFixed(0)}`;
}

function formatInt(value: number): string {
  return value.toLocaleString();
}

function sparklineFor(
  metric: KPISparkline["metric"],
  summary: KPISummary | undefined,
): number[] {
  const series =
    summary?.sparklines?.find((s) => s.metric === metric)?.points ??
    (metric === "revenue" ? summary?.sparkline : undefined);
  if (!series?.length) return [];
  const values = series.map((p: TimeSeriesPoint) => Number(p.value) || 0);
  const max = Math.max(...values, 1);
  // Invert to match the 0→40 viewBox in KpiCard's sparkline (smaller y = higher)
  return values.map((v) => 32 - (v / max) * 28);
}

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "just now";
  const d = new Date(iso).getTime();
  if (Number.isNaN(d)) return "just now";
  const diff = Math.max(0, Date.now() - d);
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function todayLabel(date = new Date()): string {
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function DashboardPage() {
  const [period, setPeriod] = useState<Period>("Month");
  const { data: session } = useSession();
  const firstName =
    session?.user?.name?.split(" ")[0] ||
    session?.user?.email?.split("@")[0] ||
    "there";

  useEffect(() => {
    trackFirstDashboardView();
  }, []);

  const { data: dashboard, isLoading: kpiLoading } = useDashboard();
  const { data: revenueForecast, isLoading: revenueLoading } = useRevenueForecast(
    periodToApi[period],
  );
  const { data: channels, isLoading: channelsLoading } = useChannels();
  const { data: reorder, isLoading: reorderLoading } = useReorderAlerts();
  const { data: expiryCalendar, isLoading: calendarLoading } = useExpiryCalendar();
  const { data: expiryExposure, isLoading: exposureLoading } = useExpiryExposure();
  const { data: anomalies, isLoading: anomaliesLoading } = useAnomalyCards(6);
  const { data: pipeline, isLoading: pipelineLoading } = usePipelineHealth();
  const { data: topInsight, isLoading: insightLoading } = useTopInsight();
  const { data: sites, isLoading: sitesLoading } = useSites();

  const summary = dashboard?.kpi;

  const kpis: Array<{
    id: string;
    label: string;
    value: string;
    valueSuffix?: string;
    delta: { dir: KpiDir; text: string };
    sub: string;
    color: KpiColor;
    sparkline: number[];
    iconKey: keyof typeof DEFAULT_KPI_ICONS;
  }> = summary
    ? [
        {
          id: "revenue",
          label: "Total Revenue",
          value: formatEgp(summary.period_gross ?? summary.mtd_gross ?? 0),
          delta: {
            dir: (summary.mom_growth_pct ?? 0) >= 0 ? "up" : "down",
            text: `${Math.abs(summary.mom_growth_pct ?? 0).toFixed(1)}%`,
          },
          sub: "vs last month",
          color: "accent",
          sparkline: sparklineFor("revenue", summary),
          iconKey: "revenue",
        },
        {
          id: "orders",
          label: "Orders",
          value: formatInt(summary.period_transactions ?? summary.mtd_transactions ?? 0),
          delta: {
            dir: "up",
            text: `${formatInt(summary.daily_transactions ?? 0)} today`,
          },
          sub: `${formatInt(summary.period_customers ?? 0)} customers`,
          color: "purple",
          sparkline: sparklineFor("orders", summary),
          iconKey: "orders",
        },
        {
          id: "stock",
          label: "Stock Risk",
          value: formatInt(summary.stock_risk_count ?? 0),
          valueSuffix: "SKUs",
          delta: {
            dir: (summary.stock_risk_delta ?? 0) <= 0 ? "up" : "down",
            text:
              summary.stock_risk_delta != null
                ? `${summary.stock_risk_delta > 0 ? "+" : ""}${summary.stock_risk_delta} new`
                : "needing reorder",
          },
          sub: "needing reorder",
          color: "amber",
          sparkline: sparklineFor("stock_risk", summary),
          iconKey: "stock",
        },
        {
          id: "expiry",
          label: "Expiry Exposure",
          value: formatEgp(summary.expiry_exposure_egp ?? 0),
          delta: { dir: "down", text: "30-day window" },
          sub: `${formatInt(summary.expiry_batch_count ?? 0)} batches`,
          color: "red",
          sparkline: sparklineFor("expiry_exposure", summary),
          iconKey: "expiry",
        },
      ]
    : [];

  const syncedAgo = relativeTime(pipeline?.last_run?.at);
  const branchNames = Array.from(new Set((reorder ?? []).map((r) => r.site_name))).filter(Boolean);
  const sitesItems = sites?.items ?? [];

  return (
    <div className="min-h-screen bg-page text-ink-primary font-sans grid grid-cols-1 xl:grid-cols-[248px_1fr]">
      <DashboardSidebar activeHref="/dashboard" />

      <main id="main-content" className="px-8 py-7 pb-16 max-w-[1600px]">
        <header className="flex flex-wrap items-end gap-5 mb-6">
          <div className="flex-1 min-w-[320px]">
            <div className="text-sm text-ink-secondary flex items-center gap-2 flex-wrap">
              Good morning, {firstName} — here&apos;s the pulse for{" "}
              <b className="text-ink-primary">{todayLabel()}</b>
              <LiveBadge label={`Synced ${syncedAgo}`} />
            </div>
            <h1 className="text-3xl font-bold tracking-tight mt-1">
              Daily operations overview
            </h1>
          </div>
          <PageActions period={period} onPeriodChange={setPeriod} />
        </header>

        <AlertBanner data={topInsight} loading={insightLoading} />

        {/* Phase 2 Golden-Path (#398) retained — self-hides when complete. */}
        <div className="mt-5 flex flex-col gap-4">
          <OnboardingStrip />
          <FirstInsightCard />
        </div>

        <section
          className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mt-5"
          aria-label="Key performance indicators"
        >
          {(kpiLoading || !summary ? Array.from({ length: 4 }) : kpis).map(
            (k, i) => {
              if (kpiLoading || !summary) {
                return (
                  <div
                    key={i}
                    className="rounded-[14px] bg-card border border-border/40 p-5 h-[168px] animate-pulse"
                    aria-busy="true"
                  />
                );
              }
              const kpi = k as (typeof kpis)[number];
              return (
                <KpiCard
                  key={kpi.id}
                  label={kpi.label}
                  value={kpi.value}
                  valueSuffix={kpi.valueSuffix}
                  delta={kpi.delta}
                  sub={kpi.sub}
                  color={kpi.color}
                  sparkline={kpi.sparkline}
                  icon={DEFAULT_KPI_ICONS[kpi.iconKey]}
                />
              );
            },
          )}
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-[2fr_1fr] gap-4 mt-5">
          <RevenueChart
            data={revenueForecast}
            loading={revenueLoading}
            mode="Revenue"
          />
          <ChannelDonut data={channels} loading={channelsLoading} />
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-5">
          <div className="xl:col-span-2">
            <InventoryTable
              data={reorder}
              loading={reorderLoading}
              branches={branchNames}
            />
          </div>
          <ExpiryHeatmap
            calendar={expiryCalendar}
            exposure={expiryExposure}
            loading={calendarLoading || exposureLoading}
          />
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-5">
          <BranchList data={sitesItems} loading={sitesLoading} />
          <AnomalyFeed data={anomalies} loading={anomaliesLoading} />
          <PipelineHealthCard data={pipeline} loading={pipelineLoading} />
        </section>
      </main>
    </div>
  );
}

function LiveBadge({ label }: { label: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 text-[11px] text-accent-strong font-mono uppercase tracking-wider"
      aria-live="polite"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" aria-hidden />
      {label}
    </span>
  );
}

function PageActions({
  period,
  onPeriodChange,
}: {
  period: Period;
  onPeriodChange: (p: Period) => void;
}) {
  return (
    <div className="flex items-center gap-3 ml-auto">
      <div
        role="tablist"
        aria-label="Period"
        className="inline-flex p-1 rounded-full bg-card/80 border border-border/40"
      >
        {PERIODS.map((p) => (
          <button
            key={p}
            role="tab"
            aria-selected={period === p}
            onClick={() => onPeriodChange(p)}
            className={[
              "px-3.5 py-1.5 rounded-full text-[13px] transition",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
              period === p
                ? "bg-elevated text-ink-primary shadow-[inset_0_0_0_1px_rgba(0,199,242,0.3)]"
                : "text-ink-secondary hover:text-ink-primary",
            ].join(" ")}
          >
            {p}
          </button>
        ))}
      </div>
      <button
        type="button"
        className="px-3.5 py-2 rounded-lg border border-border/60 text-[13px] inline-flex items-center gap-2 hover:bg-elevated/60
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        <Download className="w-3.5 h-3.5" aria-hidden />
        Export
      </button>
      <button
        type="button"
        className="px-3.5 py-2 rounded-lg bg-accent text-page font-semibold text-[13px] inline-flex items-center gap-2 hover:bg-accent-strong
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        <Plus className="w-3.5 h-3.5" aria-hidden />
        New report
      </button>
    </div>
  );
}
