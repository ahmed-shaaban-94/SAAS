"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { SummaryStats } from "@/components/shared/summary-stats";
import { EmptyState } from "@/components/empty-state";
import { formatCurrency, formatCompact } from "@/lib/formatters";
import { useChartTheme } from "@/hooks/use-chart-theme";
import type { SiteDetail } from "@/types/api";

interface SiteDetailViewProps {
  site: SiteDetail;
}

function TrendTooltip(props: Record<string, unknown>) {
  const { active, payload, label } = props;
  const items = payload as Array<{ value: number }> | undefined;
  if (!active || !items?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-card/95 px-4 py-3 shadow-xl backdrop-blur-sm">
      <p className="text-xs font-medium text-text-secondary">{String(label)}</p>
      <p className="mt-1 text-lg font-bold text-accent">
        {formatCurrency(items[0].value)}
      </p>
    </div>
  );
}

export function SiteDetailView({ site }: SiteDetailViewProps) {
  const CHART_THEME = useChartTheme();

  const stats = [
    { label: "Total Net Sales", value: formatCurrency(site.total_net_amount) },
    { label: "Transactions", value: site.transaction_count.toLocaleString() },
    { label: "Unique Customers", value: site.unique_customers.toLocaleString() },
    { label: "Unique Staff", value: site.unique_staff.toLocaleString() },
    { label: "Walk-in Ratio", value: `${(site.walk_in_ratio * 100).toFixed(1)}%` },
    { label: "Insurance Ratio", value: `${(site.insurance_ratio * 100).toFixed(1)}%` },
    { label: "Return Rate", value: `${site.return_rate.toFixed(1)}%` },
  ];

  const trendData = (site.monthly_trend ?? []).map((p) => ({
    month: p.period,
    value: p.value,
  }));

  return (
    <div>
      {/* Summary Stats */}
      <SummaryStats stats={stats} />

      {/* Monthly Trend */}
      <div className="mt-6 rounded-xl border border-border bg-card p-5">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-secondary">
          Monthly Revenue Trend
        </h3>
        {trendData.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={trendData}>
              <defs>
                <linearGradient id="siteGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CHART_THEME.accentColor} stopOpacity={0.4} />
                  <stop offset="100%" stopColor={CHART_THEME.accentColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.gridStroke} vertical={false} />
              <XAxis
                dataKey="month"
                tick={{ fill: CHART_THEME.tickFill, fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fill: CHART_THEME.tickFill, fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => formatCompact(v)}
              />
              <Tooltip content={<TrendTooltip />} />
              <Area
                type="monotone"
                dataKey="value"
                stroke={CHART_THEME.accentColor}
                strokeWidth={2.5}
                fill="url(#siteGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <EmptyState title="No trend data available" />
        )}
      </div>
    </div>
  );
}
