"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { CHART_COLORS, CHART_THEME } from "@/lib/constants";

interface DistributionChartProps {
  data: { name: string; value: number }[];
  title?: string;
  className?: string;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { name: string; value: number; payload: { name: string } }[];
}) {
  if (!active || !payload || payload.length === 0) return null;

  const entry = payload[0];
  return (
    <div
      className="rounded-md border px-3 py-2 text-sm shadow-lg"
      style={{
        backgroundColor: CHART_THEME.tooltipBg,
        borderColor: CHART_THEME.tooltipBorder,
        color: CHART_THEME.tooltipColor,
      }}
    >
      <p className="font-medium">{entry.payload.name}</p>
      <p>{entry.value.toLocaleString()}</p>
    </div>
  );
}

export default function DistributionChart({
  data,
  title,
  className,
}: DistributionChartProps) {
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
          <Tooltip content={<CustomTooltip />} />
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
