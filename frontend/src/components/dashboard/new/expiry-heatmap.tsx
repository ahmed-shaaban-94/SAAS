"use client";

import { useMemo } from "react";
import type { ExpiryCalendarDay } from "@/types/expiry";
import type { ExpiryExposureTier } from "@/types/api";

interface ExpiryHeatmapProps {
  calendar?: ExpiryCalendarDay[];
  exposure?: ExpiryExposureTier[];
  loading?: boolean;
}

const PALETTE = [
  "rgba(51,80,107,0.25)",
  "rgba(255,171,61,0.2)",
  "rgba(255,171,61,0.4)",
  "rgba(255,171,61,0.65)",
  "rgba(255,123,123,0.7)",
  "#ff7b7b",
] as const;

const TIER_CLS: Record<ExpiryExposureTier["tone"], string> = {
  red: "text-growth-red",
  amber: "text-chart-amber",
  green: "text-growth-green",
};

const SEVERITY_BY_ALERT: Record<string, number> = {
  expired: 5,
  critical: 4,
  warning: 3,
  caution: 2,
  safe: 1,
};

const CELLS = 14 * 7; // 14 weeks × 7 days

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `EGP ${(value / 1_000).toFixed(0)}K`;
  return `EGP ${value.toFixed(0)}`;
}

function severityForDay(day: ExpiryCalendarDay | undefined): number {
  if (!day) return 0;
  const fromLevel = SEVERITY_BY_ALERT[day.alert_level as keyof typeof SEVERITY_BY_ALERT];
  if (fromLevel != null) return Math.min(5, fromLevel + (day.batch_count > 0 ? 0 : -1));
  // Fallback: bucket by batch_count.
  if (day.batch_count >= 5) return 5;
  if (day.batch_count >= 3) return 4;
  if (day.batch_count >= 2) return 2;
  if (day.batch_count >= 1) return 1;
  return 0;
}

export function ExpiryHeatmap({ calendar, exposure, loading }: ExpiryHeatmapProps) {
  const { cells, totalEgp, totalBatches } = useMemo(() => {
    const dayByOffset = new Map<number, ExpiryCalendarDay>();
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    (calendar ?? []).forEach((d) => {
      const dt = new Date(d.date);
      dt.setHours(0, 0, 0, 0);
      const diffDays = Math.floor((dt.getTime() - today.getTime()) / 86_400_000);
      if (diffDays >= 0 && diffDays < CELLS) {
        dayByOffset.set(diffDays, d);
      }
    });
    const out: Array<{ severity: number; label: string }> = [];
    for (let i = 0; i < CELLS; i++) {
      const d = dayByOffset.get(i);
      const severity = severityForDay(d);
      const date = new Date(today.getTime() + i * 86_400_000);
      const label = d
        ? `${date.toISOString().slice(0, 10)} · ${d.batch_count} batch${d.batch_count === 1 ? "" : "es"} · severity ${severity}`
        : `${date.toISOString().slice(0, 10)} · no batches`;
      out.push({ severity, label });
    }
    const total = (exposure ?? []).reduce((acc, t) => acc + t.total_egp, 0);
    const batches = (exposure ?? []).reduce((acc, t) => acc + t.batch_count, 0);
    return { cells: out, totalEgp: total, totalBatches: batches };
  }, [calendar, exposure]);

  return (
    <div className="rounded-[14px] bg-card border border-border/40 p-6">
      <header className="flex items-center gap-3 mb-2">
        <h3 className="text-[15px] font-semibold">Expiry calendar</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">next 14 weeks</span>
      </header>
      <p className="text-[12.5px] text-ink-secondary mb-3">
        <b className="text-ink-primary">{formatEgp(totalEgp)}</b> exposure across{" "}
        <b className="text-ink-primary">{totalBatches} batch{totalBatches === 1 ? "" : "es"}</b>.
        Quarantine flow is active.
      </p>

      {loading ? (
        <div className="h-28 bg-elevated/30 rounded animate-pulse" aria-busy="true" />
      ) : (
        <div
          className="grid gap-1"
          style={{ gridTemplateColumns: "repeat(14, minmax(0, 1fr))" }}
          role="grid"
          aria-label="Expiry severity calendar, 14 weeks × 7 days"
        >
          {cells.map((c, i) => (
            <div
              key={i}
              role="gridcell"
              className="aspect-square rounded-[3px]"
              style={{ background: PALETTE[Math.min(c.severity, PALETTE.length - 1)] }}
              title={c.label}
              aria-label={c.label}
            />
          ))}
        </div>
      )}

      <div className="flex items-center gap-1.5 mt-3 text-[11px] text-ink-tertiary" aria-hidden>
        <span>Low</span>
        {PALETTE.slice(1).map((p, i) => (
          <span key={i} className="w-3 h-3 rounded-[2px]" style={{ background: p }} />
        ))}
        <span>High</span>
      </div>

      <div className="mt-4 pt-3 border-t border-border/35 flex flex-col gap-2.5">
        {(exposure ?? []).map((tier) => (
          <div key={tier.tier} className="flex justify-between text-[12.5px]">
            <span className="text-ink-secondary">{tier.label}</span>
            <span className={`tabular-nums font-semibold ${TIER_CLS[tier.tone]}`}>
              {formatEgp(tier.total_egp)} · {tier.batch_count} batch{tier.batch_count === 1 ? "" : "es"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
