"use client";

import { useState } from "react";
import { useTargetSummary, useQuarterlySummary } from "@/hooks/use-targets";
import { useBudgetSummary } from "@/hooks/use-budget";
import { formatCurrency, formatCompact, formatAbsolutePercent } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { postAPI } from "@/lib/api-client";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { Target, Plus, TrendingUp, TrendingDown, CheckCircle2, Wallet } from "lucide-react";

function ProgressRing({ pct, size = 120 }: { pct: number; size?: number }) {
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedPct = Math.min(Math.max(pct, 0), 150);
  const offset = circumference - (clampedPct / 100) * circumference;
  const color = pct >= 100 ? "#059669" : pct >= 75 ? "#FFB300" : "#EF4444";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size/2} cy={size/2} r={radius} stroke="currentColor" strokeWidth="6" fill="none" className="text-divider" />
        <circle cx={size/2} cy={size/2} r={radius} stroke={color} strokeWidth="6" fill="none"
          strokeDasharray={circumference} strokeDashoffset={Math.max(offset, 0)} strokeLinecap="round"
          className="transition-all duration-1000 ease-out" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-text-primary">{formatAbsolutePercent(pct)}</span>
        <span className="text-[10px] text-text-secondary">achieved</span>
      </div>
    </div>
  );
}

const ORIGIN_COLORS: Record<string, string> = {
  Pharma: "#4F46E5",
  "Non-pharma": "#10B981",
  HVI: "#F59E0B",
  Services: "#6B7280",
  Other: "#9CA3AF",
};

