"use client";

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
  const chartData = items.map((item, i) => ({
    name: item.name,
    value: item.value,
    fill: CHART_COLORS[i % CHART_COLORS.length],
  }));

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
                <h3 className="text-lg font-semibold text-text-primary">
                  {site.name}
                </h3>
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
              tick={{ fill: "#A8B3BD", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#30363D" }}
              tickFormatter={(v) => formatCurrency(v)}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: "#A8B3BD", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={150}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#161B22",
                border: "1px solid #30363D",
                borderRadius: "8px",
                color: "#E6EDF3",
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
