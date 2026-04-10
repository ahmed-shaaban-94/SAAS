"use client";

import { useSites } from "@/hooks/use-sites";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { formatCurrency } from "@/lib/formatters";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Legend,
} from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { CHART_COLORS } from "@/lib/constants";
import { useEffect, useState } from "react";
import { fetchAPI } from "@/lib/api-client";
import type { SiteDetail } from "@/types/api";

export function RadarComparison() {
  const { filters } = useFilters();
  const { data: ranking, isLoading: rankingLoading } = useSites(filters);
  const [siteDetails, setSiteDetails] = useState<SiteDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const theme = useChartTheme();

  useEffect(() => {
    if (!ranking?.items.length) return;
    setLoading(true);
    Promise.all(
      ranking.items.map((item) =>
        fetchAPI<SiteDetail>(`/api/v1/analytics/sites/${item.key}`).catch(() => null)
      )
    ).then((results) => {
      setSiteDetails(results.filter(Boolean) as SiteDetail[]);
      setLoading(false);
    });
  }, [ranking]);

  if (rankingLoading || loading) return <LoadingCard className="h-72" />;
  if (siteDetails.length < 2) return <EmptyState title="Need at least 2 sites for comparison" />;

  // Normalize values to 0-100 scale for radar
  const metrics = [
    { key: "revenue", label: "Revenue" },
    { key: "transactions", label: "Transactions" },
    { key: "customers", label: "Customers" },
    { key: "staff", label: "Staff" },
    { key: "walk_in", label: "Walk-in %" },
    { key: "insurance", label: "Insurance %" },
  ];

  const getValue = (site: SiteDetail, metricKey: string): number => {
    switch (metricKey) {
      case "revenue": {
        // Use filtered ranking value instead of all-time detail value
        const ri = ranking?.items.find((r) => r.key === site.site_key);
        return ri?.value ?? site.total_net_amount;
      }
      case "transactions": return site.transaction_count;
      case "customers": return site.unique_customers;
      case "staff": return site.unique_staff;
      case "walk_in": return site.walk_in_ratio * 100;
      case "insurance": return site.insurance_ratio * 100;
      default: return 0;
    }
  };

  const maxValues: Record<string, number> = {};
  metrics.forEach((m) => {
    maxValues[m.key] = Math.max(
      ...siteDetails.map((s) => getValue(s, m.key)),
      1
    );
  });

  const radarData = metrics.map((m) => {
    const point: Record<string, string | number> = { metric: m.label };
    siteDetails.forEach((s) => {
      const val = getValue(s, m.key);
      point[s.site_name] = Math.round((val / maxValues[m.key]) * 100);
    });
    return point;
  });

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">Site Comparison Radar</h3>

      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={radarData}>
          <PolarGrid stroke={theme.gridStroke} />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fontSize: 10, fill: theme.tickFill }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={{ fontSize: 8, fill: theme.tickFill }}
          />
          {siteDetails.map((s, i) => (
            <Radar
              key={s.site_key}
              name={s.site_name}
              dataKey={s.site_name}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              fill={CHART_COLORS[i % CHART_COLORS.length]}
              fillOpacity={0.15}
              strokeWidth={2}
            />
          ))}
          <Legend
            wrapperStyle={{ fontSize: "11px" }}
          />
        </RadarChart>
      </ResponsiveContainer>

      {/* Quick stats — use filtered ranking data for revenue (not all-time detail) */}
      <div className="mt-3 grid grid-cols-2 gap-3">
        {siteDetails.map((s, i) => {
          // Use the filtered ranking value if available, otherwise fall back to detail
          const rankingItem = ranking?.items.find((r) => r.key === s.site_key);
          const filteredRevenue = rankingItem?.value ?? s.total_net_amount;
          return (
            <div key={s.site_key} className="rounded-lg border border-border p-3">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                <span className="text-xs font-semibold text-text-primary">{s.site_name}</span>
              </div>
              <div className="grid grid-cols-2 gap-1 text-[10px]">
                <span className="text-text-secondary">Revenue: <span className="text-text-primary">{formatCurrency(filteredRevenue)}</span></span>
                <span className="text-text-secondary">Return Rate: <span className={s.return_rate > 5 ? "text-red-500" : "text-green-500"}>{s.return_rate.toFixed(1)}%</span></span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
