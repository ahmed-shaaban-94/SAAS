"use client";

import { useMemo } from "react";
import {
  ComposedChart,
  Area,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { ApiGet } from "@/lib/api-types";

type RevenueForecast = ApiGet<"/api/v1/analytics/revenue-forecast">;

type Mode = "Revenue" | "Orders" | "AOV";

interface RevenueChartProps {
  data?: RevenueForecast;
  loading?: boolean;
  mode?: Mode;
  onModeChange?: (mode: Mode) => void;
}

const MODES: Mode[] = ["Revenue", "Orders", "AOV"];

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `EGP ${(value / 1_000).toFixed(0)}K`;
  return `EGP ${value.toFixed(0)}`;
}

export function RevenueChart({
  data,
  loading,
  mode = "Revenue",
  onModeChange,
}: RevenueChartProps) {
  const { series, targetValue, todayDate, stats, targetStatus, confidence } = useMemo(() => {
    if (!data) {
      return {
        series: [] as Array<{ date: string; actual?: number; forecast?: number; lo?: number; hi?: number }>,
        targetValue: null as number | null,
        todayDate: "",
        stats: null as RevenueForecast["stats"] | null,
        targetStatus: "",
        confidence: null as number | null,
      };
    }
    const merged = new Map<string, { date: string; actual?: number; forecast?: number; lo?: number; hi?: number }>();
    (data.actual ?? []).forEach((p) => {
      merged.set(p.period, { date: p.period, actual: p.value });
    });
    (data.forecast ?? []).forEach((p) => {
      const existing = merged.get(p.date) ?? { date: p.date };
      merged.set(p.date, {
        ...existing,
        forecast: p.value,
        lo: p.ci_low,
        hi: p.ci_high,
      });
    });
    const sorted = Array.from(merged.values()).sort((a, b) => a.date.localeCompare(b.date));
    return {
      series: sorted,
      targetValue: data.target?.value ?? null,
      todayDate: data.today,
      stats: data.stats ?? null,
      targetStatus: data.target?.status ?? "unknown",
      confidence: data.stats?.confidence ?? null,
    };
  }, [data]);

  const thisMonthLabel = stats ? formatEgp(stats.this_period_egp) : "—";
  const deltaPct = stats?.delta_pct;
  const forecastLast = data?.forecast?.[(data.forecast?.length ?? 0) - 1]?.value ?? null;
  const forecastLabel = forecastLast ? formatEgp(forecastLast) : "—";
  const targetLabel = targetValue ? formatEgp(targetValue) : "—";
  const targetStatusLabel =
    targetStatus === "on_track"
      ? "On track"
      : targetStatus === "behind"
        ? "Behind"
        : targetStatus === "ahead"
          ? "Ahead"
          : "—";

  return (
    <div className="rounded-[14px] bg-card border border-border/40 p-6">
      <header className="flex flex-wrap items-center gap-3 mb-4">
        <h3 className="text-[15px] font-semibold">Revenue trend</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">last 30 days · EGP</span>
        <div className="ml-auto flex gap-1" role="tablist" aria-label="Chart metric">
          {MODES.map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={mode === m}
              onClick={() => onModeChange?.(m)}
              className={[
                "px-2.5 py-1 rounded-full text-[12px] border transition",
                "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
                mode === m
                  ? "bg-accent/15 text-accent-strong border-accent/40"
                  : "bg-transparent text-ink-secondary border-border/40 hover:text-ink-primary",
              ].join(" ")}
            >
              {m}
            </button>
          ))}
        </div>
      </header>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <Stat
          label="This month"
          value={thisMonthLabel}
          delta={deltaPct != null ? `▲ ${deltaPct.toFixed(1)}%` : "—"}
          tone="green"
        />
        <Stat
          label="Forecast (MTD + horizon)"
          value={forecastLabel}
          delta={confidence != null ? `${Math.round(confidence * 100)}% confidence` : "—"}
          tone="purple"
        />
        <Stat label="Target" value={targetLabel} delta={targetStatusLabel} tone="dim" />
      </div>

      <div className="flex items-center gap-4 text-xs text-ink-secondary mb-2">
        <Legend color="var(--accent-color)" label="Actual" />
        <Legend color="var(--chart-purple)" label="Forecast" dim />
        <Legend color="var(--text-tertiary)" label="Target" dim />
      </div>

      <div className="w-full h-[240px]" role="img" aria-label="Revenue trend with forecast and target">
        {loading || series.length === 0 ? (
          <div className="w-full h-full rounded-lg bg-elevated/30 animate-pulse" aria-busy="true" />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={series} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent-color)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--accent-color)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="fcBand" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-purple)" stopOpacity={0.18} />
                  <stop offset="100%" stopColor="var(--chart-purple)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(51,80,107,0.25)" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="var(--text-tertiary)"
                tick={{ fontSize: 10, fill: "var(--text-tertiary)" }}
                tickLine={false}
              />
              <YAxis
                stroke="var(--text-tertiary)"
                tick={{ fontSize: 10, fill: "var(--text-tertiary)" }}
                tickLine={false}
                width={48}
                tickFormatter={(v: number) => (v >= 1000 ? `${(v / 1000).toFixed(0)}K` : `${v}`)}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-color)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              {/* Confidence band (rendered behind everything) */}
              <Area
                type="monotone"
                dataKey="hi"
                stroke="none"
                fill="url(#fcBand)"
                activeDot={false}
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="actual"
                stroke="var(--accent-color)"
                strokeWidth={2.5}
                fill="url(#revFill)"
              />
              <Line
                type="monotone"
                dataKey="forecast"
                stroke="var(--chart-purple)"
                strokeWidth={2.5}
                strokeDasharray="5 5"
                dot={false}
              />
              {targetValue !== null && (
                <ReferenceLine
                  y={targetValue}
                  stroke="var(--text-tertiary)"
                  strokeDasharray="4 6"
                  label={{
                    value: `Target ${targetLabel.replace("EGP ", "")}`,
                    position: "right",
                    fill: "var(--text-tertiary)",
                    fontSize: 10,
                  }}
                />
              )}
              {todayDate && (
                <ReferenceLine
                  x={todayDate}
                  stroke="var(--accent-color)"
                  strokeOpacity={0.3}
                  strokeDasharray="2 3"
                  label={{
                    value: "TODAY",
                    position: "insideBottom",
                    fill: "var(--accent-color)",
                    fontSize: 9.5,
                  }}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  delta,
  tone,
}: {
  label: string;
  value: string;
  delta: string;
  tone: "green" | "purple" | "dim";
}) {
  const toneCls =
    tone === "green"
      ? "text-growth-green"
      : tone === "purple"
        ? "text-chart-purple"
        : "text-ink-tertiary";
  const valueCls =
    tone === "purple" ? "text-chart-purple" : tone === "dim" ? "text-ink-secondary" : "";
  return (
    <div>
      <div className="text-xs text-ink-tertiary uppercase tracking-wider">{label}</div>
      <div className={`text-2xl font-bold tabular-nums mt-1 ${valueCls}`}>{value}</div>
      <div className={`text-xs mt-0.5 ${toneCls}`}>{delta}</div>
    </div>
  );
}

function Legend({ color, label, dim }: { color: string; label: string; dim?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="w-3 h-1.5 rounded-sm"
        style={{ background: color, opacity: dim ? 0.5 : 1 }}
        aria-hidden
      />
      {label}
    </span>
  );
}
