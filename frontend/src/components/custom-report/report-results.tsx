"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Download } from "lucide-react";
import { CHART_COLORS } from "@/lib/constants";
import { friendlyColumnLabel, type ChartType } from "./report-config";
import type { ExploreResult } from "@/types/api";

interface ReportResultsProps {
  result: ExploreResult;
  chartType: ChartType;
}

function toChartData(result: ExploreResult): Record<string, unknown>[] {
  return result.rows.map((row) => {
    const obj: Record<string, unknown> = {};
    result.columns.forEach((col, i) => {
      obj[col] = row[i];
    });
    return obj;
  });
}

/** Metrics that represent money amounts */
const CURRENCY_COLS = new Set([
  "total_net_sales",
  "total_gross_sales",
  "total_discount",
  "avg_order_value",
]);

function formatCell(value: unknown, colName?: string): string {
  if (value === null || value === undefined) return "\u2014";
  if (typeof value === "number") {
    if (colName && CURRENCY_COLS.has(colName)) {
      return value.toLocaleString("en-EG", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    }
    return value.toLocaleString("en-EG", { maximumFractionDigits: 1 });
  }
  return String(value);
}

function ResultTable({ result }: { result: ExploreResult }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-background">
            {result.columns.map((col) => (
              <th
                key={col}
                className="px-4 py-3 text-left text-xs font-medium text-text-secondary whitespace-nowrap"
              >
                {friendlyColumnLabel(col)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map((row, i) => (
            <tr
              key={i}
              className="border-b border-border last:border-0 hover:bg-divider/50 transition-colors"
            >
              {row.map((cell, j) => (
                <td
                  key={j}
                  className="px-4 py-2.5 text-sm text-text-primary whitespace-nowrap"
                >
                  {formatCell(cell, result.columns[j])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResultBarChart({ result }: { result: ExploreResult }) {
  const chartData = toChartData(result).slice(0, 20);
  const dimCol = result.columns[0];
  const metricCols = result.columns.slice(1);

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
        <XAxis dataKey={dimCol} tick={{ fontSize: 11 }} interval={0} angle={-30} textAnchor="end" height={60} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
          }}
          formatter={(value: number) => value.toLocaleString()}
        />
        {metricCols.map((col, i) => (
          <Bar
            key={col}
            dataKey={col}
            name={friendlyColumnLabel(col)}
            fill={CHART_COLORS[i % CHART_COLORS.length]}
            radius={[4, 4, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

function ResultLineChart({ result }: { result: ExploreResult }) {
  const chartData = toChartData(result);
  const dimCol = result.columns[0];
  const metricCols = result.columns.slice(1);

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
        <XAxis dataKey={dimCol} tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
          }}
          formatter={(value: number) => value.toLocaleString()}
        />
        {metricCols.map((col, i) => (
          <Line
            key={col}
            type="monotone"
            dataKey={col}
            name={friendlyColumnLabel(col)}
            stroke={CHART_COLORS[i % CHART_COLORS.length]}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

function ResultPieChart({ result }: { result: ExploreResult }) {
  const chartData = toChartData(result).slice(0, 10);
  const dimCol = result.columns[0];
  const metricCol = result.columns[1];

  return (
    <ResponsiveContainer width="100%" height={400}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey={metricCol}
          nameKey={dimCol}
          cx="50%"
          cy="50%"
          outerRadius={150}
          label={(entry) => entry[dimCol]}
        >
          {chartData.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(value: number) => value.toLocaleString()} />
      </PieChart>
    </ResponsiveContainer>
  );
}

function downloadCSV(result: ExploreResult) {
  const header = result.columns.map(friendlyColumnLabel).join(",");
  const rows = result.rows.map((row) =>
    row.map((cell) => {
      if (cell === null || cell === undefined) return "";
      if (typeof cell === "string" && cell.includes(",")) return `"${cell}"`;
      return String(cell);
    }).join(","),
  );
  const csv = [header, ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "report.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export function ReportResults({ result, chartType }: ReportResultsProps) {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-5 py-3">
        <span className="text-sm text-text-secondary">
          {result.row_count.toLocaleString()} results
          {result.truncated && " (showing first 500)"}
        </span>
        <button
          onClick={() => downloadCSV(result)}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary hover:border-border-hover transition-colors"
        >
          <Download className="h-3.5 w-3.5" />
          Download CSV
        </button>
      </div>

      {/* Chart */}
      {chartType !== "table" && (
        <div className="p-4">
          {chartType === "bar" && <ResultBarChart result={result} />}
          {chartType === "line" && <ResultLineChart result={result} />}
          {chartType === "pie" && <ResultPieChart result={result} />}
        </div>
      )}

      {/* Table (always shown) */}
      <div className={chartType !== "table" ? "border-t border-border" : ""}>
        <ResultTable result={result} />
      </div>
    </div>
  );
}
