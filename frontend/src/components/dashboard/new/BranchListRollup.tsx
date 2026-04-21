"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { BranchRollupRow } from "@/lib/branch-rollup";

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `EGP ${(value / 1_000).toFixed(0)}K`;
  return `EGP ${value.toFixed(0)}`;
}

export function BranchListRollup({
  rows,
  loading,
}: {
  rows: BranchRollupRow[];
  loading: boolean;
}) {
  if (loading) {
    return (
      <section
        aria-label="Branches"
        className="rounded-[14px] bg-card border border-border/40 h-[360px] animate-pulse"
      />
    );
  }

  const sorted = [...rows].sort((a, b) => b.revenue - a.revenue);

  return (
    <section
      aria-label="Branches"
      className="rounded-[14px] bg-card border border-border/40 p-4 h-[360px] flex flex-col"
    >
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-ink-primary">Branches</h2>
        <Link
          href="/sites"
          className="text-xs text-accent-strong inline-flex items-center gap-1 hover:underline"
        >
          <ArrowUpRight className="w-3 h-3" aria-hidden />
          All
        </Link>
      </div>
      <ul className="flex-1 overflow-y-auto">
        {sorted.map((r) => (
          <li
            key={r.key}
            className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-3 py-1.5
                       text-sm text-ink-primary border-b border-border/20 last:border-0"
          >
            <Link
              href={`/sites/${r.key}`}
              className="truncate hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 rounded"
            >
              {r.name}
            </Link>
            <span className="text-xs text-ink-secondary font-mono">{formatEgp(r.revenue)}</span>
            <span
              className={`text-xs font-mono ${r.riskCount > 0 ? "text-amber-400" : "text-ink-secondary"}`}
              aria-label={`${r.riskCount} stock risk items`}
            >
              {r.riskCount}⚠
            </span>
            <span
              className={`text-xs font-mono ${r.expiryExposureEgp > 0 ? "text-red-400" : "text-ink-secondary"}`}
              aria-label={`${formatEgp(r.expiryExposureEgp)} expiry exposure`}
            >
              {formatEgp(r.expiryExposureEgp)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
