"use client";

import Link from "next/link";
import { useState } from "react";
import { useVouchers } from "@/hooks/use-vouchers";
import type { VoucherStatus } from "@/types/vouchers";

const STATUSES: Array<{ value: VoucherStatus | "all"; label: string }> = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "redeemed", label: "Redeemed" },
  { value: "expired", label: "Expired" },
  { value: "void", label: "Void" },
];

const STATUS_PILL: Record<VoucherStatus, string> = {
  active: "bg-green-500/20 text-green-400 border-green-500/30",
  redeemed: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  expired: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
  void: "bg-red-500/20 text-red-400 border-red-500/30",
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

export default function VouchersPage() {
  const [statusFilter, setStatusFilter] = useState<VoucherStatus | "all">("all");
  const { data, error, isLoading } = useVouchers(
    statusFilter === "all" ? undefined : { status: statusFilter },
  );

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Vouchers</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Create and manage redeemable discount codes for your POS.
          </p>
        </div>
        <Link
          href="/settings/vouchers/new"
          className="px-4 py-2 rounded-md bg-accent text-white hover:opacity-90 transition"
        >
          New voucher
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
          Loading vouchers…
        </div>
      )}

      {error && (
        <div className="text-sm text-red-400" role="alert">
          Failed to load vouchers. Please try again.
        </div>
      )}

      {!isLoading && !error && data.length === 0 && (
        <div className="border border-dashed border-zinc-700 rounded-md p-10 text-center">
          <p className="text-zinc-300 font-medium">No vouchers yet</p>
          <p className="text-sm text-zinc-500 mt-1">
            Create your first discount code to get started.
          </p>
          <Link
            href="/settings/vouchers/new"
            className="inline-block mt-4 px-4 py-2 rounded-md bg-accent text-white hover:opacity-90 transition"
          >
            New voucher
          </Link>
        </div>
      )}

      {!isLoading && !error && data.length > 0 && (
        <div className="overflow-x-auto border border-zinc-800 rounded-md">
          <table className="w-full text-sm">
            <thead className="bg-zinc-900 text-zinc-400">
              <tr>
                <th className="text-left px-4 py-2">Code</th>
                <th className="text-left px-4 py-2">Type</th>
                <th className="text-right px-4 py-2">Value</th>
                <th className="text-right px-4 py-2">Uses</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="text-left px-4 py-2">Starts</th>
                <th className="text-left px-4 py-2">Ends</th>
                <th className="text-left px-4 py-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {data.map((v) => (
                <tr key={v.id} className="border-t border-zinc-800">
                  <td className="px-4 py-2 font-mono">{v.code}</td>
                  <td className="px-4 py-2 capitalize">{v.discount_type}</td>
                  <td className="px-4 py-2 text-right">
                    {formatValue(v.discount_type, v.value)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {v.uses} / {v.max_uses}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs border ${STATUS_PILL[v.status]}`}
                    >
                      {v.status}
                    </span>
                  </td>
                  <td className="px-4 py-2">{formatDate(v.starts_at)}</td>
                  <td className="px-4 py-2">{formatDate(v.ends_at)}</td>
                  <td className="px-4 py-2">{formatDate(v.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
