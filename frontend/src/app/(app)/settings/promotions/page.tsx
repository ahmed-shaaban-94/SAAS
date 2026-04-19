"use client";

import Link from "next/link";
import { useState } from "react";
import { usePromotions } from "@/hooks/use-promotions";
import type { PromotionStatus } from "@/types/promotions";

const STATUSES: Array<{ value: PromotionStatus | "all"; label: string }> = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "paused", label: "Paused" },
  { value: "expired", label: "Expired" },
];

const STATUS_PILL: Record<PromotionStatus, string> = {
  active: "bg-green-500/20 text-green-400 border-green-500/30",
  paused: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  expired: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};

function formatValue(type: "amount" | "percent", value: number): string {
  return type === "percent" ? `${value}%` : `EGP ${value.toFixed(2)}`;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function PromotionsPage() {
  const [statusFilter, setStatusFilter] = useState<PromotionStatus | "all">("all");
  const { data, error, isLoading } = usePromotions(
    statusFilter === "all" ? undefined : { status: statusFilter },
  );

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Promotions</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Seasonal discount campaigns that cashiers can apply at checkout.
          </p>
        </div>
        <Link
          href="/settings/promotions/new"
          className="px-4 py-2 rounded-md bg-accent text-white hover:opacity-90 transition"
        >
          New promotion
        </Link>
      </div>

      <div className="flex gap-2 mb-4" role="tablist" aria-label="Filter by status">
        {STATUSES.map((s) => (
          <button
            key={s.value}
            role="tab"
            aria-selected={statusFilter === s.value}
            onClick={() => setStatusFilter(s.value)}
            className={`px-3 py-1.5 text-sm rounded-md border transition ${
              statusFilter === s.value
                ? "bg-accent/20 border-accent text-accent"
                : "border-zinc-700 text-zinc-400 hover:border-zinc-500"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="text-sm text-zinc-400" role="status">
          Loading promotions…
        </div>
      )}

      {error && (
        <div className="text-sm text-red-400" role="alert">
          Failed to load promotions. Please try again.
        </div>
      )}

      {!isLoading && !error && data.length === 0 && (
        <div className="border border-dashed border-zinc-700 rounded-md p-10 text-center">
          <p className="text-zinc-300 font-medium">No promotions yet</p>
          <p className="text-sm text-zinc-500 mt-1">
            Create your first campaign to start offering targeted discounts.
          </p>
          <Link
            href="/settings/promotions/new"
            className="inline-block mt-4 px-4 py-2 rounded-md bg-accent text-white hover:opacity-90 transition"
          >
            New promotion
          </Link>
        </div>
      )}

      {!isLoading && !error && data.length > 0 && (
        <div className="overflow-x-auto border border-zinc-800 rounded-md">
          <table className="w-full text-sm">
            <thead className="bg-zinc-900 text-zinc-400">
              <tr>
                <th className="text-left px-4 py-2">Name</th>
                <th className="text-left px-4 py-2">Type</th>
                <th className="text-right px-4 py-2">Value</th>
                <th className="text-left px-4 py-2">Scope</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="text-right px-4 py-2">Used</th>
                <th className="text-left px-4 py-2">Starts</th>
                <th className="text-left px-4 py-2">Ends</th>
                <th className="text-left px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {data.map((p) => (
                <tr key={p.id} className="border-t border-zinc-800">
                  <td className="px-4 py-2 font-medium">{p.name}</td>
                  <td className="px-4 py-2 capitalize">{p.discount_type}</td>
                  <td className="px-4 py-2 text-right">
                    {formatValue(p.discount_type, p.value)}
                  </td>
                  <td className="px-4 py-2 capitalize">{p.scope}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs border ${STATUS_PILL[p.status]}`}
                    >
                      {p.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">{p.usage_count}</td>
                  <td className="px-4 py-2">{formatDate(p.starts_at)}</td>
                  <td className="px-4 py-2">{formatDate(p.ends_at)}</td>
                  <td className="px-4 py-2">
                    <Link
                      href={`/settings/promotions/${p.id}`}
                      className="text-accent hover:underline"
                    >
                      Edit
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