function BudgetSection({ year }: { year: number }) {
  const { data, isLoading, error } = useBudgetSummary(year);
  const theme = useChartTheme();

  if (isLoading) return <LoadingCard className="h-64" />;
  if (error) return <ErrorRetry title="Failed to load budget data" />;
  if (!data || data.monthly.length === 0) return null;

  // Pivot monthly data: one row per month, budget/actual per origin
  const months = Array.from(new Set(data.monthly.map((m) => m.month))).sort((a, b) => a - b);
  const origins = Array.from(new Set(data.monthly.map((m) => m.origin)));
  const chartData = months.map((mo) => {
    const row: Record<string, string | number> = {
      month: data.monthly.find((m) => m.month === mo)?.month_name ?? String(mo),
    };
    for (const origin of origins) {
      const item = data.monthly.find((m) => m.month === mo && m.origin === origin);
      row[`${origin}_budget`] = item?.budget ?? 0;
      row[`${origin}_actual`] = item?.actual ?? 0;
    }
    return row;
  });

  return (
    <div className="space-y-4">
      <h3 className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
        <Wallet className="h-4 w-4 text-accent" />
        Budget vs Actual by Origin
      </h3>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {data.by_origin.map((o) => {
          const met = o.ytd_actual >= o.ytd_budget;
          return (
            <div key={o.origin} className="viz-panel viz-card-hover rounded-[1.5rem] p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-text-primary">{o.origin}</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  o.ytd_achievement_pct >= 100 ? "bg-green-500/10 text-green-500" :
                  o.ytd_achievement_pct >= 75 ? "bg-yellow-500/10 text-yellow-500" : "bg-red-500/10 text-red-500"
                }`}>
                  {formatAbsolutePercent(o.ytd_achievement_pct)}
                </span>
              </div>
              <div className="flex justify-between text-xs text-text-secondary mb-1">
                <span>Budget: {formatCompact(o.ytd_budget)}</span>
                <span>Actual: {formatCompact(o.ytd_actual)}</span>
              </div>
              <div className="h-1.5 rounded-full bg-divider overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(o.ytd_achievement_pct, 100)}%`,
                    backgroundColor: ORIGIN_COLORS[o.origin] ?? "#6B7280",
                  }}
                />
              </div>
              <p className={`text-xs mt-1 font-medium ${met ? "text-green-500" : "text-red-500"}`}>
                {met ? "+" : ""}{formatCompact(o.ytd_variance)}
              </p>
            </div>
          );
        })}
      </div>

      <div className="viz-panel rounded-[1.75rem] p-4 sm:p-5">
        <h4 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">Monthly Budget vs Actual</h4>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: theme.tickFill }} />
            <YAxis tick={{ fontSize: 10, fill: theme.tickFill }} tickFormatter={(v: number) => formatCompact(v)} />
            <Tooltip
              contentStyle={{ backgroundColor: theme.tooltipBg, border: `1px solid ${theme.gridStroke}`, borderRadius: "8px", fontSize: "12px" }}
              formatter={(value: number, name: string) => [formatCurrency(value), name.replace("_budget", " Budget").replace("_actual", " Actual")]}
            />
            <Legend wrapperStyle={{ fontSize: "11px" }} formatter={(v: string) => v.replace("_budget", " Budget").replace("_actual", " Actual")} />
            {origins.map((origin) => (
              <Bar key={`${origin}_budget`} dataKey={`${origin}_budget`} stackId="budget"
                fill={ORIGIN_COLORS[origin] ?? "#6B7280"} opacity={0.3} radius={0} />
            ))}
            {origins.map((origin) => (
              <Bar key={`${origin}_actual`} dataKey={`${origin}_actual`} stackId="actual"
                fill={ORIGIN_COLORS[origin] ?? "#6B7280"} radius={0} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function QuarterlyView({ year }: { year: number }) {
  const { data, isLoading } = useQuarterlySummary(year);
  const theme = useChartTheme();

  if (isLoading) return <LoadingCard className="h-64" />;
  if (!data || data.quarters.length === 0) {
    return <div className="viz-panel rounded-[1.75rem] p-8 text-center text-text-tertiary">No quarterly data for {year}</div>;
  }

  const chartData = data.quarters.map((q) => ({
    period: q.quarter_label,
    target: q.target_value,
    actual: q.actual_value,
    achievement: q.achievement_pct,
  }));

  return (
    <div className="space-y-4">
      <div className="viz-panel rounded-[1.75rem] p-4 sm:p-5">
        <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">Quarterly Target vs Actual</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
            <XAxis dataKey="period" tick={{ fontSize: 12, fill: theme.tickFill }} />
            <YAxis tick={{ fontSize: 10, fill: theme.tickFill }} tickFormatter={(v: number) => formatCompact(v)} />
            <Tooltip
              contentStyle={{ backgroundColor: theme.tooltipBg, border: `1px solid ${theme.gridStroke}`, borderRadius: "8px", fontSize: "12px" }}
              formatter={(value: number, name: string) => [formatCurrency(value), name === "target" ? "Target" : "Actual"]}
            />
            <Legend wrapperStyle={{ fontSize: "11px" }} />
            <Bar dataKey="target" name="Target" fill={theme.gridStroke} radius={[4, 4, 0, 0]} opacity={0.5} />
            <Bar dataKey="actual" name="Actual" fill={theme.palette[0]} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="viz-panel overflow-x-auto rounded-[1.75rem] p-4">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-[11px] font-semibold uppercase tracking-[0.18em] text-text-secondary">
              <th className="text-left py-2 px-3">Quarter</th>
              <th className="text-right py-2 px-3">Target</th>
              <th className="text-right py-2 px-3">Actual</th>
              <th className="text-right py-2 px-3">Variance</th>
              <th className="text-right py-2 px-3">Achievement</th>
            </tr>
          </thead>
          <tbody>
            {data.quarters.map((q) => (
              <tr key={q.quarter} className="border-b border-border/50 hover:bg-divider/50">
                <td className="py-2 px-3 font-medium text-text-primary">{q.quarter_label}</td>
                <td className="py-2 px-3 text-right text-text-secondary">{formatCurrency(q.target_value)}</td>
                <td className="py-2 px-3 text-right text-text-primary font-medium">{formatCurrency(q.actual_value)}</td>
                <td className={`py-2 px-3 text-right font-medium ${q.variance >= 0 ? "text-green-500" : "text-red-500"}`}>
                  {q.variance >= 0 ? "+" : ""}{formatCurrency(q.variance)}
                </td>
                <td className="py-2 px-3 text-right">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                    q.achievement_pct >= 100 ? "bg-green-500/10 text-green-500" :
                    q.achievement_pct >= 75 ? "bg-yellow-500/10 text-yellow-500" : "bg-red-500/10 text-red-500"
                  }`}>{formatAbsolutePercent(q.achievement_pct)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function GoalsOverview() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [viewMode, setViewMode] = useState<"monthly" | "quarterly">("monthly");
  const { data, isLoading, mutate } = useTargetSummary(year);
  const theme = useChartTheme();
  const [showForm, setShowForm] = useState(false);
  const [formMonth, setFormMonth] = useState("");
  const [formValue, setFormValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleAddTarget = async () => {
    if (!formMonth || !formValue) return;
    setSaving(true);
    setSaveError(null);
    try {
      await postAPI("/api/v1/targets/", {
        target_type: "revenue",
        granularity: "monthly",
        period: formMonth,
        target_value: parseFloat(formValue),
      });
      setFormMonth("");
      setFormValue("");
      setShowForm(false);
      mutate();
    } catch (e) {
      setSaveError("Failed to save target. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) return <LoadingCard className="h-96" />;

  const hasTargets = data && data.monthly_targets.length > 0;

  const chartData = data?.monthly_targets.map((m) => {
    const monthName = new Date(m.period + "-01").toLocaleDateString("en", { month: "short" });
    return {
      period: monthName,
      target: m.target_value,
      actual: m.actual_value,
      achievement: m.achievement_pct,
    };
  }) ?? [];

  return (
    <div className="mt-6 space-y-6">
      <div className="viz-panel-soft flex flex-wrap items-center gap-3 rounded-[1.5rem] p-3 sm:p-4">
        <button onClick={() => setYear(y => y - 1)} className="viz-panel-soft rounded-xl px-3 py-2 text-sm text-text-secondary transition-colors hover:text-accent">&larr;</button>
        <span className="text-lg font-bold text-text-primary">{year}</span>
        <button onClick={() => setYear(y => Math.min(y + 1, currentYear))} disabled={year >= currentYear}
          className="viz-panel-soft rounded-xl px-3 py-2 text-sm text-text-secondary transition-colors hover:text-accent disabled:opacity-30">&rarr;</button>
        <div className="ml-0 flex overflow-hidden rounded-xl border border-border sm:ml-4">
          {(["monthly", "quarterly"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] transition-colors ${
                viewMode === mode
                  ? "bg-accent text-white"
                  : "text-text-secondary hover:bg-background/60"
              }`}
            >
              {mode === "monthly" ? "Monthly" : "Quarterly"}
            </button>
          ))}
        </div>

        <button onClick={() => setShowForm(!showForm)}
          className="ml-auto flex items-center gap-1.5 rounded-2xl bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-accent/90">
          <Plus className="h-4 w-4" />
          Add Target
        </button>
      </div>

      {showForm && (
        <div className="viz-panel rounded-[1.75rem] border border-accent/20 p-5 animate-in fade-in slide-in-from-top-2">
          <h4 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">Set Monthly Revenue Target</h4>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="text-xs text-text-secondary block mb-1">Month</label>
              <input type="month" value={formMonth} onChange={(e) => setFormMonth(e.target.value)}
                className="rounded-xl border border-border/70 bg-background/60 px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-text-secondary block mb-1">Target (EGP)</label>
              <input type="number" value={formValue} onChange={(e) => setFormValue(e.target.value)} placeholder="500000"
                className="w-40 rounded-xl border border-border/70 bg-background/60 px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none" />
            </div>
            <button onClick={handleAddTarget} disabled={saving || !formMonth || !formValue}
              className="rounded-2xl bg-accent px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent/90 disabled:opacity-50">
              {saving ? "Saving..." : "Save"}
            </button>
            <button onClick={() => setShowForm(false)} className="viz-panel-soft rounded-2xl px-4 py-2.5 text-sm text-text-secondary transition-colors hover:text-text-primary">Cancel</button>
          </div>
          {saveError && (
            <p className="mt-2 text-xs text-red-500">{saveError}</p>
          )}
        </div>
      )}

      {viewMode === "quarterly" ? (
        <QuarterlyView year={year} />
      ) : !hasTargets ? (
        <div className="viz-panel rounded-[1.75rem] p-12 text-center">
          <Target className="h-12 w-12 text-text-secondary mx-auto mb-3 opacity-30" />
          <p className="text-sm text-text-secondary">No targets set for {year}</p>
          <p className="text-xs text-text-secondary mt-1">Click &quot;Add Target&quot; to set monthly revenue goals</p>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="viz-panel viz-card-hover flex items-center gap-4 rounded-[1.5rem] p-4">
              <ProgressRing pct={data!.ytd_achievement_pct} size={80} />
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">YTD Achievement</p>
                <p className="text-sm font-bold text-text-primary">{formatAbsolutePercent(data!.ytd_achievement_pct)}</p>
              </div>
            </div>
            <div className="viz-panel viz-card-hover rounded-[1.5rem] p-4">
              <Target className="mb-2 h-4 w-4 text-accent" />
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">YTD Target</p>
              <p className="text-lg font-bold text-text-primary">{formatCompact(data!.ytd_target)}</p>
            </div>
            <div className="viz-panel viz-card-hover rounded-[1.5rem] p-4">
              <CheckCircle2 className="mb-2 h-4 w-4 text-green-500" />
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">YTD Actual</p>
              <p className="text-lg font-bold text-text-primary">{formatCompact(data!.ytd_actual)}</p>
            </div>
            <div className="viz-panel viz-card-hover rounded-[1.5rem] p-4">
              {data!.ytd_actual >= data!.ytd_target ? (
                <TrendingUp className="mb-2 h-4 w-4 text-green-500" />
              ) : (
                <TrendingDown className="mb-2 h-4 w-4 text-red-500" />
              )}
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-text-secondary">Variance</p>
              <p className={`text-lg font-bold ${data!.ytd_actual >= data!.ytd_target ? "text-green-500" : "text-red-500"}`}>
                {data!.ytd_actual >= data!.ytd_target ? "+" : ""}{formatCompact(data!.ytd_actual - data!.ytd_target)}
              </p>
            </div>
          </div>

          <div className="viz-panel rounded-[1.75rem] p-4 sm:p-5">
            <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">Monthly Target vs Actual</h3>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
                <XAxis dataKey="period" tick={{ fontSize: 11, fill: theme.tickFill }} />
                <YAxis tick={{ fontSize: 10, fill: theme.tickFill }} tickFormatter={(v: number) => formatCompact(v)} />
                <Tooltip
                  contentStyle={{ backgroundColor: theme.tooltipBg, border: `1px solid ${theme.gridStroke}`, borderRadius: "8px", fontSize: "12px" }}
                  formatter={(value: number, name: string) => [formatCurrency(value), name === "target" ? "Target" : "Actual"]}
                />
                <Legend wrapperStyle={{ fontSize: "11px" }} />
                <Bar dataKey="target" name="Target" fill={theme.gridStroke} radius={[4, 4, 0, 0]} opacity={0.5} />
                <Bar dataKey="actual" name="Actual" fill={theme.palette[0]} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="viz-panel rounded-[1.75rem] p-4 sm:p-5">
            <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">Monthly Breakdown</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-[11px] font-semibold uppercase tracking-[0.18em] text-text-secondary">
                    <th className="text-left py-2 px-3">Month</th>
                    <th className="text-right py-2 px-3">Target</th>
                    <th className="text-right py-2 px-3">Actual</th>
                    <th className="text-right py-2 px-3">Variance</th>
                    <th className="text-right py-2 px-3">Achievement</th>
                    <th className="py-2 px-3 w-32"></th>
                  </tr>
                </thead>
                <tbody>
                  {data!.monthly_targets.map((m) => (
                    <tr key={m.period} className="border-b border-border/50 hover:bg-divider/50">
                      <td className="py-2 px-3 font-medium text-text-primary">{m.period}</td>
                      <td className="py-2 px-3 text-right text-text-secondary">{formatCurrency(m.target_value)}</td>
                      <td className="py-2 px-3 text-right text-text-primary font-medium">{formatCurrency(m.actual_value)}</td>
                      <td className={`py-2 px-3 text-right font-medium ${m.variance >= 0 ? "text-green-500" : "text-red-500"}`}>
                        {m.variance >= 0 ? "+" : ""}{formatCurrency(m.variance)}
                      </td>
                      <td className="py-2 px-3 text-right">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                          m.achievement_pct >= 100 ? "bg-green-500/10 text-green-500" :
                          m.achievement_pct >= 75 ? "bg-yellow-500/10 text-yellow-500" : "bg-red-500/10 text-red-500"
                        }`}>
                          {formatAbsolutePercent(m.achievement_pct)}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        <div className="h-1.5 rounded-full bg-divider overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${Math.min(m.achievement_pct, 100)}%`,
                              backgroundColor: m.achievement_pct >= 100 ? "#059669" : m.achievement_pct >= 75 ? "#FFB300" : "#EF4444",
                            }} />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Budget vs Actual section */}
      <BudgetSection year={year} />
    </div>
  );
}
