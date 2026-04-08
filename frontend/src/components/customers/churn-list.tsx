"use client";

import { useState } from "react";
import { useChurnPredictions } from "@/hooks/use-churn-prediction";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { formatCurrency } from "@/lib/formatters";

const RISK_COLORS: Record<string, string> = {
  high: "bg-red-500/10 text-red-500",
  medium: "bg-yellow-500/10 text-yellow-500",
  low: "bg-green-500/10 text-green-500",
};

export function ChurnList() {
  const [filter, setFilter] = useState<string | undefined>(undefined);
  const { data, isLoading, error } = useChurnPredictions(filter);

  if (isLoading && data.length === 0) return <LoadingCard className="h-64" />;
  if (error) return <ErrorRetry title="Failed to load churn predictions" />;

  const highCount = data.filter((c) => c.risk_level === "high").length;
  const medCount = data.filter((c) => c.risk_level === "medium").length;

  return (
    <div className="space-y-4">
      {/* Risk filter */}
      <div className="flex gap-2">
        {[undefined, "high", "medium", "low"].map((level) => (
          <button
            key={level ?? "all"}
            onClick={() => setFilter(level)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              filter === level
                ? "bg-accent text-white"
                : "border border-border text-text-secondary hover:bg-divider"
            }`}
          >
            {level ? `${level.charAt(0).toUpperCase() + level.slice(1)} Risk` : "All"}
          </button>
        ))}
      </div>

      {/* Summary */}
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-3">
          <p className="text-xs text-text-secondary">High Risk</p>
          <p className="text-xl font-bold text-red-500">{highCount}</p>
        </div>
        <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-3">
          <p className="text-xs text-text-secondary">Medium Risk</p>
          <p className="text-xl font-bold text-yellow-500">{medCount}</p>
        </div>
        <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-3">
          <p className="text-xs text-text-secondary">Low Risk</p>
          <p className="text-xl font-bold text-green-500">{data.length - highCount - medCount}</p>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-secondary">
              <th className="px-4 py-3 font-medium">Customer</th>
              <th className="px-4 py-3 font-medium">Risk</th>
              <th className="px-4 py-3 font-medium">Churn Prob.</th>
              <th className="px-4 py-3 font-medium">Health</th>
              <th className="px-4 py-3 font-medium">Recency</th>
              <th className="px-4 py-3 font-medium">Trend</th>
              <th className="px-4 py-3 font-medium text-right">Revenue (3m)</th>
            </tr>
          </thead>
          <tbody>
            {data.map((c) => (
              <tr key={c.customer_key} className="border-b border-border/50 hover:bg-muted/50">
                <td className="px-4 py-2 font-medium text-text-primary max-w-[200px] truncate">{c.customer_name}</td>
                <td className="px-4 py-2">
                  <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${RISK_COLORS[c.risk_level]}`}>
                    {c.risk_level}
                  </span>
                </td>
                <td className="px-4 py-2 text-xs font-mono font-bold text-text-primary">
                  {(c.churn_probability * 100).toFixed(0)}%
                </td>
                <td className="px-4 py-2 text-xs text-text-secondary">{c.health_band}</td>
                <td className="px-4 py-2 text-xs text-text-secondary">{c.recency_days}d</td>
                <td className="px-4 py-2 text-xs text-text-secondary">{c.trend}</td>
                <td className="px-4 py-2 text-right text-xs font-mono text-text-primary">
                  {formatCurrency(c.monetary_3m)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
