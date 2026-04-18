"use client";

import { useTopProducts } from "@/hooks/use-top-products";
import { useOriginBreakdown } from "@/hooks/use-origin-breakdown";
import { useFilters } from "@/contexts/filter-context";
import { SummaryStats } from "@/components/shared/summary-stats";
import { RankingChart } from "@/components/shared/ranking-chart";
import { RankingTableLinked } from "@/components/shared/ranking-table-linked";
import CsvExportButton from "@/components/shared/csv-export-button";
import { EmptyState } from "@/components/empty-state";
import { UploadDataAction } from "@/components/shared/empty-state-actions";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { RankingTableSkeleton } from "@/components/ui/table-skeleton";
import { formatCurrency, formatCompact, formatNumber } from "@/lib/formatters";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";

export function ProductOverview() {
  const { filters } = useFilters();
  const { data, error, isLoading } = useTopProducts(filters);
  const { data: originData } = useOriginBreakdown(filters);
  const CHART_THEME = useChartTheme();

  if (isLoading) {
    return (
      <div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <LoadingCard key={i} lines={2} />
          ))}
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <LoadingCard lines={8} className="h-96" />
          <div className="rounded-xl border border-border bg-card p-5">
            <RankingTableSkeleton rows={8} />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorRetry
        title="Failed to load product data"
        description="Failed to load data. Please try again."
      />
    );
  }

  if (!data?.items?.length) {
    return (
      <EmptyState
        title="No product data available"
        description="Try adjusting your filters or upload sales data to see product analytics."
        action={<UploadDataAction />}
      />
    );
  }

  const topProduct = data.items[0];

  const stats = [
    { label: "Total Revenue", value: formatCurrency(data.total) },
    { label: "Product Count", value: formatNumber(data.items.length) },
    { label: "Top Product", value: topProduct.name },
    { label: "Top Product Revenue", value: formatCurrency(topProduct.value) },
  ];

  const exportData = data.items.map((item) => ({
    Rank: item.rank,
    Product: item.name,
    Revenue: item.value,
    "% of Total": item.pct_of_total,
  }));

  return (
    <div>
      <SummaryStats stats={stats} />
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="viz-panel rounded-[1.7rem] p-6">
          <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.2em] text-text-secondary">
            Top Products by Revenue
          </h3>
          <RankingChart items={data.items.slice(0, 10)} />
        </div>
        <div className="viz-panel rounded-[1.7rem] p-6">
          <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.2em] text-text-secondary">
            Revenue by Origin
          </h3>
          {originData && originData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={originData.length * 56}>
                <BarChart data={originData} layout="vertical" margin={{ left: 10, right: 90 }}>
                  <XAxis
                    type="number"
                    tick={{ fill: CHART_THEME.tickFill, fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => formatCompact(v)}
                  />
                  <YAxis
                    type="category"
                    dataKey="origin"
                    tick={{ fill: CHART_THEME.tickFill, fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                    width={90}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: CHART_THEME.tooltipBg,
                      border: `1px solid ${CHART_THEME.tooltipBorder}`,
                      borderRadius: "8px",
                      color: CHART_THEME.tooltipColor,
                    }}
                    formatter={(value: number) => [formatCurrency(value), "Revenue"]}
                  />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={28}>
                    {originData.map((_, i) => (
                      <Cell key={i} fill={CHART_THEME.palette[i % CHART_THEME.palette.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-3 flex flex-wrap gap-3 text-xs text-text-secondary">
                {originData.map((d, i) => (
                  <span key={d.origin} className="flex items-center gap-1.5">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: CHART_THEME.palette[i % CHART_THEME.palette.length] }}
                    />
                    {d.origin}: {d.pct}% ({d.product_count} products)
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div className="flex h-40 items-center justify-center text-sm text-text-secondary">
              No origin data available
            </div>
          )}
        </div>
        <div className="viz-panel rounded-[1.7rem] p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Product Rankings
            </h3>
            <CsvExportButton data={exportData} filename="products" />
          </div>
          <RankingTableLinked items={data.items} entityLabel="Product" hrefPrefix="/products" />
        </div>
      </div>
    </div>
  );
}
