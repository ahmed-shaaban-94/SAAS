"use client";

import { useState } from "react";
import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ComposedChart,
} from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { useScenario, type Adjustment } from "@/hooks/use-scenario";
import { LoadingCard } from "@/components/loading-card";
import { ChartCard } from "@/components/shared/chart-card";
import { formatCurrency } from "@/lib/formatters";
import { Play, RotateCcw, TrendingUp, TrendingDown, Percent } from "lucide-react";

function SliderInput({
  label,
  value,
  onChange,
  min = -50,
  max = 100,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
}) {
  const color = value > 0 ? "text-green-500" : value < 0 ? "text-red-500" : "text-text-secondary";

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-text-primary">{label}</label>
        <span className={`text-sm font-semibold ${color}`}>
          {value > 0 ? "+" : ""}{value}%
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-divider rounded-lg appearance-none cursor-pointer accent-accent"
      />
      <div className="flex justify-between text-xs text-text-tertiary">
        <span>{min}%</span>
        <span>0%</span>
        <span>+{max}%</span>
      </div>
    </div>
  );
}

function ImpactCard({
  label,
  baseline,
  projected,
  change,
  pctChange,
}: {
  label: string;
  baseline: number;
  projected: number;
  change: number;
  pctChange: number;
}) {
  const isPositive = change >= 0;
  const Icon = isPositive ? TrendingUp : TrendingDown;

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">{label}</p>
      <p className="mt-2 text-xl font-bold text-text-primary">{formatCurrency(projected)}</p>
      <div className="mt-1 flex items-center gap-1.5">
        <Icon className={`h-3.5 w-3.5 ${isPositive ? "text-green-500" : "text-red-500"}`} />
        <span className={`text-sm font-medium ${isPositive ? "text-green-500" : "text-red-500"}`}>
          {pctChange > 0 ? "+" : ""}{pctChange}%
        </span>
        <span className="text-xs text-text-tertiary">vs baseline {formatCurrency(baseline)}</span>
      </div>
    </div>
  );
}

export function ScenarioOverview() {
  const [priceChange, setPriceChange] = useState(0);
  const [volumeChange, setVolumeChange] = useState(0);
  const [costChange, setCostChange] = useState(0);
  const [months, setMonths] = useState(6);
  const { result, loading, error, simulate } = useScenario();
  const theme = useChartTheme();

  const handleSimulate = () => {
    const adjustments: Adjustment[] = [];
    if (priceChange !== 0)
      adjustments.push({ parameter: "price", change_type: "percentage", change_value: priceChange });
    if (volumeChange !== 0)
      adjustments.push({ parameter: "volume", change_type: "percentage", change_value: volumeChange });
    if (costChange !== 0)
      adjustments.push({ parameter: "cost", change_type: "percentage", change_value: costChange });

    if (adjustments.length === 0) {
      adjustments.push({ parameter: "price", change_type: "percentage", change_value: 0 });
    }
    simulate(adjustments, months);
  };

  const handleReset = () => {
    setPriceChange(0);
    setVolumeChange(0);
    setCostChange(0);
  };

  return (
    <div className="space-y-6 mt-6">
      {/* Scenario Builder */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Percent className="h-4 w-4 text-accent" />
          Scenario Parameters
        </h3>

        <div className="grid gap-6 md:grid-cols-3">
          <SliderInput label="Price Change" value={priceChange} onChange={setPriceChange} />
          <SliderInput label="Volume Change" value={volumeChange} onChange={setVolumeChange} />
          <SliderInput label="Cost Change" value={costChange} onChange={setCostChange} />
        </div>

        <div className="mt-5 flex items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-sm text-text-secondary">Months:</label>
            <select
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              className="rounded-lg border border-border bg-surface px-2 py-1 text-sm text-text-primary"
            >
              {[3, 6, 9, 12].map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          <div className="flex-1" />

          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-text-secondary hover:bg-muted"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Reset
          </button>
          <button
            onClick={handleSimulate}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90 disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5" /> {loading ? "Simulating..." : "Run Simulation"}
          </button>
        </div>
      </div>

      {loading && <LoadingCard className="h-64" />}

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-500">
          {error}
        </div>
      )}

      {result && !loading && (
        <>
          {/* Impact Summary */}
          <div className="grid gap-4 md:grid-cols-2">
            <ImpactCard
              label="Projected Revenue"
              baseline={result.revenue_impact.baseline_total}
              projected={result.revenue_impact.projected_total}
              change={result.revenue_impact.absolute_change}
              pctChange={result.revenue_impact.percentage_change}
            />
            <ImpactCard
              label="Projected Margin"
              baseline={result.margin_impact.baseline_total}
              projected={result.margin_impact.projected_total}
              change={result.margin_impact.absolute_change}
              pctChange={result.margin_impact.percentage_change}
            />
          </div>

          {/* Revenue Chart */}
          <ChartCard title="Revenue: Baseline vs Projected">
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={result.revenue_series}>
                <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
                <XAxis dataKey="month" tick={{ fill: theme.tickFill, fontSize: 12 }} />
                <YAxis tick={{ fill: theme.tickFill, fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: theme.tooltipBg, border: `1px solid ${theme.tooltipBorder}`, borderRadius: 8 }}
                  labelStyle={{ color: theme.tooltipColor }}
                  formatter={(value: number) => [formatCurrency(value), ""]}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="baseline"
                  name="Baseline"
                  stroke={theme.chartBlue}
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="projected"
                  name="Projected"
                  stroke={theme.chartAmber}
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Margin Chart */}
          <ChartCard title="Margin: Baseline vs Projected">
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={result.margin_series}>
                <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
                <XAxis dataKey="month" tick={{ fill: theme.tickFill, fontSize: 12 }} />
                <YAxis tick={{ fill: theme.tickFill, fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{ backgroundColor: theme.tooltipBg, border: `1px solid ${theme.tooltipBorder}`, borderRadius: 8 }}
                  labelStyle={{ color: theme.tooltipColor }}
                  formatter={(value: number) => [formatCurrency(value), ""]}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="baseline"
                  name="Baseline"
                  stroke={theme.chartBlue}
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="projected"
                  name="Projected"
                  stroke={theme.accentColor}
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </ChartCard>
        </>
      )}
    </div>
  );
}
