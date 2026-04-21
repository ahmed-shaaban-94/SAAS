"use client";

import type { RankingItem } from "@/types/api";

interface BranchListProps {
  data?: RankingItem[];
  loading?: boolean;
  limit?: number;
}

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `EGP ${(value / 1_000).toFixed(0)}K`;
  return `EGP ${value.toFixed(0)}`;
}

export function BranchList({ data = [], loading, limit = 6 }: BranchListProps) {
  const rows = data.slice(0, limit);

  return (
    <div className="rounded-[14px] bg-card border border-border/40 p-6">
      <header className="flex items-center gap-3 mb-3">
        <h3 className="text-[15px] font-semibold">Top branches</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">by revenue · MTD</span>
      </header>

      {loading ? (
        <div className="h-48 bg-elevated/30 rounded animate-pulse" aria-busy="true" />
      ) : rows.length === 0 ? (
        <p className="text-sm text-ink-tertiary py-4">No branch data.</p>
      ) : (
        <ul className="flex flex-col" aria-label="Top branches by revenue">
          {rows.map((branch) => {
            const rank = branch.rank;
            const staff = branch.staff_count ?? null;
            return (
              <li
                key={`${branch.name}-${rank}`}
                className="flex items-center gap-3 py-2.5 border-t first:border-t-0 border-border/30"
              >
                <div
                  className={[
                    "w-8 h-8 rounded-lg grid place-items-center font-mono text-[12px] font-bold tabular-nums",
                    rank === 1
                      ? "bg-chart-amber/20 text-chart-amber"
                      : "bg-elevated text-ink-secondary",
                  ].join(" ")}
                  aria-hidden
                >
                  {String(rank).padStart(2, "0")}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-[13.5px] truncate">{branch.name}</div>
                  <div className="text-[11.5px] text-ink-tertiary truncate">
                    {staff != null
                      ? `${staff} staff · ${branch.pct_of_total.toFixed(0)}% of total`
                      : `${branch.pct_of_total.toFixed(0)}% of total`}
                  </div>
                </div>
                <div className="tabular-nums font-semibold text-[13px]">
                  {formatEgp(branch.value)}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
