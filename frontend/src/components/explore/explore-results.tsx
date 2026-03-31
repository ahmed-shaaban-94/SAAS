"use client";

import { useState } from "react";
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
import { Table, BarChart3, LineChartIcon, PieChartIcon, Code } from "lucide-react";
import { cn } from "@/lib/utils";
import { CHART_COLORS } from "@/lib/constants";
import type { ExploreResult } from "@/types/api";

type ViewMode = "table" | "bar" | "line" | "pie" | "sql";

interface ExploreResultsProps {
  result: ExploreResult;
}

const VIEW_OPTIONS: { key: ViewMode; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: "table", label: "Table", icon: Table },
  { key: "bar", label: "Bar", icon: BarChart3 },
  { key: "line", label: "Line", icon: LineChartIcon },
  { key: "pie", label: "Pie", icon: PieChartIcon },
  { key: "sql", label: "SQL", icon: Code },
];

function ResultTable({ result }: { result: ExploreResult }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-background">
            {result.columns.map((col) => (
              <th
                key={col}
                className="px-4 py-3 text-left font-medium text-text-secondary"
              >
                {col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
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
                <td key={j} className="px-4 py-2.5 text-text-primary">
                  {typeof cell === "number"
                    ? cell.toLocaleString("en-EG", { maximumFractionDigits: 2 })
                    : cell ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
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

function ResultBarChart({ result }: { result: ExploreResult }) {
  const chartData = toChartData(result);
  const dimCol = result.columns[0];
  const metricCols = result.columns.slice(1);

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
        <XAxis dataKey={dimCol} tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
          }}
        />
        {metricCols.map((col, i) => (
          <Bar
            key={col}
            dataKey={col}
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
        <XAxis dataKey={dimCol} tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
          }}
        />
        {metricCols.map((col, i) => (
          <Line
            key={col}
            type="monotone"
            dataKey={col}
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
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}

function SqlView({ sql }: { sql: string }) {
  return (
    <pre className="overflow-x-auto rounded-lg bg-background border border-border p-4 text-sm text-text-primary font-mono whitespace-pre-wrap">
      {sql}
    </pre>
  );
}

export function ExploreResults({ result }: ExploreResultsProps) {
  const [view, setView] = useState<ViewMode>("table");

  return (
    <div className="space-y-4">
      {/* View toggle + stats */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 rounded-lg bg-background p-1">
          {VIEW_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setView(opt.key)}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all",
                view === opt.key
                  ? "bg-accent/20 text-accent"
                  : "text-text-secondary hover:text-text-primary",
              )}
            >
              <opt.icon className="h-3.5 w-3.5" />
              {opt.label}
            </button>
          ))}
        </div>
        <span className="text-xs text-text-secondary">
          {result.row_count.toLocaleString()} rows
          {result.truncated && " (truncated)"}
        </span>
      </div>

      {/* Result view */}
      {view === "table" && <ResultTable result={result} />}
      {view === "bar" && <ResultBarChart result={result} />}
      {view === "line" && <ResultLineChart result={result} />}
      {view === "pie" && <ResultPieChart result={result} />}
      {view === "sql" && <SqlView sql={result.sql} />}
    </div>
  );
}
