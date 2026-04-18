"use client";

/**
 * Burning Cash — expiry risk visualised as a row of columns that shift
 * green → amber → red as they approach expiry. The red columns carry a
 * flickering flame on top ("morbid. unforgettable. effective." — the
 * landing copy promise).
 *
 * Each column represents a bucket of inventory grouped by days-to-expiry.
 */

interface ExpiryBucket {
  label: string;     // "0-30d", "30-60d", etc.
  valueEGP: number;
  tier: "green" | "amber" | "red";
}

const MOCK_BUCKETS: ExpiryBucket[] = [
  { label: ">180d", valueEGP: 1_240_000, tier: "green" },
  { label: "120-180d", valueEGP: 820_000, tier: "green" },
  { label: "90-120d", valueEGP: 514_000, tier: "amber" },
  { label: "60-90d", valueEGP: 342_000, tier: "amber" },
  { label: "30-60d", valueEGP: 186_000, tier: "red" },
  { label: "0-30d", valueEGP: 94_000, tier: "red" },
  { label: "expired", valueEGP: 22_000, tier: "amber" },
];

function fmtEGP(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
}

export function BurningCash() {
  const max = Math.max(...MOCK_BUCKETS.map((b) => b.valueEGP));
  const totalAtRisk = MOCK_BUCKETS
    .filter((b) => b.tier === "red")
    .reduce((s, b) => s + b.valueEGP, 0);

  return (
    <div className="viz-panel w-span-6">
      <div className="widget-head">
        <span className="tag">07 · BURNING CASH</span>
        <h3>Expiry risk, in a language everyone remembers.</h3>
      </div>

      <div style={{ fontSize: 13, color: "var(--ink-2)", marginBottom: 12 }}>
        You have{" "}
        <span style={{ color: "var(--red)", fontWeight: 600, borderBottom: "1px solid rgba(255,123,123,0.4)" }}>
          EGP {fmtEGP(totalAtRisk)} of expiry exposure
        </span>{" "}
        in the next 60 days. One decision this morning covers it.
      </div>

      <div className="burn-stage">
        {MOCK_BUCKETS.map((b) => {
          const heightPct = Math.max(8, (b.valueEGP / max) * 100);
          return (
            <div key={b.label} className="burn-col">
              <div className={`burn-bar ${b.tier}`} style={{ height: `${heightPct}%` }} />
              <div className="burn-label">{b.label}</div>
              <div className="burn-value">EGP {fmtEGP(b.valueEGP)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
