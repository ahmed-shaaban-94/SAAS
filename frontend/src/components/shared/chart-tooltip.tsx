"use client";

import { formatCurrency } from "@/lib/formatters";

interface TooltipPayloadItem {
  value: number;
  dataKey?: string;
  name?: string;
  payload?: Record<string, unknown>;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
  /** CSS class for the primary value text (e.g. "text-accent", "text-chart-blue") */
  accentClass?: string;
  /** Custom value formatter. Defaults to formatCurrency. */
  formatValue?: (v: number) => string;
  /** If provided, shows a "Previous: ..." line from a dataKey named "prev" */
  showPrevious?: boolean;
}

/**
 * Shared Recharts tooltip with consistent styling across all chart components.
 *
 * Usage: `<Tooltip content={<ChartTooltip accentClass="text-accent" />} />`
 */
export function ChartTooltip({
  active,
  payload,
  label,
  accentClass = "text-accent",
  formatValue = formatCurrency,
  showPrevious = false,
}: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  const current = payload.find((i) => i.dataKey === "value") ?? payload[0];
  const prev = showPrevious ? payload.find((i) => i.dataKey === "prev") : undefined;

  return (
    <div className="rounded-xl border border-border bg-card/95 px-4 py-3 shadow-xl backdrop-blur-sm">
      {label && (
        <p className="text-xs font-medium text-text-secondary">{String(label)}</p>
      )}
      <p className={`mt-1 text-lg font-bold ${accentClass}`}>
        {formatValue(current?.value ?? 0)}
      </p>
      {prev && prev.value !== undefined && (
        <p className="text-xs text-text-secondary">
          Previous: {formatValue(prev.value)}
        </p>
      )}
    </div>
  );
}
