"use client";

import { memo, useId } from "react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";

interface InlineSparklineProps {
  data: Array<{ value: number }>;
  /** "auto" = green if trending up, red if down */
  color?: string;
  width?: number;
  height?: number;
}

/**
 * Tiny inline sparkline chart for use in table cells.
 * Shows trend direction at a glance without labels or axes.
 */
export const InlineSparkline = memo(function InlineSparkline({
  data,
  color = "auto",
  width = 80,
  height = 28,
}: InlineSparklineProps) {
  const gradientId = useId();

  if (!data || data.length < 2) return null;

  const first = data[0].value;
  const last = data[data.length - 1].value;
  const trendColor =
    last >= first ? "var(--growth-green)" : "var(--growth-red)";
  const effectiveColor = color === "auto" ? trendColor : color;

  return (
    <div style={{ width, height }} className="inline-block align-middle">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 2, right: 0, left: 0, bottom: 2 }}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="0%"
                stopColor={effectiveColor}
                stopOpacity={0.3}
              />
              <stop
                offset="100%"
                stopColor={effectiveColor}
                stopOpacity={0}
              />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={effectiveColor}
            strokeWidth={1.5}
            fill={`url(#${gradientId})`}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
});
