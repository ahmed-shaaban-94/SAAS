"use client";

import { useHealthDistribution, useAtRiskCustomers } from "@/hooks/use-customer-health";
import { formatCurrency } from "@/lib/formatters";
import { ErrorRetry } from "@/components/error-retry";
import type { CustomerHealthScore, HealthDistribution } from "@/types/api";

const BAND_COLORS: Record<string, string> = {
  Thriving: "bg-emerald-500",
  Healthy: "bg-green-400",
  "Needs Attention": "bg-yellow-400",
  "At Risk": "bg-orange-500",
  Critical: "bg-red-500",
};

const BAND_TEXT: Record<string, string> = {
  Thriving: "text-emerald-500",
  Healthy: "text-green-400",
  "Needs Attention": "text-yellow-400",
  "At Risk": "text-orange-500",
  Critical: "text-red-500",
};

function DistributionBar({ dist }: { dist: HealthDistribution }) {
  const bands = [
    { label: "Thriving", count: dist.thriving },
    { label: "Healthy", count: dist.healthy },
    { label: "Needs Attention", count: dist.needs_attention },
    { label: "At Risk", count: dist.at_risk },
    { label: "Critical", count: dist.critical },
  ];

  return (
    <div>
      <div className="flex h-6 rounded-full overflow-hidden mb-3">
        {bands.map((b) =>
          b.count > 0 ? (
            <div
              key={b.label}
              className={`${BAND_COLORS[b.label]} transition-all`}
              style={{ width: `${(b.count / dist.total) * 100}%` }}
              title={`${b.label}: ${b.count}`}
              role="meter"
              aria-label={`${b.label}: ${b.count} customers`}
              aria-valuenow={b.count}
              aria-valuemin={0}
              aria-valuemax={dist.total}
            />
          ) : null,
        )}
      </div>
      <div className="flex flex-wrap gap-4 text-sm">
        {bands.map((b) => (
          <div key={b.label} className="flex items-center gap-1.5">
            <span className={`w-3 h-3 rounded-full ${BAND_COLORS[b.label]}`} />
            <span className="text-muted-foreground">{b.label}:</span>
            <span className="font-medium">{b.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AtRiskTable({ customers }: { customers: CustomerHealthScore[] }) {
  if (!customers.length) {
    return <p className="text-sm text-muted-foreground">No at-risk customers found.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-muted-foreground">
            <th className="text-left py-2 font-medium">Customer</th>
            <th className="text-right py-2 font-medium">Score</th>
            <th className="text-left py-2 font-medium">Band</th>
            <th className="text-right py-2 font-medium">Last Purchase</th>
            <th className="text-right py-2 font-medium">Revenue (3m)</th>
            <th className="text-left py-2 font-medium">Trend</th>
          </tr>
        </thead>
        <tbody>
          {customers.map((c) => (
            <tr key={c.customer_key} className="border-b border-border/50">
              <td className="py-2">{c.customer_name}</td>
              <td className="py-2 text-right font-mono">{c.health_score}</td>
              <td className="py-2">
                <span className={`text-xs font-medium ${BAND_TEXT[c.health_band] || ""}`}>
                  {c.health_band}
                </span>
              </td>
              <td className="py-2 text-right">{c.recency_days}d ago</td>
              <td className="py-2 text-right">{formatCurrency(c.monetary_3m)}</td>
              <td className="py-2">
                <span
                  className={
                    c.trend === "improving"
                      ? "text-emerald-500"
                      : c.trend === "declining"
                        ? "text-red-500"
                        : "text-muted-foreground"
                  }
                >
                  {c.trend}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function HealthDashboard() {
  const { data: dist, isLoading: distLoading, error: distError } = useHealthDistribution();
  const { data: atRisk, isLoading: riskLoading, error: riskError } = useAtRiskCustomers(15);

  if (distLoading || riskLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 animate-pulse">
        <div className="h-6 bg-muted rounded w-1/3 mb-4" />
        <div className="h-6 bg-muted rounded mb-3" />
        <div className="h-40 bg-muted rounded" />
      </div>
    );
  }

  if (distError || riskError) return <ErrorRetry title="Failed to load customer health data" />;

  return (
    <div className="rounded-lg border border-border bg-card p-6 space-y-6">
      <h3 className="text-lg font-semibold">Customer Health</h3>

      {dist && <DistributionBar dist={dist} />}

      <div>
        <h4 className="text-sm font-medium mb-3 text-muted-foreground">
          At-Risk Customers ({atRisk?.length || 0})
        </h4>
        {atRisk && <AtRiskTable customers={atRisk} />}
      </div>
    </div>
  );
}
