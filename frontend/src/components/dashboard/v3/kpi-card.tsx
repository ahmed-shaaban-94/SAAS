"use client";

import { useId } from "react";
import { TrendingUp, TrendingDown, Package, ShoppingCart, AlertTriangle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { KpiData } from "./types";

const colorMap = {
  accent: {
    stroke: "#00c7f2",
    tintBg: "bg-accent/15",
    tintText: "text-accent",
  },
  purple: {
    stroke: "#7467f8",
    tintBg: "bg-chart-purple/15",
    tintText: "text-chart-purple",
  },
  amber: {
    stroke: "#ffab3d",
    tintBg: "bg-chart-amber/15",
    tintText: "text-chart-amber",
  },
  red: {
    stroke: "#ff7b7b",
    tintBg: "bg-growth-red/15",
    tintText: "text-growth-red",
  },
} as const;

const iconMap = {
  revenue: TrendingUp,
  orders: ShoppingCart,
  stock: Package,
  expiry: Clock,
} as const;

export function KpiCard({
  id,
  label,
  value,
  valueSuffix,
  delta,
  sub,
  color,
  sparkline,
}: KpiData) {
  const c = colorMap[color] ?? colorMap.accent;
  const Icon = iconMap[id] ?? AlertTriangle;
  const sparkId = useId();
  const up = delta.dir === "up";

  return (
    <div className="relative flex flex-col gap-2 overflow-hidden rounded-card border border-border/40 bg-card p-5">
      <div className="flex items-center gap-2.5">
        <div
          className={cn(
            "grid h-7 w-7 place-items-center rounded-lg",
            c.tintBg,
            c.tintText,
          )}
        >
          <Icon className="h-3.5 w-3.5" aria-hidden />
        </div>
        <div className="text-[11px] uppercase tracking-[0.18em] text-text-tertiary">
          {label}
        </div>
      </div>

      <div
        className="flex items-baseline gap-1.5 text-3xl font-bold tabular-nums"
        data-kpi-value
      >
        {value}
        {valueSuffix && (
          <span className="text-sm font-medium text-text-tertiary">
            {valueSuffix}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 text-xs">
        <span
          className={cn(
            "inline-flex items-center gap-0.5 font-semibold",
            up ? "text-growth-green" : "text-growth-red",
          )}
        >
          {up ? (
            <TrendingUp className="h-3 w-3" aria-hidden />
          ) : (
            <TrendingDown className="h-3 w-3" aria-hidden />
          )}
          {delta.text}
        </span>
        <span className="text-text-tertiary">{sub}</span>
      </div>

      <Sparkline
        data={sparkline}
        color={c.stroke}
        gradientId={`spark-${sparkId}`}
      />
    </div>
  );
}

function Sparkline({
  data,
  color,
  gradientId,
}: {
  data: number[];
  color: string;
  gradientId: string;
}) {
  if (!data.length) return null;
  const w = 200;
  const h = 40;
  const step = w / Math.max(data.length - 1, 1);
  const pts = data.map((y, i) => `${i * step} ${y}`).join(" L");
  const path = `M${pts}`;
  const fill = `M${pts} L${w} ${h} L0 ${h} Z`;

  return (
    <svg
      className="-mx-1 mt-auto"
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      width="100%"
      height={40}
      role="img"
      aria-label="Trend sparkline"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity={0.3} />
          <stop offset="1" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={fill} fill={`url(#${gradientId})`} />
      <path d={path} stroke={color} strokeWidth={2} fill="none" />
    </svg>
  );
}
