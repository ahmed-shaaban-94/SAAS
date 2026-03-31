"use client";

import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  Funnel,
  FunnelChart,
  LabelList,
  PieChart,
  Pie,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Treemap,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART_COLORS } from "@/lib/constants";

interface ChartDataProps {
  data: Record<string, unknown>[];
  dimKey: string;
  metricKeys: string[];
}

export function StackedBarChart({ data, dimKey, metricKeys }: ChartDataProps) {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
        <XAxis dataKey={dimKey} tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        {metricKeys.map((key, i) => (
          <Bar
            key={key}
            dataKey={key}
            stackId="stack"
            fill={CHART_COLORS[i % CHART_COLORS.length]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function HorizontalBarChart({ data, dimKey, metricKeys }: ChartDataProps) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(300, data.length * 40)}>
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
        <XAxis type="number" tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey={dimKey} width={120} tick={{ fontSize: 11 }} />
        <Tooltip />
        {metricKeys.map((key, i) => (
          <Bar
            key={key}
            dataKey={key}
            fill={CHART_COLORS[i % CHART_COLORS.length]}
            radius={[0, 4, 4, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function GroupedBarChart({ data, dimKey, metricKeys }: ChartDataProps) {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
        <XAxis dataKey={dimKey} tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        {metricKeys.map((key, i) => (
          <Bar
            key={key}
            dataKey={key}
            fill={CHART_COLORS[i % CHART_COLORS.length]}
            radius={[4, 4, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function AreaChartView({ data, dimKey, metricKeys }: ChartDataProps) {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
        <XAxis dataKey={dimKey} tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        {metricKeys.map((key, i) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stroke={CHART_COLORS[i % CHART_COLORS.length]}
            fill={CHART_COLORS[i % CHART_COLORS.length]}
            fillOpacity={0.2}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function StackedAreaChart({ data, dimKey, metricKeys }: ChartDataProps) {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
        <XAxis dataKey={dimKey} tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        {metricKeys.map((key, i) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stackId="stack"
            stroke={CHART_COLORS[i % CHART_COLORS.length]}
            fill={CHART_COLORS[i % CHART_COLORS.length]}
            fillOpacity={0.4}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function DonutChart({ data, dimKey, metricKeys }: ChartDataProps) {
  const metricKey = metricKeys[0];
  return (
    <ResponsiveContainer width="100%" height={400}>
      <PieChart>
        <Pie
          data={data}
          dataKey={metricKey}
          nameKey={dimKey}
          cx="50%"
          cy="50%"
          innerRadius={80}
          outerRadius={150}
          label={(entry) => entry[dimKey]}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function ScatterPlot({ data, metricKeys }: Omit<ChartDataProps, "dimKey">) {
  if (metricKeys.length < 2) return null;
  return (
    <ResponsiveContainer width="100%" height={400}>
      <ScatterChart>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" />
        <XAxis dataKey={metricKeys[0]} name={metricKeys[0]} tick={{ fontSize: 12 }} />
        <YAxis dataKey={metricKeys[1]} name={metricKeys[1]} tick={{ fontSize: 12 }} />
        <Tooltip />
        <Scatter data={data} fill={CHART_COLORS[0]} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export function RadarChartView({ data, dimKey, metricKeys }: ChartDataProps) {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <RadarChart data={data}>
        <PolarGrid stroke="var(--divider)" />
        <PolarAngleAxis dataKey={dimKey} tick={{ fontSize: 11 }} />
        <PolarRadiusAxis tick={{ fontSize: 10 }} />
        <Tooltip />
        {metricKeys.map((key, i) => (
          <Radar
            key={key}
            dataKey={key}
            stroke={CHART_COLORS[i % CHART_COLORS.length]}
            fill={CHART_COLORS[i % CHART_COLORS.length]}
            fillOpacity={0.3}
          />
        ))}
      </RadarChart>
    </ResponsiveContainer>
  );
}

export function FunnelChartView({ data, dimKey, metricKeys }: ChartDataProps) {
  const metricKey = metricKeys[0];
  const funnelData = data.map((d, i) => ({
    name: String(d[dimKey]),
    value: Number(d[metricKey]) || 0,
    fill: CHART_COLORS[i % CHART_COLORS.length],
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <FunnelChart>
        <Tooltip />
        <Funnel dataKey="value" data={funnelData} isAnimationActive>
          <LabelList position="right" fill="var(--text-primary)" fontSize={12} />
        </Funnel>
      </FunnelChart>
    </ResponsiveContainer>
  );
}

export function TreemapChart({ data, dimKey, metricKeys }: ChartDataProps) {
  const metricKey = metricKeys[0];
  const treemapData = data.map((d, i) => ({
    name: String(d[dimKey]),
    size: Number(d[metricKey]) || 0,
    fill: CHART_COLORS[i % CHART_COLORS.length],
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <Treemap
        data={treemapData}
        dataKey="size"
        nameKey="name"
        stroke="var(--border)"
        fill="var(--accent)"
        aspectRatio={4 / 3}
      >
        <Tooltip />
      </Treemap>
    </ResponsiveContainer>
  );
}

export function GaugeChart({ data, metricKeys }: Omit<ChartDataProps, "dimKey">) {
  const value = data.length > 0 ? Number(data[0][metricKeys[0]]) || 0 : 0;
  const formatted = value.toLocaleString("en-EG", { maximumFractionDigits: 2 });

  return (
    <div className="flex flex-col items-center justify-center h-[400px]">
      <div className="text-6xl font-bold text-accent">{formatted}</div>
      <div className="mt-2 text-sm text-text-secondary">
        {metricKeys[0]?.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
      </div>
    </div>
  );
}
