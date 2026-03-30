"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { CHART_COLORS } from "@/lib/constants";
import { formatCurrency } from "@/lib/formatters";
import { useChartTheme } from "@/hooks/use-chart-theme";

interface DistributionChartProps {
  data: { name: string; value: number }[];
  title?: string;
  className?: string;
}

export default function DistributionChart({
  data,
  title,
  className,
}: DistributionChartProps) {
  const CHART_THEME = useChartTheme();
  if (!data || data.length === 0) return null;

  return (
    <div className={className}>
      {title && (
        <h3 className="mb-4 text-sm font-medium text-text-secondary">
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={2}
            dataKey="value"
            nameKey="name"
          >
            {data.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={CHART_COLORS[index % CHART_COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: CHART_THEME.tooltipBg,
              border: `1px solid ${CHART_THEME.tooltipBorder}`,
              borderRadius: "8px",
              color: CHART_THEME.tooltipColor,
            }}
            formatter={(value: number) => [formatCurrency(value)]}
          />
          <Legend
            verticalAlign="bottom"
            iconType="circle"
            iconSize={8}
            wrapperStyle={{
              color: CHART_THEME.tickFill,
              fontSize: CHART_THEME.tickFontSize,
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
