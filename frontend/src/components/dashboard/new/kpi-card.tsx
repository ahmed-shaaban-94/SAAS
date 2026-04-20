"use client";

import { useId } from "react";
import {
  Banknote,
  ShoppingCart,
  TriangleAlert,
  CalendarClock,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import type { ComponentType, SVGProps } from "react";

export type KpiColor = "accent" | "purple" | "amber" | "red";
export type KpiDir = "up" | "down";

interface KpiCardProps {
  id?: string;
  label: string;
  value: string;
  valueSuffix?: string;
  delta: { dir: KpiDir; text: string };
  sub: string;
  color?: KpiColor;
  sparkline?: number[];
  icon?: ComponentType<SVGProps<SVGSVGElement>>;
  ariaLabel?: string;
}

const COLOR_MAP: Record<KpiColor, { stroke: string; tint: string }> = {
  accent: { stroke: "#00c7f2", tint: "bg-accent/15 text-accent" },
  purple: { stroke: "#7467f8", tint: "bg-chart-purple/15 text-chart-purple" },
  amber: { stroke: "#ffab3d", tint: "bg-chart-amber/15 text-chart-amber" },
  red: { stroke: "#ff7b7b", tint: "bg-growth-red/15 text-growth-red" },
};

export const DEFAULT_KPI_ICONS: Record<string, ComponentType<SVGProps<SVGSVGElement>>> = {
  revenue: Banknote,
  orders: ShoppingCart,
  stock: TriangleAlert,
  expiry: CalendarClock,
};

export function KpiCard({
  label,
  value,
  valueSuffix,
  delta,
  sub,
  color = "accent",
  sparkline = [],
  icon: Icon,
  ariaLabel,
}: KpiCardProps) {
  const colors = COLOR_MAP[color] ?? COLOR_MAP.accent;
  const reactId = useId();
  const gradientId = `spark-${reactId.replace(/:/g, "")}`;

  return (
    <div className="relative overflow-hidden rounded-[14px] bg-card border border-border/40 p-5 flex flex-col gap-2">
      <div className="flex items-center gap-2.5">
        <div className={`w-7 h-7 rounded-lg grid place-items-center ${colors.tint}`} aria-hidden>
          {Icon ? <Icon className="w-3.5 h-3.5" /> : <span className="text-[12px]">◆</span>}
        </div>
        <div className="text-[11px] tracking-[0.18em] uppercase text-ink-tertiary">{label}</div>
      </div>
      <div
        className="text-3xl font-bold tabular-nums flex items-baseline gap-1.5"
        data-kpi-value
        aria-label={ariaLabel ?? `${label}: ${value}${valueSuffix ? " " + valueSuffix : ""}`}
      >
        {value}
        {valueSuffix && (
          <span className="text-sm text-ink-tertiary font-medium">{valueSuffix}</span>
        )}
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span
          className={[
            "font-semibold inline-flex items-center gap-1",
            delta.dir === "up" ? "text-growth-green" : "text-growth-red",
          ].join(" ")}
        >
          {delta.dir === "up" ? (
            <TrendingUp className="w-3 h-3" aria-hidden />
          ) : (
            <TrendingDown className="w-3 h-3" aria-hidden />
          )}
          {delta.text}
        </span>
        <span className="text-ink-tertiary">{sub}</span>
      </div>
      <Sparkline data={sparkline} color={colors.stroke} gradientId={gradientId} label={label} />
    </div>
  );
}

function Sparkline({
  data,
  color,
  gradientId,
  label,
}: {
  data: number[];
  color: string;
  gradientId: string;
  label: string;
}) {
  if (!data.length) return null;
  const w = 200;
  const h = 40;
  const step = data.length > 1 ? w / (data.length - 1) : w;
  const pts = data.map((y, i) => `${i * step} ${y}`).join(" L");
  const path = `M${pts}`;
  const fill = `M${pts} L${w} ${h} L0 ${h} Z`;
  return (
    <svg
      className="mt-auto -mx-1"
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      width="100%"
      height="40"
      role="img"
      aria-label={`${label} sparkline trend`}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.3" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={fill} fill={`url(#${gradientId})`} />
      <path d={path} stroke={color} strokeWidth="2" fill="none" />
    </svg>
  );
}
