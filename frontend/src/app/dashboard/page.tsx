"use client";

/**
 * /dashboard -- Action-Center redesign (2026-04-21).
 *
 * Four vertical zones: AttentionQueue (hero) -> KpiStrip -> Evidence rows
 * (RevenueChart + ExpiryHeatmap, then InventoryTable + BranchListRollup)
 * -> DashboardFooterBar. Spec:
 * docs/superpowers/specs/2026-04-21-home-dashboard-action-center-design.md
 *
 * All data bindings use existing SWR hooks -- no new endpoints.
 * Golden-Path telemetry (#398/#399) retained via trackFirstDashboardView.
 */

import { useEffect, useMemo, useState } from "react";
import { Download, Plus } from "lucide-react";
import { useSession } from "@/lib/auth-bridge";

import {
  AttentionQueue,
  KpiStrip,
  DashboardFooterBar,
  BranchListRollup,
  RevenueChart,
  ChannelDonut,
  InventoryTable,
  ExpiryHeatmap,
  type KpiPill,
} from "@/components/dashboard/new";
import { DashboardShell } from "@/components/dashboard-v2/shell";
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
import { useSites } from "@/hooks/use-sites";
import { buildBranchRollup } from "@/lib/branch-rollup";
import { trackFirstDashboardView } from "@/lib/analytics-events";
import type {
  AnomalyCard,
  ExpiryExposureTier,
  KPISparkline,
  KPISummary,
  PipelineHealth,
  TimeSeriesPoint,
} from "@/types/api";
import type { ReorderAlert } from "@/types/inventory";

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

// The attention-queue/branch-rollup libs were authored against loose
// payload shapes that predate the typed hook responses. These pure mappers
// adapt the real hook data without touching lib or hook types.
const TIER_DAYS: Record<ExpiryExposureTier["tier"], number> = {
  "30d": 30,
  "60d": 60,
  "90d": 90,
};

function exposureTiersToBuckets(
  tiers: ExpiryExposureTier[] | undefined,
): Array<{ bucket: string; days_out: number; exposure_egp: number; batch_count: number }> {
  if (!tiers?.length) return [];
  return tiers.map((t) => ({
    bucket: t.tier,
    days_out: TIER_DAYS[t.tier] ?? 90,
    exposure_egp: t.total_egp ?? 0,
    batch_count: t.batch_count ?? 0,
  }));
}

function aggregateExposureTotal(
  tiers: ExpiryExposureTier[] | undefined,
): { total_egp: number } | undefined {
  if (!tiers?.length) return undefined;
  return { total_egp: tiers.reduce((s, t) => s + (t.total_egp ?? 0), 0) };
}

function reorderAlertsToRows(
  rows: ReorderAlert[] | undefined,
): Array<{
  drug_code: string;
  drug_name: string;
  on_hand: number;
  reorder_point: number;
  site_name: string;
}> {
  if (!rows?.length) return [];
  return rows.map((r) => ({
    drug_code: r.drug_code,
    drug_name: r.drug_name,
    on_hand: r.current_quantity,
    reorder_point: r.reorder_point,
    site_name: r.site_name,
  }));
}

function anomalyCardsToRows(
  cards: AnomalyCard[] | undefined,
): Array<{ id: string; title: string; severity: string; detected_at?: string }> {
  if (!cards?.length) return [];
  // AnomalyCard.kind ("up"/"down"/"info") maps loosely to severity bands.
  return cards.map((c) => ({
    id: String(c.id),
    title: c.title,
    severity: c.kind === "down" ? "amber" : c.kind === "up" ? "blue" : "blue",
  }));
}

