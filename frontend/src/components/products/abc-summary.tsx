"use client";

import { useABCAnalysis } from "@/hooks/use-abc-analysis";
import { formatNumber } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";

const CLASS_COLORS = { A: "#00BFA5", B: "#FFB300", C: "#64748b" };

export function ABCSummary() {
  const { data, isLoading } = useABCAnalysis("product");
  const theme = useChartTheme();

  if (isLoading) return <LoadingCard className="h-48" />;
  if (!data) return null;

  const pieData = [
    { name: "Class A", value: data.class_a_count, pct: data.class_a_pct, color: CLASS_COLORS.A },
    { name: "Class B", value: data.class_b_count, pct: data.class_b_pct, color: CLASS_COLORS.B },
    { name: "Class C", value: data.class_c_count, pct: data.class_c_pct, color: CLASS_COLORS.C },
  ];

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">ABC Classification</h3>

      <div className="flex items-center gap-4">
        <div className="w-32 h-32">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={30}
                outerRadius={55}
                paddingAngle={3}
                dataKey="value"
              >
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: theme.tooltipBg,
                  border: `1px solid ${theme.tooltipBorder}`,
                  borderRadius: "8px",
                  fontSize: "12px",
                  color: theme.tooltipColor,
                }}
                formatter={(value: number, name: string) => [`${value} products`, name]}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="flex-1 space-y-3">
          {pieData.map((cls) => (
            <div key={cls.name} className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: cls.color }} />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-text-primary">{cls.name}</span>
                  <span className="text-xs text-text-secondary">{formatNumber(cls.value)} products</span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-divider overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${cls.pct}%`, backgroundColor: cls.color }}
                  />
                </div>
                <span className="text-[10px] text-text-secondary">{cls.pct.toFixed(1)}% of revenue</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
