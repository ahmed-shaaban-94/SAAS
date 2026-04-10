"use client";

import { useState } from "react";
import { useActiveAnomalies, acknowledgeAnomaly } from "@/hooks/use-anomalies";
import { formatCurrency } from "@/lib/formatters";
import { useToast } from "@/components/ui/toast";
import type { AnomalyAlertItem } from "@/types/api";

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-500/10 text-red-500 border-red-500/30",
  high: "bg-orange-500/10 text-orange-500 border-orange-500/30",
  medium: "bg-yellow-500/10 text-yellow-500 border-yellow-500/30",
  low: "bg-blue-500/10 text-blue-500 border-blue-500/30",
};

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-500 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-yellow-500 text-black",
  low: "bg-blue-500 text-white",
};

export function AnomalyBanner() {
  const { data: alerts, isLoading, mutate } = useActiveAnomalies(10);
  const { success, error: toastError } = useToast();
  const [expanded, setExpanded] = useState(false);

  if (isLoading || !alerts?.length) return null;

  const handleAcknowledge = async (id: number) => {
    try {
      await acknowledgeAnomaly(id);
      mutate();
      success("Anomaly acknowledged");
    } catch {
      toastError("Failed to acknowledge anomaly");
    }
  };

  return (
    <div role="alert" className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 mb-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left"
        aria-expanded={expanded}
        aria-label={`${alerts.length} anomalies detected. ${expanded ? "Collapse" : "Expand"} details`}
      >
        <div className="flex items-center gap-2">
          <span className="text-amber-500 text-lg">&#9888;</span>
          <span className="font-medium">
            {alerts.length} anomal{alerts.length === 1 ? "y" : "ies"} detected
          </span>
        </div>
        <span className="text-sm text-muted-foreground">
          {expanded ? "Collapse" : "Expand"}
        </span>
      </button>

      {expanded && (
        <div className="mt-3 space-y-2">
          {alerts.map((alert: AnomalyAlertItem) => (
            <div
              key={alert.id}
              className={`flex items-center justify-between rounded-md border p-3 ${SEVERITY_STYLES[alert.severity] || ""}`}
            >
              <div className="flex items-center gap-3">
                <span
                  className={`text-xs px-2 py-0.5 rounded font-medium ${SEVERITY_BADGE[alert.severity] || ""}`}
                >
                  {alert.severity.toUpperCase()}
                </span>
                <div>
                  <span className="font-medium text-sm">{alert.metric}</span>
                  <span className="text-xs text-muted-foreground ml-2">
                    {alert.direction === "spike" ? "above" : "below"} expected
                  </span>
                </div>
                <div className="text-xs">
                  <span>Actual: {formatCurrency(alert.actual_value)}</span>
                  <span className="mx-1">|</span>
                  <span>Expected: {formatCurrency(alert.expected_value)}</span>
                </div>
              </div>
              <button
                onClick={() => handleAcknowledge(alert.id)}
                className="text-xs px-2 py-1 rounded border border-border hover:bg-accent transition-colors"
              >
                Acknowledge
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
