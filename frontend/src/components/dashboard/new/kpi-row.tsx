"use client";

import { DollarSign, ShoppingCart, AlertTriangle, Clock } from "lucide-react";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { KPISummary, TimeSeriesPoint } from "@/types/api";
import { KpiCard } from "@/components/dashboard/new/kpi-card";
import { cn } from "@/lib/utils";

export interface KpiRowProps {
  /** Override the hook — useful for Storybook / tests. */
  summary?: KPISummary;
  className?: string;
}

function useDashboardSummary() {
  const { data, error, isLoading } = useSWR<KPISummary>(
    "/api/v1/analytics/summary",
    () => fetchAPI<KPISummary>("/api/v1/analytics/summary"),
  );
  return { data, error, isLoading };
}

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `EGP ${Math.round(value / 1_000)}K`;
  return `EGP ${Math.round(value)}`;
}

function formatCount(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return Math.round(value).toString();
}

function findSparkline(
  summary: KPISummary,
  metric: string,
): TimeSeriesPoint[] {
  return (
    summary.sparklines?.find((s) => s.metric === metric)?.points ?? []
  );
}

/**
 * Four-card KPI row for the dashboard header (#503). Wires
 * ``/analytics/summary`` into the generic ``KpiCard`` leaves.
 *
 * Layout: Revenue · Orders · Stock Risk · Expiry Exposure.
 * Fields are optional in the response — ``stock_risk_count`` /
 * ``expiry_exposure_egp`` default to 0 when the tenant's plan doesn't
 * include the auxiliary modules. The card still renders (shows zero),
 * so the four-column grid stays stable.
 */
export function KpiRow({ summary, className }: KpiRowProps) {
  const hookResult = useDashboardSummary();
  const data = summary !== undefined ? summary : hookResult.data;

  if (!data) {
    // Parent decides its own loading skeleton; row stays silent.
    return null;
  }

  const revenueSpark = findSparkline(data, "revenue");
  const ordersSpark = findSparkline(data, "orders");
  const stockSpark = findSparkline(data, "stock_risk");
  const expirySpark = findSparkline(data, "expiry_exposure");

  const stockRisk = data.stock_risk_count ?? 0;
  const expiryEgp = Number(data.expiry_exposure_egp ?? 0);

  return (
    <div
      className={cn(
        "grid grid-cols-2 gap-3 sm:grid-cols-2 lg:grid-cols-4",
        className,
      )}
    >
      <KpiCard
        label="Revenue"
        value={formatEgp(Number(data.period_gross ?? data.today_gross))}
        deltaPct={data.mom_growth_pct}
        sublabel="MTD"
        sparkline={revenueSpark}
        icon={DollarSign}
        sparklineLabel="Revenue trend (11 days)"
      />
      <KpiCard
        label="Orders"
        value={formatCount(data.period_transactions ?? data.daily_transactions)}
        sublabel="Transactions"
        sparkline={ordersSpark}
        icon={ShoppingCart}
        sparklineLabel="Orders trend (11 days)"
      />
      <KpiCard
        label="Stock Risk"
        value={formatCount(stockRisk)}
        deltaPct={data.stock_risk_delta ?? null}
        sublabel="SKUs below reorder"
        sparkline={stockSpark}
        tone={stockRisk > 0 ? "warning" : "default"}
        icon={AlertTriangle}
        sparklineLabel="Stock risk trend"
      />
      <KpiCard
        label="Expiry Exposure"
        value={formatEgp(expiryEgp)}
        sublabel={`${data.expiry_batch_count ?? 0} batch${
          (data.expiry_batch_count ?? 0) === 1 ? "" : "es"
        }`}
        sparkline={expirySpark}
        tone={expiryEgp > 0 ? "danger" : "default"}
        icon={Clock}
        sparklineLabel="Expiry exposure trend"
      />
    </div>
  );
}