// PipelineHealth doesn't expose a single roll-up status -- derive it from
// node states so the footer chip turns red/amber/green appropriately.
function derivePipelineStatus(pipeline: PipelineHealth | undefined): string {
  if (!pipeline) return "unknown";
  const nodes = pipeline.nodes ?? [];
  if (nodes.some((n) => n.status === "failed")) return "failed";
  if (nodes.some((n) => n.status === "running")) return "running";
  if (nodes.some((n) => n.status === "pending")) return "pending";
  return "success";
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
  const { data: revenueForecast, isLoading: revenueLoading } =
    useRevenueForecast(periodToApi[period]);
  const { data: channels, isLoading: channelsLoading } = useChannels();
  const { data: reorder, isLoading: reorderLoading } = useReorderAlerts();
  const { data: expiryCalendar, isLoading: calendarLoading } = useExpiryCalendar();
  const { data: expiryExposure, isLoading: exposureLoading } = useExpiryExposure();
  const { data: anomalies, isLoading: anomaliesLoading } = useAnomalyCards(10);
  const { data: pipeline, isLoading: pipelineLoading } = usePipelineHealth();
  const { data: sites, isLoading: sitesLoading } = useSites();

  const summary = dashboard?.kpi;
  const syncedAgo = relativeTime(pipeline?.last_run?.at);

  const pills: KpiPill[] = useMemo(() => {
    if (!summary) return [];
    const momDir: KpiPill["deltaDir"] =
      (summary.mom_growth_pct ?? 0) > 0.1 ? "up"
      : (summary.mom_growth_pct ?? 0) < -0.1 ? "down"
      : "flat";
    const stockDir: KpiPill["deltaDir"] =
      (summary.stock_risk_delta ?? 0) <= 0 ? "up" : "down";
    return [
      {
        id: "revenue",
        label: "Total Revenue",
        value: formatEgp(summary.period_gross ?? summary.mtd_gross ?? 0),
        deltaDir: momDir,
        deltaText: `${Math.abs(summary.mom_growth_pct ?? 0).toFixed(1)}%`,
        sub: "vs last month",
        sparkline: sparklineFor("revenue", summary),
        href: "/sales-summary",
      },
      {
        id: "orders",
        label: "Orders",
        value: formatInt(summary.period_transactions ?? 0),
        deltaDir: "up",
        deltaText: `${formatInt(summary.daily_transactions ?? 0)} today`,
        sub: `${formatInt(summary.period_customers ?? 0)} customers`,
        sparkline: sparklineFor("orders", summary),
        href: "/sales-summary?tab=orders",
      },
      {
        id: "stock",
        label: "Stock Risk",
        value: formatInt(summary.stock_risk_count ?? 0),
        valueSuffix: "SKUs",
        deltaDir: stockDir,
        deltaText:
          summary.stock_risk_delta != null
            ? `${summary.stock_risk_delta > 0 ? "+" : ""}${summary.stock_risk_delta} new`
            : "needing reorder",
        sub: "needing reorder",
        sparkline: sparklineFor("stock_risk", summary),
        href: "/inventory?filter=below-reorder",
      },
      {
        id: "expiry",
        label: "Expiry Exposure",
        value: formatEgp(summary.expiry_exposure_egp ?? 0),
        deltaDir: "down",
        deltaText: "30-day window",
        sub: `${formatInt(summary.expiry_batch_count ?? 0)} batches`,
        sparkline: sparklineFor("expiry_exposure", summary),
        href: "/expiry",
      },
    ];
  }, [summary]);

  // Feed branch-rollup the tier-derived buckets (lib expects `exposure_egp`
  // per bucket; raw calendar-by-day lacks EGP). Per-site expiry isn't in
  // the tier payload so site expiry exposure will show zero until #506
  // exposes a site_code breakdown -- accepted by spec for this task.
  const rollupCalendar = useMemo(
    () => exposureTiersToBuckets(expiryExposure),
    [expiryExposure],
  );
  const rollupReorder = useMemo(
    () => reorderAlertsToRows(reorder),
    [reorder],
  );
  const branchRollup = useMemo(
    () => buildBranchRollup({ sites, reorder: rollupReorder, calendar: rollupCalendar }),
    [sites, rollupReorder, rollupCalendar],
  );

  const queueLoading =
    reorderLoading ||
    calendarLoading ||
    exposureLoading ||
    anomaliesLoading ||
    pipelineLoading;

  const pipelineSummary = useMemo(() => {
    if (!pipeline) return null;
    const gatesTotal = pipeline.gates?.total ?? 0;
    const testsTotal = pipeline.tests?.total ?? 0;
    const gatesPassed = pipeline.gates?.passed ?? 0;
    const testsPassed = pipeline.tests?.passed ?? 0;
    const checksTotal = gatesTotal + testsTotal;
    const checksFailed =
      (gatesTotal - gatesPassed) + (testsTotal - testsPassed);
    return {
      status: derivePipelineStatus(pipeline),
      lastRunAt: pipeline.last_run?.at ?? undefined,
      checksTotal: checksTotal > 0 ? checksTotal : undefined,
      checksFailed: checksTotal > 0 ? Math.max(0, checksFailed) : undefined,
    };
  }, [pipeline]);

  return (
    <DashboardShell
      activeHref="/dashboard"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Overview" },
      ]}
    >
      <div className="page">
        <header className="flex flex-wrap items-end gap-5 mb-6">
          <div className="flex-1 min-w-[320px]">
            <div className="text-sm text-ink-secondary flex items-center gap-2 flex-wrap">
              Good morning, {firstName} -- here&apos;s the pulse for{" "}
              <b className="text-ink-primary">{todayLabel()}</b>
              <LiveBadge label={`Synced ${syncedAgo}`} />
            </div>
            <h1 className="text-3xl font-bold tracking-tight mt-1">
              Daily operations overview
            </h1>
          </div>
          <PageActions period={period} onPeriodChange={setPeriod} />
        </header>

        {/* Phase 2 Golden-Path (#398) retained -- strips self-hide when complete. */}
        <div className="flex flex-col gap-4 mb-5">
          <OnboardingStrip />
          <FirstInsightCard />
        </div>

        {/* ZONE 1 -- Action */}
        <AttentionQueue
          inputs={{
            calendar: rollupCalendar,
            exposure: aggregateExposureTotal(expiryExposure),
            reorder: rollupReorder,
            anomalies: anomalyCardsToRows(anomalies),
            pipeline: pipeline
              ? {
                  last_run: pipeline.last_run
                    ? { status: derivePipelineStatus(pipeline), at: pipeline.last_run.at }
                    : null,
                  checks_failed: pipelineSummary?.checksFailed ?? 0,
                }
              : null,
          }}
          loading={queueLoading}
          syncedLabel={`Synced ${syncedAgo}`}
        />

        {/* ZONE 2 -- Status */}
        <div className="mt-5">
          <KpiStrip pills={pills} loading={kpiLoading || !summary} />
        </div>

        {/* ZONE 3 Row A -- Trend + pharma-critical */}
        <section className="grid grid-cols-1 xl:grid-cols-[2fr_1fr] gap-4 mt-5">
          <RevenueChart data={revenueForecast} loading={revenueLoading} mode="Revenue" />
          <ExpiryHeatmap
            calendar={expiryCalendar}
            exposure={expiryExposure}
            loading={calendarLoading || exposureLoading}
          />
        </section>

        {/* ZONE 3 Row B -- Ops evidence */}
        <section className="grid grid-cols-1 xl:grid-cols-[2fr_1fr] gap-4 mt-5">
          <InventoryTable data={reorder} loading={reorderLoading} branches={[]} />
          <BranchListRollup rows={branchRollup} loading={sitesLoading} />
        </section>

        {/* ZONE 4 -- Plumbing */}
        <DashboardFooterBar
          pipeline={pipelineSummary}
          channelsSlot={<ChannelDonut data={channels} loading={channelsLoading} />}
        />
      </div>
    </DashboardShell>
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
        className="h-11 md:h-9 px-3.5 rounded-lg border border-border/60 text-[13px] inline-flex items-center gap-2 hover:bg-elevated/60
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        <Download className="w-3.5 h-3.5" aria-hidden />
        Export
      </button>
      <button
        type="button"
        className="h-11 md:h-9 px-3.5 rounded-lg bg-accent text-page font-semibold text-[13px] inline-flex items-center gap-2 hover:bg-accent-strong
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      >
        <Plus className="w-3.5 h-3.5" aria-hidden />
        New report
      </button>
    </div>
  );
}
