/**
 * Chart type registry — maps chart type strings to metadata.
 *
 * Used by the explore results and dashboard tile renderer to offer
 * chart type selection and auto-suggestion.
 */

export type ChartType =
  | "table"
  | "bar"
  | "stacked-bar"
  | "horizontal-bar"
  | "grouped-bar"
  | "line"
  | "area"
  | "stacked-area"
  | "pie"
  | "donut"
  | "scatter"
  | "radar"
  | "funnel"
  | "treemap"
  | "waterfall"
  | "gauge";

export interface ChartTypeInfo {
  type: ChartType;
  label: string;
  /** Minimum dimensions needed */
  minDimensions: number;
  /** Minimum metrics needed */
  minMetrics: number;
  /** Max recommended data points */
  maxDataPoints: number;
}

export const CHART_REGISTRY: ChartTypeInfo[] = [
  { type: "table", label: "Table", minDimensions: 0, minMetrics: 0, maxDataPoints: 10000 },
  { type: "bar", label: "Bar", minDimensions: 1, minMetrics: 1, maxDataPoints: 50 },
  { type: "stacked-bar", label: "Stacked Bar", minDimensions: 1, minMetrics: 2, maxDataPoints: 30 },
  { type: "horizontal-bar", label: "Horizontal Bar", minDimensions: 1, minMetrics: 1, maxDataPoints: 20 },
  { type: "grouped-bar", label: "Grouped Bar", minDimensions: 1, minMetrics: 2, maxDataPoints: 30 },
  { type: "line", label: "Line", minDimensions: 1, minMetrics: 1, maxDataPoints: 365 },
  { type: "area", label: "Area", minDimensions: 1, minMetrics: 1, maxDataPoints: 365 },
  { type: "stacked-area", label: "Stacked Area", minDimensions: 1, minMetrics: 2, maxDataPoints: 365 },
  { type: "pie", label: "Pie", minDimensions: 1, minMetrics: 1, maxDataPoints: 10 },
  { type: "donut", label: "Donut", minDimensions: 1, minMetrics: 1, maxDataPoints: 10 },
  { type: "scatter", label: "Scatter", minDimensions: 0, minMetrics: 2, maxDataPoints: 500 },
  { type: "radar", label: "Radar", minDimensions: 1, minMetrics: 1, maxDataPoints: 10 },
  { type: "funnel", label: "Funnel", minDimensions: 1, minMetrics: 1, maxDataPoints: 8 },
  { type: "treemap", label: "Treemap", minDimensions: 1, minMetrics: 1, maxDataPoints: 50 },
  { type: "waterfall", label: "Waterfall", minDimensions: 1, minMetrics: 1, maxDataPoints: 20 },
  { type: "gauge", label: "Gauge", minDimensions: 0, minMetrics: 1, maxDataPoints: 1 },
];

/**
 * Auto-suggest the best chart type based on selected dimensions and metrics.
 */
export function suggestChartType(
  dimensionCount: number,
  metricCount: number,
  rowCount: number,
): ChartType {
  // Single metric, no dimensions -> gauge
  if (dimensionCount === 0 && metricCount === 1) return "gauge";
  // 2+ metrics, no dimensions -> bar (comparison)
  if (dimensionCount === 0 && metricCount >= 2) return "bar";
  // Time-like dimension with 1 metric -> line
  if (dimensionCount === 1 && metricCount === 1 && rowCount > 10) return "line";
  // 1 dim + 1 metric, few rows -> pie
  if (dimensionCount === 1 && metricCount === 1 && rowCount <= 10) return "pie";
  // 1 dim + 2+ metrics -> stacked bar
  if (dimensionCount === 1 && metricCount >= 2) return "stacked-bar";
  // 2 metrics -> scatter
  if (metricCount >= 2) return "scatter";
  // Default -> bar
  return "bar";
}
