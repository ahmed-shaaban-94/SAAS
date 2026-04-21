"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export interface KpiPill {
  id: string;
  label: string;
  value: string;
  valueSuffix?: string;
  deltaDir: "up" | "down" | "flat";
  deltaText: string;
  sub: string;
  sparkline: number[];
  href: string;
}

function DeltaIcon({ dir }: { dir: KpiPill["deltaDir"] }) {
  if (dir === "up") return <TrendingUp className="w-3 h-3" aria-hidden />;
  if (dir === "down") return <TrendingDown className="w-3 h-3" aria-hidden />;
  return <Minus className="w-3 h-3" aria-hidden />;
}

function Sparkline({ points }: { points: number[] }) {
  // A single point renders no stroke; require at least two to draw a line.
  if (points.length < 2) return null;
  const w = 120;
  const h = 16;
  const step = w / Math.max(1, points.length - 1);
  const d = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${(i * step).toFixed(1)} ${p.toFixed(1)}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-4 text-accent/70" aria-hidden>
      <path d={d} fill="none" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

function Pill({ pill, children }: { pill: KpiPill; children?: ReactNode }) {
  const deltaColor =
    pill.deltaDir === "up"
      ? "text-accent-strong"
      : pill.deltaDir === "down"
      ? "text-red-400"
      : "text-ink-secondary";
  return (
    <Link
      href={pill.href}
      className="block p-4 hover:bg-elevated/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
      aria-label={`${pill.label}: ${pill.value}${pill.valueSuffix ? " " + pill.valueSuffix : ""}. ${pill.deltaText} ${pill.sub}`}
    >
      <div className="text-[11px] uppercase tracking-wider text-ink-secondary">
        {pill.label}
      </div>
      <div className="flex items-baseline gap-2 mt-1">
        <span className="text-xl font-semibold text-ink-primary">{pill.value}</span>
        {pill.valueSuffix && (
          <span className="text-[11px] text-ink-secondary">{pill.valueSuffix}</span>
        )}
        <span className={`text-xs inline-flex items-center gap-1 ${deltaColor}`}>
          <DeltaIcon dir={pill.deltaDir} />
          {pill.deltaText}
        </span>
      </div>
      <Sparkline points={pill.sparkline} />
      <div className="text-[11px] text-ink-secondary mt-0.5">{pill.sub}</div>
      {children}
    </Link>
  );
}

export function KpiStrip({ pills, loading }: { pills: KpiPill[]; loading: boolean }) {
  if (loading) {
    return (
      <section
        aria-label="Key performance indicators"
        className="rounded-[14px] bg-card border border-border/40 h-[88px] animate-pulse"
      />
    );
  }
  return (
    <section
      aria-label="Key performance indicators"
      className="rounded-[14px] bg-card border border-border/40
                 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-border/40"
    >
      {pills.map((p) => (
        <Pill key={p.id} pill={p} />
      ))}
    </section>
  );
}
