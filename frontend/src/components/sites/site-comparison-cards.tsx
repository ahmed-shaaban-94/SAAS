"use client";

import { useMemo } from "react";
import Link from "next/link";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { RankingItem } from "@/types/api";
import { ProgressBar } from "@/components/shared/progress-bar";
import { formatCurrency } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { useChartTheme } from "@/hooks/use-chart-theme";

interface SiteComparisonCardsProps {
  items: RankingItem[];
  total: number;
}

function RankBadge({ rank }: { rank: number }) {
  const colors =
    rank === 1
      ? "bg-accent/20 text-accent"
      : "bg-divider text-text-secondary";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors}`}
    >
      #{rank}
    </span>
  );
}

export function SiteComparisonCards({ items, total }: SiteComparisonCardsProps) {
  const CHART_THEME = useChartTheme();
  const chartData = useMemo(
    () =>
      items.map((item, i) => ({
        name: item.name,
        value: item.value,
        fill: CHART_COLORS[i % CHART_COLORS.length],
      })),
    [items],
  );

  return (
    <div>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {items.map((site) => (
          <div
            key={site.key}
            className="rounded-lg border border-border bg-card p-6"
          >
            <div className="flex items-start justify-between">
              <div>
                <Link
                  href={`/sites/${site.key}`}
                  className="text-lg font-semibold text-text-primary transition-colors hover:text-accent"
                >
                  {site.name}
                </Link>
                <p className="mt-1 text-2xl font-bold text-accent">
                  {formatCurrency(site.value)}
                </p>
              </div>
              <RankBadge rank={site.rank} />
            </div>
            <div className="mt-4">
              <div className="flex items-center justify-between text-sm text-text-secondary">
                <span>Share of Total</span>
                <span>{site.pct_of_total.toFixed(1)}%</span>
              </div>
              <ProgressBar
                value={site.pct_of_total}
                className="mt-2"
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-lg border border-border bg-card p-6">
        <h3 className="mb-4 text-sm font-medium text-text-secondary">
          Revenue Comparison
        </h3>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 0 }}>
            <XAxis
              type="number"
              tick={{ fill: CHART_THEME.tickFill, fontSize: CHART_THEME.tickFontSize }}
              tickLine={false}
              axisLine={{ stroke: CHART_THEME.axisStroke }}
              tickFormatter={(v) => formatCurrency(v)}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: CHART_THEME.tickFill, fontSize: CHART_THEME.tickFontSize }}
              tickLine={false}
              axisLine={false}
              width={150}
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
            <Bar dataKey="value" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
