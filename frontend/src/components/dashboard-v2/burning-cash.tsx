"use client";

/**
 * Burning Cash — expiry risk visualised as green → amber → red columns.
 * Red columns carry a flickering flame animation.
 *
 * Real data: aggregates useExpirySummary() across all sites and maps:
 *   - caution_count   → green bucket (90d+)
 *   - warning_count   → amber bucket (60-90d)
 *   - critical_count  → red bucket (30-60d)
 *   - expired_count   → red bucket (< 30d / expired)
 *
 * The server currently returns *counts* per bucket; value-per-bucket
 * will come from a later endpoint extension. For now we use
 * total_expired_value as the red-bucket value and scale the others from
 * count ratios — still useful for eyeballing relative risk.
 */

import { useMemo } from "react";
import { useExpirySummary } from "@/hooks/use-expiry-summary";

interface ExpiryBucket {
  label: string;
  valueEGP: number;
  tier: "green" | "amber" | "red";
  count: number;
}

function fmtEGP(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
}

const MOCK_BUCKETS: ExpiryBucket[] = [
  { label: ">180d", valueEGP: 1_240_000, tier: "green", count: 820 },
  { label: "90-180d", valueEGP: 820_000, tier: "green", count: 540 },
  { label: "60-90d", valueEGP: 514_000, tier: "amber", count: 320 },
  { label: "30-60d", valueEGP: 342_000, tier: "amber", count: 210 },
  { label: "< 30d", valueEGP: 186_000, tier: "red", count: 118 },
  { label: "expired", valueEGP: 22_000, tier: "red", count: 14 },
];

export function BurningCash() {
  const { data, isLoading, error } = useExpirySummary();

  const { buckets, usingMock } = useMemo(() => {
    if (!data || data.length === 0) {
      return { buckets: MOCK_BUCKETS, usingMock: true };
    }
    // Aggregate across sites.
    const agg = data.reduce(
      (acc, row) => {
        acc.caution += row.caution_count;
        acc.warning += row.warning_count;
        acc.critical += row.critical_count;
        acc.expired += row.expired_count;
        acc.expiredValue += row.total_expired_value;
        return acc;
      },
      { caution: 0, warning: 0, critical: 0, expired: 0, expiredValue: 0 },
    );

    // Derive per-bucket values. Assume expired value scales ~ count for
    // the red/amber buckets (rough — replaced when backend exposes per-
    // bucket value).
    const totalCountsRed = agg.expired + agg.critical;
    const perUnit = totalCountsRed > 0 ? agg.expiredValue / totalCountsRed : 0;

    const built: ExpiryBucket[] = [
      { label: ">180d", valueEGP: 0, tier: "green", count: 0 },
      { label: "90-180d", valueEGP: 0, tier: "green", count: agg.caution },
      { label: "60-90d", valueEGP: 0, tier: "amber", count: agg.warning },
      { label: "30-60d", valueEGP: Math.round(agg.critical * perUnit * 0.6), tier: "amber", count: agg.critical },
      { label: "< 30d", valueEGP: Math.round(agg.critical * perUnit), tier: "red", count: agg.critical },
      { label: "expired", valueEGP: Math.round(agg.expired * perUnit), tier: "red", count: agg.expired },
    ];
    return { buckets: built, usingMock: false };
  }, [data]);

  const max = Math.max(...buckets.map((b) => b.count || 1));
  const totalAtRisk = buckets
    .filter((b) => b.tier === "red")
    .reduce((s, b) => s + b.valueEGP, 0);

  return (
    <div className="viz-panel w-span-6">
      <div className="widget-head">
        <span className="tag">07 · BURNING CASH</span>
        <h3>Expiry risk, in a language everyone remembers.</h3>
        <span className="spacer" />
        {isLoading && !data && (
          <span style={{ fontSize: 12, color: "var(--ink-3)" }}>loading…</span>
        )}
        {error && (
          <span style={{ fontSize: 12, color: "var(--ink-3)" }}>offline</span>
        )}
        {usingMock && !isLoading && !error && (
          <span style={{ fontSize: 12, color: "var(--ink-3)" }}>preview data</span>
        )}
      </div>

      <div style={{ fontSize: 13, color: "var(--ink-2)", marginBottom: 12 }}>
        You have{" "}
        <span style={{ color: "var(--red)", fontWeight: 600, borderBottom: "1px solid rgba(255,123,123,0.4)" }}>
          EGP {fmtEGP(totalAtRisk)} of expiry exposure
        </span>{" "}
        in the next 30 days. One decision this morning covers it.
      </div>

      <div className="burn-stage">
        {buckets.map((b) => {
          const heightPct = Math.max(8, ((b.count || 0) / max) * 100);
          return (
            <div key={b.label} className="burn-col">
              <div className={`burn-bar ${b.tier}`} style={{ height: `${heightPct}%` }} />
              <div className="burn-label">{b.label}</div>
              <div className="burn-value">
                {b.valueEGP > 0 ? `EGP ${fmtEGP(b.valueEGP)}` : `${b.count} batches`}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
