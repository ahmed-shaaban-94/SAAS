"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Download } from "lucide-react";
import { useChartTheme } from "@/hooks/use-chart-theme";
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

const CURRENCY_COLS = new Set([
  "total_net_sales",
  "total_gross_sales",
  "total_discount",
  "avg_order_value",
]);

const PLAIN_INT_COLS = new Set([
  "year",
  "month",
  "quarter",
  "year_month",
  "year_quarter",
  "day_of_week",
]);

function formatCell(value: unknown, colName?: string): string {
  if (value === null || value === undefined) return "\u2014";
  if (typeof value !== "number") return String(value ?? "");
  if (colName && PLAIN_INT_COLS.has(colName)) return String(value);
  if (colName && CURRENCY_COLS.has(colName)) {
    return value.toLocaleString("en-EG", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  return value.toLocaleString("en-EG", { maximumFractionDigits: 1 });
}

function ResultTable({ result }: { result: ExploreResult }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-background/50">
            {result.columns.map((col) => (
              <th
                key={col}
                className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-text-secondary whitespace-nowrap"
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
              className="border-b border-border/70 last:border-0 transition-colors hover:bg-background/50"
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
  const theme = useChartTheme();
  const chartData = toChartData(result).slice(0, 20);
  const dimCol = result.columns[0];
  const metricCols = result.columns.slice(1);

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
        <XAxis dataKey={dimCol} tick={{ fontSize: 11, fill: theme.tickFill }} interval={0} angle={-30} textAnchor="end" height={60} />
        <YAxis tick={{ fontSize: 11, fill: theme.tickFill }} />
        <Tooltip
          contentStyle={{
            backgroundColor: theme.tooltipBg,
            border: `1px solid ${theme.tooltipBorder}`,
            borderRadius: "8px",
          }}
          formatter={(value: number) => value.toLocaleString()}
        />
        {metricCols.map((col, i) => (
          <Bar
            key={col}
            dataKey={col}
            name={friendlyColumnLabel(col)}
            fill={theme.palette[i % theme.palette.length]}
            radius={[4, 4, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

function ResultLineChart({ result }: { result: ExploreResult }) {
  const theme = useChartTheme();
  const chartData = toChartData(result);
  const dimCol = result.columns[0];
  const metricCols = result.columns.slice(1);

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
        <XAxis dataKey={dimCol} tick={{ fontSize: 11, fill: theme.tickFill }} />
        <YAxis tick={{ fontSize: 11, fill: theme.tickFill }} />
        <Tooltip
          contentStyle={{
            backgroundColor: theme.tooltipBg,
            border: `1px solid ${theme.tooltipBorder}`,
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
            stroke={theme.palette[i % theme.palette.length]}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

function ResultPieChart({ result }: { result: ExploreResult }) {
  const theme = useChartTheme();
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
          label={(entry) => String(entry[dimCol] ?? "")}
        >
          {chartData.map((_, i) => (
            <Cell key={i} fill={theme.palette[i % theme.palette.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number) => value.toLocaleString()}
          contentStyle={{
            backgroundColor: theme.tooltipBg,
            border: `1px solid ${theme.tooltipBorder}`,
            borderRadius: "8px",
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

function downloadCSV(result: ExploreResult) {
  const header = result.columns.map(friendlyColumnLabel).join(",");
  const rows = result.rows.map((row) =>
    row
      .map((cell) => {
        if (cell === null || cell === undefined) return "";
        if (
          typeof cell === "string" &&
          (cell.includes(",") || cell.includes('"') || cell.includes("\n"))
        ) {
          return `"${cell.replace(/"/g, '""')}"`;
        }
        return String(cell);
      })
      .join(","),
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
    <div className="viz-panel overflow-hidden rounded-[1.75rem]">
      <div className="flex items-center justify-between border-b border-border px-5 py-3">
        <span className="text-sm text-text-secondary">
          {result.row_count.toLocaleString()} results
          {result.truncated && " (showing first 500)"}
        </span>
        <button
          onClick={() => downloadCSV(result)}
          className="viz-panel-soft flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-text-secondary transition-colors hover:text-accent"
        >
          <Download className="h-3.5 w-3.5" />
          Download CSV
        </button>
      </div>

      {chartType !== "table" && (
        <div className="p-4">
          {chartType === "bar" && <ResultBarChart result={result} />}
          {chartType === "line" && <ResultLineChart result={result} />}
          {chartType === "pie" && <ResultPieChart result={result} />}
        </div>
      )}

      <div className={chartType !== "table" ? "border-t border-border" : ""}>
        <ResultTable result={result} />
      </div>
    </div>
  );
}
