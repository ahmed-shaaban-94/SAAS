"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ReorderAlert } from "@/types/inventory";

type Status = "critical" | "low" | "healthy";

interface InventoryTableProps {
  data?: ReorderAlert[];
  loading?: boolean;
  branches?: string[];
}

const PILL_CLS: Record<Status, string> = {
  critical: "bg-growth-red/15 text-growth-red",
  low: "bg-chart-amber/15 text-chart-amber",
  healthy: "bg-growth-green/15 text-growth-green",
};

const DOS_TONE_CLS: Record<Status, string> = {
  critical: "text-growth-red",
  low: "text-chart-amber",
  healthy: "text-growth-green",
};

function toStatus(alert: ReorderAlert): Status {
  // Backend (#507) returns a derived status tier — prefer it.
  if (alert.status) return alert.status;
  if (alert.risk_level === "stockout" || alert.risk_level === "critical") return "critical";
  if (alert.risk_level === "at_risk") return "low";
  return "healthy";
}

export function InventoryTable({ data = [], loading, branches = [] }: InventoryTableProps) {
  const [filter, setFilter] = useState<string>("All branches");
  const allFilters = useMemo(() => ["All branches", ...branches], [branches]);

  const rows = useMemo(() => {
    const filtered =
      filter === "All branches"
        ? data
        : data.filter((r) => r.site_name === filter || r.site_code === filter);
    return [...filtered].sort((a, b) => {
      const ao = a.days_of_stock ?? Infinity;
      const bo = b.days_of_stock ?? Infinity;
      return ao - bo;
    });
  }, [data, filter]);

  return (
    <div className="rounded-[14px] bg-card border border-border/40 p-6">
      <header className="flex flex-wrap items-center gap-3 mb-3">
        <h3 className="text-[15px] font-semibold">Inventory — reorder watchlist</h3>
        <span className="font-mono text-[11px] text-ink-tertiary">sorted by days-of-stock</span>
        {allFilters.length > 1 && (
          <div className="ml-auto flex gap-1 flex-wrap">
            {allFilters.map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={[
                  "px-2.5 py-1 rounded-full text-[12px] border transition",
                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
                  filter === f
                    ? "bg-accent/15 text-accent-strong border-accent/40"
                    : "bg-transparent text-ink-secondary border-border/40 hover:text-ink-primary",
                ].join(" ")}
              >
                {f}
              </button>
            ))}
          </div>
        )}
      </header>

      {loading ? (
        <div className="h-48 bg-elevated/30 rounded animate-pulse" aria-busy="true" />
      ) : rows.length === 0 ? (
        <p className="text-sm text-ink-tertiary py-6 text-center">
          No reorder alerts — inventory is healthy.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-[11px] uppercase tracking-wider text-ink-tertiary">
                <th className="text-left font-medium py-2">Product</th>
                <th className="text-left font-medium py-2">SKU</th>
                <th className="text-right font-medium py-2">On-hand</th>
                <th className="text-right font-medium py-2">Days of stock</th>
                <th className="text-right font-medium py-2">Velocity</th>
                <th className="text-left font-medium py-2">Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const status = toStatus(row);
                const dos = row.days_of_stock;
                const velocity = row.velocity ?? null;
                return (
                  <tr key={`${row.product_key}-${row.site_code}`} className="border-t border-border/30">
                    <td className="py-3 font-medium">{row.drug_name}</td>
                    <td className="py-3 font-mono text-ink-tertiary">{row.drug_code}</td>
                    <td className="py-3 tabular-nums text-right">{row.current_quantity}</td>
                    <td className={`py-3 tabular-nums text-right font-semibold ${DOS_TONE_CLS[status]}`}>
                      {dos != null ? `${dos.toFixed(1)}d` : "—"}
                    </td>
                    <td className="py-3 tabular-nums text-right">
                      {velocity != null ? `${velocity.toFixed(0)} / day` : "—"}
                    </td>
                    <td className="py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider ${PILL_CLS[status]}`}
                      >
                        {status === "critical"
                          ? "Critical"
                          : status === "low"
                            ? "Low"
                            : "Healthy"}
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      {status === "healthy" ? (
                        <Link
                          href={`/inventory?sku=${encodeURIComponent(row.drug_code)}`}
                          className="text-ink-tertiary text-[12.5px] hover:underline"
                        >
                          Watch
                        </Link>
                      ) : (
                        <Link
                          href={`/purchase-orders/new?sku=${encodeURIComponent(row.drug_code)}`}
                          className="text-accent-strong text-[12.5px] font-semibold hover:underline"
                        >
                          Reorder →
                        </Link>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
