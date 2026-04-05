"use client";

import { friendlyMetricLabel } from "./report-config";
import type { ExploreResult } from "@/types/api";

interface ReportSummaryProps {
  result: ExploreResult;
}

/** Metrics that represent money amounts (formatted with currency) */
const CURRENCY_METRICS = new Set([
  "total_net_sales",
  "total_gross_sales",
  "total_discount",
  "avg_order_value",
]);

/** Metrics where SUM makes sense; the rest get AVG */
const SUM_METRICS = new Set([
  "total_net_sales",
  "total_gross_sales",
  "total_discount",
  "total_quantity",
  "transaction_count",
  "unique_customers",
  "unique_products",
]);

function formatKpiValue(value: number, colName: string): string {
  if (CURRENCY_METRICS.has(colName)) {
    if (Math.abs(value) >= 1_000_000) {
      return `${(value / 1_000_000).toFixed(2)}M`;
    }
    if (Math.abs(value) >= 1_000) {
      return `${(value / 1_000).toFixed(1)}K`;
    }
    return value.toFixed(2);
  }
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toLocaleString("en-EG", { maximumFractionDigits: 1 });
}

function computeKpis(
  result: ExploreResult,
): { label: string; value: string; sublabel: string; colName: string }[] {
  const kpis: { label: string; value: string; sublabel: string; colName: string }[] = [];

  result.columns.forEach((col, colIdx) => {
    // Only summarize numeric metric columns
    const numericValues = result.rows
      .map((row) => row[colIdx])
      .filter((v): v is number => typeof v === "number");

    if (numericValues.length === 0) return;

    const isSummable = SUM_METRICS.has(col);

    if (isSummable) {
      const total = numericValues.reduce((sum, v) => sum + v, 0);
      kpis.push({
        label: friendlyMetricLabel(col),
        value: formatKpiValue(total, col),
        sublabel: "Total",
        colName: col,
      });
    } else {
      const avg =
        numericValues.reduce((sum, v) => sum + v, 0) / numericValues.length;
      kpis.push({
        label: friendlyMetricLabel(col),
        value: formatKpiValue(avg, col),
        sublabel: "Average",
        colName: col,
      });
    }
  });

  return kpis;
}

export function ReportSummary({ result }: ReportSummaryProps) {
  const kpis = computeKpis(result);

  if (kpis.length === 0) return null;

  return (
    <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
      {kpis.map((kpi) => (
        <div
          key={kpi.colName}
          className="rounded-xl border border-border bg-card p-4"
        >
          <p className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
            {kpi.sublabel}
          </p>
          <p className="mt-1 text-2xl font-bold text-text-primary">
            {kpi.value}
          </p>
          <p className="mt-0.5 text-xs text-text-secondary">{kpi.label}</p>
        </div>
      ))}
    </div>
  );
}
