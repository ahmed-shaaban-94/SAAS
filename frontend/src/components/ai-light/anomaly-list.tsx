"use client";

import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { useAIAnomalies } from "@/hooks/use-ai-anomalies";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatNumber } from "@/lib/formatters";

const severityStyles: Record<string, string> = {
  high: "bg-growth-red/10 text-growth-red",
  medium: "bg-amber-500/10 text-amber-500",
  low: "bg-blue-500/10 text-blue-500",
};

export function AnomalyList() {
  const { data, error, isLoading } = useAIAnomalies();

  if (isLoading) {
    return <LoadingCard lines={6} className="h-72" />;
  }

  if (error) {
    return (
      <div className="viz-panel rounded-[1.75rem] p-6">
        <p className="text-sm text-growth-red">
          Failed to load anomaly report. Please try again later.
        </p>
      </div>
    );
  }

  if (!data || !data.anomalies || data.anomalies.length === 0) {
    return (
      <EmptyState
        title="No anomalies detected"
        description="All metrics are within expected ranges."
      />
    );
  }

  return (
    <div className="viz-panel rounded-[1.9rem] p-6 sm:p-7">
      <div className="mb-5 flex items-center gap-3">
        <div className="viz-panel-soft flex h-10 w-10 items-center justify-center rounded-2xl">
          <AlertTriangle className="h-4.5 w-4.5 text-amber-500" />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
            Anomalies
          </p>
          <h3 className="mt-2 text-xl font-bold text-text-primary sm:text-2xl">Outlier Report</h3>
        </div>
        <span className="ml-auto text-xs text-text-secondary">
          {data.anomalies.length} of {data.total_checked} checked &middot; {data.period}
        </span>
      </div>
      <div className="space-y-3">
        {data.anomalies.map((anomaly, i) => (
          <div
            key={i}
            className="viz-panel-soft rounded-[1.25rem] p-4 transition-colors hover:border-accent/30"
          >
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                  severityStyles[anomaly.severity] ?? severityStyles.low,
                )}
              >
                {anomaly.severity}
              </span>
              <span className="text-sm font-medium text-text-primary">{anomaly.metric}</span>
              <span className="ml-auto text-xs text-text-secondary">{anomaly.date}</span>
            </div>
            <p className="mt-2 text-sm text-text-secondary">{anomaly.description}</p>
            <p className="mt-1 text-xs text-text-secondary">
              Actual: {formatNumber(anomaly.actual_value)} &middot; Expected:{" "}
              {formatNumber(anomaly.expected_range_low)} &ndash;{" "}
              {formatNumber(anomaly.expected_range_high)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
