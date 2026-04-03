"use client";

import { useState } from "react";
import { useTargetSummary } from "@/hooks/use-targets";
import { formatCurrency, formatPercent, formatCompact } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { postAPI } from "@/lib/api-client";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { Target, Plus, TrendingUp, TrendingDown, CheckCircle2 } from "lucide-react";

function ProgressRing({ pct, size = 120 }: { pct: number; size?: number }) {
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedPct = Math.min(Math.max(pct, 0), 150);
  const offset = circumference - (clampedPct / 100) * circumference;
  const color = pct >= 100 ? "#FF5722" : pct >= 75 ? "#FFB300" : "#EF4444";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size/2} cy={size/2} r={radius} stroke="currentColor" strokeWidth="6" fill="none" className="text-divider" />
        <circle cx={size/2} cy={size/2} r={radius} stroke={color} strokeWidth="6" fill="none"
          strokeDasharray={circumference} strokeDashoffset={Math.max(offset, 0)} strokeLinecap="round"
          className="transition-all duration-1000 ease-out" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-text-primary">{formatPercent(pct)}</span>
        <span className="text-[10px] text-text-secondary">achieved</span>
      </div>
    </div>
  );
}

export function GoalsOverview() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const { data, isLoading, mutate } = useTargetSummary(year);
  const theme = useChartTheme();
  const [showForm, setShowForm] = useState(false);
  const [formMonth, setFormMonth] = useState("");
  const [formValue, setFormValue] = useState("");
  const [saving, setSaving] = useState(false);

  const handleAddTarget = async () => {
    if (!formMonth || !formValue) return;
    setSaving(true);
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
      console.error("Failed to save target", e);
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
    <div className="space-y-6 mt-6">
      {/* Year selector */}
      <div className="flex items-center gap-3">
        <button onClick={() => setYear(y => y - 1)} className="rounded-lg px-3 py-1 text-sm text-text-secondary hover:bg-divider">&larr;</button>
        <span className="text-lg font-bold text-text-primary">{year}</span>
        <button onClick={() => setYear(y => Math.min(y + 1, currentYear))} disabled={year >= currentYear}
          className="rounded-lg px-3 py-1 text-sm text-text-secondary hover:bg-divider disabled:opacity-30">&rarr;</button>
        <button onClick={() => setShowForm(!showForm)}
          className="ml-auto flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90 transition-colors">
          <Plus className="h-4 w-4" />
          Add Target
        </button>
      </div>

      {/* Add target form */}
      {showForm && (
        <div className="rounded-xl border border-accent/30 bg-accent/5 p-4 animate-in fade-in slide-in-from-top-2">
          <h4 className="text-sm font-semibold text-text-primary mb-3">Set Monthly Revenue Target</h4>
          <div className="flex items-end gap-3">
            <div>
              <label className="text-xs text-text-secondary block mb-1">Month</label>
              <input type="month" value={formMonth} onChange={(e) => setFormMonth(e.target.value)}
                className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-text-secondary block mb-1">Target (EGP)</label>
              <input type="number" value={formValue} onChange={(e) => setFormValue(e.target.value)} placeholder="500000"
                className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-text-primary focus:border-accent focus:outline-none w-40" />
            </div>
            <button onClick={handleAddTarget} disabled={saving || !formMonth || !formValue}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90 disabled:opacity-50 transition-colors">
              {saving ? "Saving..." : "Save"}
            </button>
            <button onClick={() => setShowForm(false)} className="rounded-lg px-4 py-2 text-sm text-text-secondary hover:bg-divider">Cancel</button>
          </div>
        </div>
      )}

      {!hasTargets ? (
        <div className="rounded-xl border border-border bg-card p-12 text-center">
          <Target className="h-12 w-12 text-text-secondary mx-auto mb-3 opacity-30" />
          <p className="text-sm text-text-secondary">No targets set for {year}</p>
          <p className="text-xs text-text-secondary mt-1">Click &quot;Add Target&quot; to set monthly revenue goals</p>
        </div>
      ) : (
        <>
          {/* KPI Summary Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
              <ProgressRing pct={data!.ytd_achievement_pct} size={80} />
              <div>
                <p className="text-xs text-text-secondary">YTD Achievement</p>
                <p className="text-sm font-bold text-text-primary">{formatPercent(data!.ytd_achievement_pct)}</p>
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <Target className="h-4 w-4 text-accent mb-2" />
              <p className="text-xs text-text-secondary">YTD Target</p>
              <p className="text-lg font-bold text-text-primary">{formatCompact(data!.ytd_target)}</p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              <CheckCircle2 className="h-4 w-4 text-green-500 mb-2" />
              <p className="text-xs text-text-secondary">YTD Actual</p>
              <p className="text-lg font-bold text-text-primary">{formatCompact(data!.ytd_actual)}</p>
            </div>
            <div className="rounded-xl border border-border bg-card p-4">
              {data!.ytd_actual >= data!.ytd_target ? (
                <TrendingUp className="h-4 w-4 text-green-500 mb-2" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-500 mb-2" />
              )}
              <p className="text-xs text-text-secondary">Variance</p>
              <p className={`text-lg font-bold ${data!.ytd_actual >= data!.ytd_target ? "text-green-500" : "text-red-500"}`}>
                {data!.ytd_actual >= data!.ytd_target ? "+" : ""}{formatCompact(data!.ytd_actual - data!.ytd_target)}
              </p>
            </div>
          </div>

          {/* Target vs Actual Chart */}
          <div className="rounded-xl border border-border bg-card p-4">
            <h3 className="text-sm font-semibold text-text-primary mb-4">Monthly Target vs Actual</h3>
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
                <Bar dataKey="actual" name="Actual" fill="#FF5722" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Monthly breakdown table */}
          <div className="rounded-xl border border-border bg-card p-4">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Monthly Breakdown</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 px-3 font-medium text-text-secondary">Month</th>
                    <th className="text-right py-2 px-3 font-medium text-text-secondary">Target</th>
                    <th className="text-right py-2 px-3 font-medium text-text-secondary">Actual</th>
                    <th className="text-right py-2 px-3 font-medium text-text-secondary">Variance</th>
                    <th className="text-right py-2 px-3 font-medium text-text-secondary">Achievement</th>
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
                          {formatPercent(m.achievement_pct)}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        <div className="h-1.5 rounded-full bg-divider overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${Math.min(m.achievement_pct, 100)}%`,
                              backgroundColor: m.achievement_pct >= 100 ? "#FF5722" : m.achievement_pct >= 75 ? "#FFB300" : "#EF4444",
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
    </div>
  );
}
